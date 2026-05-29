from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from backend.infrastructure.ml.dataset_builder.generate_deadline_dataset import (
    calculate_day_load_score,
    clamp,
    generate_synthetic_row,
    get_free_hours_today,
    get_hours_until_next_subject_event,
    get_priority_score,
    get_task_type_score,
)


def test_clamp():
    assert clamp(15, 0, 10) == 10
    assert clamp(-1, 0, 10) == 0


def test_priority_score():
    assert get_priority_score("urgent") == 4
    assert get_priority_score("bad") == 2


def test_task_type_score():
    assert get_task_type_score("project") == 4
    assert get_task_type_score("unknown") == 2


def test_day_load_score():
    now = datetime.now(UTC)

    event = SimpleNamespace(
        start_time=now,
        end_time=now + timedelta(hours=3),
    )

    assert calculate_day_load_score([event]) > 0


def test_get_free_hours():
    now = datetime.now(UTC)

    event = SimpleNamespace(
        start_time=now,
        end_time=now + timedelta(hours=4),
    )

    result = get_free_hours_today([event])

    assert result < 14


def test_get_hours_until_next_subject_event():
    now = datetime.now(UTC)

    task = SimpleNamespace(subject_id=1)

    event = SimpleNamespace(
        subject_id=1,
        start_time=now + timedelta(hours=10),
    )

    result = get_hours_until_next_subject_event(
        task,
        [event],
        now,
    )

    assert result >= 1


def test_generate_synthetic_row():
    row = generate_synthetic_row()

    assert row["difficulty_score"] >= 1
    assert row["recommended_deadline_hours"] >= 1
