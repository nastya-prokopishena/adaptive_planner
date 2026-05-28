from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from backend.domain.services.auto_planner import (
    build_candidate_slots,
    plan_task_with_ortools,
)


def test_auto_planner_rejects_empty_title():
    with pytest.raises(ValueError, match="Title is required"):
        plan_task_with_ortools(
            existing_events=[],
            title="",
            duration_minutes=60,
            date_from="2026-05-01",
            date_to="2026-05-02",
        )


def test_auto_planner_rejects_invalid_duration():
    with pytest.raises(ValueError, match="Duration must be greater than zero"):
        plan_task_with_ortools(
            existing_events=[],
            title="Test task",
            duration_minutes=0,
            date_from="2026-05-01",
            date_to="2026-05-02",
        )


def test_build_candidate_slots_excludes_busy_time():
    date_from = datetime.now() + timedelta(days=2)
    date_to = date_from + timedelta(days=1)

    busy_event = SimpleNamespace(
        start_time=date_from.replace(hour=10, minute=0, second=0, microsecond=0),
        end_time=date_from.replace(hour=11, minute=0, second=0, microsecond=0),
        recurrence_type="none",
    )

    candidates = build_candidate_slots(
        existing_events=[busy_event],
        date_from=date_from,
        date_to=date_to,
        duration_minutes=60,
        day_start="10:00",
        day_end="12:00",
    )

    assert candidates
    assert all(
        not (
            item["start"] < busy_event.end_time
            and item["end"] > busy_event.start_time
        )
        for item in candidates
    )
