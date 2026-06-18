from datetime import date
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, Header, Request, Query
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import uvicorn

from models import Base, engine, SessionLocal, WorkEntry, UserSession, WorkType
from schemas import (UserRegister, UserLogin, ProjectCreate, WorkEntryCreate,
                     WorkEntryUpdate, SummaryQuery, ExportQuery,
                     TaskCreate, TaskUpdate, TaskAssignAction)
from auth import hash_password, verify_password, create_access_token, get_current_user, get_db
from crud import (create_user, get_user_by_username, get_users,
                  update_user, delete_user,
                  create_project, get_projects,
                  update_project, delete_project,
                  create_work_entry, get_work_entries, update_work_entry, delete_work_entry,
                  get_summary, create_session, get_active_sessions,
                  deactivate_session, deactivate_all_sessions,
                  create_task, get_task_by_id, get_tasks_published, get_tasks_assigned_to_user,
                  assign_task_to_users, update_task_assignment_status, delete_task,
                  get_work_types, create_work_type, update_work_type, delete_work_type)
from export_utils import export_to_excel, fill_monthly_template

app = FastAPI(title="AI工时管理系统", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")


# ==================== 页面路由 ====================
@app.get("/", response_class=HTMLResponse)
async def page_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def page_register(request: Request):
    return RedirectResponse("/")


@app.get("/dashboard", response_class=HTMLResponse)
async def page_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "today": date.today().isoformat()})


@app.get("/entry", response_class=HTMLResponse)
async def page_entry(request: Request):
    return templates.TemplateResponse("entry_form.html", {"request": request})


@app.get("/summary", response_class=HTMLResponse)
async def page_summary(request: Request):
    return templates.TemplateResponse("summary.html", {"request": request})


@app.get("/users", response_class=HTMLResponse)
async def page_users(request: Request):
    return templates.TemplateResponse("users.html", {"request": request})


@app.get("/monthly-summary", response_class=HTMLResponse)
async def page_monthly_summary(request: Request):
    return templates.TemplateResponse("monthly_summary.html", {"request": request})


@app.get("/performance", response_class=HTMLResponse)
async def page_performance(request: Request):
    return templates.TemplateResponse("performance.html", {"request": request})


@app.get("/goals", response_class=HTMLResponse)
async def page_goals(request: Request):
    return templates.TemplateResponse("goals.html", {"request": request})


@app.get("/tasks", response_class=HTMLResponse)
async def page_tasks(request: Request):
    return templates.TemplateResponse("tasks.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def page_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


# ==================== 认证 API ====================
@app.post("/api/register")
async def api_register():
    raise HTTPException(status_code=403, detail="注册已关闭，请联系管理员创建账号")


@app.post("/api/login")
async def api_login(data: UserLogin, db=Depends(get_db)):
    user = get_user_by_username(db, data.username)
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    token = create_access_token({"sub": str(user.id), "username": user.username})
    create_session(db, user.id, token, data.device_type, data.device_name)
    return {"access_token": token, "token_type": "bearer",
            "user": {"id": user.id, "username": user.username,
                     "real_name": user.real_name, "role": user.role}}


@app.post("/api/logout")
async def api_logout(authorization: str = Header(None), db=Depends(get_db)):
    token = authorization.replace("Bearer ", "") if authorization else ""
    if token:
        deactivate_session(db, token)
    return {"message": "已登出"}


@app.get("/api/me")
async def api_me(current_user=Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username,
            "real_name": current_user.real_name,
            "role": current_user.role, "phone": current_user.phone}


@app.put("/api/profile")
async def api_update_profile(body: dict, db=Depends(get_db),
                             current_user=Depends(get_current_user)):
    update_data = {}
    if body.get("real_name"):
        update_data["real_name"] = body["real_name"]
    if body.get("phone") is not None:
        update_data["phone"] = body["phone"]
    if body.get("password"):
        update_data["password_hash"] = hash_password(body["password"])
    user = update_user(db, current_user.id, **update_data) if update_data else current_user
    return {"real_name": user.real_name, "phone": user.phone}


@app.post("/api/logout-all")
async def api_logout_all(current_user=Depends(get_current_user), db=Depends(get_db)):
    deactivate_all_sessions(db, current_user.id)
    return {"message": "所有设备已登出"}


@app.get("/api/sessions")
async def api_my_sessions(current_user=Depends(get_current_user), db=Depends(get_db)):
    sessions = get_active_sessions(db, current_user.id)
    return [{"id": s.id, "device_type": s.device_type, "device_name": s.device_name,
             "ip_address": s.ip_address, "last_activity": s.last_activity.isoformat()}
            for s in sessions]


@app.post("/api/logout-device")
async def api_logout_device(body: dict, db=Depends(get_db),
                            current_user=Depends(get_current_user)):
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="缺少session_id")
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权操作")
    session.is_active = False
    db.commit()
    return {"message": "设备已登出"}


