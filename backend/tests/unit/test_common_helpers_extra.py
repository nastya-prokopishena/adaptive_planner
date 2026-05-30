from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from flask import session

from backend.app.routes import common


class ExtraFakeQuery:
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


class ExtraFakeDB:
    def __init__(self, items=None, first_item=None, count_value=0):
        self.items = items or []
        self.first_item = first_item
        self.count_value = count_value
        self.added = []
        self.closed = False

    def query(self, model):
        return ExtraFakeQuery(
            items=self.items,
            first_item=self.first_item,
            count_value=self.count_value,
        )

    def add(self, item):
        self.added.append(item)

    def close(self):
        self.closed = True


def test_to_aware_utc_and_storage_datetime():
    naive = datetime(2026, 5, 30, 10, 0)
    aware = datetime(2026, 5, 30, 10, 0, tzinfo=UTC)

    assert common.to_aware_utc(None) is None
    assert common.to_aware_utc(naive).tzinfo == UTC
    assert common.to_aware_utc(aware).tzinfo == UTC

    stored = common.to_storage_datetime(aware)

    assert stored.tzinfo is None
    assert stored.hour == 10


def test_refresh_task_deadline_status_marks_missed():
    now = datetime(2026, 5, 30, 12, 0, tzinfo=UTC)

    task = SimpleNamespace(
        due_date=datetime(2026, 5, 29, 12, 0),
        status="planned",
        missed_at=None,
        completed_at=datetime(2026, 5, 29, 13, 0),
        updated_at=None,
    )

    changed = common.refresh_task_deadline_status(task, now=now)

    assert changed is True
    assert task.status == common.MISSED_TASK_STATUS
    assert task.completed_at is None
    assert task.missed_at is not None


def test_refresh_task_deadline_status_ignores_completed_and_empty_task():
    now = datetime(2026, 5, 30, 12, 0, tzinfo=UTC)

    completed_task = SimpleNamespace(
        due_date=datetime(2026, 5, 29, 12, 0),
        status="done",
        missed_at=None,
        completed_at=None,
        updated_at=None,
    )

    assert common.refresh_task_deadline_status(None, now=now) is False
    assert common.refresh_task_deadline_status(completed_task, now=now) is False


def test_should_auto_replan_task_edge_cases():
    now = datetime(2026, 5, 30, 12, 0, tzinfo=UTC)

    overdue = SimpleNamespace(
        due_date=datetime(2026, 5, 29, 12, 0),
        status="planned",
    )
    future = SimpleNamespace(
        due_date=datetime(2026, 6, 1, 12, 0),
        status="planned",
    )
    done = SimpleNamespace(
        due_date=datetime(2026, 5, 29, 12, 0),
        status="completed",
    )

    assert common.should_auto_replan_task(overdue, now=now) is True
    assert common.should_auto_replan_task(future, now=now) is False
    assert common.should_auto_replan_task(done, now=now) is False
    assert common.should_auto_replan_task(None, now=now) is False


def test_get_replan_count_and_limit_log_empty_task_id():
    db = ExtraFakeDB(count_value=2)

    assert common.get_task_auto_replan_count(db, None) == 0
    assert common.has_auto_replan_limit_log(db, None) is False


def test_set_tasks_auto_replan_metadata_updates_all_tasks():
    db = ExtraFakeDB(count_value=1)

    tasks = [
        SimpleNamespace(id=1),
        SimpleNamespace(id=2),
    ]

    result = common.set_tasks_auto_replan_metadata(db, tasks)

    assert result == tasks
    assert tasks[0].auto_replan_count == 1
    assert tasks[1].auto_replan_attempts_left == 2


def test_current_user_returns_none_without_session(app):
    with app.test_request_context("/"):
        assert common.current_user() is None


def test_current_user_loads_user_from_session(app, monkeypatch):
    user = SimpleNamespace(id=1, email="test@example.com")
    db = ExtraFakeDB(first_item=user)

    monkeypatch.setattr(common, "SessionLocal", lambda: db)

    with app.test_request_context("/"):
        session["user_id"] = 1

        result = common.current_user()

    assert result == user
    assert db.closed is True


def test_parse_optional_datetime_accepts_z_and_rejects_invalid():
    result = common.parse_optional_datetime("2026-05-30T10:00:00Z")

    assert result is not None
    assert common.parse_optional_datetime("bad-date") is None
    assert common.parse_optional_datetime(None) is None


