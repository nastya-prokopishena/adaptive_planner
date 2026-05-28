from datetime import datetime, timedelta
from types import SimpleNamespace

from backend.domain.services.auto_planner import (
    build_busy_ranges,
    build_candidate_slots,
    calculate_day_load_minutes,
    calculate_nearby_event_penalty,
    choose_repeating_slots_greedy,
    choose_single_slot_with_ortools,
    get_event_ranges,
    get_weekday_code,
    normalize_allowed_days,
    normalize_date,
    parse_clock,
    plan_task_with_ortools,
    score_slot,
)


def test_parse_clock_returns_default_for_empty_value():
    default = datetime(2026, 5, 28, 8, 0).time()

    assert parse_clock(None, default) == default


def test_normalize_date_accepts_date_and_datetime_strings():
    assert normalize_date("2026-05-28").hour == 0
    assert normalize_date("2026-05-28T12:30:00").hour == 12


def test_get_weekday_code_returns_expected_code():
    assert get_weekday_code(datetime(2026, 5, 25).date()) == "MO"


def test_normalize_allowed_days_supports_ukrainian_and_numbers():
    result = normalize_allowed_days(["ПН", "вт", "6", "SUNDAY", "bad"])

    assert "MO" in result
    assert "TU" in result

    assert "SU" in result

    assert len(result) == 3


def test_get_event_ranges_for_non_recurring_event():
    event = SimpleNamespace(
        start_time=datetime(2026, 5, 28, 10),
        end_time=datetime(2026, 5, 28, 11),
        recurrence_type="none",
    )

    ranges = get_event_ranges(
        event,
        datetime(2026, 5, 28),
        datetime(2026, 5, 29),
    )

    assert ranges == [(event.start_time, event.end_time)]


def test_build_busy_ranges_collects_event_ranges():
    event = SimpleNamespace(
        start_time=datetime(2026, 5, 28, 10),
        end_time=datetime(2026, 5, 28, 11),
        recurrence_type="none",
    )

    result = build_busy_ranges(
        [event],
        datetime(2026, 5, 28),
        datetime(2026, 5, 29),
    )

    assert len(result) == 1


def test_day_load_and_nearby_penalty_are_calculated():
    day = datetime(2026, 5, 28).date()
    busy = [
        (
            datetime(2026, 5, 28, 10),
            datetime(2026, 5, 28, 11),
        )
    ]

    load = calculate_day_load_minutes(day, busy)
    penalty = calculate_nearby_event_penalty(
        datetime(2026, 5, 28, 11, 10),
        datetime(2026, 5, 28, 12, 0),
        busy,
    )

    assert load == 60
    assert penalty > 0


def test_score_slot_prefers_preferred_day_and_time():
    preferred_slot = {
        "start": datetime(2026, 6, 1, 10),
        "end": datetime(2026, 6, 1, 11),
        "weekday": "MO",
        "day": datetime(2026, 6, 1).date(),
        "day_load_minutes": 0,
        "nearby_event_penalty": 0,
    }
    other_slot = {
        **preferred_slot,
        "start": datetime(2026, 6, 1, 20),
        "weekday": "TU",
    }

    assert score_slot(preferred_slot, "10:00", {"MO"}) < score_slot(
        other_slot,
        "10:00",
        {"MO"},
    )


def test_choose_single_slot_with_ortools_returns_one_candidate():
    candidates = [
        {
            "start": datetime(2026, 6, 1, 9),
            "end": datetime(2026, 6, 1, 10),
            "weekday": "MO",
            "day": datetime(2026, 6, 1).date(),
            "day_load_minutes": 0,
            "nearby_event_penalty": 0,
        },
        {
            "start": datetime(2026, 6, 1, 10),
            "end": datetime(2026, 6, 1, 11),
            "weekday": "MO",
            "day": datetime(2026, 6, 1).date(),
            "day_load_minutes": 0,
            "nearby_event_penalty": 0,
        },
    ]

    selected = choose_single_slot_with_ortools(candidates, preferred_time="10:00")

    assert selected in candidates


def test_choose_repeating_slots_greedy_limits_slots_per_week():
    candidates = []

    for day_offset in range(5):
        start = datetime(2026, 6, 1 + day_offset, 10)
        candidates.append(
            {
                "start": start,
                "end": start + timedelta(hours=1),
                "weekday": get_weekday_code(start.date()),
                "day": start.date(),
                "week": start.isocalendar().week,
                "year": start.isocalendar().year,
                "day_load_minutes": 0,
                "nearby_event_penalty": 0,
            }
        )

    selected = choose_repeating_slots_greedy(candidates, times_per_week=2)

    assert len(selected) == 2


def test_plan_task_with_ortools_returns_planned_event():
    result = plan_task_with_ortools(
        existing_events=[],
        title="Study",
        duration_minutes=60,
        date_from=(datetime.utcnow() + timedelta(days=1)).date().isoformat(),
        date_to=(datetime.utcnow() + timedelta(days=2)).date().isoformat(),
        preferred_time="10:00",
    )

    assert result is not None
    assert result["planned_count"] >= 1
    assert result["events"][0]["title"] == "Study"


def test_plan_task_with_ortools_rejects_reversed_range():
    try:
        plan_task_with_ortools(
            existing_events=[],
            title="Bad",
            duration_minutes=60,
            date_from="2026-05-30",
            date_to="2026-05-28",
        )
    except ValueError as exc:
        assert "End date" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
