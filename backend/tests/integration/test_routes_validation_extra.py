from types import SimpleNamespace

import pytest

from backend.app.routes import (
    analytics_routes,
    event_routes,
    frontend_routes,
    schedule_import_routes,
    task_routes,
)


def test_event_create_requires_title_start_and_end(app, monkeypatch):
    monkeypatch.setattr(event_routes, "current_user", lambda: SimpleNamespace(id=1))

    with app.test_request_context("/api/events", method="POST", json={}):
        response, status = event_routes.create_event_api()

    assert status == 400
    assert response.get_json()["error"] == "Title, start and end are required"


def test_event_create_rejects_invalid_datetime(app, monkeypatch):
    monkeypatch.setattr(event_routes, "current_user", lambda: SimpleNamespace(id=1))

    with app.test_request_context(
        "/api/events",
        method="POST",
        json={"title": "Bad event", "start": "bad", "end": "also-bad"},
    ):
        response, status = event_routes.create_event_api()

    assert status == 400
    assert response.get_json()["error"] == "Invalid datetime format"


def test_auto_plan_event_rejects_empty_title(app, monkeypatch):
    monkeypatch.setattr(event_routes, "current_user", lambda: SimpleNamespace(id=1))

    class FakeDB:
        def query(self, model):
            return self

        def filter_by(self, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return []

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(event_routes, "SessionLocal", lambda: FakeDB())

    with app.test_request_context(
        "/api/planner/auto-plan",
        method="POST",
        json={
            "duration_minutes": 60,
            "date_from": "2026-05-28",
            "date_to": "2026-05-29",
        },
    ):
        response, status = event_routes.auto_plan_event_api()

    assert status == 400
    assert "Title is required" in response.get_json()["error"]


def test_task_create_requires_title(app, monkeypatch):
    monkeypatch.setattr(task_routes, "current_user", lambda: SimpleNamespace(id=1))

    with app.test_request_context("/api/tasks", method="POST", json={}):
        response, status = task_routes.create_task()

    assert status == 400
    assert response.get_json()["error"] == "Task title is required"


def test_update_task_status_rejects_invalid_status(app, monkeypatch):
    monkeypatch.setattr(task_routes, "current_user", lambda: SimpleNamespace(id=1))

    with app.test_request_context(
        "/api/tasks/1/status",
        method="PUT",
        json={"status": "unknown"},
    ):
        response, status = task_routes.update_task_status(1)

    assert status == 400
    assert response.get_json()["error"] == "Invalid task status"


def test_update_task_deadline_rejects_invalid_date(app, monkeypatch):
    monkeypatch.setattr(task_routes, "current_user", lambda: SimpleNamespace(id=1))

    with app.test_request_context(
        "/api/tasks/1/deadline",
        method="PUT",
        json={"due_date": "not-a-date"},
    ):
        response, status = task_routes.update_task_deadline(1)

    assert status == 400
    assert response.get_json()["error"] == "Invalid due_date"


def test_auto_deadline_requires_title(app, monkeypatch):
    monkeypatch.setattr(task_routes, "current_user", lambda: SimpleNamespace(id=1))

    with app.test_request_context("/api/tasks/auto-deadline", method="POST", json={}):
        response, status = task_routes.auto_deadline_for_manual_task()

    assert status == 400
    assert response.get_json()["error"] == "Task title is required"


def test_analyze_task_text_rejects_empty_text(app, monkeypatch):
    monkeypatch.setattr(task_routes, "current_user", lambda: SimpleNamespace(id=1))

    with app.test_request_context(
        "/api/task-import/analyze-text",
        method="POST",
        json={"text": "   "},
    ):
        response, status = task_routes.analyze_task_text_api()

    assert status == 400
    assert response.get_json()["error"] == "Текст завдання порожній"


def test_create_subject_from_import_requires_name(app, monkeypatch):
    monkeypatch.setattr(task_routes, "current_user", lambda: SimpleNamespace(id=1))

    with app.test_request_context(
        "/api/task-import/create-subject",
        method="POST",
        json={},
    ):
        response, status = task_routes.create_subject_from_task_import_api()

    assert status == 400
    assert "обов" in response.get_json()["error"]


def test_create_tasks_from_import_requires_tasks(app, monkeypatch):
    monkeypatch.setattr(task_routes, "current_user", lambda: SimpleNamespace(id=1))

    with app.test_request_context(
        "/api/task-import/create-tasks",
        method="POST",
        json={"tasks": []},
    ):
        response, status = task_routes.create_tasks_from_import_api()

    assert status == 400
    assert response.get_json()["error"] == "Немає задач для створення"


def test_productivity_predict_requires_date(app, monkeypatch):
    monkeypatch.setattr(analytics_routes, "current_user", lambda: SimpleNamespace(id=1))

    with app.test_request_context(
        "/api/ml/productivity/predict",
        method="POST",
        json={},
    ):
        response, status = analytics_routes.productivity_predict_api()

    assert status == 400
    assert response.get_json()["error"] == "Date is required"


def test_schedule_upload_requires_file(app):
    with app.test_request_context(
        "/api/schedule-import/upload",
        method="POST",
        data={},
    ):
        response, status = schedule_import_routes.upload_schedule_api()

    assert status == 400
    assert response.get_json()["error"] == "Файл розкладу не передано"


def test_schedule_preview_requires_file_for_multipart(app):
    with app.test_request_context(
        "/api/schedule-import/preview",
        method="POST",
        data={},
        content_type="multipart/form-data",
    ):
        response, status = schedule_import_routes.schedule_import_preview()

    assert status == 400
    assert response.get_json()["events"] == []


def test_frontend_api_path_returns_404(app):
    with app.test_request_context("/api/unknown", method="GET"):
        response, status = frontend_routes.serve_react("api/unknown")

    assert status == 404
    assert response.get_json()["error"] == "Not found"
