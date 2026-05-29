from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from backend.application.ml_task_planner_service import MLTaskPlannerService


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
    def __init__(self, tasks=None, events=None, blocks=None, existing_block=None):
        self.tasks = tasks or []
        self.events = events or []
        self.blocks = blocks or []
        self.existing_block = existing_block
        self.added = []
        self.flushed = False
        self.committed = False

    def query(self, model):
        model_name = getattr(model, "__name__", "")
        if model_name == "Task":
            return FakeQuery(self.tasks)
        if model_name == "Event":
            return FakeQuery(self.events)
        if model_name == "TaskScheduleBlock":
            return FakeQuery(self.blocks, self.existing_block)
        return FakeQuery([])

    def add(self, value):
        self.added.append(value)

    def flush(self):
        self.flushed = True

    def commit(self):
        self.committed = True


def make_task(task_id=1, hours=3, status="planned"):
    return SimpleNamespace(
        id=task_id,
        estimated_duration_hours=hours,
        status=status,
        due_date=datetime.now(UTC) + timedelta(days=1),
    )


def make_interval(start_hour=9, duration_hours=1):
    start = datetime(2026, 5, 29, start_hour, 0, tzinfo=UTC)
    return SimpleNamespace(start_time=start, end_time=start + timedelta(hours=duration_hours))


def test_get_busy_intervals_combines_events_and_blocks():
    service = MLTaskPlannerService()
    event = make_interval(9, 1)
    block = make_interval(12, 2)
    db = FakeDB(events=[event], blocks=[block])

    result = service.get_busy_intervals(
        db=db,
        user_id=1,
        start_date=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
        end_date=datetime(2026, 5, 30, 8, 0, tzinfo=UTC),
    )

    assert result == [(event.start_time, event.end_time), (block.start_time, block.end_time)]


def test_overlaps_detects_intersection_and_free_range():
    service = MLTaskPlannerService()
    busy_start = datetime(2026, 5, 29, 10, 0, tzinfo=UTC)
    busy_end = busy_start + timedelta(hours=1)

    assert service.overlaps(
        busy_start + timedelta(minutes=30),
        busy_end + timedelta(minutes=30),
        [(busy_start, busy_end)],
    )
    assert not service.overlaps(busy_end, busy_end + timedelta(hours=1), [(busy_start, busy_end)])


def test_find_free_slot_skips_busy_interval():
    service = MLTaskPlannerService()
    start = datetime(2026, 5, 29, 8, 15, tzinfo=UTC)
    end = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    busy = [
        (
            datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
            datetime(2026, 5, 29, 9, 30, tzinfo=UTC),
        )
    ]

    slot_start, slot_end = service.find_free_slot(
        busy_intervals=busy,
        start_date=start,
        end_date=end,
        duration_hours=1,
    )

    assert slot_start == datetime(2026, 5, 29, 9, 30, tzinfo=UTC)
    assert slot_end == datetime(2026, 5, 29, 10, 30, tzinfo=UTC)


def test_find_free_slot_returns_none_when_day_is_full():
    service = MLTaskPlannerService()
    start = datetime(2026, 5, 29, 8, 0, tzinfo=UTC)
    end = datetime(2026, 5, 29, 10, 0, tzinfo=UTC)

    slot_start, slot_end = service.find_free_slot(
        busy_intervals=[(start, end)],
        start_date=start,
        end_date=end,
        duration_hours=1,
    )

    assert slot_start is None
    assert slot_end is None


def test_plan_tasks_returns_empty_without_tasks():
    service = MLTaskPlannerService()
    db = FakeDB(tasks=[])

    result = service.plan_tasks(db=db, user_id=1, days=7)

    assert result == []
    assert db.committed is False


def test_plan_tasks_skips_task_with_existing_block():
    service = MLTaskPlannerService()
    existing_block = SimpleNamespace(task_id=1)
    db = FakeDB(tasks=[make_task()], existing_block=existing_block)

    result = service.plan_tasks(db=db, user_id=1, days=7)

    assert result == []
    assert db.added == []
    assert db.committed is True


def test_plan_tasks_creates_block_for_task_without_existing_block():
    service = MLTaskPlannerService()
    db = FakeDB(tasks=[make_task(task_id=5, hours=5)])

    result = service.plan_tasks(db=db, user_id=10, days=1)

    assert len(result) == 1
    assert len(db.added) == 1
    assert db.flushed is True
    assert db.committed is True

    block = result[0]
    assert block.user_id == 10
    assert block.task_id == 5
    assert block.generated_by_ai is True
    assert block.source == "ml_planner"
    assert block.confidence_score == 0.75
    assert block.end_time - block.start_time == timedelta(hours=2)
