import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.infrastructure.db.models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:31220566@localhost:5432/planner"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)