import csv
import os
from collections import defaultdict

from backend.infrastructure.db.database import SessionLocal
from backend.infrastructure.db.models import Event, EventType, Subject, Task, TaskActivityLog

OUTPUT_PATH = "backend/infrastructure/ml/datasets/schedule_load_dataset.csv"

MAX_SINGLE_EVENT_DURATION_HOURS = 6

EXCLUDED_EVENT_WORDS = [
    "train",
    "поїзд",
    "потяг",
    "дорога",
    "подорож",
    "львів",
    "одеса",
    "яремче",
    "татарів",
    "буковель",
]


FIELDNAMES = [
    "date",
    "total_event_hours",
    "number_of_events",
    "first_event_hour",
    "last_event_hour",
    "day_span_hours",
    "lecture_hours",
    "practice_hours",
    "lab_hours",
    "exam_hours",
    "consultation_hours",
    "work_hours",
    "personal_hours",
    "study_event_hours",
    "lecture_count",
    "practice_count",
    "lab_count",
    "exam_count",
    "consultation_count",
    "work_count",
    "personal_count",
    "study_event_count",
    "number_of_subjects",
    "number_of_tasks",
    "planned_tasks",
    "in_progress_tasks",
    "completed_tasks",
    "missed_tasks",
    "total_task_difficulty",
    "avg_task_difficulty",
    "total_task_duration",
    "avg_task_duration",
    "completion_rate",
    "missed_rate",
    "status_changes_count",
    "done_logs_count",
    "missed_logs_count",
    "schedule_load_score",
]


EVENT_TYPES = [
    "lecture",
    "practice",
    "lab",
    "exam",
    "consultation",
    "work",
    "personal",
    "study",
]


def empty_row(date):
    return {
        "date": date,
        "total_event_hours": 0,
        "number_of_events": 0,
        "first_event_hour": 0,
        "last_event_hour": 0,
        "day_span_hours": 0,
        "lecture_hours": 0,
        "practice_hours": 0,
        "lab_hours": 0,
        "exam_hours": 0,
        "consultation_hours": 0,
        "work_hours": 0,
        "personal_hours": 0,
        "study_event_hours": 0,
        "lecture_count": 0,
        "practice_count": 0,
        "lab_count": 0,
        "exam_count": 0,
        "consultation_count": 0,
        "work_count": 0,
        "personal_count": 0,
        "study_event_count": 0,
        "number_of_subjects": 0,
        "number_of_tasks": 0,
        "planned_tasks": 0,
        "in_progress_tasks": 0,
        "completed_tasks": 0,
        "missed_tasks": 0,
        "total_task_difficulty": 0,
        "avg_task_difficulty": 0,
        "total_task_duration": 0,
        "avg_task_duration": 0,
        "completion_rate": 70,
        "missed_rate": 0,
        "status_changes_count": 0,
        "done_logs_count": 0,
        "missed_logs_count": 0,
        "schedule_load_score": 0,
        "_events": [],
        "_subject_ids": set(),
    }


def normalize_text(value):
    return (value or "").strip().lower()


def detect_event_type(event, event_type=None, subject=None):
    title = normalize_text(event.title)
    event_type_name = normalize_text(event_type.name if event_type else "")
    subject_name = normalize_text(subject.name if subject else "")

    full_text = f"{title} {event_type_name} {subject_name}"

    if any(
        word in full_text
        for word in [
            "лекція",
            "лекц",
            "lecture",
            "(л)",
            " л ",
        ]
    ):
        return "lecture"

    if any(
        word in full_text
        for word in [
            "практична",
            "практ",
            "семінар",
            "seminar",
            "practice",
            "(пр)",
            "пр.",
        ]
    ):
        return "practice"

    if any(
        word in full_text
        for word in [
            "лабораторна",
            "лаба",
            "лаб",
            "lab",
            "laboratory",
            "(лаб)",
        ]
    ):
        return "lab"

    if any(
        word in full_text
        for word in [
            "іспит",
            "екзамен",
            "залік",
            "модуль",
            "контрольна",
            "exam",
            "test",
        ]
    ):
        return "exam"

    if any(
        word in full_text
        for word in [
            "консультація",
            "консультац",
            "конс",
            "consultation",
        ]
    ):
        return "consultation"

    if any(
        word in full_text
        for word in [
            "робота",
            "work",
            "job",
            "стажування",
        ]
    ):
        return "work"

    if any(
        word in full_text
        for word in [
            "зал",
            "тренування",
            "спорт",
            "gym",
            "personal",
            "особисте",
            "автошкола",
            "медитація",
        ]
    ):
        return "personal"

    return "study"


