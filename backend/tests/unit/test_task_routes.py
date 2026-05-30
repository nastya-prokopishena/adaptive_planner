from datetime import UTC, datetime, timedelta
from io import BytesIO
from types import SimpleNamespace

import pytest

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

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return self.items

    def first(self):
        return self.first_item

    def count(self):
        return len(self.items)


class FakeDB:
    def __init__(
        self,
        task=None,
        tasks=None,
        subject=None,
        subjects=None,
        event_type=None,
        event_types=None,
        blocks=None,
        logs=None,
    ):
        self.task = task
        self.tasks = tasks or ([] if task is None else [task])
        self.subject = subject
        self.subjects = subjects or ([] if subject is None else [subject])
        self.event_type = event_type
        self.event_types = event_types or ([] if event_type is None else [event_type])
        self.blocks = blocks or []
        self.logs = logs or []
        self.added = []
        self.deleted = []
        self.commits = 0
        self.flushes = 0
        self.refreshes = []
        self.closed = False
        self.rolled_back = False

    def query(self, model):
        model_name = getattr(model, "__name__", "")

        if model_name == "Task":
            return FakeQuery(
                self.tasks,
                self.task or (self.tasks[0] if self.tasks else None),
            )

        if model_name == "Subject":
            return FakeQuery(
                self.subjects,
                self.subject or (self.subjects[0] if self.subjects else None),
            )

        if model_name == "EventType":
            return FakeQuery(
                self.event_types,
                self.event_type or (self.event_types[0] if self.event_types else None),
            )

        if model_name == "TaskScheduleBlock":
            return FakeQuery(
                self.blocks,
                self.blocks[0] if self.blocks else None,
            )

        if model_name == "TaskActivityLog":
            return FakeQuery(
                self.logs,
                self.logs[0] if self.logs else None,
            )

        return FakeQuery([])

    def add(self, item):
        if getattr(item, "id", None) is None:
            item.id = 100 + len(self.added)
        self.added.append(item)

    def delete(self, item):
        self.deleted.append(item)

    def flush(self):
        self.flushes += 1

    def commit(self):
        self.commits += 1

    def refresh(self, item):
        self.refreshes.append(item)
        if getattr(item, "id", None) is None:
            item.id = 100 + len(self.refreshes)

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def patch_user_and_db(monkeypatch, db, user=None):
    monkeypatch.setattr(routes, "current_user", lambda: user or SimpleNamespace(id=1))
    monkeypatch.setattr(routes, "SessionLocal", lambda: db)


def unpack(result):
    if isinstance(result, tuple):
        return result
    return result, result.status_code


