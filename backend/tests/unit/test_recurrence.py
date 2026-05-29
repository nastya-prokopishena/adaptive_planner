from datetime import datetime, timedelta

from backend.domain.recurrence import (
    build_google_rrule,
    generate_occurrences,
    get_weekday_code,
    parse_recurrence_days,
    time_ranges_overlap,
)


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


def test_parse_recurrence_days_variants():
    assert parse_recurrence_days(None) == []
    assert parse_recurrence_days("") == []
    assert parse_recurrence_days(["MO", "WE"]) == ["MO", "WE"]
    assert parse_recurrence_days("MO, WE,FR") == ["MO", "WE", "FR"]


def test_get_weekday_code():
    assert get_weekday_code(datetime(2026, 5, 25)) == "MO"
    assert get_weekday_code(datetime(2026, 5, 31)) == "SU"


def test_build_google_rrule_returns_none_for_none_type():
    assert build_google_rrule(recurrence_type="none") is None
    assert build_google_rrule(recurrence_type="bad") is None


def test_build_google_rrule_daily_weekdays_and_weekly():
    start = datetime(2026, 5, 25, 10, 0)

    assert build_google_rrule("daily", recurrence_interval=2) == "RRULE:FREQ=DAILY;INTERVAL=2"

    assert build_google_rrule("weekdays") == "RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,TU,WE,TH,FR"

    assert build_google_rrule("weekly", start_time=start) == "RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO"


def test_build_google_rrule_biweekly_monthly_yearly():
    start = datetime(2026, 5, 26, 10, 0)

    assert (
        build_google_rrule("biweekly", start_time=start) == "RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=TU"
    )
    assert build_google_rrule("monthly") == "RRULE:FREQ=MONTHLY;INTERVAL=1"
    assert build_google_rrule("yearly") == "RRULE:FREQ=YEARLY;INTERVAL=1"


def test_build_google_rrule_custom_units():
    start = datetime(2026, 5, 25, 10, 0)

    assert (
        build_google_rrule("custom", recurrence_unit="day", recurrence_interval=3)
        == "RRULE:FREQ=DAILY;INTERVAL=3"
    )

    assert (
        build_google_rrule(
            "custom",
            recurrence_unit="week",
            recurrence_interval=2,
            recurrence_days="MO,FR",
            start_time=start,
        )
        == "RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,FR"
    )

    assert (
        build_google_rrule("custom", recurrence_unit="month", recurrence_interval=2)
        == "RRULE:FREQ=MONTHLY;INTERVAL=2"
    )
    assert (
        build_google_rrule("custom", recurrence_unit="year", recurrence_interval=2)
        == "RRULE:FREQ=YEARLY;INTERVAL=2"
    )


def test_build_google_rrule_end_conditions():
    start = datetime(2026, 5, 25, 10, 0)
    end_date = datetime(2026, 6, 1)

    assert build_google_rrule(
        "weekly",
        start_time=start,
        recurrence_end_type="on",
        recurrence_end_date=end_date,
    ).endswith("UNTIL=20260601T235959Z")

    assert build_google_rrule(
        "weekly",
        start_time=start,
        recurrence_end_type="after",
        recurrence_count=5,
    ).endswith("COUNT=5")


def test_generate_occurrences_none_and_missing_dates():
    start = datetime(2026, 5, 25, 10, 0)
    end = start + timedelta(hours=2)

    assert generate_occurrences(None, end) == []
    assert generate_occurrences(start, None) == []
    assert generate_occurrences(start, end, recurrence_type="none") == [(start, end)]


def test_generate_occurrences_daily_with_count():
    start = datetime(2026, 5, 25, 10, 0)
    end = start + timedelta(hours=1)

    result = generate_occurrences(
        start,
        end,
        recurrence_type="daily",
        recurrence_end_type="after",
        recurrence_count=3,
    )

    assert len(result) == 3
    assert result[1][0] == start + timedelta(days=1)


def test_generate_occurrences_weekdays_and_custom_week():
    start = datetime(2026, 5, 25, 10, 0)
    end = start + timedelta(hours=1)

    weekdays = generate_occurrences(
        start,
        end,
        recurrence_type="weekdays",
        recurrence_end_type="after",
        recurrence_count=5,
    )

    assert len(weekdays) == 5

    custom = generate_occurrences(
        start,
        end,
        recurrence_type="custom",
        recurrence_unit="week",
        recurrence_days="MO,WE",
        recurrence_end_type="after",
        recurrence_count=4,
    )

    assert len(custom) == 4


def test_generate_occurrences_unknown_returns_original_range():
    start = datetime(2026, 5, 25, 10, 0)
    end = start + timedelta(hours=1)

    assert generate_occurrences(start, end, recurrence_type="unknown") == [(start, end)]


def test_time_ranges_overlap_edges():
    start = datetime(2026, 5, 25, 10, 0)

    assert time_ranges_overlap(
        start,
        start + timedelta(hours=2),
        start + timedelta(hours=1),
        start + timedelta(hours=3),
    )

    assert not time_ranges_overlap(
        start,
        start + timedelta(hours=1),
        start + timedelta(hours=1),
        start + timedelta(hours=2),
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
    assert (
        build_google_rrule("biweekly", start_time=start) == "RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=MO"
    )
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

    daily = generate_occurrences(
        start, end, "daily", recurrence_end_type="after", recurrence_count=3
    )
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

    monthly = generate_occurrences(
        start, end, "monthly", recurrence_end_type="after", recurrence_count=2
    )
    yearly = generate_occurrences(
        start, end, "yearly", recurrence_end_type="after", recurrence_count=2
    )
    assert len(monthly) == 2
    assert len(yearly) == 2

    fallback = generate_occurrences(start, end, "unknown")
    assert fallback == [(start, end)]
