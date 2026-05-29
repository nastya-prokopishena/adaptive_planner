from types import SimpleNamespace

import pytest

from backend.app.routes import event_routes


class FakeQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model
        self.items = list(db.data.get(model, []))

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, **kwargs):
        self.items = [
            item
            for item in self.items
            if all(getattr(item, key, None) == value for key, value in kwargs.items())
        ]
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.items)

    def first(self):
        return self.items[0] if self.items else None


class FakeDB:
    def __init__(self):
        self.data = {event_routes.Event: []}
        self.deleted = []
        self.commits = 0
        self.closed = False

    def query(self, model):
        return FakeQuery(self, model)

    def add(self, item):
        collection = self.data.setdefault(type(item), [])
        if getattr(item, "id", None) is None:
            item.id = len(collection) + 1
        collection.append(item)

    def commit(self):
        self.commits += 1

    def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = 1

    def delete(self, item):
        self.deleted.append(item)
        for collection in self.data.values():
            if item in collection:
                collection.remove(item)

    def close(self):
        self.closed = True


@pytest.fixture
def fake_event_context(monkeypatch):
    db = FakeDB()
    user = SimpleNamespace(id=1, google_credentials=None)

    monkeypatch.setattr(event_routes, "current_user", lambda: user)
    monkeypatch.setattr(event_routes, "SessionLocal", lambda: db)
    monkeypatch.setattr(event_routes, "sync_google_events_to_db", lambda user, db: None)

    return db


@pytest.mark.integration
def test_event_lifecycle_create_search_update_delete(client, fake_event_context, monkeypatch):
    monkeypatch.setattr(event_routes, "has_time_conflict", lambda **kwargs: None)

    create_response = client.post(
        "/api/events",
        json={
            "title": "Лекція з архітектури",
            "start": "2026-06-01T10:00:00",
            "end": "2026-06-01T11:20:00",
        },
    )

    assert create_response.status_code == 201

    event = create_response.get_json()
    event_id = event["master_id"]

    search_response = client.get("/api/events/search?query=архітектури")

    assert search_response.status_code == 200
    assert any(item["title"] == "Лекція з архітектури" for item in search_response.get_json())

    update_response = client.put(
        f"/api/events/{event_id}",
        json={
            "title": "Оновлена лекція",
            "start": "2026-06-01T12:00:00",
            "end": "2026-06-01T13:20:00",
        },
    )

    assert update_response.status_code == 200
    assert update_response.get_json()["title"] == "Оновлена лекція"

    delete_response = client.delete(f"/api/events/{event_id}", json={})

    assert delete_response.status_code == 200
    assert delete_response.get_json()["message"] == "Event deleted"


@pytest.mark.integration
def test_create_event_rejects_time_conflict(client, fake_event_context, monkeypatch):
    monkeypatch.setattr(event_routes, "has_time_conflict", lambda **kwargs: None)

    first_response = client.post(
        "/api/events",
        json={
            "title": "Перша пара",
            "start": "2026-06-02T10:00:00",
            "end": "2026-06-02T11:00:00",
        },
    )

    assert first_response.status_code == 201

    conflict_event = fake_event_context.data[event_routes.Event][0]
    monkeypatch.setattr(event_routes, "has_time_conflict", lambda **kwargs: conflict_event)

    second_response = client.post(
        "/api/events",
        json={
            "title": "Конфліктна пара",
            "start": "2026-06-02T10:30:00",
            "end": "2026-06-02T11:30:00",
        },
    )

    assert second_response.status_code == 409
    assert second_response.get_json()["error"] == "Time conflict"


@pytest.mark.integration
def test_recurring_event_creation_returns_occurrences(client, fake_event_context, monkeypatch):
    monkeypatch.setattr(event_routes, "has_time_conflict", lambda **kwargs: None)

    response = client.post(
        "/api/events",
        json={
            "title": "Щотижнева лекція",
            "start": "2026-06-03T10:00:00",
            "end": "2026-06-03T11:00:00",
            "recurrence": {
                "type": "weekly",
                "interval": 1,
                "endType": "after",
                "count": 3,
            },
        },
    )

    assert response.status_code == 201

    events_response = client.get("/api/events")

    assert events_response.status_code == 200
    assert any(item["title"] == "Щотижнева лекція" for item in events_response.get_json())
