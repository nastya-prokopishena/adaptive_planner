from backend.infrastructure.db.database import SessionLocal
from backend.infrastructure.db.models import Event

class EventRepository:

    def create_event(self, data):
        db = SessionLocal()

        event = Event(
            user_id=data["user_id"],
            title=data["title"],
            start_time=data["start"],
            end_time=data["end"],
            source="google",
            google_event_id=data.get("google_event_id")
        )

        db.add(event)
        db.commit()
        db.refresh(event)

        return event

    def get_events(self, user_id):
        db = SessionLocal()
        return db.query(Event).filter_by(user_id=user_id).all()