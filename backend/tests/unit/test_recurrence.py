from datetime import datetime

from backend.domain.recurrence import build_google_rrule, generate_occurrences, time_ranges_overlap


def test_time_ranges_overlap_returns_true_for_intersection():
    start_a = datetime(2026, 5, 1, 10, 0)
    end_a = datetime(2026, 5, 1, 11, 0)
    start_b = datetime(2026, 5, 1, 10, 30)
    end_b = datetime(2026, 5, 1, 12, 0)

    assert time_ranges_overlap(start_a, end_a, start_b, end_b) is True


def test_time_ranges_overlap_returns_false_for_separate_ranges():
    start_a = datetime(2026, 5, 1, 10, 0)
    end_a = datetime(2026, 5, 1, 11, 0)
    start_b = datetime(2026, 5, 1, 11, 0)
    end_b = datetime(2026, 5, 1, 12, 0)

    assert time_ranges_overlap(start_a, end_a, start_b, end_b) is False


def test_build_google_weekly_rrule():
    start = datetime(2026, 5, 4, 10, 0)  # Monday

    rule = build_google_rrule(
        recurrence_type="weekly",
        start_time=start,
    )

    assert rule == "RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO"


def test_generate_daily_occurrences_with_count():
    start = datetime(2026, 5, 1, 10, 0)
    end = datetime(2026, 5, 1, 11, 0)

    occurrences = generate_occurrences(
        start_time=start,
        end_time=end,
        recurrence_type="daily",
        recurrence_count=3,
        recurrence_end_type="after",
    )

    assert len(occurrences) == 3
    assert occurrences[0] == (start, end)
