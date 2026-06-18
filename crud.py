from datetime import datetime, date, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from models import User, Project, WorkEntry, UserSession, Task, TaskAssignment, SessionLocal, WorkType


# ==================== 用户 ====================
def create_user(db: Session, username: str, password_hash: str, real_name: str,
                phone: str = "", role: str = "member") -> User:
    user = User(username=username, password_hash=password_hash,
                real_name=real_name, phone=phone, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_users(db: Session) -> List[User]:
    return db.query(User).order_by(User.id).all()


# ==================== 用户管理（管理员）====================
def update_user(db: Session, user_id: int, **kwargs) -> Optional[User]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    for k, v in kwargs.items():
        if v is not None:
            setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    """软删除：将 is_active 置为 False"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    user.is_active = False
    db.commit()
    return True


# ==================== 会话 ====================
def create_session(db: Session, user_id: int, token: str, device_type: str = "pc",
                   device_name: str = "", ip_address: str = "") -> UserSession:
    session = UserSession(user_id=user_id, token=token, device_type=device_type,
                          device_name=device_name, ip_address=ip_address)
    db.add(session)
    db.commit()
    return session


def get_active_sessions(db: Session, user_id: int) -> List[UserSession]:
    return db.query(UserSession).filter(
        UserSession.user_id == user_id, UserSession.is_active == True
    ).all()


def deactivate_session(db: Session, token: str):
    session = db.query(UserSession).filter(UserSession.token == token).first()
    if session:
        session.is_active = False
        db.commit()


def deactivate_all_sessions(db: Session, user_id: int):
    db.query(UserSession).filter(
        UserSession.user_id == user_id, UserSession.is_active == True
    ).update({"is_active": False})
    db.commit()


# ==================== 项目 ====================
def create_project(db: Session, name: str, category: str, description: str = "") -> Project:
    project = Project(name=name, category=category, description=description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_projects(db: Session, category: Optional[str] = None) -> List[Project]:
    q = db.query(Project).filter(Project.is_active == True)
    if category:
        q = q.filter(Project.category == category)
    return q.order_by(Project.id).all()


# ==================== 项目管理（管理员）====================
def update_project(db: Session, project_id: int, **kwargs) -> Optional[Project]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None
    for k, v in kwargs.items():
        if v is not None:
            setattr(project, k, v)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int) -> bool:
    """软删除：将 is_active 置为 False"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return False
    project.is_active = False
    db.commit()
    return True


# ==================== 工时录入 ====================
def create_work_entry(db: Session, user_id: int, project_id: int, hours: float,
                      work_type: str, description: str, entry_date: date,
                      device_info: str = "", location: str = "",
                      project_number: str = "", completion_status: str = "") -> WorkEntry:
    entry = WorkEntry(user_id=user_id, project_id=project_id, hours=hours,
                      work_type=work_type, description=description,
                      entry_date=entry_date, device_info=device_info,
                      location=location, project_number=project_number,
                      completion_status=completion_status)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_work_entries(db: Session, user_id: Optional[int] = None,
                     project_id: Optional[int] = None,
                     start_date: Optional[date] = None,
                     end_date: Optional[date] = None,
                     limit: int = 100) -> List[WorkEntry]:
    q = db.query(WorkEntry).filter(WorkEntry.is_active == True)
    if user_id:
        q = q.filter(WorkEntry.user_id == user_id)
    if project_id:
        q = q.filter(WorkEntry.project_id == project_id)
    if start_date:
        q = q.filter(WorkEntry.entry_date >= start_date)
    if end_date:
        q = q.filter(WorkEntry.entry_date <= end_date)
    return q.order_by(WorkEntry.entry_date.desc()).limit(limit).all()


def update_work_entry(db: Session, entry_id: int, **kwargs) -> Optional[WorkEntry]:
    entry = db.query(WorkEntry).filter(WorkEntry.id == entry_id).first()
    if entry:
        for k, v in kwargs.items():
            if v is not None:
                setattr(entry, k, v)
        db.commit()
        db.refresh(entry)
    return entry


def delete_work_entry(db: Session, entry_id: int) -> bool:
    entry = db.query(WorkEntry).filter(WorkEntry.id == entry_id).first()
    if entry:
        entry.is_active = False
        db.commit()
        return True
    return False


# ==================== 汇总统计 ====================
def get_summary(db: Session, dimension: str = "日", start_date: Optional[date] = None,
                end_date: Optional[date] = None, project_id: Optional[int] = None,
                user_id: Optional[int] = None, category: Optional[str] = None) -> dict:
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    q = db.query(WorkEntry).options(
        joinedload(WorkEntry.project), joinedload(WorkEntry.user)
    ).filter(
        WorkEntry.is_active == True,
        WorkEntry.entry_date >= start_date, WorkEntry.entry_date <= end_date
    )
    if project_id:
        q = q.filter(WorkEntry.project_id == project_id)
    if user_id:
        q = q.filter(WorkEntry.user_id == user_id)

    entries = q.all()
    groups = {}
    for e in entries:
        proj_name = e.project.name if e.project else ""
        proj_category = e.project.category if e.project else ""
        if category and proj_category != category:
            continue

        if dimension == "日":
            key = str(e.entry_date)
        elif dimension == "周":
            iso = e.entry_date.isocalendar()
            key = f"{iso[0]}W{iso[1]:02d}"
        else:
            key = e.entry_date.strftime("%Y-%m")

        if key not in groups:
            groups[key] = {"total_hours": 0, "count": 0, "by_project": {}, "by_user": {}}
        groups[key]["total_hours"] += e.hours
        groups[key]["count"] += 1
        groups[key]["by_project"][proj_name] = groups[key]["by_project"].get(proj_name, 0) + e.hours
        uname = e.user.real_name if e.user else str(e.user_id)
        groups[key]["by_user"][uname] = groups[key]["by_user"].get(uname, 0) + e.hours

    items = []
    grand_total = 0
    for label in sorted(groups.keys()):
        g = groups[label]
        items.append({
            "label": label, "total_hours": round(g["total_hours"], 1),
            "entries_count": g["count"],
            "by_project": g["by_project"], "by_user": g["by_user"]
        })
        grand_total += g["total_hours"]
    return {"dimension": f"{dimension}汇总", "items": items, "grand_total_hours": round(grand_total, 1)}


# ==================== 任务 ====================
def create_task(db: Session, publisher_id: int, project_id: int, title: str,
                description: str, start_time: datetime, end_time: datetime,
                location: str = "", status: str = "pending") -> Task:
    task = Task(publisher_id=publisher_id, project_id=project_id,
                title=title, description=description,
                start_time=start_time, end_time=end_time,
                location=location, status=status)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task_by_id(db: Session, task_id: int) -> Optional[Task]:
    return db.query(Task).filter(Task.id == task_id).first()


def get_tasks_published(db: Session, publisher_id: int, status: Optional[str] = None) -> List[Task]:
    from sqlalchemy.orm import joinedload
    q = db.query(Task).options(
        joinedload(Task.project),
        joinedload(Task.assignments).joinedload(TaskAssignment.user)
    ).filter(Task.publisher_id == publisher_id)
    if status:
        q = q.filter(Task.status == status)
    return q.order_by(Task.created_at.desc()).all()


def get_tasks_assigned_to_user(db: Session, user_id: int, status: Optional[str] = None):
    """获取分配给某用户的所有任务（通过 assignment）"""
    from sqlalchemy.orm import joinedload
    q = db.query(Task).options(
        joinedload(Task.publisher),
        joinedload(Task.project),
        joinedload(Task.assignments)
    ).join(TaskAssignment).filter(
        TaskAssignment.user_id == user_id
    )
    if status:
        if status == "pending":
            q = q.filter(TaskAssignment.status == "pending")
        elif status == "accepted":
            q = q.filter(TaskAssignment.status == "accepted")
        elif status == "done":
            q = q.filter(TaskAssignment.status == "done")
    return q.order_by(Task.created_at.desc()).all()


def assign_task_to_users(db: Session, task_id: int, user_ids: List[int]):
    """将任务分配给多个用户"""
    for uid in user_ids:
        existing = db.query(TaskAssignment).filter(
            TaskAssignment.task_id == task_id, TaskAssignment.user_id == uid
        ).first()
        if not existing:
            assignment = TaskAssignment(task_id=task_id, user_id=uid, status="pending")
            db.add(assignment)
    db.commit()


def update_task_assignment_status(db: Session, task_id: int, user_id: int,
                                  new_status: str) -> Optional[TaskAssignment]:
    """更新任务分配状态：接受/拒绝/完成"""
    assignment = db.query(TaskAssignment).filter(
        TaskAssignment.task_id == task_id, TaskAssignment.user_id == user_id
    ).first()
    if not assignment:
        return None
    assignment.status = new_status
    now = datetime.now()
    if new_status == "accepted":
        assignment.accepted_at = now
    elif new_status == "done":
        assignment.completed_at = now
    db.commit()
    db.refresh(assignment)

    # 自动更新任务状态
    all_assignments = db.query(TaskAssignment).filter(TaskAssignment.task_id == task_id).all()
    accepted_count = sum(1 for a in all_assignments if a.status in ["accepted", "done"])
    done_count = sum(1 for a in all_assignments if a.status == "done")

    task = db.query(Task).filter(Task.id == task_id).first()
    if task and len(all_assignments) > 0:
        if done_count >= len(all_assignments):
            task.status = "completed"
        elif accepted_count > 0:
            task.status = "in_progress"
        db.commit()

    return assignment


def delete_task(db: Session, task_id: int) -> bool:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return False
    task.status = "cancelled"
    db.commit()
    return True


# ==================== 工时类型 ====================
def get_work_types(db: Session) -> list:
    return db.query(WorkType).filter(WorkType.is_active == True).order_by(WorkType.id).all()


def create_work_type(db: Session, name: str) -> WorkType:
    wt = WorkType(name=name)
    db.add(wt)
    db.commit()
    db.refresh(wt)
    return wt


def update_work_type(db: Session, type_id: int, name: str) -> WorkType | None:
    wt = db.query(WorkType).filter(WorkType.id == type_id).first()
    if wt:
        wt.name = name
        db.commit()
        db.refresh(wt)
    return wt


def delete_work_type(db: Session, type_id: int) -> bool:
    wt = db.query(WorkType).filter(WorkType.id == type_id).first()
    if wt:
        wt.is_active = False
        db.commit()
        return True
    return False
