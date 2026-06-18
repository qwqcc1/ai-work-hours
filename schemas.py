from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional


class UserRegister(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=6)
    real_name: str = ""
    phone: str = ""


class UserLogin(BaseModel):
    username: str
    password: str
    device_type: str = "pc"
    device_name: str = ""


class ProjectCreate(BaseModel):
    name: str
    category: str  # 方舱 / 运维项目
    description: str = ""


class WorkEntryCreate(BaseModel):
    project_id: int
    hours: float = Field(..., gt=0, le=24)
    work_type: str = "日常运维"
    description: str = ""
    entry_date: date
    location: str = ""
    project_number: str = ""
    completion_status: str = ""


class WorkEntryUpdate(BaseModel):
    project_id: Optional[int] = None
    hours: Optional[float] = Field(None, gt=0, le=24)
    work_type: Optional[str] = None
    description: Optional[str] = None
    entry_date: Optional[date] = None
    location: Optional[str] = None
    project_number: Optional[str] = None
    completion_status: Optional[str] = None


class SummaryQuery(BaseModel):
    dimension: str = "日"  # 日/周/月
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    category: Optional[str] = None


class ExportQuery(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    format: str = "xlsx"


# ==================== 任务 ====================
class TaskCreate(BaseModel):
    project_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    start_time: datetime  # ISO format string from frontend
    end_time: datetime
    location: str = ""
    assignee_ids: list[int] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    status: Optional[str] = None


class TaskAssignAction(BaseModel):
    action: str = Field(..., description="accept / reject / done")