def should_skip_event(event, duration_hours):
    title = normalize_text(event.title)

    if duration_hours <= 0:
        return True

    if duration_hours > MAX_SINGLE_EVENT_DURATION_HOURS:
        return True

    if any(word in title for word in EXCLUDED_EVENT_WORDS):
        return True

    return False


def event_duplicate_key(event):
    return (
        normalize_text(event.title),
        event.start_time.isoformat() if event.start_time else "",
        event.end_time.isoformat() if event.end_time else "",
        event.subject_id,
        event.event_type_id,
    )


def merge_intervals(intervals):
    if not intervals:
        return []

    sorted_intervals = sorted(intervals, key=lambda item: item[0])
    merged = [sorted_intervals[0]]

    for current_start, current_end in sorted_intervals[1:]:
        last_start, last_end = merged[-1]

        if current_start <= last_end:
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))

    return merged


def calculate_union_hours(intervals):
    merged = merge_intervals(intervals)

    total = 0

    for start, end in merged:
        total += max((end - start).total_seconds() / 3600, 0)

    return round(total, 2)


def calculate_schedule_load_score(row):
    score = (
        row["lecture_hours"] * 7
        + row["practice_hours"] * 8
        + row["lab_hours"] * 10
        + row["exam_hours"] * 15
        + row["consultation_hours"] * 5
        + row["work_hours"] * 8
        + row["personal_hours"] * 3
        + row["study_event_hours"] * 6
        + row["lecture_count"] * 1.5
        + row["practice_count"] * 2
        + row["lab_count"] * 3
        + row["exam_count"] * 7
        + row["consultation_count"] * 1.5
        + row["work_count"] * 3
        + row["personal_count"] * 0.5
        + row["study_event_count"] * 1.5
        + row["number_of_subjects"] * 2
        + row["number_of_tasks"] * 6
        + row["in_progress_tasks"] * 4
        + row["missed_tasks"] * 8
        + row["total_task_difficulty"] * 4
        + row["total_task_duration"] * 3
        + row["status_changes_count"] * 0.5
    )

    if row["completion_rate"] < 50:
        score += 12
    elif row["completion_rate"] < 70:
        score += 6

    if row["missed_rate"] > 40:
        score += 10
    elif row["missed_rate"] > 20:
        score += 5

    if row["day_span_hours"] > 10:
        score += 8
    elif row["day_span_hours"] > 7:
        score += 4

    return round(min(100, max(0, score)), 2)


def aggregate_events_for_day(row):
    events = row["_events"]

    if not events:
        return

    all_intervals = [(item["start"], item["end"]) for item in events]

    row["total_event_hours"] = calculate_union_hours(all_intervals)
    row["number_of_events"] = len(events)

    first_start = min(item["start"] for item in events)
    last_end = max(item["end"] for item in events)

    row["first_event_hour"] = round(
        first_start.hour + first_start.minute / 60,
        2,
    )

    row["last_event_hour"] = round(
        last_end.hour + last_end.minute / 60,
        2,
    )

    row["day_span_hours"] = round(
        max((last_end - first_start).total_seconds() / 3600, 0),
        2,
    )

    for event_type in EVENT_TYPES:
        type_events = [item for item in events if item["type"] == event_type]

        type_intervals = [(item["start"], item["end"]) for item in type_events]

        hours_key = "study_event_hours" if event_type == "study" else f"{event_type}_hours"

        count_key = "study_event_count" if event_type == "study" else f"{event_type}_count"

        row[hours_key] = calculate_union_hours(type_intervals)
        row[count_key] = len(type_events)


