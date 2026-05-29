from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from backend.app.routes import task_routes


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
    def __init__(self):
        self.data = {
            task_routes.Task: [],
            task_routes.TaskActivityLog: [],
            task_routes.Subject: [],
            task_routes.TaskScheduleBlock: [],
        }
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

    def flush(self):
        for collection in self.data.values():
            for index, item in enumerate(collection, start=1):
                if getattr(item, "id", None) is None:
                    item.id = index

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

    def rollback(self):
        pass

    def close(self):
        self.closed = True


@pytest.fixture
def fake_task_context(monkeypatch):
    db = FakeDB()
    user = SimpleNamespace(id=1)

    monkeypatch.setattr(task_routes, "current_user", lambda: user)
    monkeypatch.setattr(task_routes, "SessionLocal", lambda: db)
    monkeypatch.setattr(task_routes, "set_auto_replan_metadata", lambda db, task: task)

    return db


@pytest.mark.integration
def test_task_lifecycle_create_update_status_delete(client, fake_task_context):
    create_response = client.post(
        "/api/tasks",
        json={
            "title": "Підготувати лабораторну",
            "description": "Оформити звіт і перевірити код",
            "priority": "high",
            "estimated_duration_hours": 2,
            "difficulty_score": 4,
            "keywords": ["лабораторна", "звіт"],
        },
    )

    assert create_response.status_code == 201

    task = create_response.get_json()
    task_id = task["id"]
    assert task["title"] == "Підготувати лабораторну"

    update_response = client.put(
        f"/api/tasks/{task_id}",
        json={
            "title": "Підготувати лабораторну роботу",
            "priority": "medium",
            "keywords": ["оновлено"],
        },
    )

    assert update_response.status_code == 200
    assert update_response.get_json()["title"] == "Підготувати лабораторну роботу"

    status_response = client.put(
        f"/api/tasks/{task_id}/status",
        json={"status": "done"},
    )

    assert status_response.status_code == 200
    assert status_response.get_json()["status"] == "done"

    delete_response = client.delete(f"/api/tasks/{task_id}")

    assert delete_response.status_code == 200
    assert delete_response.get_json()["message"] == "Task deleted"


@pytest.mark.integration
def test_task_deadline_endpoint_rejects_invalid_date(client, fake_task_context):
    create_response = client.post(
        "/api/tasks",
        json={"title": "Task with deadline"},
    )

    assert create_response.status_code == 201
    task_id = create_response.get_json()["id"]

    response = client.put(
        f"/api/tasks/{task_id}/deadline",
        json={"due_date": "invalid-date"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid due_date"


@pytest.mark.integration
def test_activity_logs_available_after_task_actions(client, fake_task_context):
    create_response = client.post(
        "/api/tasks",
        json={"title": "Task for logs"},
    )

    assert create_response.status_code == 201
    task_id = create_response.get_json()["id"]

    client.put(
        f"/api/tasks/{task_id}/status",
        json={"status": "in_progress"},
    )

    logs_response = client.get(f"/api/activity-logs?task_id={task_id}")

    assert logs_response.status_code == 200
    assert isinstance(logs_response.get_json(), list)