def make_task(task_id=1, title="Task", status="planned"):
    return SimpleNamespace(
        id=task_id,
        user_id=1,
        event_id=None,
        subject_id=10,
        title=title,
        description="Description",
        status=status,
        priority="medium",
        due_date=datetime.now(UTC) + timedelta(days=2),
        completed_at=None,
        missed_at=None,
        task_type="other",
        keywords="[]",
        estimated_duration_hours=1,
        difficulty_score=3,
        nlp_source="manual",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def make_subject(subject_id=10, name="Фізика"):
    return SimpleNamespace(
        id=subject_id,
        user_id=1,
        name=name,
        teacher=None,
        description=None,
        color="#64748b",
        created_at=datetime.now(UTC),
    )


def make_block(task_id=1):
    return SimpleNamespace(
        id=20,
        user_id=1,
        task_id=task_id,
        start_time=datetime.now(UTC) + timedelta(hours=2),
        end_time=datetime.now(UTC) + timedelta(hours=3),
        source="ml_planner",
        generated_by_ai=True,
        confidence_score=0.75,
        reason="test",
    )


def make_log():
    return SimpleNamespace(
        id=1,
        user_id=1,
        task_id=1,
        action="status_changed",
        old_status="planned",
        new_status="done",
        details="changed",
        created_at=datetime.now(UTC),
    )


def test_event_type_and_subject_crud_basic(app, monkeypatch):
    event_type = SimpleNamespace(id=1, user_id=1, name="Old", color="#000")
    subject = make_subject()
    db = FakeDB(event_type=event_type, subject=subject, subjects=[subject])
    patch_user_and_db(monkeypatch, db)

    monkeypatch.setattr(
        routes,
        "serialize_event_type",
        lambda item: {"id": item.id, "name": item.name},
    )
    monkeypatch.setattr(
        routes,
        "serialize_subject",
        lambda item: {"id": item.id, "name": item.name},
    )

    with app.test_request_context(
        "/api/event-types",
        method="POST",
        json={"name": "Лекція", "color": "#fff"},
    ):
        response, status = routes.create_event_type()

    assert status == 201
    assert response.get_json()["name"] == "Лекція"

    with app.test_request_context("/api/subjects"):
        response = routes.get_subjects()

    assert response.get_json() == [{"id": 10, "name": "Фізика"}]

    with app.test_request_context(
        "/api/event-types/1",
        method="PUT",
        json={"name": "Практика"},
    ):
        response, status = routes.update_event_type(1)

    assert status == 200
    assert response.get_json()["name"] == "Практика"


@pytest.mark.parametrize(
    ("route_func", "url", "method", "payload", "expected_error"),
    [
        (routes.create_event_type, "/api/event-types", "POST", {}, "Name is required"),
        (routes.create_subject, "/api/subjects", "POST", {}, "Name is required"),
        (
            routes.create_task,
            "/api/tasks",
            "POST",
            {},
            "Task title is required",
        ),
    ],
)
def test_required_fields_are_validated(
    app,
    monkeypatch,
    route_func,
    url,
    method,
    payload,
    expected_error,
):
    db = FakeDB()
    patch_user_and_db(monkeypatch, db)

    with app.test_request_context(url, method=method, json=payload):
        response, status = route_func()

    assert status == 400
    assert response.get_json()["error"] == expected_error


def test_get_tasks_filters_and_returns_meta(app, monkeypatch):
    planned = make_task(task_id=1, status="planned")
    done = make_task(task_id=2, status="done")
    db = FakeDB(tasks=[planned, done])
    patch_user_and_db(monkeypatch, db)

    monkeypatch.setattr(
        routes,
        "refresh_and_replan_missed_tasks",
        lambda **kwargs: {"replanned": [{"id": 1}], "replanned_count": 1},
    )
    monkeypatch.setattr(
        routes,
        "serialize_task",
        lambda task: {"id": task.id, "status": task.status},
    )

    with app.test_request_context("/api/tasks?include_meta=1"):
        response = routes.get_tasks()

    assert response.get_json()["auto_replanned_count"] == 1

    with app.test_request_context("/api/tasks?status=done&event_id=1&subject_id=10"):
        response = routes.get_tasks()

    assert response.get_json() == [{"id": 2, "status": "done"}]


def test_task_crud_success_paths(app, monkeypatch):
    task = make_task()
    db = FakeDB(task=task)
    patch_user_and_db(monkeypatch, db)

    monkeypatch.setattr(routes, "create_task_log", lambda **kwargs: None)
    monkeypatch.setattr(routes, "set_auto_replan_metadata", lambda db, task: None)
    monkeypatch.setattr(
        routes,
        "serialize_task",
        lambda task: {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "keywords": task.keywords,
            "due_date": task.due_date.isoformat() if task.due_date else None,
        },
    )

    with app.test_request_context(
        "/api/tasks",
        method="POST",
        json={"title": "Task", "keywords": ["a"], "estimated_duration_hours": 2},
    ):
        response, status = routes.create_task()

    assert status == 201
    assert response.get_json()["title"] == "Task"

    with app.test_request_context(
        "/api/tasks/1",
        method="PUT",
        json={"title": "Updated", "keywords": ["x", "y"]},
    ):
        response, status = routes.update_task(1)

    assert status == 200
    assert response.get_json()["title"] == "Updated"

    with app.test_request_context(
        "/api/tasks/1/deadline",
        method="PUT",
        json={"due_date": "2026-06-01T12:00:00"},
    ):
        response, status = routes.update_task_deadline(1)

    assert status == 200

    with app.test_request_context("/api/tasks/1", method="DELETE"):
        response = routes.delete_task(1)

    assert response.get_json()["message"] == "Task deleted"
    assert db.deleted == [task]


@pytest.mark.parametrize(
    ("route_func", "args", "url", "method", "payload"),
    [
        (routes.update_task, (999,), "/api/tasks/999", "PUT", {"title": "New"}),
        (
            routes.update_task_deadline,
            (999,),
            "/api/tasks/999/deadline",
            "PUT",
            {"due_date": "2026-06-01T12:00:00"},
        ),
        (routes.delete_task, (999,), "/api/tasks/999", "DELETE", None),
        (
            routes.update_task_status,
            (999,),
            "/api/tasks/999/status",
            "PUT",
            {"status": "done"},
        ),
        (routes.auto_plan_existing_task, (999,), "/api/tasks/999/auto-plan", "POST", {}),
    ],
)
def test_task_not_found_responses(app, monkeypatch, route_func, args, url, method, payload):
    db = FakeDB(task=None)
    patch_user_and_db(monkeypatch, db)

    with app.test_request_context(url, method=method, json=payload):
        response, status = route_func(*args)

    assert status == 404
    assert "error" in response.get_json()


@pytest.mark.parametrize("new_status", ["done", "missed"])
def test_update_task_status_success(app, monkeypatch, new_status):
    task = make_task(status="planned")
    db = FakeDB(task=task)
    patch_user_and_db(monkeypatch, db)

    monkeypatch.setattr(routes, "create_task_log", lambda **kwargs: None)
    monkeypatch.setattr(routes, "set_auto_replan_metadata", lambda db, task: None)
    monkeypatch.setattr(routes, "auto_replan_missed_task", lambda **kwargs: None)
    monkeypatch.setattr(
        routes,
        "serialize_task",
        lambda task: {"id": task.id, "status": task.status},
    )

    with app.test_request_context(
        "/api/tasks/1/status",
        method="PUT",
        json={"status": new_status},
    ):
        response = routes.update_task_status(1)

    assert response.status_code == 200
    assert response.get_json()["status"] == new_status


def test_update_task_status_rejects_invalid_status(app, monkeypatch):
    task = make_task()
    db = FakeDB(task=task)
    patch_user_and_db(monkeypatch, db)

    with app.test_request_context(
        "/api/tasks/1/status",
        method="PUT",
        json={"status": "unknown"},
    ):
        response, status = routes.update_task_status(1)

    assert status == 400
    assert response.get_json()["error"] == "Invalid task status"


def test_activity_logs_and_blocks(app, monkeypatch):
    task = make_task()
    block = make_block(task_id=task.id)
    log = make_log()
    db = FakeDB(task=task, blocks=[block], logs=[log])
    patch_user_and_db(monkeypatch, db)

    monkeypatch.setattr(
        routes,
        "serialize_activity_log",
        lambda log: {"id": log.id, "action": log.action},
    )
    monkeypatch.setattr(
        routes,
        "serialize_task_schedule_block",
        lambda block, task: {"block_id": block.id, "task_title": task.title},
    )

    with app.test_request_context("/api/activity-logs?task_id=1"):
        response = routes.get_activity_logs()

    assert response.get_json() == [{"id": 1, "action": "status_changed"}]

    with app.test_request_context("/api/task-schedule-blocks"):
        response = routes.get_task_schedule_blocks()

    assert response.get_json() == [{"block_id": 20, "task_title": "Task"}]


@pytest.mark.parametrize(
    ("route_func", "url", "method"),
    [
        (routes.get_event_types, "/api/event-types", "GET"),
        (routes.get_task_schedule_blocks, "/api/task-schedule-blocks", "GET"),
        (
            routes.generate_synthetic_deadline_dataset,
            "/api/ml/deadline-dataset/generate",
            "POST",
        ),
        (routes.get_activity_logs, "/api/activity-logs", "GET"),
    ],
)
def test_unauthorized_routes(app, monkeypatch, route_func, url, method):
    monkeypatch.setattr(routes, "current_user", lambda: None)

    with app.test_request_context(url, method=method):
        response, status = route_func()

    assert status == 401


def test_auto_deadline_success_and_fallbacks(app, monkeypatch):
    db = FakeDB()
    patch_user_and_db(monkeypatch, db)

    deadline = datetime.now(UTC) + timedelta(days=3)

    monkeypatch.setattr(routes, "resolve_subject_id", lambda **kwargs: 10)
    monkeypatch.setattr(routes, "get_subject_events", lambda **kwargs: [])
    monkeypatch.setattr(routes, "get_user_calendar_events", lambda **kwargs: [])
    monkeypatch.setattr(routes, "get_existing_subject_deadline_count", lambda **kwargs: 0)
    monkeypatch.setattr(routes, "get_existing_deadline_dates", lambda db, user_id: [])
    monkeypatch.setattr(
        routes,
        "safe_predict_deadline",
        lambda **kwargs: {
            "deadline": deadline,
            "confidence": 0.9,
            "reason": "Best deadline",
        },
    )

    with app.test_request_context(
        "/api/tasks/auto-deadline",
        method="POST",
        json={"title": "Task", "subject": "Фізика"},
    ):
        response, status = unpack(routes.auto_deadline_for_manual_task())

    assert status == 200
    assert response.get_json()["confidence_score"] == 0.9

    with app.test_request_context("/api/tasks/auto-deadline", method="POST", json={}):
        response, status = unpack(routes.auto_deadline_for_manual_task())

    assert status == 400
    assert "error" in response.get_json()

    monkeypatch.setattr(
        routes,
        "safe_predict_deadline",
        lambda **kwargs: {"deadline": None, "confidence": 0.1, "reason": "fallback"},
    )

    with app.test_request_context(
        "/api/tasks/auto-deadline",
        method="POST",
        json={"title": "Task"},
    ):
        response, status = unpack(routes.auto_deadline_for_manual_task())

    assert status == 200
    assert response.get_json()["due_date"] is None


def test_auto_plan_preview_success_and_edge_cases(app, monkeypatch):
    db = FakeDB()
    patch_user_and_db(monkeypatch, db)

    deadline = datetime.now(UTC) + timedelta(days=2)

    monkeypatch.setattr(routes, "resolve_subject_id", lambda **kwargs: 10)
    monkeypatch.setattr(routes, "get_subject_name_by_id", lambda **kwargs: "Фізика")
    monkeypatch.setattr(routes, "get_existing_deadline_dates", lambda db, user_id: [])
    monkeypatch.setattr(routes, "get_user_calendar_events", lambda db, user_id: [])
    monkeypatch.setattr(routes, "get_subject_events", lambda **kwargs: [])
    monkeypatch.setattr(routes, "get_existing_subject_deadline_count", lambda **kwargs: 0)
    monkeypatch.setattr(routes, "build_subject_distribution_index", lambda **kwargs: 0)
    monkeypatch.setattr(
        routes,
        "safe_predict_deadline",
        lambda **kwargs: {
            "deadline": deadline,
            "confidence": 0.8,
            "reason": "planned",
        },
    )

    with app.test_request_context(
        "/api/tasks/auto-plan-deadlines-preview",
        method="POST",
        json={"mode": "best_time", "tasks": [{"title": "Task", "subject_id": 10}]},
    ):
        response = routes.auto_plan_deadlines_preview()

    task = response.get_json()["tasks"][0]
    assert task["title"] == "Task"
    assert task["confidence_score"] == 0.8

    with app.test_request_context(
        "/api/tasks/auto-plan-deadlines-preview",
        method="POST",
        json={"tasks": []},
    ):
        response = routes.auto_plan_deadlines_preview()

    assert response.get_json() == {"tasks": []}

    with app.test_request_context(
        "/api/tasks/auto-plan-deadlines-preview",
        method="POST",
        json={"tasks": ["Підготувати лабораторну"]},
    ):
        response = routes.auto_plan_deadlines_preview()

    assert response.get_json()["tasks"][0]["title"] == "Підготувати лабораторну"


def test_auto_plan_preview_handles_prediction_error(app, monkeypatch):
    db = FakeDB()
    patch_user_and_db(monkeypatch, db)

    monkeypatch.setattr(routes, "resolve_subject_id", lambda **kwargs: 10)
    monkeypatch.setattr(routes, "get_existing_deadline_dates", lambda db, user_id: [])
    monkeypatch.setattr(routes, "get_user_calendar_events", lambda db, user_id: [])
    monkeypatch.setattr(routes, "get_subject_events", lambda **kwargs: [])
    monkeypatch.setattr(
        routes,
        "safe_predict_deadline",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("prediction failed")),
    )

    with app.test_request_context(
        "/api/tasks/auto-plan-deadlines-preview",
        method="POST",
        json={"tasks": [{"title": "Broken task"}]},
    ):
        response = routes.auto_plan_deadlines_preview()

    assert response.status_code == 200
    assert response.get_json()["tasks"][0]["error"] == "prediction failed"


