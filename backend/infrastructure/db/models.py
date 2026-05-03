from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()
from sqlalchemy.sql import func
from backend.infrastructure.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)  # може бути null для Google-користувачів
    google_credentials = Column(JSON, nullable=True)  # зберігаємо токени
    created_at = Column(DateTime, server_default=func.now())

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    title = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    source = Column(String)
    google_event_id = Column(String)