from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
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


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    source = Column(String, default="local")
    google_event_id = Column(String, nullable=True)
    recurrence_type = Column(String, default="none")
    recurrence_interval = Column(Integer, default=1)
    recurrence_unit = Column(String, nullable=True)
    recurrence_days = Column(String, nullable=True)
    recurrence_end_type = Column(String, default="never")
    recurrence_end_date = Column(DateTime, nullable=True)
    recurrence_count = Column(Integer, nullable=True)
    recurrence_rule = Column(String, nullable=True)