def test_serializers_for_event_type_subject_activity_log_and_block():
    now = datetime(2026, 5, 30, 10, 0)

    event_type = SimpleNamespace(
        id=1,
        user_id=2,
        name="Lecture",
        color="#fff",
        is_default=True,
        created_at=now,
    )
    subject = SimpleNamespace(
        id=3,
        user_id=2,
        name="Math",
        teacher="Teacher",
        description="Desc",
        color="#000",
        created_at=now,
    )
    log = SimpleNamespace(
        id=4,
        user_id=2,
        task_id=5,
        action="created",
        old_status=None,
        new_status="planned",
        details="details",
        created_at=now,
    )
    block = SimpleNamespace(
        id=6,
        task_id=5,
        start_time=now,
        end_time=now + timedelta(hours=1),
        source="ai",
        generated_by_ai=True,
        confidence_score=0.8,
        reason="reason",
    )
    task = SimpleNamespace(title="Task")

    assert common.serialize_event_type(event_type)["name"] == "Lecture"
    assert common.serialize_subject(subject)["teacher"] == "Teacher"
    assert common.serialize_activity_log(log)["action"] == "created"

    serialized_block = common.serialize_task_schedule_block(block, task)

    assert serialized_block["id"] == 6
    assert serialized_block["calendar_type"] == "ai_task_block"
    assert "Task" in serialized_block["title"]


def test_create_task_log_adds_log_to_db():
    db = ExtraFakeDB()

    common.create_task_log(
        db=db,
        user_id=1,
        task_id=2,
        action="status_changed",
        old_status="planned",
        new_status="done",
        details="changed",
    )

    assert len(db.added) == 1
    assert db.added[0].action == "status_changed"
    assert db.added[0].new_status == "done"


def test_find_subject_by_name_returns_none_for_empty_name():
    db = ExtraFakeDB()

    assert common.find_subject_by_name(db, user_id=1, subject_name="") is None


def test_resolve_subject_id_parses_int_and_falls_back_to_subject(monkeypatch):
    subject = SimpleNamespace(id=15, name="Math")
    db = ExtraFakeDB(first_item=subject)

    assert common.resolve_subject_id(db, user_id=1, subject_id="12") == 12

    monkeypatch.setattr(common, "find_subject_by_name", lambda **kwargs: subject)

    assert (
        common.resolve_subject_id(
            db,
            user_id=1,
            subject_id="bad-id",
            subject_name="Math",
        )
        == 15
    )


def test_get_subject_name_by_id_empty_and_found():
    subject = SimpleNamespace(id=10, name="Physics")
    db = ExtraFakeDB(first_item=subject)

    assert common.get_subject_name_by_id(db, user_id=1, subject_id=None) is None
    assert common.get_subject_name_by_id(db, user_id=1, subject_id=10) == "Physics"


def test_get_excluded_dates_filters_empty_values():
    event = SimpleNamespace(recurrence_excluded_dates="2026-05-30T10:00:00, ,2026-06-01T10:00:00")

    result = common.get_excluded_dates(event)

    assert result == ["2026-05-30T10:00:00", "2026-06-01T10:00:00"]


def test_get_event_occurrences_filters_excluded_dates(monkeypatch):
    start = datetime(2026, 5, 30, 10, 0)
    end = datetime(2026, 5, 30, 11, 0)
    second_start = datetime(2026, 6, 1, 10, 0)
    second_end = datetime(2026, 6, 1, 11, 0)

    event = SimpleNamespace(
        start_time=start,
        end_time=end,
        recurrence_type="weekly",
        recurrence_interval=1,
        recurrence_unit=None,
        recurrence_days=None,
        recurrence_end_type="count",
        recurrence_end_date=None,
        recurrence_count=2,
        recurrence_excluded_dates=start.isoformat(),
    )

    monkeypatch.setattr(
        common,
        "generate_occurrences",
        lambda **kwargs: [(start, end), (second_start, second_end)],
    )

    result = common.get_event_occurrences(event)

    assert result == [(second_start, second_end)]


def test_has_time_conflict_returns_matching_event(monkeypatch):
    start = datetime(2026, 5, 30, 10, 0)
    end = datetime(2026, 5, 30, 11, 0)

    existing = SimpleNamespace(
        id=1,
        start_time=start,
        end_time=end,
    )

    db = ExtraFakeDB(items=[existing])

    monkeypatch.setattr(common, "get_candidate_occurrences", lambda *args, **kwargs: [(start, end)])
    monkeypatch.setattr(common, "get_event_occurrences", lambda event: [(start, end)])

    result = common.has_time_conflict(
        db=db,
        user_id=1,
        start_time=start,
        end_time=end,
        recurrence_data={
            "recurrence_type": "none",
            "recurrence_interval": 1,
            "recurrence_unit": None,
            "recurrence_days": "",
            "recurrence_end_type": "never",
            "recurrence_end_date": None,
            "recurrence_count": None,
        },
    )

    assert result == existing


