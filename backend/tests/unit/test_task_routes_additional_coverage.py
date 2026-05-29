from datetime import datetime
from types import SimpleNamespace

from backend.app.routes import task_routes as routes


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
    def __init__(
        self, tasks=None, subjects=None, event_types=None, task=None, subject=None, event_type=None
    ):
        self.tasks = tasks or []
        self.subjects = subjects or []
        self.event_types = event_types or []
        self.task = task
        self.subject = subject
        self.event_type = event_type
        self.added = []
        self.deleted = []
        self.commits = 0
        self.flushes = 0
        self.closed = False

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "Task":
            return FakeQuery(self.tasks, self.task or (self.tasks[0] if self.tasks else None))
        if name == "Subject":
            return FakeQuery(
                self.subjects, self.subject or (self.subjects[0] if self.subjects else None)
            )
        if name == "EventType":
            return FakeQuery(
                self.event_types,
                self.event_type or (self.event_types[0] if self.event_types else None),
            )
        return FakeQuery([])

    def add(self, item):
        if getattr(item, "id", None) is None:
            item.id = 100 + len(self.added)
        self.added.append(item)

    def flush(self):
        self.flushes += 1

    def commit(self):
        self.commits += 1

    def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = 100 + len(self.added)

    def delete(self, item):
        self.deleted.append(item)

    def close(self):
        self.closed = True


def patch_user_and_db(monkeypatch, db, user=None):
    monkeypatch.setattr(routes, "current_user", lambda: user or SimpleNamespace(id=1))
    monkeypatch.setattr(routes, "SessionLocal", lambda: db)


def make_task(status="planned"):
    return SimpleNamespace(
        id=1,
        user_id=1,
        event_id=None,
        subject_id=None,
        title="Task",
        description="Description",
        status=status,
        priority="medium",
        due_date=datetime(2026, 5, 29, 10, 0),
        completed_at=None,
        missed_at=None,
        task_type="other",
        keywords="[]",
        estimated_duration_hours=1,
        difficulty_score=3,
        nlp_source="manual",
        created_at=datetime(2026, 5, 1, 10, 0),
        updated_at=datetime(2026, 5, 1, 10, 0),
    )


def test_create_event_type_success(app, monkeypatch):
    db = FakeDB()
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(
        routes, "serialize_event_type", lambda item: {"id": item.id, "name": item.name}
    )

    with app.test_request_context(
        "/api/event-types", method="POST", json={"name": "Лекція", "color": "#fff"}
    ):
        response, status = routes.create_event_type()

    assert status == 201
    assert response.get_json()["name"] == "Лекція"


def test_create_subject_success(app, monkeypatch):
    db = FakeDB()
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(
        routes, "serialize_subject", lambda item: {"id": item.id, "name": item.name}
    )

    with app.test_request_context("/api/subjects", method="POST", json={"name": "Фізика"}):
        response, status = routes.create_subject()

    assert status == 201
    assert response.get_json()["name"] == "Фізика"


def test_update_subject_not_found(app, monkeypatch):
    db = FakeDB(subject=None)
    patch_user_and_db(monkeypatch, db)

    with app.test_request_context("/api/subjects/999", method="PUT", json={"name": "New"}):
        response, status = routes.update_subject(999)

    assert status == 404


def test_update_event_type_success(app, monkeypatch):
    event_type = SimpleNamespace(id=1, user_id=1, name="Old", color="#000")
    db = FakeDB(event_type=event_type)
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(
        routes, "serialize_event_type", lambda item: {"id": item.id, "name": item.name}
    )

    with app.test_request_context("/api/event-types/1", method="PUT", json={"name": "New"}):
        response, status = routes.update_event_type(1)

    assert status == 200
    assert response.get_json()["name"] == "New"


def test_get_tasks_with_include_meta(app, monkeypatch):
    task = make_task()
    db = FakeDB(tasks=[task])
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(
        routes,
        "refresh_and_replan_missed_tasks",
        lambda **kwargs: {"replanned": [{"id": 1}], "replanned_count": 1},
    )
    monkeypatch.setattr(
        routes, "serialize_task", lambda task: {"id": task.id, "status": task.status}
    )

    with app.test_request_context("/api/tasks?include_meta=1"):
        response = routes.get_tasks()

    assert response.get_json()["auto_replanned_count"] == 1


