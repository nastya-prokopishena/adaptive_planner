from datetime import datetime, timedelta

from backend.domain.recurrence import (
    build_google_rrule,
    generate_occurrences,
    get_weekday_code,
    parse_recurrence_days,
)


def test_parse_recurrence_days_accepts_empty_string_and_list():
    assert parse_recurrence_days(None) == []
    assert parse_recurrence_days("") == []
    assert parse_recurrence_days(["MO", "WE"]) == ["MO", "WE"]
    assert parse_recurrence_days("MO, WE,,FR") == ["MO", "WE", "FR"]


def test_get_weekday_code_for_known_date():
    assert get_weekday_code(datetime(2026, 5, 25)) == "MO"
    assert get_weekday_code(datetime(2026, 5, 31)) == "SU"


def test_build_google_rrule_covers_common_types():
    start = datetime(2026, 5, 25, 10, 0)
    end_date = datetime(2026, 6, 1, 10, 0)

    assert build_google_rrule("none") is None
    assert build_google_rrule("daily", 2) == "RRULE:FREQ=DAILY;INTERVAL=2"
    assert build_google_rrule("weekdays") == "RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,TU,WE,TH,FR"
    assert build_google_rrule("weekly", start_time=start) == "RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO"
    assert build_google_rrule("biweekly", start_time=start) == "RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=MO"
    assert build_google_rrule("monthly") == "RRULE:FREQ=MONTHLY;INTERVAL=1"
    assert build_google_rrule("yearly") == "RRULE:FREQ=YEARLY;INTERVAL=1"
    assert build_google_rrule("unknown") is None

    custom = build_google_rrule(
        recurrence_type="custom",
        recurrence_interval=3,
        recurrence_unit="week",
        recurrence_days="TU,TH",
        recurrence_end_type="after",
        recurrence_count=5,
        start_time=start,
    )
    assert custom == "RRULE:FREQ=WEEKLY;INTERVAL=3;BYDAY=TU,TH;COUNT=5"

    with_until = build_google_rrule(
        recurrence_type="custom",
        recurrence_interval=1,
        recurrence_unit="day",
        recurrence_end_type="on",
        recurrence_end_date=end_date,
    )
    assert "UNTIL=20260601T235959Z" in with_until


def test_generate_occurrences_covers_multiple_recurrence_modes():
    start = datetime(2026, 5, 25, 10, 0)
    end = start + timedelta(hours=1)

    assert generate_occurrences(None, end) == []
    assert generate_occurrences(start, None) == []
    assert len(generate_occurrences(start, end, "none")) == 1

    daily = generate_occurrences(start, end, "daily", recurrence_end_type="after", recurrence_count=3)
    assert len(daily) == 3
    assert daily[1][0] == start + timedelta(days=1)

    weekly_custom = generate_occurrences(
        start,
        end,
        recurrence_type="custom",
        recurrence_unit="week",
        recurrence_days="MO,WE",
        recurrence_end_type="after",
        recurrence_count=4,
    )
    assert len(weekly_custom) == 4

    monthly = generate_occurrences(start, end, "monthly", recurrence_end_type="after", recurrence_count=2)
    yearly = generate_occurrences(start, end, "yearly", recurrence_end_type="after", recurrence_count=2)
    assert len(monthly) == 2
    assert len(yearly) == 2

    fallback = generate_occurrences(start, end, "unknown")
    assert fallback == [(start, end)]
