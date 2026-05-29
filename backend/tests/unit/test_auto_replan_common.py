from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from backend.app.routes import common


class FakeDb:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commits += 1


def make_task(**overrides):
    now = datetime.now(UTC)

    values = {
        "id": 1,
        "user_id": 10,
        "event_id": None,
        "subject_id": None,
        "title": "Test task",
        "description": "Description",
        "status": "planned",
        "priority": "medium",
        "due_date": now + timedelta(days=1),
        "completed_at": None,
        "missed_at": None,
        "task_type": "other",
        "keywords": "[]",
        "estimated_duration_hours": 1,
        "difficulty_score": 3,
        "nlp_source": "manual",
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)

    return SimpleNamespace(**values)


def test_fallback_deadline_prediction_preserves_naive_subject_event_datetime():
    subject_start = datetime.utcnow() + timedelta(days=2)
    task = make_task(difficulty_score=3, estimated_duration_hours=1)
    subject_event = SimpleNamespace(start_time=subject_start)

    result = common.fallback_deadline_prediction(
        task=task,
        subject_events=[subject_event],
        mode="subject_based",
    )

    assert result["deadline"] < subject_start
    assert result["deadline"].tzinfo is None
    assert result["confidence"] == 0.72


def test_fallback_deadline_prediction_keeps_aware_subject_event_datetime():
    subject_start = datetime.now(UTC) + timedelta(days=2)
    task = make_task(difficulty_score=3, estimated_duration_hours=1)
    subject_event = SimpleNamespace(start_time=subject_start)

    result = common.fallback_deadline_prediction(
        task=task,
        subject_events=[subject_event],
        mode="subject_based",
    )

    assert result["deadline"] < subject_start
    assert result["deadline"].tzinfo is not None


def test_refresh_task_deadline_status_marks_overdue_task_as_missed():
    task = make_task(
        due_date=datetime.now(UTC) - timedelta(hours=2),
        status="planned",
        completed_at=None,
        missed_at=None,
    )

    changed = common.refresh_task_deadline_status(task, now=datetime.now(UTC))

    assert changed is True
    assert task.status == common.MISSED_TASK_STATUS
    assert task.completed_at is None
    assert task.missed_at is not None


def test_refresh_task_deadline_status_ignores_completed_task():
    task = make_task(
        due_date=datetime.now(UTC) - timedelta(hours=2),
        status="done",
    )

    changed = common.refresh_task_deadline_status(task, now=datetime.now(UTC))

    assert changed is False
    assert task.status == "done"


def test_should_auto_replan_task_detects_only_open_overdue_tasks():
    now = datetime.now(UTC)
    overdue_task = make_task(due_date=now - timedelta(minutes=10), status="planned")
    completed_task = make_task(due_date=now - timedelta(minutes=10), status="done")
    future_task = make_task(due_date=now + timedelta(days=1), status="planned")

    assert common.should_auto_replan_task(overdue_task, now=now) is True
    assert common.should_auto_replan_task(completed_task, now=now) is False
    assert common.should_auto_replan_task(future_task, now=now) is False


def test_set_auto_replan_metadata_adds_frontend_badge_fields(monkeypatch):
    db = FakeDb()
    task = make_task(id=55)

    monkeypatch.setattr(common, "get_task_auto_replan_count", lambda _db, _task_id: 2)

    result = common.set_auto_replan_metadata(db, task)

    assert result is task
    assert task.auto_replan_count == 2
    assert task.auto_replan_limit == common.MAX_AUTO_REPLAN_ATTEMPTS
    assert task.auto_replan_attempts_left == 1
    assert task.auto_replan_limit_reached is False


def test_set_auto_replan_metadata_marks_limit_reached(monkeypatch):
    db = FakeDb()
    task = make_task(id=56)

    monkeypatch.setattr(
        common,
        "get_task_auto_replan_count",
        lambda _db, _task_id: common.MAX_AUTO_REPLAN_ATTEMPTS,
    )

    common.set_auto_replan_metadata(db, task)

    assert task.auto_replan_attempts_left == 0
    assert task.auto_replan_limit_reached is True


def test_serialize_task_returns_auto_replan_metadata_for_task_badges():
    task = make_task(
        auto_replan_count=2,
        auto_replan_limit=3,
        auto_replan_attempts_left=1,
        auto_replan_limit_reached=False,
    )

    result = common.serialize_task(task)

    assert result["auto_replan_count"] == 2
    assert result["auto_replan_limit"] == 3
    assert result["auto_replan_attempts_left"] == 1
    assert result["auto_replan_limit_reached"] is False


def test_auto_replan_missed_task_success_updates_task_and_returns_metadata(monkeypatch):
    db = FakeDb()
    old_deadline = datetime.now(UTC) - timedelta(hours=1)
    new_deadline = datetime.now(UTC) + timedelta(days=1)
    task = make_task(id=70, due_date=old_deadline, status="missed", missed_at=old_deadline)
    block = SimpleNamespace(id=777)

    monkeypatch.setattr(common, "get_task_auto_replan_count", lambda _db, _task_id: 1)
    monkeypatch.setattr(common, "set_auto_replan_metadata", lambda _db, _task: _task)

    def fake_apply_auto_deadline_to_task(**kwargs):
        kwargs["task"].due_date = new_deadline
        return {
            "deadline": new_deadline,
            "confidence": 0.8,
            "reason": "test replan",
        }, block

    monkeypatch.setattr(
        common,
        "apply_auto_deadline_to_task",
        fake_apply_auto_deadline_to_task,
    )

    result = common.auto_replan_missed_task(db=db, user_id=10, task=task)

    assert result["task_id"] == task.id
    assert result["replan_count"] == 2
    assert result["attempts_left"] == 1
    assert result["block_id"] == block.id
    assert task.status == "planned"
    assert task.missed_at is None
    assert len(db.added) == 1


def test_auto_replan_missed_task_respects_attempt_limit(monkeypatch):
    db = FakeDb()
    task = make_task(id=80, due_date=datetime.now(UTC) - timedelta(hours=1), status="missed")

    monkeypatch.setattr(
        common,
        "get_task_auto_replan_count",
        lambda _db, _task_id: common.MAX_AUTO_REPLAN_ATTEMPTS,
    )
    monkeypatch.setattr(common, "has_auto_replan_limit_log", lambda _db, _task_id: False)
    monkeypatch.setattr(common, "set_auto_replan_metadata", lambda _db, _task: _task)

    result = common.auto_replan_missed_task(db=db, user_id=10, task=task)

    assert result is None
    assert task.status == common.MISSED_TASK_STATUS
    assert task.priority == common.HIGH_PRIORITY
    assert len(db.added) == 1
