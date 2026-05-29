from datetime import datetime, timedelta
from types import SimpleNamespace

from backend.app.routes import analytics_routes as routes


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
    def __init__(self, tasks=None, events=None, blocks=None, task=None):
        self.tasks = tasks or []
        self.events = events or []
        self.blocks = blocks or []
        self.task = task
        self.added = []
        self.commits = 0
        self.closed = False

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "Task":
            return FakeQuery(self.tasks, self.task or (self.tasks[0] if self.tasks else None))
        if name == "Event":
            return FakeQuery(self.events)
        if name == "TaskScheduleBlock":
            return FakeQuery(self.blocks)
        return FakeQuery([])

    def add(self, item):
        if getattr(item, "id", None) is None:
            item.id = 99
        self.added.append(item)

    def commit(self):
        self.commits += 1

    def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = 99

    def close(self):
        self.closed = True


def patch_user_and_db(monkeypatch, db, user=None):
    monkeypatch.setattr(routes, "current_user", lambda: user or SimpleNamespace(id=1))
    monkeypatch.setattr(routes, "SessionLocal", lambda: db)


def test_analytics_dashboard_api_success(app, monkeypatch):
    db = FakeDB(tasks=[SimpleNamespace(id=1)], events=[SimpleNamespace(id=2)])
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(
        routes.analytics_service,
        "build_dashboard_analytics",
        lambda **kwargs: {"summary": {"total": len(kwargs["tasks"])}},
    )

    with app.test_request_context("/api/analytics/dashboard?date_from=2026-05-01"):
        response, status = routes.analytics_dashboard_api()

    assert status == 200
    assert response.get_json()["summary"]["total"] == 1
    assert db.closed is True


def test_analytics_dashboard_api_unauthorized(app, monkeypatch):
    monkeypatch.setattr(routes, "current_user", lambda: None)

    with app.test_request_context("/api/analytics/dashboard"):
        response, status = routes.analytics_dashboard_api()

    assert status == 401


def test_productivity_predict_api_success(app, monkeypatch):
    db = FakeDB(tasks=[SimpleNamespace(id=1)], events=[SimpleNamespace(id=2)])
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(
        routes.productivity_model_service,
        "predict_day",
        lambda **kwargs: {"productivity_score": 88},
    )

    with app.test_request_context(
        "/api/ml/productivity/predict",
        method="POST",
        json={"date": "2026-05-29T10:00:00"},
    ):
        response, status = routes.productivity_predict_api()

    assert status == 200
    assert response.get_json()["productivity_score"] == 88


def test_replan_task_api_returns_404_when_task_missing(app, monkeypatch):
    db = FakeDB(task=None)
    patch_user_and_db(monkeypatch, db)

    with app.test_request_context("/api/tasks/999/replan", method="POST", json={}):
        response, status = routes.replan_task_api(999)

    assert status == 404


def test_replan_task_api_returns_409_when_no_slot(app, monkeypatch):
    task = SimpleNamespace(
        id=1,
        title="Task",
        status="missed",
        estimated_duration_hours=2,
        subject_id=3,
        event_id=None,
        updated_at=None,
        missed_at=datetime.utcnow(),
    )
    db = FakeDB(task=task)
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(routes, "plan_task_with_ortools", lambda **kwargs: None)

    with app.test_request_context("/api/tasks/1/replan", method="POST", json={}):
        response, status = routes.replan_task_api(1)

    assert status == 409
    assert response.get_json()["error"] == "No free slot"


def test_replan_task_api_success(app, monkeypatch):
    task = SimpleNamespace(
        id=1,
        title="Task",
        status="missed",
        estimated_duration_hours=1,
        subject_id=3,
        event_id=None,
        updated_at=None,
        missed_at=datetime.utcnow(),
    )
    db = FakeDB(task=task)
    patch_user_and_db(monkeypatch, db)

    start = datetime(2026, 5, 29, 12, 0)
    monkeypatch.setattr(
        routes,
        "plan_task_with_ortools",
        lambda **kwargs: {"events": [{"start": start, "end": start + timedelta(hours=1)}]},
    )
    monkeypatch.setattr(routes, "create_task_log", lambda **kwargs: None)
    monkeypatch.setattr(
        routes, "serialize_task", lambda task: {"id": task.id, "status": task.status}
    )
    monkeypatch.setattr(
        routes, "serialize_event", lambda event: {"id": event.id, "title": event.title}
    )

    with app.test_request_context("/api/tasks/1/replan", method="POST", json={}):
        response, status = routes.replan_task_api(1)

    data = response.get_json()
    assert status == 201
    assert data["task"]["status"] == "planned"
    assert data["event"]["title"].startswith("Переплановано")


def test_generate_ml_task_plan_success(app, monkeypatch):
    block = SimpleNamespace(task_id=10)
    task = SimpleNamespace(id=10, title="Task")
    db = FakeDB(tasks=[task])
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(routes.ml_task_planner_service, "plan_tasks", lambda **kwargs: [block])
    monkeypatch.setattr(
        routes,
        "serialize_task_schedule_block",
        lambda block, task: {"task_id": block.task_id, "title": task.title},
    )

    with app.test_request_context("/api/ml/plan-tasks", method="POST", json={"days": 3}):
        response = routes.generate_ml_task_plan()

    assert response.get_json()["blocks"][0]["task_id"] == 10


def test_unified_calendar_success(app, monkeypatch):
    event = SimpleNamespace(id=1, title="Event")
    task = SimpleNamespace(id=2, title="Task", due_date=datetime(2026, 5, 29, 10, 0))
    block = SimpleNamespace(task_id=2)
    db = FakeDB(tasks=[task], events=[event], blocks=[block])
    patch_user_and_db(monkeypatch, db)
    monkeypatch.setattr(
        routes, "serialize_event", lambda event: {"id": event.id, "title": event.title}
    )
    monkeypatch.setattr(
        routes,
        "serialize_task_schedule_block",
        lambda block, task: {"id": f"block-{block.task_id}", "calendar_type": "task_block"},
    )

    with app.test_request_context("/api/unified-calendar"):
        response = routes.get_unified_calendar()

    data = response.get_json()
    assert len(data) == 3
    assert data[0]["calendar_type"] == "fixed_event"
    assert data[1]["calendar_type"] == "task_deadline"
