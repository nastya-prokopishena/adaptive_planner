from datetime import datetime, timedelta
from types import SimpleNamespace

from backend.infrastructure.ml.export_schedule_load_dataset import (
    aggregate_events_for_day,
    calculate_schedule_load_score,
    calculate_union_hours,
    detect_event_type,
    empty_row,
    event_duplicate_key,
    merge_intervals,
    normalize_text,
    should_skip_event,
)


def make_event(title="Лекція з Python", hours=2):
    start = datetime(2026, 5, 29, 10, 0)
    return SimpleNamespace(
        title=title,
        start_time=start,
        end_time=start + timedelta(hours=hours),
        subject_id=1,
        event_type_id=1,
    )


def test_normalize_text():
    assert normalize_text("  ТЕСТ  ") == "тест"
    assert normalize_text(None) == ""


def test_detect_event_type_by_title():
    assert detect_event_type(make_event("Лекція з математики")) == "lecture"
    assert detect_event_type(make_event("Лабораторна робота")) == "lab"
    assert detect_event_type(make_event("Практична робота")) == "practice"
    assert detect_event_type(make_event("Іспит")) == "exam"
    assert detect_event_type(make_event("Консультація")) == "consultation"
    assert detect_event_type(make_event("Робота")) == "work"
    assert detect_event_type(make_event("Тренування в залі")) == "personal"
    assert detect_event_type(make_event("Звичайна пара")) == "study"


def test_should_skip_event():
    assert should_skip_event(make_event(hours=0), 0) is True
    assert should_skip_event(make_event(hours=8), 8) is True
    assert should_skip_event(make_event("Потяг Львів Одеса", hours=2), 2) is True
    assert should_skip_event(make_event("Лекція", hours=2), 2) is False


def test_event_duplicate_key_contains_stable_values():
    event = make_event()

    key = event_duplicate_key(event)

    assert key[0] == "лекція з python"
    assert key[3] == 1
    assert key[4] == 1


def test_merge_intervals_and_union_hours():
    start = datetime(2026, 5, 29, 10, 0)

    intervals = [
        (start, start + timedelta(hours=2)),
        (start + timedelta(hours=1), start + timedelta(hours=3)),
        (start + timedelta(hours=4), start + timedelta(hours=5)),
    ]

    merged = merge_intervals(intervals)

    assert len(merged) == 2
    assert calculate_union_hours(intervals) == 4


def test_aggregate_events_for_day():
    row = empty_row("2026-05-29")
    start = datetime(2026, 5, 29, 10, 0)

    row["_events"].append(
        {
            "start": start,
            "end": start + timedelta(hours=2),
            "type": "lecture",
        }
    )

    row["_events"].append(
        {
            "start": start + timedelta(hours=3),
            "end": start + timedelta(hours=4),
            "type": "lab",
        }
    )

    aggregate_events_for_day(row)

    assert row["total_event_hours"] == 3
    assert row["number_of_events"] == 2
    assert row["lecture_hours"] == 2
    assert row["lab_hours"] == 1


def test_calculate_schedule_load_score_bounds_result():
    row = empty_row("2026-05-29")
    row["lecture_hours"] = 2
    row["lab_hours"] = 3
    row["number_of_tasks"] = 2
    row["total_task_difficulty"] = 8
    row["completion_rate"] = 40
    row["missed_rate"] = 50
    row["day_span_hours"] = 11

    score = calculate_schedule_load_score(row)

    assert 0 <= score <= 100
