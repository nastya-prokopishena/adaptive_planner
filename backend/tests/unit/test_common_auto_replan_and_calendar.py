import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from backend.app.routes import common


class FakeQuery:
    def __init__(self, items=None, first_item=None, count_value=0):
        self.items = items or []
        self.first_item = first_item
        self.count_value = count_value

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

    def count(self):
        return self.count_value


class FakeDB:
    def __init__(self, events=None, tasks=None, subject=None, logs_count=0, limit_log=None):
        self.events = events or []
        self.tasks = tasks or []
        self.subject = subject
        self.logs_count = logs_count
        self.limit_log = limit_log
        self.added = []
        self.committed = False

    def query(self, model):
        name = getattr(model, "__name__", "")

        if name == "Event":
            return FakeQuery(self.events)

        if name == "Task":
            return FakeQuery(self.tasks, count_value=len(self.tasks))

        if name == "Subject":
            return FakeQuery(first_item=self.subject)

        if name == "TaskActivityLog":
            return FakeQuery(first_item=self.limit_log, count_value=self.logs_count)

        return FakeQuery([])

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.committed = True


def make_event(title="Фізика", days=1, recurrence_type="none"):
    start = datetime.now(UTC) + timedelta(days=days)
    return SimpleNamespace(
        id=1,
        master_id=1,
        title=title,
        start_time=start,
        end_time=start + timedelta(hours=1),
        subject_id=10,
        source="local",
        recurrence_type=recurrence_type,
        recurrence_interval=1,
        recurrence_unit=None,
        recurrence_days=None,
        recurrence_end_type="after",
        recurrence_end_date=None,
        recurrence_count=2,
        recurrence_rule=None,
        recurrence_excluded_dates=None,
    )


def make_task(task_id=1, due_days=-1, status="planned"):
    return SimpleNamespace(
        id=task_id,
        title="Task",
        status=status,
        due_date=datetime.now(UTC) + timedelta(days=due_days),
        missed_at=None,
        completed_at=None,
        updated_at=None,
        priority="medium",
        subject_id=10,
        estimated_duration_hours=1,
        difficulty_score=3,
    )


def test_set_auto_replan_metadata_sets_limit_values():
    task = make_task()
    db = FakeDB(logs_count=2)

    result = common.set_auto_replan_metadata(db, task)

    assert result.auto_replan_count == 2
    assert result.auto_replan_limit == common.MAX_AUTO_REPLAN_ATTEMPTS
    assert result.auto_replan_attempts_left == 1
    assert result.auto_replan_limit_reached is False


def test_auto_replan_missed_task_marks_limit_reached(monkeypatch):
    task = make_task(status="missed")
    db = FakeDB(logs_count=common.MAX_AUTO_REPLAN_ATTEMPTS, limit_log=None)

    monkeypatch.setattr(common, "create_task_log", lambda **kwargs: db.added.append(kwargs))

    result = common.auto_replan_missed_task(db=db, user_id=1, task=task)

    assert result is None
    assert task.status == common.MISSED_TASK_STATUS
    assert task.priority == common.HIGH_PRIORITY
    assert db.added[0]["action"] == common.AUTO_REPLAN_LIMIT_ACTION


def test_auto_replan_missed_task_success(monkeypatch):
    task = make_task(status="missed")
    db = FakeDB(logs_count=1)
    block = SimpleNamespace(id=77)
    new_deadline = datetime.now(UTC) + timedelta(days=3)

    monkeypatch.setattr(
        common,
        "apply_auto_deadline_to_task",
        lambda **kwargs: (
            {
                "deadline": new_deadline,
                "confidence": 0.8,
                "reason": "test reason",
            },
            block,
        ),
    )
    monkeypatch.setattr(common, "create_task_log", lambda **kwargs: db.added.append(kwargs))

    result = common.auto_replan_missed_task(db=db, user_id=1, task=task)

    assert result["task_id"] == task.id
    assert result["block_id"] == 77
    assert result["replan_count"] == 2
    assert task.status == "planned"


def test_get_subject_events_expands_recurring(monkeypatch):
    event = make_event(recurrence_type="weekly")
    db = FakeDB(events=[event])
    monkeypatch.setattr(
        common,
        "get_event_occurrences",
        lambda event: [
            (datetime.now(UTC) + timedelta(days=1), datetime.now(UTC) + timedelta(days=1, hours=1)),
            (
                datetime.now(UTC) - timedelta(days=1),
                datetime.now(UTC) - timedelta(days=1, hours=-1),
            ),
        ],
    )

    result = common.get_subject_events(db=db, user_id=1, subject_id=10)

    assert len(result) == 1
    assert result[0].master_id == event.id


def test_get_user_calendar_events_filters_future_events(monkeypatch):
    future = make_event(title="Future", days=2)
    past = make_event(title="Past", days=-2)
    db = FakeDB(events=[future, past])

    result = common.get_user_calendar_events(db=db, user_id=1)

    assert len(result) == 1
    assert result[0].title == "Future"


def test_get_existing_deadline_dates_returns_future_dates():
    future = make_task(due_days=2)
    past = make_task(task_id=2, due_days=-2)
    db = FakeDB(tasks=[future, past])

    result = common.get_existing_deadline_dates(db=db, user_id=1)

    assert future.due_date.date() in result
    assert past.due_date.date() in result


def test_sync_google_events_to_db_adds_and_updates_events(monkeypatch):
    existing = make_event()
    db = FakeDB(events=[existing])
    user = SimpleNamespace(id=1, google_credentials=json.dumps({"token": "x"}))

    google_events = [
        {
            "id": "google-1",
            "summary": "Updated",
            "start": {"dateTime": "2026-05-29T10:00:00+00:00"},
            "end": {"dateTime": "2026-05-29T11:00:00+00:00"},
        },
        {
            "id": "google-2",
            "summary": "New",
            "start": {"date": "2026-05-30"},
            "end": {"date": "2026-05-31"},
        },
        {"id": None},
    ]

    calls = {"index": 0}

    class QueryByGoogleId(FakeQuery):
        def filter_by(self, **kwargs):
            if kwargs.get("google_event_id") == "google-1":
                self.first_item = existing
            else:
                self.first_item = None
            return self

    def query(model):
        return QueryByGoogleId(db.events)

    db.query = query

    monkeypatch.setattr(
        common.schedule_service, "get_google_events", lambda *args, **kwargs: google_events
    )

    common.sync_google_events_to_db(user, db)

    assert existing.title == "Updated"
    assert len(db.added) == 1
    assert db.added[0].title == "New"
    assert db.committed is True