def test_auto_plan_existing_task_success_and_error(app, monkeypatch):
    task = make_task()
    block = make_block(task_id=task.id)
    db = FakeDB(task=task)
    patch_user_and_db(monkeypatch, db)

    monkeypatch.setattr(
        routes,
        "apply_auto_deadline_to_task",
        lambda **kwargs: ({"reason": "auto planned"}, block),
    )
    monkeypatch.setattr(routes, "serialize_task", lambda task: {"id": task.id})
    monkeypatch.setattr(
        routes,
        "serialize_task_schedule_block",
        lambda block, task: {"id": block.id, "task_id": task.id},
    )

    with app.test_request_context("/api/tasks/1/auto-plan", method="POST", json={}):
        response = routes.auto_plan_existing_task(1)

    assert response.get_json()["schedule_block"]["id"] == 20

    monkeypatch.setattr(
        routes,
        "apply_auto_deadline_to_task",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("planner crashed")),
    )

    with app.test_request_context("/api/tasks/1/auto-plan", method="POST", json={}):
        response, status = routes.auto_plan_existing_task(1)

    assert status == 500
    assert db.rolled_back is True


def test_task_import_model_info_and_analysis(app, monkeypatch):
    subject = make_subject()
    db = FakeDB(subject=subject)
    patch_user_and_db(monkeypatch, db)

    monkeypatch.setattr(
        routes.task_nlp_service.difficulty_ml_service,
        "get_model_info",
        lambda: {"loaded": True},
    )

    with app.test_request_context("/api/task-import/model-info"):
        response, status = routes.task_model_info_api()

    assert status == 200
    assert response.get_json() == {"loaded": True}

    monkeypatch.setattr(
        routes.task_nlp_service,
        "analyze_many",
        lambda **kwargs: [{"title": "Task", "subject": "Фізика"}],
    )
    monkeypatch.setattr(routes, "find_subject_by_name", lambda **kwargs: subject)

    with app.test_request_context(
        "/api/task-import/analyze-text",
        method="POST",
        json={"text": "Зробити лабораторну", "subject": "Фізика"},
    ):
        response, status = routes.analyze_task_text_api()

    assert status == 200
    assert response.get_json()["tasks"][0]["subject_exists"] is True

    monkeypatch.setattr(
        routes.task_file_extractor_service,
        "extract_text",
        lambda filename, file_bytes: "дуже довгий текст завдання для аналізу",
    )

    with app.test_request_context(
        "/api/task-import/analyze-file",
        method="POST",
        data={"file": (BytesIO(b"file"), "task.txt")},
        content_type="multipart/form-data",
    ):
        response, status = routes.analyze_task_file_api()

    assert status == 200
    assert response.get_json()["tasks"][0]["source_filename"] == "task.txt"


