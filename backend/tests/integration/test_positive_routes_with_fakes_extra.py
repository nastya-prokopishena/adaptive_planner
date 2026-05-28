from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest


class FakeQuery:
    def __init__(self, items):
        self.items = list(items)

    def filter_by(self, **kwargs):
        self.items = [
            item for item in self.items
            if all(getattr(item, key, None) == value for key, value in kwargs.items())
        ]
        return self

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, value):
        self.items = self.items[:value]
        return self

    def all(self):
        return list(self.items)

    def first(self):
        return self.items[0] if self.items else None

    def count(self):
        return len(self.items)


class FakeDB:
    def __init__(self, data=None):
        self.data = data or {}
        self.added = []
        self.deleted = []
        self.commits = 0
        self.closed = False

    def query(self, model):
        return FakeQuery(self.data.get(model, []))

    def add(self, item):
        self.added.append(item)
        if getattr(item, "id", None) is None:
            item.id = len(self.added) + 100

    def flush(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = len(self.added) + 100

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass

    def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = 999

    def delete(self, item):
        self.deleted.append(item)

    def close(self):
        self.closed = True


def unwrap(result):
    if isinstance(result, tuple):
        response, status = result
        return response.get_json(), status
    return result.get_json(), result.status_code


@pytest.fixture
def fake_user():
    return SimpleNamespace(id=1, google_credentials=None)


def test_get_subjects_returns_serialized_subjects(app, monkeypatch, fake_user):
    from backend.app.routes import task_routes

    subject = SimpleNamespace(
        id=10,
        user_id=1,
        name="Архітектура ПЗ",
        teacher="Викладач",
        description="Опис",
        color="#000000",
        created_at=datetime(2026, 5, 1),
    )
    fake_db = FakeDB({task_routes.Subject: [subject]})

    monkeypatch.setattr(task_routes, "current_user", lambda: fake_user)
    monkeypatch.setattr(task_routes, "SessionLocal", lambda: fake_db)

    with app.test_request_context("/api/subjects", method="GET"):
        data, status = unwrap(task_routes.get_subjects())

    assert status == 200
    assert data[0]["name"] == "Архітектура ПЗ"
    assert fake_db.closed is True


def test_create_subject_adds_subject_and_returns_201(app, monkeypatch, fake_user):
    from backend.app.routes import task_routes

    fake_db = FakeDB()
    monkeypatch.setattr(task_routes, "current_user", lambda: fake_user)
    monkeypatch.setattr(task_routes, "SessionLocal", lambda: fake_db)

    with app.test_request_context(
        "/api/subjects",
        method="POST",
        json={"name": "Бази даних", "teacher": "Іваненко", "color": "#123456"},
    ):
        data, status = unwrap(task_routes.create_subject())

    assert status == 201
    assert data["name"] == "Бази даних"
    assert fake_db.added
    assert fake_db.commits == 1


def test_get_event_types_returns_serialized_event_types(app, monkeypatch, fake_user):
    from backend.app.routes import task_routes

    event_type = SimpleNamespace(
        id=7,
        user_id=1,
        name="Лекція",
        color="#2563eb",
        is_default=False,
        created_at=datetime(2026, 5, 1),
    )
    fake_db = FakeDB({task_routes.EventType: [event_type]})
    monkeypatch.setattr(task_routes, "current_user", lambda: fake_user)
    monkeypatch.setattr(task_routes, "SessionLocal", lambda: fake_db)

    with app.test_request_context("/api/event-types", method="GET"):
        data, status = unwrap(task_routes.get_event_types())

    assert status == 200
    assert data[0]["name"] == "Лекція"


def test_create_event_type_adds_type_and_returns_201(app, monkeypatch, fake_user):
    from backend.app.routes import task_routes

    fake_db = FakeDB()
    monkeypatch.setattr(task_routes, "current_user", lambda: fake_user)
    monkeypatch.setattr(task_routes, "SessionLocal", lambda: fake_db)

    with app.test_request_context(
        "/api/event-types",
        method="POST",
        json={"name": "Практична", "color": "#22c55e"},
    ):
        data, status = unwrap(task_routes.create_event_type())

    assert status == 201
    assert data["name"] == "Практична"
    assert fake_db.added


def test_create_local_event_successfully(app, monkeypatch, fake_user):
    from backend.app.routes import event_routes

    fake_db = FakeDB()
    monkeypatch.setattr(event_routes, "current_user", lambda: fake_user)
    monkeypatch.setattr(event_routes, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(event_routes, "has_time_conflict", lambda **kwargs: None)

    with app.test_request_context(
        "/api/events",
        method="POST",
        json={
            "title": "Лекція",
            "start": "2026-05-01T10:00:00",
            "end": "2026-05-01T11:00:00",
        },
    ):
        data, status = unwrap(event_routes.create_event_api())

    assert status == 201
    assert data["title"] == "Лекція"
    assert data["source"] == "local"
    assert fake_db.added


def test_search_events_returns_matching_local_event(app, monkeypatch, fake_user):
    from backend.app.routes import event_routes

    event = SimpleNamespace(
        id=1,
        title="Лекція з Python",
        start_time=datetime(2026, 5, 1, 10, 0),
        end_time=datetime(2026, 5, 1, 11, 0),
        source="local",
        google_event_id=None,
        recurrence_type="none",
        recurrence_interval=1,
        recurrence_unit=None,
        recurrence_days=None,
        recurrence_end_type="never",
        recurrence_end_date=None,
        recurrence_count=None,
        subject_id=None,
        user_id=1,
    )
    fake_db = FakeDB({event_routes.Event: [event]})
    monkeypatch.setattr(event_routes, "current_user", lambda: fake_user)
    monkeypatch.setattr(event_routes, "SessionLocal", lambda: fake_db)

    with app.test_request_context("/api/events/search?query=python", method="GET"):
        data, status = unwrap(event_routes.search_events_api())

    assert status == 200
    assert len(data) == 1
    assert data[0]["title"] == "Лекція з Python"


def test_analytics_dashboard_route_uses_service_result(app, monkeypatch, fake_user):
    from backend.app.routes import analytics_routes

    fake_db = FakeDB({analytics_routes.Task: [], analytics_routes.Event: []})
    monkeypatch.setattr(analytics_routes, "current_user", lambda: fake_user)
    monkeypatch.setattr(analytics_routes, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(
        analytics_routes.analytics_service,
        "build_dashboard_analytics",
        lambda tasks, events, date_from, date_to: {"summary": {"total": 0}},
    )

    with app.test_request_context("/api/analytics/dashboard", method="GET"):
        data, status = unwrap(analytics_routes.analytics_dashboard_api())

    assert status == 200
    assert data["summary"]["total"] == 0


def test_schedule_preview_json_uses_service(app, monkeypatch):
    from backend.app.routes import schedule_import_routes

    class FakeService:
        def build_preview_from_text(self, raw_text, group_name, subgroup):
            return {
                "events": [{"title": raw_text, "group": group_name, "subgroup": subgroup}],
                "total_found": 1,
            }

    monkeypatch.setattr(schedule_import_routes, "ScheduleImportService", lambda: FakeService())

    with app.test_request_context(
        "/api/schedule-import/preview",
        method="POST",
        json={"text": "Пара", "group": "ФеП-42", "subgroup": "1"},
    ):
        data, status = unwrap(schedule_import_routes.schedule_import_preview())

    assert status == 200
    assert data["total_found"] == 1
    assert data["events"][0]["group"] == "ФеП-42"
