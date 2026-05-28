from datetime import datetime, timedelta, time
from collections import defaultdict

from ortools.sat.python import cp_model

from backend.domain.recurrence import generate_occurrences, time_ranges_overlap


def parse_clock(value, default):
    if not value:
        return default

    hours, minutes = str(value).split(":")
    return time(hour=int(hours), minute=int(minutes))


def normalize_date(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    cleaned = str(value).replace("Z", "")

    if "T" in cleaned:
        return datetime.fromisoformat(cleaned)

    return datetime.fromisoformat(cleaned + "T00:00:00")


def get_weekday_code(date_value):
    codes = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
    return codes[date_value.weekday()]


def normalize_allowed_days(allowed_days):
    """
    allowed_days = бажані дні, а не жорстке обмеження.

    Приклад:
    times_per_week = 3
    allowed_days = ["TU", "TH", "SA", "SU"]

    Це означає:
    - треба створити 3 події на тиждень;
    - бажано вибрати 3 найкращі дні з цих 4;
    - якщо всі бажані дні дуже погані за розкладом, можна взяти інший день.
    """
    if not allowed_days:
        return set()

    result = set()

    aliases = {
        "MO": "MO", "MON": "MO", "MONDAY": "MO", "ПН": "MO", "ПОНЕДІЛОК": "MO",
        "TU": "TU", "TUE": "TU", "TUESDAY": "TU", "ВТ": "TU", "ВІВТОРОК": "TU",
        "WE": "WE", "WED": "WE", "WEDNESDAY": "WE", "СР": "WE", "СЕРЕДА": "WE",
        "TH": "TH", "THU": "TH", "THURSDAY": "TH", "ЧТ": "TH", "ЧЕТВЕР": "TH",
        "FR": "FR", "FRI": "FR", "FRIDAY": "FR", "ПТ": "FR", "ПʼЯТНИЦЯ": "FR", "П'ЯТНИЦЯ": "FR",
        "SA": "SA", "SAT": "SA", "SATURDAY": "SA", "СБ": "SA", "СУБОТА": "SA",
        "SU": "SU", "SUN": "SU", "SUNDAY": "SU", "НД": "SU", "НЕДІЛЯ": "SU",
    }

    for day in allowed_days:
        if day is None:
            continue

        value = str(day).strip().upper()

        if value in aliases:
            result.add(aliases[value])
            continue

        try:
            number = int(value)

            if 0 <= number <= 6:
                result.add(["MO", "TU", "WE", "TH", "FR", "SA", "SU"][number])
            elif 1 <= number <= 7:
                result.add(["MO", "TU", "WE", "TH", "FR", "SA", "SU"][number - 1])

        except ValueError:
            pass

    return result


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


def build_busy_ranges(existing_events, horizon_start, horizon_end):
    busy_ranges = []

    for event in existing_events:
        busy_ranges.extend(get_event_ranges(event, horizon_start, horizon_end))

    return busy_ranges


def calculate_day_load_minutes(day, busy_ranges):
    total = 0

    for busy_start, busy_end in busy_ranges:
        if busy_start.date() != day:
            continue

        total += max(int((busy_end - busy_start).total_seconds() // 60), 0)

    return total


def calculate_nearby_event_penalty(slot_start, slot_end, busy_ranges):
    """
    Штраф за те, що слот дуже близько до інших подій.
    Це зменшує шанс, що автопланування поставить задачу впритул до пар.
    """
    penalty = 0

    for busy_start, busy_end in busy_ranges:
        if busy_start.date() != slot_start.date():
            continue

        minutes_before = abs(int((slot_start - busy_end).total_seconds() // 60))
        minutes_after = abs(int((busy_start - slot_end).total_seconds() // 60))

        nearest_gap = min(minutes_before, minutes_after)

        if nearest_gap < 30:
            penalty += 120
        elif nearest_gap < 60:
            penalty += 70
        elif nearest_gap < 120:
            penalty += 35

    return penalty


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
    """
    Генеруємо кандидати для ВСІХ днів у діапазоні.

    allowed_days тут спеціально не використовується як фільтр.
    Це тільки побажання користувача, яке враховується у score_slot().
    """
    work_start = parse_clock(day_start, time(hour=8, minute=0))
    work_end = parse_clock(day_end, time(hour=22, minute=0))

    duration = timedelta(minutes=int(duration_minutes))
    step = timedelta(minutes=step_minutes)

    horizon_start = datetime.combine(date_from.date(), time.min)
    horizon_end = datetime.combine(date_to.date(), time.max)

    busy_ranges = build_busy_ranges(existing_events, horizon_start, horizon_end)

    candidates = []

    current_day = date_from.date()
    last_day = date_to.date()

    while current_day <= last_day:
        weekday_code = get_weekday_code(current_day)

        slot_start = datetime.combine(current_day, work_start)
        day_finish = datetime.combine(current_day, work_end)

        while slot_start + duration <= day_finish:
            slot_end = slot_start + duration

            if slot_start <= datetime.now():
                slot_start += step
                continue

            is_busy = False

            for busy_start, busy_end in busy_ranges:
                if time_ranges_overlap(slot_start, slot_end, busy_start, busy_end):
                    is_busy = True
                    break

            if not is_busy:
                day_load_minutes = calculate_day_load_minutes(current_day, busy_ranges)

                candidates.append(
                    {
                        "start": slot_start,
                        "end": slot_end,
                        "week": slot_start.isocalendar().week,
                        "year": slot_start.isocalendar().year,
                        "day": slot_start.date(),
                        "weekday": weekday_code,
                        "day_load_minutes": day_load_minutes,
                        "nearby_event_penalty": calculate_nearby_event_penalty(
                            slot_start,
                            slot_end,
                            busy_ranges,
                        ),
                    }
                )

            slot_start += step

        current_day += timedelta(days=1)

    return candidates


def score_slot(
    slot,
    preferred_time="10:00",
    preferred_days=None,
    selected_day_counts=None,
):
    """
    Чим менший score, тим кращий слот.

    Логіка:
    1. times_per_week визначає кількість подій.
    2. preferred_days — це сильна перевага, але не заборона інших днів.
    3. preferred_time — бажаний час, але не обов'язковий.
    4. Реальне навантаження дня важливіше за просте побажання.
    """
    preferred_days = preferred_days or set()
    selected_day_counts = selected_day_counts or {}

    preferred = parse_clock(preferred_time, time(hour=10, minute=0))
    preferred_minutes = preferred.hour * 60 + preferred.minute

    start = slot["start"]
    start_minutes = start.hour * 60 + start.minute

    time_distance = abs(start_minutes - preferred_minutes)

    # Реальне навантаження дня.
    day_load_penalty = slot.get("day_load_minutes", 0) * 1.8

    # Не ставимо декілька повторів в один і той самий день.
    same_day_penalty = selected_day_counts.get(slot["day"], 0) * 900

    # Бажані дні дуже бажані, але не є жорстким фільтром.
    preferred_day_bonus = -800 if slot["weekday"] in preferred_days else 0

    # Якщо користувач обрав preferred days, то інші дні гірші,
    # але не заборонені повністю.
    non_preferred_penalty = (
        350
        if preferred_days and slot["weekday"] not in preferred_days
        else 0
    )

    # Вихідні не заборонені, але якщо вони не preferred — трохи гірші.
    weekend_penalty = 90 if slot["weekday"] in {"SA", "SU"} else 0

    late_penalty = 0
    if start.hour >= 20:
        late_penalty = 180
    elif start.hour >= 18:
        late_penalty = 80

    early_penalty = 60 if start.hour < 9 else 0
    nearby_event_penalty = slot.get("nearby_event_penalty", 0)

    return (
        day_load_penalty
        + time_distance
        + same_day_penalty
        + weekend_penalty
        + late_penalty
        + early_penalty
        + nearby_event_penalty
        + preferred_day_bonus
        + non_preferred_penalty
    )


def choose_single_slot_with_ortools(
    candidates,
    preferred_time="10:00",
    preferred_days=None,
):
    if not candidates:
        return None

    model = cp_model.CpModel()
    choices = []

    for index in range(len(candidates)):
        choices.append(model.NewBoolVar(f"slot_{index}"))

    model.Add(sum(choices) == 1)

    scores = [
        int(score_slot(slot, preferred_time, preferred_days))
        for slot in candidates
    ]

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
    preferred_days=None,
):
    """
    Вибирає РІВНО times_per_week слотів у кожному тижні.

    Якщо користувач вибрав 4 бажані дні, але times_per_week = 3,
    буде вибрано тільки 3 найкращі слоти.
    """
    if not candidates:
        return []

    times_per_week = int(times_per_week or 1)
    preferred_days = preferred_days or set()

    candidates_by_week = defaultdict(list)

    for index, slot in enumerate(candidates):
        week_key = (slot["year"], slot["week"])
        candidates_by_week[week_key].append(index)

    model = cp_model.CpModel()

    choices = []

    for index in range(len(candidates)):
        choices.append(model.NewBoolVar(f"slot_{index}"))

    for week_key, indexes in candidates_by_week.items():
        week_limit = min(times_per_week, len(indexes))
        model.Add(sum(choices[index] for index in indexes) == week_limit)

    candidates_by_day = defaultdict(list)

    for index, slot in enumerate(candidates):
        candidates_by_day[slot["day"]].append(index)

    # Не більше одного повтору в один день.
    for day, indexes in candidates_by_day.items():
        model.Add(sum(choices[index] for index in indexes) <= 1)

    scores = [
        int(
            score_slot(
                slot=slot,
                preferred_time=preferred_time,
                preferred_days=preferred_days,
            )
        )
        for slot in candidates
    ]

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


def choose_repeating_slots_greedy(
    candidates,
    times_per_week=1,
    preferred_time="10:00",
    preferred_days=None,
):
    """
    Fallback, якщо OR-Tools не знайшов feasible рішення.
    Так само вибирає максимум times_per_week слотів на тиждень,
    а не всі preferred days.
    """
    if not candidates:
        return []

    preferred_days = preferred_days or set()
    times_per_week = int(times_per_week or 1)

    candidates_by_week = defaultdict(list)

    for slot in candidates:
        candidates_by_week[(slot["year"], slot["week"])].append(slot)

    selected = []

    for week_key in sorted(candidates_by_week.keys()):
        week_slots = candidates_by_week[week_key]
        selected_day_counts = {}
        week_selected = []

        for _ in range(min(times_per_week, len(week_slots))):
            available = [
                slot
                for slot in week_slots
                if slot["day"] not in selected_day_counts
            ]

            if not available:
                break

            best = sorted(
                available,
                key=lambda slot: score_slot(
                    slot=slot,
                    preferred_time=preferred_time,
                    preferred_days=preferred_days,
                    selected_day_counts=selected_day_counts,
                ),
            )[0]

            week_selected.append(best)
            selected_day_counts[best["day"]] = selected_day_counts.get(best["day"], 0) + 1

        selected.extend(week_selected)

    selected.sort(key=lambda slot: slot["start"])

    return selected


def build_relaxed_candidates(
    existing_events,
    start_date,
    end_date,
    duration_minutes,
):
    """
    Якщо в стандартному проміжку немає слотів,
    пробуємо ширший день і менший крок.
    """
    return build_candidate_slots(
        existing_events=existing_events,
        date_from=start_date,
        date_to=end_date,
        duration_minutes=int(duration_minutes),
        day_start="07:00",
        day_end="23:00",
        step_minutes=15,
        allowed_days=None,
    )


def serialize_planned_events(
    selected_slots,
    title,
    duration_minutes,
    preferred_days,
):
    planned_events = []

    for slot in selected_slots:
        planned_events.append(
            {
                "title": title,
                "start": slot["start"],
                "end": slot["end"],
                "duration_minutes": int(duration_minutes),
                "weekday": slot["weekday"],
                "day_load_minutes": slot.get("day_load_minutes", 0),
                "soft_preference_used": slot["weekday"] in preferred_days,
            }
        )

    return planned_events


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

    preferred_days = normalize_allowed_days(allowed_days)

    candidates = build_candidate_slots(
        existing_events=existing_events,
        date_from=start_date,
        date_to=end_date,
        duration_minutes=int(duration_minutes),
        day_start=day_start,
        day_end=day_end,
        step_minutes=30,
        allowed_days=None,
    )

    relaxed_used = False

    if not candidates:
        candidates = build_relaxed_candidates(
            existing_events=existing_events,
            start_date=start_date,
            end_date=end_date,
            duration_minutes=duration_minutes,
        )
        relaxed_used = True

    if not candidates:
        return None

    if repeat_enabled:
        selected_slots = choose_repeating_slots_with_ortools(
            candidates=candidates,
            times_per_week=times_per_week,
            preferred_time=preferred_time,
            preferred_days=preferred_days,
        )

        if not selected_slots:
            selected_slots = choose_repeating_slots_greedy(
                candidates=candidates,
                times_per_week=times_per_week,
                preferred_time=preferred_time,
                preferred_days=preferred_days,
            )
    else:
        slot = choose_single_slot_with_ortools(
            candidates=candidates,
            preferred_time=preferred_time,
            preferred_days=preferred_days,
        )

        if not slot:
            slot = sorted(
                candidates,
                key=lambda candidate: score_slot(
                    candidate,
                    preferred_time=preferred_time,
                    preferred_days=preferred_days,
                ),
            )[0]

        selected_slots = [slot] if slot else []

    if not selected_slots:
        return None

    planned_events = serialize_planned_events(
        selected_slots=selected_slots,
        title=title,
        duration_minutes=duration_minutes,
        preferred_days=preferred_days,
    )

    return {
        "events": planned_events,
        "candidates_count": len(candidates),
        "planned_count": len(planned_events),
        "relaxed_search_used": relaxed_used,
        "soft_preferences": {
            "preferred_time": preferred_time,
            "preferred_days": sorted(list(preferred_days)),
            "is_strict": False,
            "times_per_week": int(times_per_week or 1),
        },
    }