@pytest.mark.parametrize(
    ("url", "payload", "expected_error"),
    [
        (
            "/api/task-import/analyze-text",
            {"text": "   "},
            "Текст завдання порожній",
        ),
        (
            "/api/task-import/create-subject",
            {},
            None,
        ),
        (
            "/api/task-import/create-tasks",
            {"tasks": []},
            None,
        ),
    ],
)
def test_task_import_validation_errors(app, monkeypatch, url, payload, expected_error):
    db = FakeDB()
    patch_user_and_db(monkeypatch, db)

    route_func = {
        "/api/task-import/analyze-text": routes.analyze_task_text_api,
        "/api/task-import/create-subject": routes.create_subject_from_task_import_api,
        "/api/task-import/create-tasks": routes.create_tasks_from_import_api,
    }[url]

    with app.test_request_context(url, method="POST", json=payload):
        response, status = route_func()

    assert status == 400
    if expected_error:
        assert response.get_json()["error"] == expected_error


def test_create_subject_from_task_import_existing_and_new(app, monkeypatch):
    subject = make_subject()
    db = FakeDB(subject=subject)
    patch_user_and_db(monkeypatch, db)

    monkeypatch.setattr(routes, "find_subject_by_name", lambda *args, **kwargs: subject)
    monkeypatch.setattr(
        routes,
        "serialize_subject",
        lambda subject: {"id": subject.id, "name": subject.name},
    )

    with app.test_request_context(
        "/api/task-import/create-subject",
        method="POST",
        json={"name": "Фізика"},
    ):
        response, status = routes.create_subject_from_task_import_api()

    assert status == 200
    assert response.get_json()["name"] == "Фізика"

    monkeypatch.setattr(routes, "find_subject_by_name", lambda *args, **kwargs: None)

    with app.test_request_context(
        "/api/task-import/create-subject",
        method="POST",
        json={"name": "Математика"},
    ):
        response, status = routes.create_subject_from_task_import_api()

    assert status == 201
    assert response.get_json()["name"] == "Математика"


