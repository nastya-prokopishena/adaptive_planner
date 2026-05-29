from datetime import datetime, timedelta
from types import SimpleNamespace

from backend.infrastructure.db.repositories.event_repo import EventRepository


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter_by(self, **kwargs):
        self.filter_kwargs = kwargs
        return self

    def all(self):
        return self.result


class FakeSession:
    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []
        self.events = [SimpleNamespace(id=1, user_id=10)]

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.committed = True

    def refresh(self, value):
        self.refreshed.append(value)

    def query(self, model):
        return FakeQuery(self.events)


def test_create_event(monkeypatch):
    session = FakeSession()

    monkeypatch.setattr(
        "backend.infrastructure.db.repositories.event_repo.SessionLocal",
        lambda: session,
    )

    start = datetime(2026, 5, 29, 10, 0)
    end = start + timedelta(hours=1)

    event = EventRepository().create_event(
        {
            "user_id": 10,
            "title": "Test",
            "start": start,
            "end": end,
            "google_event_id": "google-1",
        }
    )

    assert event.user_id == 10
    assert event.title == "Test"
    assert event.start_time == start
    assert event.end_time == end
    assert event.source == "google"
    assert event.google_event_id == "google-1"
    assert session.committed is True
    assert session.refreshed == [event]


def test_get_events(monkeypatch):
    session = FakeSession()

    monkeypatch.setattr(
        "backend.infrastructure.db.repositories.event_repo.SessionLocal",
        lambda: session,
    )

    result = EventRepository().get_events(user_id=10)

    assert result == session.events
