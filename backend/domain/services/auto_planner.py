from datetime import datetime, timedelta, time
from collections import defaultdict
from ortools.sat.python import cp_model

from backend.domain.recurrence import generate_occurrences, time_ranges_overlap


def parse_clock(value, default):
    if not value:
        return default

    hours, minutes = value.split(":")
    return time(hour=int(hours), minute=int(minutes))


def normalize_date(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    if "T" in value:
        return datetime.fromisoformat(value)

    return datetime.fromisoformat(value + "T00:00:00")


def get_weekday_code(date_value):
    codes = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
    return codes[date_value.weekday()]


def get_event_ranges(event, horizon_start, horizon_end):
    recurrence_type = getattr(event, "recurrence_type", "none") or "none"

    if recurrence_type != "none":
        occurrences = generate_occurrences(
            start_time=event.start_time,
            end_time=event.end_time,
            recurrence_type=event.recurrence_type or "none",
            recurrence_interval=event.recurrence_interval or 1,
            recurrence_unit=event.recurrence_unit,
            recurrence_days=event.recurrence_days,
            recurrence_end_type=event.recurrence_end_type or "never",
            recurrence_end_date=event.recurrence_end_date,
            recurrence_count=event.recurrence_count,
            horizon_days=365,
        )
    else:
        occurrences = [(event.start_time, event.end_time)]

    result = []

    for start, end in occurrences:
        if start < horizon_end and end > horizon_start:
            result.append((start, end))

    return result


def build_candidate_slots(
    existing_events,
    date_from,
    date_to,
    duration_minutes,
    day_start="08:00",
    day_end="22:00",
    step_minutes=30,
    allowed_days=None,
):
    work_start = parse_clock(day_start, time(hour=8, minute=0))
    work_end = parse_clock(day_end, time(hour=22, minute=0))

    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=step_minutes)

    horizon_start = datetime.combine(date_from.date(), time.min)
    horizon_end = datetime.combine(date_to.date(), time.max)

    busy_ranges = []

    for event in existing_events:
        busy_ranges.extend(get_event_ranges(event, horizon_start, horizon_end))

    candidates = []

    current_day = date_from.date()
    last_day = date_to.date()

    while current_day <= last_day:
        weekday_code = get_weekday_code(current_day)

        if allowed_days and weekday_code not in allowed_days:
            current_day += timedelta(days=1)
            continue

        slot_start = datetime.combine(current_day, work_start)
        day_finish = datetime.combine(current_day, work_end)

        while slot_start + duration <= day_finish:
            slot_end = slot_start + duration

            is_busy = False

            for busy_start, busy_end in busy_ranges:
                if time_ranges_overlap(slot_start, slot_end, busy_start, busy_end):
                    is_busy = True
                    break

            if not is_busy:
                candidates.append(
                    {
                        "start": slot_start,
                        "end": slot_end,
                        "week": slot_start.isocalendar().week,
                        "year": slot_start.isocalendar().year,
                        "day": slot_start.date(),
                        "weekday": get_weekday_code(slot_start.date()),
                    }
                )

            slot_start += step

        current_day += timedelta(days=1)

    return candidates


def score_slot(slot, preferred_time="10:00"):
    preferred = parse_clock(preferred_time, time(hour=10, minute=0))
    preferred_minutes = preferred.hour * 60 + preferred.minute

    start = slot["start"]
    start_minutes = start.hour * 60 + start.minute

    time_distance = abs(start_minutes - preferred_minutes)

    # Поки що це базова евристика.
    # Пізніше тут можна додати ML-оцінку:
    # - складність дня
    # - кількість подій у день
    # - типи подій
    # - історичну продуктивність користувача
    # - втому / перевантаження
    ml_placeholder_penalty = 0

    return time_distance + ml_placeholder_penalty


