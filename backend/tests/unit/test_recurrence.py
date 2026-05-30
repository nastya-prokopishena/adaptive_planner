from datetime import datetime, timedelta

from backend.domain.recurrence import (
    build_google_rrule,
    generate_occurrences,
    get_weekday_code,
    parse_recurrence_days,
    time_ranges_overlap,
)


def test_recurrence_small_helpers():
    overlap_cases = [
        (
            datetime(2026, 5, 1, 10, 0),
            datetime(2026, 5, 1, 11, 0),
            datetime(2026, 5, 1, 10, 30),
            datetime(2026, 5, 1, 12, 0),
            True,
        ),
        (
            datetime(2026, 5, 1, 10, 0),
            datetime(2026, 5, 1, 11, 0),
            datetime(2026, 5, 1, 11, 0),
            datetime(2026, 5, 1, 12, 0),
            False,
        ),
    ]

    for start_a, end_a, start_b, end_b, expected in overlap_cases:
        assert time_ranges_overlap(start_a, end_a, start_b, end_b) is expected

    recurrence_day_cases = [
        (None, []),
        ("", []),
        (["MO", "WE"], ["MO", "WE"]),
        ("MO, WE,,FR", ["MO", "WE", "FR"]),
    ]

    for value, expected in recurrence_day_cases:
        assert parse_recurrence_days(value) == expected

    assert get_weekday_code(datetime(2026, 5, 25)) == "MO"
    assert get_weekday_code(datetime(2026, 5, 31)) == "SU"


def test_build_google_rrule_main_modes():
    cases = [
        ({"recurrence_type": "none"}, None),
        ({"recurrence_type": "bad"}, None),
        ({"recurrence_type": "daily", "recurrence_interval": 2}, "RRULE:FREQ=DAILY;INTERVAL=2"),
        ({"recurrence_type": "weekdays"}, "RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,TU,WE,TH,FR"),
        (
            {"recurrence_type": "weekly", "start_time": datetime(2026, 5, 25, 10, 0)},
            "RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO",
        ),
        (
            {"recurrence_type": "biweekly", "start_time": datetime(2026, 5, 26, 10, 0)},
            "RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=TU",
        ),
        ({"recurrence_type": "monthly"}, "RRULE:FREQ=MONTHLY;INTERVAL=1"),
        ({"recurrence_type": "yearly"}, "RRULE:FREQ=YEARLY;INTERVAL=1"),
        (
            {"recurrence_type": "custom", "recurrence_unit": "day", "recurrence_interval": 3},
            "RRULE:FREQ=DAILY;INTERVAL=3",
        ),
        (
            {
                "recurrence_type": "custom",
                "recurrence_unit": "week",
                "recurrence_interval": 2,
                "recurrence_days": "MO,FR",
                "start_time": datetime(2026, 5, 25, 10, 0),
            },
            "RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,FR",
        ),
        (
            {"recurrence_type": "custom", "recurrence_unit": "month", "recurrence_interval": 2},
            "RRULE:FREQ=MONTHLY;INTERVAL=2",
        ),
        (
            {"recurrence_type": "custom", "recurrence_unit": "year", "recurrence_interval": 2},
            "RRULE:FREQ=YEARLY;INTERVAL=2",
        ),
    ]

    for args, expected in cases:
        assert build_google_rrule(**args) == expected

    start = datetime(2026, 5, 25, 10, 0)
    end_date = datetime(2026, 6, 1, 10, 0)

    assert build_google_rrule(
        recurrence_type="weekly",
        start_time=start,
        recurrence_end_type="on",
        recurrence_end_date=end_date,
    ).endswith("UNTIL=20260601T235959Z")

    assert build_google_rrule(
        recurrence_type="weekly",
        start_time=start,
        recurrence_end_type="after",
        recurrence_count=5,
    ).endswith("COUNT=5")


def test_generate_occurrences_main_modes():
    start = datetime(2026, 5, 25, 10, 0)
    end = start + timedelta(hours=1)

    assert generate_occurrences(None, end) == []
    assert generate_occurrences(start, None) == []
    assert generate_occurrences(start, end, recurrence_type="none") == [(start, end)]
    assert generate_occurrences(start, end, recurrence_type="unknown") == [(start, end)]

    cases = [
        ("daily", {"recurrence_end_type": "after", "recurrence_count": 3}, 3),
        ("weekdays", {"recurrence_end_type": "after", "recurrence_count": 5}, 5),
        (
            "custom",
            {
                "recurrence_unit": "week",
                "recurrence_days": "MO,WE",
                "recurrence_end_type": "after",
                "recurrence_count": 4,
            },
            4,
        ),
        ("monthly", {"recurrence_end_type": "after", "recurrence_count": 2}, 2),
        ("yearly", {"recurrence_end_type": "after", "recurrence_count": 2}, 2),
    ]

    for recurrence_type, kwargs, expected_count in cases:
        result = generate_occurrences(
            start_time=start,
            end_time=end,
            recurrence_type=recurrence_type,
            **kwargs,
        )
        assert len(result) == expected_count
