from sqlalchemy.orm import Session
from backend.infrastructure.db.database import SessionLocal
from backend.infrastructure.db.models import User

class UserRepository:
    def get_by_email(self, email: str) -> User | None:
        db = SessionLocal()
        user = db.query(User).filter(User.email == email).first()
        db.close()
        return user

    def create(self, email: str, password_hash: str = None) -> User:
        db = SessionLocal()
        user = User(email=email, password_hash=password_hash)
        db.add(user)
        db.commit()
        db.refresh(user)
        db.close()
        return user

    def update_google_credentials(self, user_id: int, credentials: dict) -> User:
        db = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.google_credentials = credentials
            db.commit()
            db.refresh(user)
        db.close()
        return user

    def get_by_id(self, user_id: int) -> User | None:
        db = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        db.close()
        return user