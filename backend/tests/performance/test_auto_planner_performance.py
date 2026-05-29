from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from backend.domain.services.auto_planner import build_candidate_slots, plan_task_with_ortools


def test_build_candidate_slots_performance(benchmark):
    date_from = datetime.now() + timedelta(days=1)
    date_to = date_from + timedelta(days=14)

    result = benchmark(
        build_candidate_slots,
        existing_events=[],
        date_from=date_from,
        date_to=date_to,
        duration_minutes=60,
        day_start="08:00",
        day_end="22:00",
    )

    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.performance
def test_candidate_slot_generation_performance_large_range(benchmark):
    date_from = datetime.now() + timedelta(days=1)
    date_to = date_from + timedelta(days=30)

    result = benchmark(
        build_candidate_slots,
        existing_events=[],
        date_from=date_from,
        date_to=date_to,
        duration_minutes=60,
        day_start="08:00",
        day_end="22:00",
    )

    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.performance
def test_ortools_planner_performance_with_many_busy_events(benchmark):
    date_from = datetime.now() + timedelta(days=1)
    date_to = date_from + timedelta(days=7)

    existing_events = []

    for day in range(7):
        for hour in [9, 12, 15]:
            start = date_from + timedelta(days=day, hours=hour - date_from.hour)
            existing_events.append(
                SimpleNamespace(
                    start_time=start,
                    end_time=start + timedelta(hours=1),
                )
            )

    result = benchmark(
        plan_task_with_ortools,
        existing_events=existing_events,
        title="Performance task",
        date_from=date_from.date().isoformat(),
        date_to=date_to.date().isoformat(),
        duration_minutes=90,
        day_start="08:00",
        day_end="22:00",
        preferred_time="10:00",
        repeat_enabled=False,
        times_per_week=1,
        allowed_days=[],
    )

    assert result is None or "events" in result