# ==================== 项目管理 API ====================
@app.get("/api/projects")
async def api_get_projects(category: Optional[str] = None,
                           db=Depends(get_db),
                           current_user=Depends(get_current_user)):
    projects = get_projects(db, category)
    return [{"id": p.id, "name": p.name, "category": p.category,
             "description": p.description} for p in projects]


@app.post("/api/projects")
async def api_create_project(data: ProjectCreate, db=Depends(get_db),
                             current_user=Depends(get_current_user)):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="仅管理员和经理可创建项目")
    project = create_project(db, data.name, data.category, data.description)
    return {"id": project.id, "name": project.name, "category": project.category}


# ==================== 工时录入 API ====================
@app.post("/api/work-entries")
async def api_create_entry(data: WorkEntryCreate, db=Depends(get_db),
                           current_user=Depends(get_current_user),
                           request: Request = None):
    device_info = request.headers.get("User-Agent", "")[:200] if request else ""
    entry = create_work_entry(db, current_user.id, data.project_id, data.hours,
                              data.work_type, data.description,
                              data.entry_date, device_info, data.location,
                              data.project_number, data.completion_status)
    return {"id": entry.id, "hours": entry.hours,
            "entry_date": str(entry.entry_date), "message": "录入成功"}


@app.get("/api/work-entries")
async def api_get_entries(project_id: Optional[int] = None,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          limit: int = 100,
                          db=Depends(get_db),
                          current_user=Depends(get_current_user)):
    uid = None if current_user.role == "admin" else current_user.id
    sd = date.fromisoformat(start_date) if start_date else None
    ed = date.fromisoformat(end_date) if end_date else None
    entries = get_work_entries(db, user_id=uid, project_id=project_id,
                               start_date=sd, end_date=ed, limit=limit)
    result = []
    for e in entries:
        result.append({
            "id": e.id, "user_id": e.user_id,
            "user_name": e.user.real_name if e.user else "",
            "project_id": e.project_id,
            "project_name": e.project.name if e.project else "",
            "project_category": e.project.category if e.project else "",
            "hours": e.hours, "work_type": e.work_type,
            "description": e.description,
            "entry_date": str(e.entry_date),
            "device_info": e.device_info,
            "location": e.location,
            "project_number": e.project_number or "",
            "completion_status": e.completion_status or "",
            "created_at": e.created_at.isoformat()
        })
    return result


@app.put("/api/work-entries/{entry_id}")
async def api_update_entry(entry_id: int, data: WorkEntryUpdate, db=Depends(get_db),
                           current_user=Depends(get_current_user)):
    existing = db.query(WorkEntry).filter(WorkEntry.id == entry_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="记录不存在")
    if existing.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权修改他人的记录")
    entry = update_work_entry(db, entry_id, project_id=data.project_id,
                              hours=data.hours, work_type=data.work_type,
                              description=data.description, entry_date=data.entry_date)
    return {"message": "更新成功"}


@app.delete("/api/work-entries/{entry_id}")
async def api_delete_entry(entry_id: int, db=Depends(get_db),
                           current_user=Depends(get_current_user)):
    existing = db.query(WorkEntry).filter(WorkEntry.id == entry_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="记录不存在")
    if existing.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权删除他人的记录")
    if not delete_work_entry(db, entry_id):
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"message": "删除成功"}


# ==================== 汇总统计 API ====================
@app.post("/api/summary")
async def api_summary(data: SummaryQuery, db=Depends(get_db),
                      current_user=Depends(get_current_user)):
    uid = None if current_user.role == "admin" else current_user.id
    result = get_summary(db, dimension=data.dimension,
                         start_date=data.start_date, end_date=data.end_date,
                         project_id=data.project_id, user_id=uid or data.user_id,
                         category=data.category)
    return result


