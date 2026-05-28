import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from backend.application.analytics_service import AnalyticsService
from backend.infrastructure.google_calendar_adapter import GoogleCalendarAdapter
from backend.infrastructure.ml.deadline_model_adapter import DeadlineModelAdapter
from backend.infrastructure.ml.model_registry import ModelRegistry


def test_analytics_service_builds_summary_weekly_load_and_distribution(monkeypatch):
    service = AnalyticsService()
    monkeypatch.setattr(
        service.productivity_service,
        "build_daily_dataset",
        lambda tasks, events: [{"date": "2026-05-01", "score": 0.8}],
    )

    base = datetime(2026, 5, 1, 10, 0)
    tasks = [
        SimpleNamespace(status="done", due_date=base, created_at=base, difficulty_score=5),
        SimpleNamespace(
            status="missed",
            due_date=base + timedelta(days=1),
            created_at=base,
            difficulty_score=2,
        ),
        SimpleNamespace(status="planned", due_date=None, created_at=base, difficulty_score=None),
        SimpleNamespace(status="in_progress", due_date=base, created_at=base, difficulty_score=4),
    ]
    events = [
        SimpleNamespace(start_time=base, end_time=base + timedelta(hours=2)),
        SimpleNamespace(
            start_time=base + timedelta(days=2),
            end_time=base + timedelta(days=2, hours=1),
        ),
    ]

    result = service.build_dashboard_analytics(tasks, events)

    assert result["summary"] == {
        "completed": 1,
        "missed": 1,
        "planned": 1,
        "in_progress": 1,
        "total": 4,
    }
    assert result["difficulty_distribution"]["5"] == 1
    assert result["difficulty_distribution"]["3"] == 1
    assert result["weekly_load"][0]["hours"] == 2.0
    assert result["productivity_history"][0]["score"] == 0.8


def test_analytics_filters_ignore_items_without_dates():
    service = AnalyticsService()
    start = datetime(2026, 5, 1)
    end = datetime(2026, 5, 2)

    tasks = [
        SimpleNamespace(due_date=None, created_at=None),
        SimpleNamespace(due_date=datetime(2026, 4, 30), created_at=None),
        SimpleNamespace(due_date=datetime(2026, 5, 1, 12), created_at=None),
    ]
    events = [
        SimpleNamespace(start_time=None),
        SimpleNamespace(start_time=datetime(2026, 5, 1, 9)),
        SimpleNamespace(start_time=datetime(2026, 5, 3, 9)),
    ]

    assert len(service.filter_tasks(tasks, start, end)) == 1
    assert len(service.filter_events(events, start, end)) == 1


class FakeEventsApi:
    def __init__(self):
        self.insert_body = None
        self.update_body = None
        self.deleted_event_id = None

    def list(self, **kwargs):
        self.list_kwargs = kwargs
        return SimpleNamespace(execute=lambda: {"items": [{"id": "g1"}]})

    def insert(self, calendarId, body):
        self.insert_body = body
        return SimpleNamespace(execute=lambda: {"id": "created", **body})

    def get(self, calendarId, eventId):
        return SimpleNamespace(execute=lambda: {"id": eventId, "summary": "Old"})

    def update(self, calendarId, eventId, body):
        self.update_body = body
        return SimpleNamespace(execute=lambda: {"id": eventId, **body})

    def delete(self, calendarId, eventId):
        self.deleted_event_id = eventId
        return SimpleNamespace(execute=lambda: {"deleted": eventId})


class FakeCalendarService:
    def __init__(self):
        self.events_api = FakeEventsApi()

    def events(self):
        return self.events_api


def test_google_calendar_adapter_crud_methods_use_google_events_api():
    fake_service = FakeCalendarService()
    adapter = GoogleCalendarAdapter()
    adapter.build_service = lambda credentials: fake_service

    creds = {"token": "token"}
    assert adapter.get_events(creds, single_events=True) == [{"id": "g1"}]

    created = adapter.create_event(
        creds,
        title="Test",
        start="2026-05-01T10:00:00",
        end="2026-05-01T11:00:00",
        recurrence_rule="RRULE:FREQ=WEEKLY",
    )
    assert created["id"] == "created"
    assert fake_service.events_api.insert_body["recurrence"] == ["RRULE:FREQ=WEEKLY"]

    updated = adapter.update_event(
        creds,
        event_id="g1",
        title="Updated",
        start="2026-05-02T10:00:00",
        end="2026-05-02T11:00:00",
    )
    assert updated["summary"] == "Updated"
    assert "recurrence" not in fake_service.events_api.update_body

    deleted = adapter.delete_event(creds, "g1")
    assert deleted == {"deleted": "g1"}


def test_model_registry_saves_loads_model_and_metadata(tmp_path):
    registry = ModelRegistry(model_dir=str(tmp_path))
    bundle = {"model": "fake"}

    saved = registry.save_model(bundle, {"accuracy": 0.91})

    assert saved["metadata"]["accuracy"] == 0.91
    assert registry.load_latest_model() == bundle
    assert registry.load_metadata()["accuracy"] == 0.91


def test_model_registry_returns_none_when_model_and_metadata_are_absent(tmp_path):
    registry = ModelRegistry(model_dir=str(tmp_path))

    assert registry.load_latest_model() is None
    assert registry.load_metadata() is None


def test_deadline_model_adapter_raises_when_model_file_missing(monkeypatch):
    adapter = DeadlineModelAdapter()
    monkeypatch.setattr(
        "backend.infrastructure.ml.deadline_model_adapter.os.path.exists",
        lambda path: False,
    )

    with pytest.raises(FileNotFoundError):
        adapter.load_model()


def test_deadline_model_adapter_predict_builds_expected_feature_vector(monkeypatch):
    adapter = DeadlineModelAdapter()

    class FakeModel:
        def predict(self, values):
            assert values.shape == (1, 9)
            return [4.5]

    adapter.model = FakeModel()

    result = adapter.predict(
        {
            "estimated_duration_hours": 2,
            "difficulty_score": 4,
            "priority_score": 3,
            "task_type_score": 2,
            "subject_has_events": 1,
            "hours_until_next_subject_event": 24,
            "day_load_score": 0.5,
            "free_hours_today": 3,
            "days_until_deadline": 5,
        }
    )

    assert result == 4.5
