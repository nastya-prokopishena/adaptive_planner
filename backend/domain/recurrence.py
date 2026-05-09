from datetime import datetime, timedelta
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY, YEARLY, MO, TU, WE, TH, FR, SA, SU


WEEKDAY_MAP = {
    "MO": MO,
    "TU": TU,
    "WE": WE,
    "TH": TH,
    "FR": FR,
    "SA": SA,
    "SU": SU,
}

GOOGLE_WEEKDAY_MAP = {
    "MO": "MO",
    "TU": "TU",
    "WE": "WE",
    "TH": "TH",
    "FR": "FR",
    "SA": "SA",
    "SU": "SU",
}


def parse_recurrence_days(days):
    if not days:
        return []

    if isinstance(days, list):
        return days

    return [day.strip() for day in days.split(",") if day.strip()]


def get_weekday_code(date):
    codes = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
    return codes[date.weekday()]


def build_google_rrule(
    recurrence_type="none",
    recurrence_interval=1,
    recurrence_unit=None,
    recurrence_days=None,
    recurrence_end_type="never",
    recurrence_end_date=None,
    recurrence_count=None,
    start_time=None,
):
    if recurrence_type == "none":
        return None

    interval = recurrence_interval or 1
    days = parse_recurrence_days(recurrence_days)

    if recurrence_type == "daily":
        parts = [f"FREQ=DAILY", f"INTERVAL={interval}"]

    elif recurrence_type == "weekdays":
        parts = ["FREQ=WEEKLY", "INTERVAL=1", "BYDAY=MO,TU,WE,TH,FR"]

    elif recurrence_type == "weekly":
        weekday = get_weekday_code(start_time) if start_time else "MO"
        parts = ["FREQ=WEEKLY", "INTERVAL=1", f"BYDAY={weekday}"]

    elif recurrence_type == "biweekly":
        weekday = get_weekday_code(start_time) if start_time else "MO"
        parts = ["FREQ=WEEKLY", "INTERVAL=2", f"BYDAY={weekday}"]

    elif recurrence_type == "monthly":
        parts = ["FREQ=MONTHLY", "INTERVAL=1"]

    elif recurrence_type == "yearly":
        parts = ["FREQ=YEARLY", "INTERVAL=1"]

    elif recurrence_type == "custom":
        unit = recurrence_unit or "week"

        if unit == "day":
            parts = ["FREQ=DAILY", f"INTERVAL={interval}"]

        elif unit == "week":
            if not days and start_time:
                days = [get_weekday_code(start_time)]

            parts = ["FREQ=WEEKLY", f"INTERVAL={interval}"]

            if days:
                parts.append(f"BYDAY={','.join(days)}")

        elif unit == "month":
            parts = ["FREQ=MONTHLY", f"INTERVAL={interval}"]

        elif unit == "year":
            parts = ["FREQ=YEARLY", f"INTERVAL={interval}"]

        else:
            parts = ["FREQ=WEEKLY", f"INTERVAL={interval}"]

    else:
        return None

    if recurrence_end_type == "on" and recurrence_end_date:
        until = recurrence_end_date.strftime("%Y%m%dT235959Z")
        parts.append(f"UNTIL={until}")

    elif recurrence_end_type == "after" and recurrence_count:
        parts.append(f"COUNT={recurrence_count}")

    return "RRULE:" + ";".join(parts)


def generate_occurrences(
    start_time,
    end_time,
    recurrence_type="none",
    recurrence_interval=1,
    recurrence_unit=None,
    recurrence_days=None,
    recurrence_end_type="never",
    recurrence_end_date=None,
    recurrence_count=None,
    horizon_days=365,
):
    if not start_time or not end_time:
        return []

    duration = end_time - start_time

    if recurrence_type == "none":
        return [(start_time, end_time)]

    interval = recurrence_interval or 1
    days = parse_recurrence_days(recurrence_days)

    horizon_end = start_time + timedelta(days=horizon_days)

    until = horizon_end

    if recurrence_end_type == "on" and recurrence_end_date:
        until = recurrence_end_date

    count = None

    if recurrence_end_type == "after" and recurrence_count:
        count = recurrence_count

    kwargs = {
        "dtstart": start_time,
        "interval": interval,
    }

    if count:
        kwargs["count"] = count
    else:
        kwargs["until"] = until

    if recurrence_type == "daily":
        rule = rrule(DAILY, **kwargs)

    elif recurrence_type == "weekdays":
        rule = rrule(WEEKLY, byweekday=[MO, TU, WE, TH, FR], interval=1, dtstart=start_time, count=count, until=None if count else until)

    elif recurrence_type == "weekly":
        rule = rrule(WEEKLY, interval=1, byweekday=[WEEKDAY_MAP[get_weekday_code(start_time)]], dtstart=start_time, count=count, until=None if count else until)

    elif recurrence_type == "biweekly":
        rule = rrule(WEEKLY, interval=2, byweekday=[WEEKDAY_MAP[get_weekday_code(start_time)]], dtstart=start_time, count=count, until=None if count else until)

    elif recurrence_type == "monthly":
        rule = rrule(MONTHLY, interval=1, dtstart=start_time, count=count, until=None if count else until)

    elif recurrence_type == "yearly":
        rule = rrule(YEARLY, interval=1, dtstart=start_time, count=count, until=None if count else until)

    elif recurrence_type == "custom":
        unit = recurrence_unit or "week"

        if unit == "day":
            rule = rrule(DAILY, **kwargs)

        elif unit == "week":
            if not days:
                days = [get_weekday_code(start_time)]

            weekdays = [WEEKDAY_MAP[day] for day in days if day in WEEKDAY_MAP]

            rule = rrule(
                WEEKLY,
                interval=interval,
                byweekday=weekdays,
                dtstart=start_time,
                count=count,
                until=None if count else until,
            )

        elif unit == "month":
            rule = rrule(MONTHLY, **kwargs)

        elif unit == "year":
            rule = rrule(YEARLY, **kwargs)

        else:
            rule = rrule(WEEKLY, **kwargs)

    else:
        return [(start_time, end_time)]

    occurrences = []

    for occurrence_start in rule:
        occurrence_end = occurrence_start + duration
        occurrences.append((occurrence_start, occurrence_end))

    return occurrences


def time_ranges_overlap(start_a, end_a, start_b, end_b):
    return start_a < end_b and end_a > start_b