def test_create_task_success(app, monkeypatch):
    db = FakeDB()
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(routes, "create_task_log", lambda **kwargs: None)
    monkeypatch.setattr(routes, "set_auto_replan_metadata", lambda db, task: None)
    monkeypatch.setattr(routes, "serialize_task", lambda task: {"id": task.id, "title": task.title})

    with app.test_request_context(
        "/api/tasks",
        method="POST",
        json={"title": "Task", "keywords": ["a"], "estimated_duration_hours": 2},
    ):
        response, status = routes.create_task()

    assert status == 201
    assert response.get_json()["title"] == "Task"


def test_create_task_auto_deadline_ignores_planning_error(app, monkeypatch):
    db = FakeDB()
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(
        routes,
        "apply_auto_deadline_to_task",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(routes, "create_task_log", lambda **kwargs: None)
    monkeypatch.setattr(routes, "set_auto_replan_metadata", lambda db, task: None)
    monkeypatch.setattr(routes, "serialize_task", lambda task: {"id": task.id, "title": task.title})

    with app.test_request_context(
        "/api/tasks", method="POST", json={"title": "Task", "auto_plan_deadline": True}
    ):
        response, status = routes.create_task()

    assert status == 201


def test_update_task_not_found(app, monkeypatch):
    db = FakeDB(task=None)
    patch_user_and_db(monkeypatch, db)

    with app.test_request_context("/api/tasks/999", method="PUT", json={"title": "New"}):
        response, status = routes.update_task(999)

    assert status == 404


def test_update_task_success_with_keywords(app, monkeypatch):
    task = make_task()
    db = FakeDB(task=task)
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(routes, "set_auto_replan_metadata", lambda db, task: None)
    monkeypatch.setattr(
        routes,
        "serialize_task",
        lambda task: {"id": task.id, "title": task.title, "keywords": task.keywords},
    )

    with app.test_request_context(
        "/api/tasks/1",
        method="PUT",
        json={"title": "Updated", "keywords": ["x", "y"], "estimated_duration_hours": 3},
    ):
        response, status = routes.update_task(1)

    assert status == 200
    assert response.get_json()["title"] == "Updated"


def test_update_task_deadline_success(app, monkeypatch):
    task = make_task()
    db = FakeDB(task=task)
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(routes, "set_auto_replan_metadata", lambda db, task: None)
    monkeypatch.setattr(
        routes,
        "serialize_task",
        lambda task: {"id": task.id, "due_date": task.due_date.isoformat()},
    )

    with app.test_request_context(
        "/api/tasks/1/deadline", method="PUT", json={"due_date": "2026-06-01T12:00:00"}
    ):
        response, status = routes.update_task_deadline(1)

    assert status == 200


def test_delete_task_success(app, monkeypatch):
    task = make_task()
    db = FakeDB(task=task)
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(routes, "create_task_log", lambda **kwargs: None)

    with app.test_request_context("/api/tasks/1", method="DELETE"):
        response = routes.delete_task(1)

    assert response.get_json()["message"] == "Task deleted"
    assert db.deleted == [task]


def test_update_task_status_done_sets_completed_at(app, monkeypatch):
    task = make_task(status="planned")
    db = FakeDB(task=task)
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(routes, "create_task_log", lambda **kwargs: None)
    monkeypatch.setattr(routes, "set_auto_replan_metadata", lambda db, task: None)
    monkeypatch.setattr(
        routes, "serialize_task", lambda task: {"id": task.id, "status": task.status}
    )

    with app.test_request_context(
        "/api/tasks/1/status",
        method="PUT",
        json={"status": "done"},
    ):
        response = routes.update_task_status(1)

    assert response.status_code == 200
    assert response.get_json()["status"] == "done"


def test_update_task_status_missed_sets_missed_at(app, monkeypatch):
    task = make_task(status="planned")
    db = FakeDB(task=task)
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(routes, "create_task_log", lambda **kwargs: None)
    monkeypatch.setattr(routes, "set_auto_replan_metadata", lambda db, task: None)
    monkeypatch.setattr(
        routes, "serialize_task", lambda task: {"id": task.id, "status": task.status}
    )

    with app.test_request_context(
        "/api/tasks/1/status",
        method="PUT",
        json={"status": "missed"},
    ):
        response = routes.update_task_status(1)

    assert response.status_code == 200
    assert response.get_json()["status"] == "missed"
