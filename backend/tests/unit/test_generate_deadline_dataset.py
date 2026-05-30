from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from backend.infrastructure.ml.dataset_builder.generate_deadline_dataset import (
    calculate_day_load_score,
    clamp,
    generate_synthetic_row,
    get_free_hours_today,
    get_hours_until_next_subject_event,
    get_priority_score,
    get_task_type_score,
)


@pytest.mark.parametrize(
    ("value", "minimum", "maximum", "expected"),
    [
        (15, 0, 10, 10),
        (-1, 0, 10, 0),
    ],
)
def test_clamp(value, minimum, maximum, expected):
    assert clamp(value, minimum, maximum) == expected


@pytest.mark.parametrize(
    ("priority", "expected"),
    [
        ("urgent", 4),
        ("bad", 2),
    ],
)
def test_priority_score(priority, expected):
    assert get_priority_score(priority) == expected


@pytest.mark.parametrize(
    ("task_type", "expected"),
    [
        ("project", 4),
        ("unknown", 2),
    ],
)
def test_task_type_score(task_type, expected):
    assert get_task_type_score(task_type) == expected


def test_day_load_and_free_hours_are_calculated_from_events():
    now = datetime.now(UTC)
    event = SimpleNamespace(
        start_time=now,
        end_time=now + timedelta(hours=4),
    )

    assert calculate_day_load_score([event]) > 0
    assert get_free_hours_today([event]) < 14


def test_get_hours_until_next_subject_event():
    now = datetime.now(UTC)
    task = SimpleNamespace(subject_id=1)
    event = SimpleNamespace(subject_id=1, start_time=now + timedelta(hours=10))

    result = get_hours_until_next_subject_event(task, [event], now)

    assert result >= 1


def test_generate_synthetic_row():
    row = generate_synthetic_row()

    assert row["difficulty_score"] >= 1
    assert row["recommended_deadline_hours"] >= 1