def export_dataset():
    db = SessionLocal()

    try:
        rows = defaultdict(lambda: None)

        event_types = {event_type.id: event_type for event_type in db.query(EventType).all()}

        subjects = {subject.id: subject for subject in db.query(Subject).all()}

        events = db.query(Event).all()
        tasks = db.query(Task).all()
        logs = db.query(TaskActivityLog).all()

        used_event_keys = set()

        skipped_events = 0
        duplicate_events = 0
        used_events = 0

        for event in events:
            if not event.start_time or not event.end_time:
                skipped_events += 1
                continue

            duration = max(
                (event.end_time - event.start_time).total_seconds() / 3600,
                0,
            )

            if should_skip_event(event, duration):
                skipped_events += 1
                continue

            key = event_duplicate_key(event)

            if key in used_event_keys:
                duplicate_events += 1
                continue

            used_event_keys.add(key)

            day = event.start_time.date().isoformat()

            if rows[day] is None:
                rows[day] = empty_row(day)

            row = rows[day]

            event_type = event_types.get(event.event_type_id)
            subject = subjects.get(event.subject_id)

            detected_type = detect_event_type(
                event=event,
                event_type=event_type,
                subject=subject,
            )

            row["_events"].append(
                {
                    "start": event.start_time,
                    "end": event.end_time,
                    "type": detected_type,
                }
            )

            if event.subject_id:
                row["_subject_ids"].add(event.subject_id)

            used_events += 1

        for task in tasks:
            task_date = task.due_date or task.created_at

            if not task_date:
                continue

            day = task_date.date().isoformat()

            if rows[day] is None:
                rows[day] = empty_row(day)

            row = rows[day]

            difficulty_score = task.difficulty_score or 3
            estimated_duration_hours = task.estimated_duration_hours or 1

            row["number_of_tasks"] += 1
            row["total_task_difficulty"] += int(difficulty_score)
            row["total_task_duration"] += float(estimated_duration_hours)

            if task.status == "planned":
                row["planned_tasks"] += 1
            elif task.status == "in_progress":
                row["in_progress_tasks"] += 1
            elif task.status == "done":
                row["completed_tasks"] += 1
            elif task.status == "missed":
                row["missed_tasks"] += 1

            if task.subject_id:
                row["_subject_ids"].add(task.subject_id)

        for log in logs:
            if not log.created_at:
                continue

            day = log.created_at.date().isoformat()

            if rows[day] is None:
                rows[day] = empty_row(day)

            row = rows[day]

            row["status_changes_count"] += 1

            if log.new_status == "done":
                row["done_logs_count"] += 1

            if log.new_status == "missed":
                row["missed_logs_count"] += 1

        final_rows = []

        for row in rows.values():
            aggregate_events_for_day(row)

            row["number_of_subjects"] = len(row["_subject_ids"])

            finished_tasks = row["completed_tasks"] + row["missed_tasks"]

            if finished_tasks > 0:
                row["completion_rate"] = round(
                    row["completed_tasks"] / finished_tasks * 100,
                    2,
                )

                row["missed_rate"] = round(
                    row["missed_tasks"] / finished_tasks * 100,
                    2,
                )

            if row["number_of_tasks"] > 0:
                row["avg_task_difficulty"] = round(
                    row["total_task_difficulty"] / row["number_of_tasks"],
                    2,
                )

                row["avg_task_duration"] = round(
                    row["total_task_duration"] / row["number_of_tasks"],
                    2,
                )

            for key in list(row.keys()):
                if key.endswith("_hours") or key in [
                    "total_task_duration",
                    "avg_task_duration",
                    "first_event_hour",
                    "last_event_hour",
                    "day_span_hours",
                ]:
                    row[key] = round(row[key], 2)

            row["schedule_load_score"] = calculate_schedule_load_score(row)

            row.pop("_events", None)
            row.pop("_subject_ids", None)

            final_rows.append(row)

        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

        with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(sorted(final_rows, key=lambda item: item["date"]))

        print("Dataset exported successfully")
        print(f"Path: {OUTPUT_PATH}")
        print(f"Rows: {len(final_rows)}")
        print(f"Events in DB: {len(events)}")
        print(f"Events used: {used_events}")
        print(f"Events skipped: {skipped_events}")
        print(f"Duplicate events skipped: {duplicate_events}")
        print(f"Tasks used: {len(tasks)}")
        print(f"Activity logs used: {len(logs)}")

    finally:
        db.close()


if __name__ == "__main__":
    export_dataset()
