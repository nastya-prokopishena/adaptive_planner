from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from backend.app.routes import common


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
