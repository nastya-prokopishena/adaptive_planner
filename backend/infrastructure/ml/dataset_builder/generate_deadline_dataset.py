import csv
import os
import random
from datetime import datetime

from backend.infrastructure.db.database import SessionLocal
from backend.infrastructure.db.models import Event, Task


OUTPUT_PATH = (
    "backend/infrastructure/ml/datasets/processed/"
    "deadline_recommendation_dataset.csv"
)

FIELDNAMES = [
    "estimated_duration_hours",
    "difficulty_score",
    "priority_score",
    "task_type_score",
    "subject_has_events",
    "hours_until_next_subject_event",
    "day_load_score",
    "free_hours_today",
    "days_until_deadline",
    "recommended_deadline_hours",
    "data_source",
]


PRIORITY_MAP = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "urgent": 4,
}

TASK_TYPE_MAP = {
    "reading": 1,
    "homework": 2,
    "laboratory": 3,
    "project": 4,
    "exam_preparation": 5,
    "other": 2,
}


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def get_priority_score(priority):
    return PRIORITY_MAP.get(priority or "medium", 2)


def get_task_type_score(task_type):
    return TASK_TYPE_MAP.get(task_type or "other", 2)


def calculate_day_load_score(events):
    total_hours = 0

    for event in events:
        if not event.start_time or not event.end_time:
            continue

        duration = max(
            (event.end_time - event.start_time).total_seconds() / 3600,
            0,
        )

        total_hours += duration

    return clamp(total_hours * 10, 0, 100)


def get_free_hours_today(events):
    day_capacity = 14
    used_hours = 0

    for event in events:
        if not event.start_time or not event.end_time:
            continue

        used_hours += max(
            (event.end_time - event.start_time).total_seconds() / 3600,
            0,
        )

    return clamp(day_capacity - used_hours, 0, day_capacity)


def get_hours_until_next_subject_event(task, events, reference_time):
    if not task.subject_id:
        return 0

    subject_events = [
        event
        for event in events
        if event.subject_id == task.subject_id
        and event.start_time
        and event.start_time > reference_time
    ]

    if not subject_events:
        return 0

    nearest_event = sorted(
        subject_events,
        key=lambda event: event.start_time,
    )[0]

    return max(
        1,
        int((nearest_event.start_time - reference_time).total_seconds() / 3600),
    )


def build_real_rows():
    db = SessionLocal()

    try:
        tasks = (
            db.query(Task)
            .filter(Task.due_date.isnot(None))
            .all()
        )

        events = db.query(Event).all()

        rows = []

        for task in tasks:
            if not task.due_date:
                continue

            reference_time = task.created_at or datetime.utcnow()

            if task.due_date <= reference_time:
                continue

            task_day_events = [
                event
                for event in events
                if event.start_time
                and event.start_time.date() == reference_time.date()
            ]

            recommended_hours = (
                task.due_date - reference_time
            ).total_seconds() / 3600

            if recommended_hours <= 0:
                continue

            days_until_deadline = max(
                1,
                int((task.due_date - reference_time).total_seconds() / 86400),
            )

            hours_until_next_subject_event = get_hours_until_next_subject_event(
                task=task,
                events=events,
                reference_time=reference_time,
            )

            row = {
                "estimated_duration_hours": float(
                    task.estimated_duration_hours or 1
                ),
                "difficulty_score": int(task.difficulty_score or 3),
                "priority_score": get_priority_score(task.priority),
                "task_type_score": get_task_type_score(task.task_type),
                "subject_has_events": 1 if hours_until_next_subject_event > 0 else 0,
                "hours_until_next_subject_event": hours_until_next_subject_event,
                "day_load_score": calculate_day_load_score(task_day_events),
                "free_hours_today": get_free_hours_today(task_day_events),
                "days_until_deadline": days_until_deadline,
                "recommended_deadline_hours": round(recommended_hours, 2),
                "data_source": "real",
            }

            rows.append(row)

        return rows

    finally:
        db.close()


def generate_synthetic_row():
    estimated_duration = random.choice([0.5, 1, 1.5, 2, 3, 4, 5, 6])
    difficulty = random.randint(1, 5)
    priority = random.randint(1, 4)
    task_type_score = random.randint(1, 5)
    subject_has_events = random.choice([0, 1])

    hours_until_next_subject_event = (
        random.choice([6, 12, 18, 24, 36, 48, 72])
        if subject_has_events
        else 0
    )

    day_load_score = random.randint(0, 100)
    free_hours_today = random.choice([1, 2, 3, 4, 5, 6, 7])
    days_until_deadline = random.choice([1, 2, 3, 4, 5, 7, 10, 14])

    recommended = 48

    recommended += difficulty * 8
    recommended += estimated_duration * 4
    recommended += task_type_score * 3
    recommended -= priority * 7

    if subject_has_events:
        recommended = min(
            recommended,
            max(4, hours_until_next_subject_event - 2),
        )

    if day_load_score > 75:
        recommended += 12
    elif day_load_score > 55:
        recommended += 6

    if free_hours_today <= 2:
        recommended += 8

    if days_until_deadline <= 2:
        recommended = min(recommended, 24)
    elif days_until_deadline <= 4:
        recommended = min(recommended, 48)

    recommended = clamp(recommended, 4, days_until_deadline * 24)

    return {
        "estimated_duration_hours": estimated_duration,
        "difficulty_score": difficulty,
        "priority_score": priority,
        "task_type_score": task_type_score,
        "subject_has_events": subject_has_events,
        "hours_until_next_subject_event": hours_until_next_subject_event,
        "day_load_score": day_load_score,
        "free_hours_today": free_hours_today,
        "days_until_deadline": days_until_deadline,
        "recommended_deadline_hours": round(recommended, 2),
        "data_source": "synthetic",
    }


def generate_dataset(total_rows=3000):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    real_rows = build_real_rows()

    synthetic_count = max(total_rows - len(real_rows), 0)

    synthetic_rows = [
        generate_synthetic_row()
        for _ in range(synthetic_count)
    ]

    rows = real_rows + synthetic_rows

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print("Deadline dataset created")
    print(f"Path: {OUTPUT_PATH}")
    print(f"Total rows: {len(rows)}")
    print(f"Real rows: {len(real_rows)}")
    print(f"Synthetic rows: {len(synthetic_rows)}")


if __name__ == "__main__":
    generate_dataset()