def test_create_tasks_from_import_success_and_rollback(app, monkeypatch):
    db = FakeDB()
    patch_user_and_db(monkeypatch, db)

    monkeypatch.setattr(routes, "find_subject_by_name", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes, "get_subject_name_by_id", lambda **kwargs: "Фізика")
    monkeypatch.setattr(routes, "get_existing_deadline_dates", lambda db, user_id: [])
    monkeypatch.setattr(
        routes,
        "create_task_log",
        lambda **kwargs: db.added.append(SimpleNamespace(log=True, **kwargs)),
    )
    monkeypatch.setattr(
        routes,
        "serialize_task",
        lambda task: {"id": task.id, "title": task.title},
    )

    with app.test_request_context(
        "/api/task-import/create-tasks",
        method="POST",
        json={
            "tasks": [
                {
                    "title": "Imported task",
                    "subject": "Фізика",
                    "due_date": "2026-06-01T12:00:00",
                }
            ]
        },
    ):
        response, status = routes.create_tasks_from_import_api()

    assert status == 201
    assert response.get_json()["count"] == 1

    def broken_log(**kwargs):
        raise RuntimeError("broken")

    monkeypatch.setattr(routes, "create_task_log", broken_log)

    with app.test_request_context(
        "/api/task-import/create-tasks",
        method="POST",
        json={"tasks": [{"title": "Task", "due_date": "2026-06-01T12:00:00"}]},
    ):
        response, status = routes.create_tasks_from_import_api()

    assert status == 500
    assert db.rolled_back is True