# ==================== 导出 API ====================
@app.post("/api/export")
async def api_export(data: ExportQuery, db=Depends(get_db),
                     current_user=Depends(get_current_user)):
    from urllib.parse import quote
    output = export_to_excel(db, start_date=data.start_date, end_date=data.end_date,
                             project_id=data.project_id, user_id=data.user_id)
    filename = f"work-hours-report-{date.today().isoformat()}.xlsx"
    response = Response(content=output.getvalue(),
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Content-Disposition"] = f"attachment; filename=\"{filename}\""
    return response


class MonthlyExportRequest(BaseModel):
    month: int = None
    year: int = date.today().year


@app.post("/api/export-monthly-template")
async def api_export_monthly_template(data: MonthlyExportRequest,
                                       db=Depends(get_db),
                                       current_user=Depends(get_current_user)):
    """Export work hours in the annual template format for a given month."""
    month = data.month or date.today().month
    year = data.year
    if month < 1 or month > 12:
        return {"detail": "月份必须在 1-12 之间"}, 400
    try:
        output = fill_monthly_template(db, month=month, year=year)
    except ValueError as e:
        return {"detail": str(e)}, 400
    filename = f"{year}年{month}月工时统计.xlsx"
    from urllib.parse import quote
    response = Response(content=output.getvalue(),
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Content-Disposition"] = f"attachment; filename=\"{quote(filename)}\""
    return response


# ==================== 任务发布与接收 API ====================
@app.post("/api/tasks")
async def api_create_task(data: TaskCreate, db=Depends(get_db),
                          current_user=Depends(get_current_user)):
    task = create_task(db, publisher_id=current_user.id, project_id=data.project_id,
                       title=data.title, description=data.description,
                       start_time=data.start_time, end_time=data.end_time,
                       location=data.location)
    # 分配给指定用户
    if data.assignee_ids:
        assign_task_to_users(db, task.id, data.assignee_ids)
    return {"id": task.id, "message": "任务创建成功"}


@app.get("/api/tasks/published")
async def api_get_published_tasks(
    status: Optional[str] = None,
    db=Depends(get_db),
    current_user=Depends(get_current_user)):
    tasks = get_tasks_published(db, publisher_id=current_user.id, status=status)
    result = []
    for t in tasks:
        result.append({
            "id": t.id, "title": t.title, "description": t.description,
            "project_id": t.project_id,
            "project_name": t.project.name if t.project else "",
            "start_time": t.start_time.isoformat() if t.start_time else "",
            "end_time": t.end_time.isoformat() if t.end_time else "",
            "location": t.location,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else "",
            "assignees": [
                {"user_id": a.user_id, "user_name": a.user.real_name if a.user else str(a.user_id),
                 "status": a.status}
                for a in (t.assignments or [])
            ]
        })
    return result


@app.get("/api/tasks/received")
async def api_get_received_tasks(
    status: Optional[str] = None,
    db=Depends(get_db),
    current_user=Depends(get_current_user)):
    tasks = get_tasks_assigned_to_user(db, user_id=current_user.id, status=status)
    result = []
    for t in tasks:
        my_assignment = None
        for a in (t.assignments or []):
            if a.user_id == current_user.id:
                my_assignment = a
                break
        result.append({
            "id": t.id, "title": t.title, "description": t.description,
            "publisher_name": t.publisher.real_name if t.publisher else "",
            "project_name": t.project.name if t.project else "",
            "start_time": t.start_time.isoformat() if t.start_time else "",
            "end_time": t.end_time.isoformat() if t.end_time else "",
            "location": t.location,
            "task_status": t.status,
            "assignment_status": my_assignment.status if my_assignment else "pending",
            "created_at": t.created_at.isoformat() if t.created_at else "",
        })
    return result


@app.get("/api/users/simple")
async def api_get_simple_users(db=Depends(get_db), current_user=Depends(get_current_user)):
    """获取用户列表（用于任务分配选择）"""
    users = get_users(db)
    return [{"id": u.id, "real_name": u.real_name, "username": u.username} for u in users]


@app.put("/api/tasks/{task_id}/assign")
async def api_task_assign_action(task_id: int, data: TaskAssignAction,
                                 db=Depends(get_db),
                                 current_user=Depends(get_current_user)):
    """用户对分配的任务执行操作：接受/拒绝/完成"""
    if data.action not in ("accept", "reject", "done"):
        raise HTTPException(status_code=400, detail="无效操作，仅支持 accept/reject/done")
    assignment = update_task_assignment_status(db, task_id, current_user.id, data.action)
    if not assignment:
        raise HTTPException(status_code=404, detail="任务不存在或未分配给你")
    action_map = {"accept": "已接收", "reject": "已拒绝", "done": "已完成"}
    return {"message": action_map[data.action]}


@app.delete("/api/tasks/{task_id}")
async def api_delete_task(task_id: int, db=Depends(get_db),
                          current_user=Depends(get_current_user)):
    task = get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.publisher_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只能删除自己发布的任务")
    delete_task(db, task_id)
    return {"message": "任务已取消"}


# ==================== 管理员 API ====================
@app.get("/api/admin/users")
async def api_admin_users(db=Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可查看")
    users = get_users(db)
    return [{"id": u.id, "username": u.username, "real_name": u.real_name,
             "role": u.role, "phone": u.phone, "is_active": u.is_active,
             "created_at": u.created_at.isoformat() if u.created_at else None}
            for u in users]


@app.post("/api/admin/users")
async def api_create_user(body: dict, db=Depends(get_db),
                           current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")
    username = (body.get("username") or "").strip()
    password = (body.get("password") or "").strip()
    real_name = (body.get("real_name") or "").strip()
    phone = body.get("phone", "") or ""
    role = body.get("role") or "member"
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if get_user_by_username(db, username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = create_user(db, username, hash_password(password), real_name,
                       phone=phone, role=role)
    return {"message": "创建成功", "user": {
        "id": user.id, "username": user.username, "real_name": user.real_name,
        "role": user.role, "phone": user.phone, "is_active": True}}


@app.put("/api/admin/users/{user_id}")
async def api_update_user(user_id: int, body: dict, db=Depends(get_db),
                          current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")
    # 密码需要哈希处理
    kwargs = {}
    for k, v in body.items():
        if v is not None and k != 'password':
            kwargs[k] = v
    if body.get('password'):
        kwargs['password_hash'] = hash_password(body['password'])
    user = update_user(db, user_id, **kwargs)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"message": "更新成功", "user": {
        "id": user.id, "username": user.username, "real_name": user.real_name,
        "role": user.role, "phone": user.phone, "is_active": user.is_active}}


@app.delete("/api/admin/users/{user_id}")
async def api_delete_user(user_id: int, db=Depends(get_db),
                          current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")
    if not delete_user(db, user_id):
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"message": "删除成功"}


@app.put("/api/admin/projects/{project_id}")
async def api_update_project(project_id: int, body: dict, db=Depends(get_db),
                              current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")
    project = update_project(db, project_id, **body)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"message": "更新成功"}


@app.delete("/api/admin/projects/{project_id}")
async def api_delete_project(project_id: int, db=Depends(get_db),
                              current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")
    if not delete_project(db, project_id):
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"message": "删除成功"}

# ==================== 工时类型 ====================
@app.get("/api/work-types")
async def api_get_work_types(db=Depends(get_db)):
    types = get_work_types(db)
    return [{"id": t.id, "name": t.name} for t in types]


@app.post("/api/admin/work-types")
async def api_create_work_type(body: dict, db=Depends(get_db),
                                current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="名称不能为空")
    wt = create_work_type(db, name)
    return {"id": wt.id, "name": wt.name}


@app.put("/api/admin/work-types/{type_id}")
async def api_update_work_type(type_id: int, body: dict, db=Depends(get_db),
                                current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="名称不能为空")
    wt = update_work_type(db, type_id, name)
    if not wt:
        raise HTTPException(status_code=404, detail="类型不存在")
    return {"id": wt.id, "name": wt.name}


@app.delete("/api/admin/work-types/{type_id}")
async def api_delete_work_type(type_id: int, db=Depends(get_db),
                                current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")
    if not delete_work_type(db, type_id):
        raise HTTPException(status_code=404, detail="类型不存在")
    return {"message": "删除成功"}


# ==================== 初始化 ====================
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    # Migrate: add new columns to existing tables (safe to run even if columns exist)
    from sqlalchemy import text
    with engine.connect() as conn:
        for col in ["project_number", "completion_status"]:
            try:
                conn.execute(text(f"ALTER TABLE work_entries ADD COLUMN {col} VARCHAR DEFAULT ''"))
                conn.commit()
            except Exception:
                pass
    db = SessionLocal()
    try:
        admin = get_user_by_username(db, "admin")
        if not admin:
            create_user(db, "admin", hash_password("admin123"), "系统管理员", role="admin")
        existing = get_projects(db)
        if not existing:
            for name in ["无人机机库", "银行电子锁", "发行基金物流管理系统"]:
                create_project(db, name, "运维项目", "")
        # 预置默认工时类型
        existing_types = get_work_types(db)
        if not existing_types:
            for name in ["日常运维", "故障处理", "巡检监控", "变更操作", "专项工作", "会议培训", "技术支持", "其他"]:
                create_work_type(db, name)
    finally:
        db.close()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