def test_has_time_conflict_returns_none_when_no_overlap(monkeypatch):
    start = datetime(2026, 5, 30, 10, 0)
    end = datetime(2026, 5, 30, 11, 0)

    existing = SimpleNamespace(
        id=1,
        start_time=start + timedelta(hours=3),
        end_time=end + timedelta(hours=3),
    )

    db = ExtraFakeDB(items=[existing])

    monkeypatch.setattr(common, "get_candidate_occurrences", lambda *args, **kwargs: [(start, end)])
    monkeypatch.setattr(
        common,
        "get_event_occurrences",
        lambda event: [(existing.start_time, existing.end_time)],
    )

    result = common.has_time_conflict(
        db=db,
        user_id=1,
        start_time=start,
        end_time=end,
        recurrence_data={
            "recurrence_type": "none",
            "recurrence_interval": 1,
            "recurrence_unit": None,
            "recurrence_days": "",
            "recurrence_end_type": "never",
            "recurrence_end_date": None,
            "recurrence_count": None,
        },
    )

    assert result is None


def test_sync_google_events_to_db_skips_user_without_credentials():
    db = ExtraFakeDB()
    user = SimpleNamespace(id=1, google_credentials=None)

    result = common.sync_google_events_to_db(user, db)

    assert result is None
    assert db.added == []


def test_build_subject_distribution_index_all_branches():
    assert (
        common.build_subject_distribution_index(
            existing_count=2,
            task_position=0,
            task_total=1,
            subject_events_count=5,
        )
        == 2
    )

    assert (
        common.build_subject_distribution_index(
            existing_count=1,
            task_position=1,
            task_total=3,
            subject_events_count=10,
        )
        == 4
    )

    assert (
        common.build_subject_distribution_index(
            existing_count=1,
            task_position=2,
            task_total=5,
            subject_events_count=2,
        )
        == 3
    )


def test_apply_auto_deadline_to_task_success(monkeypatch):
    deadline = datetime(2026, 6, 1, 20, 0)

    task = SimpleNamespace(
        id=1,
        user_id=1,
        subject_id=10,
        due_date=None,
        updated_at=None,
    )
    block = SimpleNamespace(id=99)
    db = ExtraFakeDB()

    monkeypatch.setattr(common, "get_subject_events", lambda **kwargs: [])
    monkeypatch.setattr(common, "get_user_calendar_events", lambda **kwargs: [])
    monkeypatch.setattr(common, "get_existing_subject_deadline_count", lambda **kwargs: 0)
    monkeypatch.setattr(
        common,
        "safe_predict_deadline",
        lambda **kwargs: {
            "deadline": deadline,
            "confidence": 0.8,
            "reason": "planned",
        },
    )
    monkeypatch.setattr(
        common.task_schedule_block_service,
        "recreate_block_for_task",
        lambda **kwargs: block,
    )

    prediction, result_block = common.apply_auto_deadline_to_task(
        db=db,
        user_id=1,
        task=task,
        mode="best_time",
    )

    assert task.due_date == deadline
    assert prediction["deadline"] == deadline
    assert result_block == block


def test_parse_datetime_accepts_iso_with_z():
    parsed = common.parse_datetime("2026-05-28T10:30:00Z")

    assert parsed is not None
    assert parsed.isoformat().startswith("2026-05-28T10:30:00")


def test_parse_datetime_returns_none_for_invalid_value():
    assert common.parse_datetime("not-a-date") is None
    assert common.parse_datetime(None) is None


def test_parse_google_event_time_reads_datetime_and_date():
    parsed_datetime = common.parse_google_event_time({"dateTime": "2026-05-28T12:00:00Z"})
    parsed_date = common.parse_google_event_time({"date": "2026-05-28"})

    assert parsed_datetime is not None
    assert parsed_date.hour == 0
    assert parsed_date.minute == 0


def test_parse_recurrence_payload_builds_weekly_rule():
    start = datetime(2026, 5, 25, 10, 0)

    result = common.parse_recurrence_payload(
        {
            "recurrence": {
                "type": "weekly",
                "interval": 1,
                "days": ["MO", "WE"],
                "endType": "count",
                "count": 5,
            }
        },
        start,
    )

    assert result["recurrence_type"] == "weekly"
    assert result["recurrence_interval"] == 1
    assert result["recurrence_days"] == "MO,WE"
    assert "RRULE" in result["recurrence_rule"]


