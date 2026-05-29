from datetime import datetime, timedelta
from types import SimpleNamespace

from backend.app.routes import event_routes as routes


class FakeQuery:
    def __init__(self, items=None, first_item=None):
        self.items = items or []
        self.first_item = first_item

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return self.items

    def first(self):
        return self.first_item


class FakeDB:
    def __init__(self, events=None, event=None):
        self.events = events or []
        self.event = event
        self.added = []
        self.deleted = []
        self.commits = 0
        self.closed = False

    def query(self, model):
        return FakeQuery(self.events, self.event or (self.events[0] if self.events else None))

    def add(self, item):
        if getattr(item, "id", None) is None:
            item.id = 50
        self.added.append(item)

    def delete(self, item):
        self.deleted.append(item)

    def commit(self):
        self.commits += 1

    def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = 50

    def close(self):
        self.closed = True


def patch_user_and_db(monkeypatch, db, user=None):
    monkeypatch.setattr(
        routes,
        "current_user",
        lambda: user or SimpleNamespace(id=1, google_credentials=None),
    )
    monkeypatch.setattr(routes, "SessionLocal", lambda: db)
    monkeypatch.setattr(routes, "sync_google_events_to_db", lambda user, db: None)


def make_event(recurrence_type="none"):
    start = datetime(2026, 5, 29, 10, 0)
    return SimpleNamespace(
        id=1,
        user_id=1,
        title="Event",
        start_time=start,
        end_time=start + timedelta(hours=1),
        source="local",
        google_event_id=None,
        event_type_id=None,
        subject_id=None,
        recurrence_type=recurrence_type,
        recurrence_interval=1,
        recurrence_unit=None,
        recurrence_days=None,
        recurrence_end_type="never",
        recurrence_end_date=None,
        recurrence_count=None,
        recurrence_rule=None,
        recurrence_excluded_dates=None,
    )


def test_get_events_serializes_recurring_and_regular_events(app, monkeypatch):
    recurring = make_event("weekly")
    regular = make_event("none")
    regular.id = 2
    db = FakeDB(events=[recurring, regular])
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(
        routes,
        "get_event_occurrences",
        lambda event: [
            (event.start_time, event.end_time),
            (event.start_time + timedelta(days=7), event.end_time + timedelta(days=7)),
        ],
    )
    monkeypatch.setattr(
        routes,
        "serialize_event",
        lambda event, occurrence_start=None, occurrence_end=None: {
            "id": event.id,
            "start": (occurrence_start or event.start_time).isoformat(),
        },
    )

    with app.test_request_context("/api/events"):
        response = routes.get_events()

    assert len(response.get_json()) == 3


def test_create_event_api_requires_fields(app, monkeypatch):
    monkeypatch.setattr(routes, "current_user", lambda: SimpleNamespace(id=1))

    with app.test_request_context("/api/events", method="POST", json={"title": "Only title"}):
        response, status = routes.create_event_api()

    assert status == 400


def test_create_event_api_rejects_invalid_datetime(app, monkeypatch):
    monkeypatch.setattr(routes, "current_user", lambda: SimpleNamespace(id=1))

    with app.test_request_context(
        "/api/events",
        method="POST",
        json={"title": "Event", "start": "bad", "end": "bad"},
    ):
        response, status = routes.create_event_api()

    assert status == 400


def test_create_event_api_detects_conflict(app, monkeypatch):
    db = FakeDB()
    patch_user_and_db(monkeypatch, db)
    conflict = make_event()
    monkeypatch.setattr(routes, "has_time_conflict", lambda **kwargs: conflict)
    monkeypatch.setattr(routes, "serialize_event", lambda event: {"id": event.id})

    with app.test_request_context(
        "/api/events",
        method="POST",
        json={
            "title": "Event",
            "start": "2026-05-29T10:00:00",
            "end": "2026-05-29T11:00:00",
        },
    ):
        response, status = routes.create_event_api()

    assert status == 409


def test_create_event_api_success(app, monkeypatch):
    db = FakeDB()
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(routes, "has_time_conflict", lambda **kwargs: None)
    monkeypatch.setattr(
        routes, "serialize_event", lambda event: {"id": event.id, "title": event.title}
    )

    with app.test_request_context(
        "/api/events",
        method="POST",
        json={
            "title": "Event",
            "start": "2026-05-29T10:00:00",
            "end": "2026-05-29T11:00:00",
        },
    ):
        response, status = routes.create_event_api()

    assert status == 201
    assert response.get_json()["title"] == "Event"


def test_update_event_api_not_found(app, monkeypatch):
    db = FakeDB(event=None)
    patch_user_and_db(monkeypatch, db)

    with app.test_request_context("/api/events/999", method="PUT", json={}):
        response, status = routes.update_event_api(999)

    assert status == 404


def test_update_event_api_success(app, monkeypatch):
    event = make_event()
    db = FakeDB(event=event)
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(routes, "has_time_conflict", lambda **kwargs: None)
    monkeypatch.setattr(
        routes, "serialize_event", lambda event: {"id": event.id, "title": event.title}
    )

    with app.test_request_context(
        "/api/events/1",
        method="PUT",
        json={"title": "Updated", "start": "2026-05-29T12:00:00", "end": "2026-05-29T13:00:00"},
    ):
        response = routes.update_event_api(1)

    assert response.get_json()["title"] == "Updated"


def test_delete_event_api_non_recurring_success(app, monkeypatch):
    event = make_event("none")
    db = FakeDB(event=event)
    patch_user_and_db(monkeypatch, db)

    with app.test_request_context("/api/events/1", method="DELETE", json={}):
        response = routes.delete_event_api(1)

    assert response.get_json()["message"] == "Event deleted"
    assert db.deleted == [event]


def test_delete_recurring_single_occurrence_requires_start(app, monkeypatch):
    event = make_event("weekly")
    db = FakeDB(event=event)
    patch_user_and_db(monkeypatch, db)

    with app.test_request_context("/api/events/1", method="DELETE", json={"scope": "this"}):
        response, status = routes.delete_event_api(1)

    assert status == 400


def test_delete_recurring_future_success(app, monkeypatch):
    event = make_event("weekly")
    db = FakeDB(event=event)
    patch_user_and_db(monkeypatch, db)

    with app.test_request_context(
        "/api/events/1",
        method="DELETE",
        json={"scope": "future", "occurrence_start": "2026-06-01T10:00:00"},
    ):
        response = routes.delete_event_api(1)

    assert response.get_json()["scope"] == "future"
    assert event.recurrence_end_type == "on"


def test_search_events_filters_by_query(app, monkeypatch):
    match = make_event("none")
    match.title = "Physics"
    other = make_event("none")
    other.id = 2
    other.title = "Math"
    db = FakeDB(events=[match, other])
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(
        routes, "serialize_event", lambda event: {"id": event.id, "title": event.title}
    )

    with app.test_request_context("/api/events/search?query=phys"):
        response = routes.search_events_api()

    data = response.get_json()
    assert len(data) == 1
    assert data[0]["title"] == "Physics"
