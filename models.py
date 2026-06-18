from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Boolean, create_engine, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    member = "member"


class ProjectCategory(str, enum.Enum):
    shelter = "方舱"
    ops = "运维项目"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    real_name = Column(String(50), nullable=False)
    role = Column(String(20), default="member")
    phone = Column(String(20), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    work_entries = relationship("WorkEntry", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    category = Column(String(20), nullable=False)
    description = Column(String(500), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    work_entries = relationship("WorkEntry", back_populates="project")


class WorkEntry(Base):
    __tablename__ = "work_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    hours = Column(Float, nullable=False)
    work_type = Column(String(50), default="日常运维", index=True)
    description = Column(String(500), default="")
    entry_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    device_info = Column(String(200), default="")
    location = Column(String(200), default="")
    project_number = Column(String(100), default="")
    completion_status = Column(String(200), default="")
    is_active = Column(Boolean, default=True, index=True)

    user = relationship("User", back_populates="work_entries")
    project = relationship("Project", back_populates="work_entries")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(500), nullable=False, index=True)
    device_type = Column(String(50), default="pc")
    device_name = Column(String(100), default="")
    ip_address = Column(String(50), default="")
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    last_activity = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="sessions")


# ==================== 任务 ====================
class TaskStatus(str, enum.Enum):
    pending = "pending"      # 待处理
    in_progress = "in_progress"  # 进行中
    completed = "completed"  # 已完成
    cancelled = "cancelled"  # 已取消


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    publisher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    location = Column(String(200), default="")
    status = Column(String(20), default="pending", index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    publisher = relationship("User", backref="published_tasks")
    project = relationship("Project")
    assignments = relationship("TaskAssignment", back_populates="task")


class AssignmentStatus(str, enum.Enum):
    pending = "pending"        # 待接收
    accepted = "accepted"      # 已接收
    rejected = "rejected"      # 已拒绝
    done = "done"              # 已完成


class TaskAssignment(Base):
    __tablename__ = "task_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), default="pending", index=True)  # pending/accepted/rejected/done
    assigned_at = Column(DateTime, default=datetime.now)
    accepted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    remark = Column(Text, default="")

    task = relationship("Task", back_populates="assignments")
    user = relationship("User", backref="received_tasks")


class WorkType(Base):
    __tablename__ = "work_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


# 数据库初始化
engine = create_engine("sqlite:///workhours.db", echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