def test_parse_recurrence_payload_keeps_existing_event_when_not_provided():
    existing = SimpleNamespace(
        recurrence_type="weekly",
        recurrence_interval=2,
        recurrence_unit=None,
        recurrence_days="TU",
        recurrence_end_type="never",
        recurrence_end_date=None,
        recurrence_count=None,
        recurrence_rule="RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=TU",
    )

    result = common.parse_recurrence_payload({}, datetime.utcnow(), existing)

    assert result["recurrence_type"] == "weekly"
    assert result["recurrence_interval"] == 2
    assert result["recurrence_rule"] == "RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=TU"


def test_serialize_event_with_recurrence_and_occurrence():
    event = SimpleNamespace(
        id=7,
        title="Math",
        start_time=datetime(2026, 5, 28, 10, 0),
        end_time=datetime(2026, 5, 28, 11, 30),
        source="local",
        google_event_id=None,
        recurrence_type="weekly",
        recurrence_interval=1,
        recurrence_unit=None,
        recurrence_days="MO,WE",
        recurrence_end_type="count",
        recurrence_end_date=None,
        recurrence_count=4,
    )

    occurrence_start = datetime(2026, 6, 1, 10, 0)
    occurrence_end = datetime(2026, 6, 1, 11, 30)
    result = common.serialize_event(event, occurrence_start, occurrence_end)

    assert result["id"] == "7__2026-06-01T10:00:00"
    assert result["master_id"] == 7
    assert result["recurrence"]["days"] == ["MO", "WE"]
    assert result["is_recurring"] is True


def test_serialize_task_handles_keywords_json_and_dates():
    now = datetime(2026, 5, 28, 10, 0)
    task = SimpleNamespace(
        id=1,
        user_id=2,
        event_id=None,
        subject_id=3,
        title="Lab",
        description="Do lab",
        status="planned",
        priority="high",
        due_date=now,
        completed_at=None,
        missed_at=None,
        task_type="laboratory",
        keywords='["python", "tests"]',
        estimated_duration_hours=2,
        difficulty_score=4,
        nlp_source="manual",
        created_at=now,
        updated_at=now,
    )

    result = common.serialize_task(task)

    assert result["title"] == "Lab"
    assert result["keywords"] == ["python", "tests"]
    assert result["due_date"] == now.isoformat()


def test_serialize_task_handles_bad_keywords_json():
    task = SimpleNamespace(
        id=1,
        user_id=2,
        event_id=None,
        subject_id=None,
        title="Task",
        description=None,
        status="planned",
        priority="medium",
        due_date=None,
        completed_at=None,
        missed_at=None,
        task_type="other",
        keywords="not-json",
        estimated_duration_hours=1,
        difficulty_score=3,
        nlp_source="manual",
        created_at=None,
        updated_at=None,
    )

    result = common.serialize_task(task)

    assert result["keywords"] == []


def test_excluded_dates_are_added_only_once():
    event = SimpleNamespace(recurrence_excluded_dates="")
    occurrence = datetime(2026, 5, 28, 10, 0)

    common.add_excluded_date(event, occurrence)
    common.add_excluded_date(event, occurrence)

    assert common.get_excluded_dates(event) == [occurrence.isoformat()]


def test_event_matches_subject_by_id_or_name():
    event = SimpleNamespace(subject_id=5, title="Algorithms lecture")

    assert common.event_matches_subject(event, subject_id=5) is True
    assert common.event_matches_subject(event, subject_name="algorithms") is True
    assert common.event_matches_subject(event, subject_id=7, subject_name="math") is False


def test_normalize_deadline_mode_aliases():
    assert common.normalize_deadline_mode("subject") == "subject_based"
    assert common.normalize_deadline_mode("free_time") == "best_free_time"
    assert common.normalize_deadline_mode(None) == "subject_based"


def test_fallback_deadline_prediction_uses_subject_event():
    now = datetime.utcnow()
    task = SimpleNamespace(difficulty_score=3, estimated_duration_hours=1)
    subject_event = SimpleNamespace(start_time=now + timedelta(days=2))

    result = common.fallback_deadline_prediction(
        task=task,
        subject_events=[subject_event],
        mode="subject_based",
    )

    assert result["deadline"] < subject_event.start_time
    assert result["confidence"] == 0.72


def test_safe_predict_deadline_falls_back_on_ml_error(monkeypatch):
    task = SimpleNamespace(difficulty_score=2, estimated_duration_hours=1)

    def raise_error(**kwargs):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(common.ml_deadline_service, "predict_deadline", raise_error)

    result = common.safe_predict_deadline(task=task, subject_events=[], calendar_events=[])

    assert "deadline" in result
    assert result["confidence"] == 0.55