def test_create_tasks_from_import_auto_planning_error_is_ignored(app, monkeypatch):
    db = FakeDB()
    patch_user_and_db(monkeypatch, db)

    monkeypatch.setattr(routes, "find_subject_by_name", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes, "get_existing_deadline_dates", lambda db, user_id: [])
    monkeypatch.setattr(routes, "get_subject_events", lambda **kwargs: [])
    monkeypatch.setattr(routes, "get_existing_subject_deadline_count", lambda **kwargs: 0)
    monkeypatch.setattr(routes, "build_subject_distribution_index", lambda **kwargs: 0)
    monkeypatch.setattr(
        routes,
        "apply_auto_deadline_to_task",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("planning failed")),
    )
    monkeypatch.setattr(routes, "create_task_log", lambda **kwargs: None)
    monkeypatch.setattr(routes, "serialize_task", lambda task: {"title": task.title})

    with app.test_request_context(
        "/api/task-import/create-tasks",
        method="POST",
        json={"tasks": [{"title": "Task without deadline", "subject": "Math"}]},
    ):
        response, status = routes.create_tasks_from_import_api()

    assert status == 201
    assert response.get_json()["count"] == 1


def test_generate_synthetic_deadline_dataset_success(app, monkeypatch):
    db = FakeDB()
    patch_user_and_db(monkeypatch, db)

    monkeypatch.setattr(
        routes.synthetic_deadline_dataset_service,
        "save_csv",
        lambda: "backend/infrastructure/ml/datasets/deadlines.csv",
    )

    with app.test_request_context("/api/ml/deadline-dataset/generate", method="POST"):
        response = routes.generate_synthetic_deadline_dataset()

    assert response.get_json()["message"] == "Synthetic deadline dataset generated"
