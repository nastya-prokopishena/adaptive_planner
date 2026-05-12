
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)

    auth_provider = Column(String, default="local")
    google_id = Column(String, nullable=True)
    google_credentials = Column(Text, nullable=True)


class EventType(Base):
    __tablename__ = "event_types"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    name = Column(String(100), nullable=False)
    color = Column(String(50), nullable=True)
    is_default = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    name = Column(String(150), nullable=False)
    teacher = Column(String(150), nullable=True)
    description = Column(Text, nullable=True)
    color = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    title = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    source = Column(String, default="local")
    google_event_id = Column(String, nullable=True)

    event_type_id = Column(
        Integer,
        ForeignKey("event_types.id", ondelete="SET NULL"),
        nullable=True,
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
    )

    recurrence_type = Column(String, default="none")
    recurrence_interval = Column(Integer, default=1)
    recurrence_unit = Column(String, nullable=True)
    recurrence_days = Column(String, nullable=True)

    recurrence_end_type = Column(String, default="never")
    recurrence_end_date = Column(DateTime, nullable=True)
    recurrence_count = Column(Integer, nullable=True)

    recurrence_rule = Column(String, nullable=True)
    recurrence_excluded_dates = Column(Text, nullable=True)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(String(50), default="planned")
    priority = Column(String(50), default="medium")

    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    missed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class TaskActivityLog(Base):
    __tablename__ = "task_activity_logs"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )

    action = Column(String(100), nullable=False)

    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)

    details = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)