def choose_single_slot_with_ortools(candidates, preferred_time="10:00"):
    if not candidates:
        return None

    model = cp_model.CpModel()
    choices = []

    for index in range(len(candidates)):
        choices.append(model.NewBoolVar(f"slot_{index}"))

    model.Add(sum(choices) == 1)

    scores = [score_slot(slot, preferred_time) for slot in candidates]

    model.Minimize(sum(scores[i] * choices[i] for i in range(len(candidates))))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 2

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    for index, choice in enumerate(choices):
        if solver.Value(choice) == 1:
            return candidates[index]

    return None


def choose_repeating_slots_with_ortools(
    candidates,
    times_per_week=1,
    preferred_time="10:00",
):
    if not candidates:
        return []

    times_per_week = int(times_per_week or 1)

    candidates_by_week = defaultdict(list)

    for index, slot in enumerate(candidates):
        week_key = (slot["year"], slot["week"])
        candidates_by_week[week_key].append(index)

    model = cp_model.CpModel()

    choices = []

    for index in range(len(candidates)):
        choices.append(model.NewBoolVar(f"slot_{index}"))

    # У кожному тижні треба вибрати задану кількість слотів.
    for week_key, indexes in candidates_by_week.items():
        week_limit = min(times_per_week, len(indexes))
        model.Add(sum(choices[index] for index in indexes) == week_limit)

    # Не більше одного разу в один день.
    candidates_by_day = defaultdict(list)

    for index, slot in enumerate(candidates):
        candidates_by_day[slot["day"]].append(index)

    for day, indexes in candidates_by_day.items():
        model.Add(sum(choices[index] for index in indexes) <= 1)

    scores = []

    first_date = candidates[0]["start"].date()

    for slot in candidates:
        base_score = score_slot(slot, preferred_time)
        day_distance = (slot["start"].date() - first_date).days

        # Невеликий штраф за дальші дні, щоб планування не тягнуло все в кінець.
        score = base_score + day_distance * 3

        scores.append(score)

    model.Minimize(sum(scores[i] * choices[i] for i in range(len(candidates))))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 3

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return []

    selected_slots = []

    for index, choice in enumerate(choices):
        if solver.Value(choice) == 1:
            selected_slots.append(candidates[index])

    selected_slots.sort(key=lambda slot: slot["start"])

    return selected_slots


def plan_task_with_ortools(
    existing_events,
    title,
    duration_minutes,
    date_from,
    date_to,
    day_start="08:00",
    day_end="22:00",
    preferred_time="10:00",
    repeat_enabled=False,
    times_per_week=1,
    allowed_days=None,
):
    start_date = normalize_date(date_from)
    end_date = normalize_date(date_to)

    if not title:
        raise ValueError("Title is required")

    if not duration_minutes or int(duration_minutes) <= 0:
        raise ValueError("Duration must be greater than zero")

    if not start_date or not end_date:
        raise ValueError("Date range is required")

    if end_date < start_date:
        raise ValueError("End date must be later than start date")

    candidates = build_candidate_slots(
        existing_events=existing_events,
        date_from=start_date,
        date_to=end_date,
        duration_minutes=int(duration_minutes),
        day_start=day_start,
        day_end=day_end,
        step_minutes=30,
        allowed_days=allowed_days,
    )

    if repeat_enabled:
        selected_slots = choose_repeating_slots_with_ortools(
            candidates=candidates,
            times_per_week=times_per_week,
            preferred_time=preferred_time,
        )
    else:
        slot = choose_single_slot_with_ortools(
            candidates=candidates,
            preferred_time=preferred_time,
        )

        selected_slots = [slot] if slot else []

    if not selected_slots:
        return None

    planned_events = []

    for slot in selected_slots:
        planned_events.append(
            {
                "title": title,
                "start": slot["start"],
                "end": slot["end"],
                "duration_minutes": int(duration_minutes),
                "weekday": slot["weekday"],
            }
        )

    return {
        "events": planned_events,
        "candidates_count": len(candidates),
        "planned_count": len(planned_events),
    }