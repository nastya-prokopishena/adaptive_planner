import json
from datetime import UTC, datetime, time, timedelta
from types import SimpleNamespace

import requests
from flask import Blueprint, current_app, jsonify, redirect, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from backend.application.analytics_service import AnalyticsService
from backend.application.ml_deadline_service import MLDeadlineService
from backend.application.ml_task_planner_service import MLTaskPlannerService
from backend.application.productivity_model_service import ProductivityModelService
from backend.application.schedule_import_service import ScheduleImportService
from backend.application.schedule_service import ScheduleService
from backend.application.synthetic_deadline_dataset_service import SyntheticDeadlineDatasetService
from backend.application.task_file_extractor_service import TaskFileExtractorService
from backend.application.task_nlp_service import TaskNLPService
from backend.application.task_schedule_block_service import TaskScheduleBlockService
from backend.domain.models.time_slot import TimeSlot
from backend.domain.recurrence import build_google_rrule, generate_occurrences, time_ranges_overlap
from backend.domain.services.auto_planner import plan_task_with_ortools
from backend.infrastructure.db.database import SessionLocal
from backend.infrastructure.db.models import (
    Event,
    EventType,
    Subject,
    Task,
    TaskActivityLog,
    TaskScheduleBlock,
    User,
)
from backend.infrastructure.google_calendar_adapter import GoogleCalendarAdapter

calendar_adapter = GoogleCalendarAdapter()
schedule_service = ScheduleService()
schedule_import_service = ScheduleImportService()
task_nlp_service = TaskNLPService()
task_file_extractor_service = TaskFileExtractorService()
analytics_service = AnalyticsService()
productivity_model_service = ProductivityModelService()
ml_task_planner_service = MLTaskPlannerService()
ml_deadline_service = MLDeadlineService()
task_schedule_block_service = TaskScheduleBlockService()
synthetic_deadline_dataset_service = SyntheticDeadlineDatasetService()


COMPLETED_TASK_STATUSES = {"done", "completed"}
MISSED_TASK_STATUS = "missed"
AUTO_REPLAN_ACTION = "task_auto_replanned"
AUTO_REPLAN_LIMIT_ACTION = "task_auto_replan_limit_reached"
MAX_AUTO_REPLAN_ATTEMPTS = 3
PRIORITY_ESCALATION_REPLAN_COUNT = 3
HIGH_PRIORITY = "high"
BEST_FREE_TIME_MODE = "best_free_time"


def to_aware_utc(value):
    if not value:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def to_storage_datetime(value):
    aware_value = to_aware_utc(value)

    if not aware_value:
        return None

    return aware_value.replace(tzinfo=None)


def refresh_task_deadline_status(task, now=None):
    if not task or not getattr(task, "due_date", None):
        return False

    current_status = (getattr(task, "status", None) or "").lower()

    if current_status in COMPLETED_TASK_STATUSES:
        return False

    deadline = to_aware_utc(task.due_date)
    current_time = now or datetime.now(UTC)

    if deadline and deadline < current_time and current_status != MISSED_TASK_STATUS:
        task.status = MISSED_TASK_STATUS
        task.missed_at = to_storage_datetime(current_time)
        task.completed_at = None
        task.updated_at = to_storage_datetime(current_time)
        return True

    return False


def get_task_auto_replan_count(db, task_id):
    if not task_id:
        return 0

    return (
        db.query(TaskActivityLog)
        .filter(TaskActivityLog.task_id == task_id)
        .filter(TaskActivityLog.action == AUTO_REPLAN_ACTION)
        .count()
    )


def has_auto_replan_limit_log(db, task_id):
    if not task_id:
        return False

    return (
        db.query(TaskActivityLog)
        .filter(TaskActivityLog.task_id == task_id)
        .filter(TaskActivityLog.action == AUTO_REPLAN_LIMIT_ACTION)
        .first()
        is not None
    )


def set_auto_replan_metadata(db, task):
    replan_count = get_task_auto_replan_count(db, task.id)
    limit_reached = replan_count >= MAX_AUTO_REPLAN_ATTEMPTS

    task.auto_replan_count = replan_count
    task.auto_replan_limit = MAX_AUTO_REPLAN_ATTEMPTS
    task.auto_replan_attempts_left = max(MAX_AUTO_REPLAN_ATTEMPTS - replan_count, 0)
    task.auto_replan_limit_reached = limit_reached

    return task


def set_tasks_auto_replan_metadata(db, tasks):
    for task in tasks:
        set_auto_replan_metadata(db, task)

    return tasks


def should_auto_replan_task(task, now=None):
    if not task or not getattr(task, "due_date", None):
        return False

    current_status = (getattr(task, "status", None) or "").lower()

    if current_status in COMPLETED_TASK_STATUSES:
        return False

    deadline = to_aware_utc(task.due_date)
    current_time = now or datetime.now(UTC)

    return bool(deadline and deadline < current_time)


def auto_replan_missed_task(db, user_id, task):
    old_deadline = task.due_date
    previous_status = task.status
    current_replan_count = get_task_auto_replan_count(db, task.id)

    if current_replan_count >= MAX_AUTO_REPLAN_ATTEMPTS:
        current_time = datetime.now(UTC)
        task.status = MISSED_TASK_STATUS
        task.missed_at = to_storage_datetime(current_time)
        task.completed_at = None
        task.priority = HIGH_PRIORITY
        task.updated_at = to_storage_datetime(current_time)
        set_auto_replan_metadata(db, task)

        if not has_auto_replan_limit_log(db, task.id):
            create_task_log(
                db=db,
                user_id=user_id,
                task_id=task.id,
                action=AUTO_REPLAN_LIMIT_ACTION,
                old_status=previous_status,
                new_status=MISSED_TASK_STATUS,
                details=(
                    f"Automatic replanning limit reached. "
                    f"Attempts: {current_replan_count}. "
                    f"Old deadline: {old_deadline}."
                ),
            )

        return None

    prediction, block = apply_auto_deadline_to_task(
        db=db,
        user_id=user_id,
        task=task,
        mode=BEST_FREE_TIME_MODE,
    )

    new_replan_count = current_replan_count + 1

    task.status = "planned"
    task.missed_at = None
    task.completed_at = None

    if new_replan_count >= PRIORITY_ESCALATION_REPLAN_COUNT:
        task.priority = HIGH_PRIORITY

    task.updated_at = to_storage_datetime(datetime.now(UTC))

    create_task_log(
        db=db,
        user_id=user_id,
        task_id=task.id,
        action=AUTO_REPLAN_ACTION,
        old_status=previous_status,
        new_status="planned",
        details=(
            f"Task automatically replanned. "
            f"Attempt: {new_replan_count}. "
            f"Old deadline: {old_deadline}. "
            f"New deadline: {prediction['deadline']}."
        ),
    )

    set_auto_replan_metadata(db, task)

    return {
        "task_id": task.id,
        "title": task.title,
        "old_deadline": old_deadline.isoformat() if old_deadline else None,
        "new_deadline": prediction["deadline"].isoformat(),
        "replan_count": new_replan_count,
        "replan_limit": MAX_AUTO_REPLAN_ATTEMPTS,
        "attempts_left": max(MAX_AUTO_REPLAN_ATTEMPTS - new_replan_count, 0),
        "limit_reached": new_replan_count >= MAX_AUTO_REPLAN_ATTEMPTS,
        "priority": task.priority,
        "reason": prediction.get("reason"),
        "block_id": getattr(block, "id", None),
    }


def refresh_and_replan_missed_tasks(db, user_id, tasks):
    now = datetime.now(UTC)
    changed = False
    replanned_tasks = []

    for task in tasks:
        if not should_auto_replan_task(task, now=now):
            set_auto_replan_metadata(db, task)
            continue

        refresh_task_deadline_status(task, now=now)
        changed = True

        try:
            replan_result = auto_replan_missed_task(
                db=db,
                user_id=user_id,
                task=task,
            )

            if replan_result:
                replanned_tasks.append(replan_result)

        except Exception as error:
            print("Auto replan missed task error:", error)
            set_auto_replan_metadata(db, task)

    if changed:
        db.commit()

    set_tasks_auto_replan_metadata(db, tasks)

    return {
        "changed": changed,
        "replanned": replanned_tasks,
        "replanned_count": len(replanned_tasks),
    }


def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    db = SessionLocal()

    try:
        return db.query(User).filter_by(id=user_id).first()
    finally:
        db.close()


def parse_datetime(value):
    if not value:
        return None

    value = value.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def parse_google_event_time(event_time):
    if not event_time:
        return None

    if event_time.get("dateTime"):
        return parse_datetime(event_time["dateTime"])

    if event_time.get("date"):
        return datetime.combine(
            datetime.fromisoformat(event_time["date"]).date(),
            time.min,
        )

    return None


def parse_recurrence_payload(data, start_time, existing_event=None):
    if "recurrence" not in data and existing_event:
        return {
            "recurrence_type": existing_event.recurrence_type or "none",
            "recurrence_interval": existing_event.recurrence_interval or 1,
            "recurrence_unit": existing_event.recurrence_unit,
            "recurrence_days": existing_event.recurrence_days,
            "recurrence_end_type": existing_event.recurrence_end_type or "never",
            "recurrence_end_date": existing_event.recurrence_end_date,
            "recurrence_count": existing_event.recurrence_count,
            "recurrence_rule": existing_event.recurrence_rule,
        }

    recurrence = data.get("recurrence") or {}

    recurrence_type = recurrence.get("type", "none")
    recurrence_interval = int(recurrence.get("interval") or 1)
    recurrence_unit = recurrence.get("unit")
    recurrence_days = recurrence.get("days") or []
    recurrence_end_type = recurrence.get("endType", "never")
    recurrence_end_date = parse_datetime(recurrence.get("endDate"))
    recurrence_count = recurrence.get("count")

    if recurrence_count:
        recurrence_count = int(recurrence_count)

    if isinstance(recurrence_days, list):
        recurrence_days_string = ",".join(recurrence_days)
    else:
        recurrence_days_string = recurrence_days

    recurrence_rule = build_google_rrule(
        recurrence_type=recurrence_type,
        recurrence_interval=recurrence_interval,
        recurrence_unit=recurrence_unit,
        recurrence_days=recurrence_days_string,
        recurrence_end_type=recurrence_end_type,
        recurrence_end_date=recurrence_end_date,
        recurrence_count=recurrence_count,
        start_time=start_time,
    )

    return {
        "recurrence_type": recurrence_type,
        "recurrence_interval": recurrence_interval,
        "recurrence_unit": recurrence_unit,
        "recurrence_days": recurrence_days_string,
        "recurrence_end_type": recurrence_end_type,
        "recurrence_end_date": recurrence_end_date,
        "recurrence_count": recurrence_count,
        "recurrence_rule": recurrence_rule,
    }


def serialize_event(event, occurrence_start=None, occurrence_end=None):
    start = occurrence_start or event.start_time
    end = occurrence_end or event.end_time
    is_occurrence = occurrence_start is not None

    return {
        "id": f"{event.id}__{start.isoformat()}" if is_occurrence else str(event.id),
        "master_id": event.id,
        "title": event.title,
        "start": start.isoformat() if start else None,
        "end": end.isoformat() if end else None,
        "source": event.source,
        "google_event_id": event.google_event_id,
        "is_recurring": (event.recurrence_type or "none") != "none",
        "recurrence": {
            "type": event.recurrence_type or "none",
            "interval": event.recurrence_interval or 1,
            "unit": event.recurrence_unit,
            "days": event.recurrence_days.split(",") if event.recurrence_days else [],
            "endType": event.recurrence_end_type or "never",
            "endDate": event.recurrence_end_date.isoformat() if event.recurrence_end_date else "",
            "count": event.recurrence_count or "",
        },
    }


def parse_optional_datetime(value):
    if not value:
        return None

    value = value.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def serialize_event_type(event_type):
    return {
        "id": event_type.id,
        "user_id": event_type.user_id,
        "name": event_type.name,
        "color": event_type.color,
        "is_default": event_type.is_default,
        "created_at": event_type.created_at.isoformat() if event_type.created_at else None,
    }


def serialize_subject(subject):
    return {
        "id": subject.id,
        "user_id": subject.user_id,
        "name": subject.name,
        "teacher": subject.teacher,
        "description": subject.description,
        "color": subject.color,
        "created_at": subject.created_at.isoformat() if subject.created_at else None,
    }


def serialize_task(task):
    keywords = []

    if getattr(task, "keywords", None):
        try:
            keywords = json.loads(task.keywords)
        except Exception:
            keywords = []

    return {
        "id": task.id,
        "user_id": task.user_id,
        "event_id": task.event_id,
        "subject_id": task.subject_id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "completed_at": (
            task.completed_at.isoformat() if getattr(task, "completed_at", None) else None
        ),
        "missed_at": task.missed_at.isoformat() if getattr(task, "missed_at", None) else None,
        "task_type": getattr(task, "task_type", "other"),
        "keywords": keywords,
        "estimated_duration_hours": getattr(
            task,
            "estimated_duration_hours",
            None,
        ),
        "difficulty_score": getattr(task, "difficulty_score", None),
        "nlp_source": getattr(task, "nlp_source", None),
        "created_at": task.created_at.isoformat() if getattr(task, "created_at", None) else None,
        "updated_at": task.updated_at.isoformat() if getattr(task, "updated_at", None) else None,
        "auto_replan_count": getattr(task, "auto_replan_count", 0),
        "auto_replan_limit": getattr(task, "auto_replan_limit", MAX_AUTO_REPLAN_ATTEMPTS),
        "auto_replan_attempts_left": getattr(
            task,
            "auto_replan_attempts_left",
            MAX_AUTO_REPLAN_ATTEMPTS,
        ),
        "auto_replan_limit_reached": getattr(task, "auto_replan_limit_reached", False),
    }


def serialize_activity_log(log):
    return {
        "id": log.id,
        "user_id": log.user_id,
        "task_id": log.task_id,
        "action": log.action,
        "old_status": log.old_status,
        "new_status": log.new_status,
        "details": log.details,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def create_task_log(
    db,
    user_id,
    task_id,
    action,
    old_status=None,
    new_status=None,
    details=None,
):
    log = TaskActivityLog(
        user_id=user_id,
        task_id=task_id,
        action=action,
        old_status=old_status,
        new_status=new_status,
        details=details,
    )

    db.add(log)


def find_subject_by_name(db, user_id, subject_name):
    if not subject_name:
        return None

    return (
        db.query(Subject)
        .filter(Subject.user_id == user_id)
        .filter(Subject.name.ilike(subject_name))
        .first()
    )


def get_excluded_dates(event):
    if not event.recurrence_excluded_dates:
        return []

    return [item.strip() for item in event.recurrence_excluded_dates.split(",") if item.strip()]


def add_excluded_date(event, occurrence_start):
    excluded_dates = get_excluded_dates(event)
    occurrence_key = occurrence_start.isoformat()

    if occurrence_key not in excluded_dates:
        excluded_dates.append(occurrence_key)

    event.recurrence_excluded_dates = ",".join(excluded_dates)


def get_event_occurrences(event):
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

    excluded_dates = get_excluded_dates(event)

    filtered_occurrences = []

    for start, end in occurrences:
        if start.isoformat() not in excluded_dates:
            filtered_occurrences.append((start, end))

    return filtered_occurrences


def get_candidate_occurrences(start_time, end_time, recurrence_data):
    return generate_occurrences(
        start_time=start_time,
        end_time=end_time,
        recurrence_type=recurrence_data["recurrence_type"],
        recurrence_interval=recurrence_data["recurrence_interval"],
        recurrence_unit=recurrence_data["recurrence_unit"],
        recurrence_days=recurrence_data["recurrence_days"],
        recurrence_end_type=recurrence_data["recurrence_end_type"],
        recurrence_end_date=recurrence_data["recurrence_end_date"],
        recurrence_count=recurrence_data["recurrence_count"],
        horizon_days=365,
    )


def has_time_conflict(
    db,
    user_id,
    start_time,
    end_time,
    recurrence_data,
    exclude_event_id=None,
):
    candidate_occurrences = get_candidate_occurrences(
        start_time=start_time,
        end_time=end_time,
        recurrence_data=recurrence_data,
    )

    query = db.query(Event).filter(Event.user_id == user_id)

    if exclude_event_id:
        query = query.filter(Event.id != exclude_event_id)

    existing_events = query.all()

    for existing_event in existing_events:
        if not existing_event.start_time or not existing_event.end_time:
            continue

        existing_occurrences = get_event_occurrences(existing_event)

        for candidate_start, candidate_end in candidate_occurrences:
            for existing_start, existing_end in existing_occurrences:
                if time_ranges_overlap(
                    candidate_start,
                    candidate_end,
                    existing_start,
                    existing_end,
                ):
                    return existing_event

    return None


def sync_google_events_to_db(user, db):
    if not user.google_credentials:
        return

    google_events = schedule_service.get_google_events(
        json.loads(user.google_credentials),
        single_events=False,
    )

    for google_event in google_events:
        google_event_id = google_event.get("id")

        if not google_event_id:
            continue

        title = google_event.get("summary") or "Без назви"
        start_time = parse_google_event_time(google_event.get("start"))
        end_time = parse_google_event_time(google_event.get("end"))

        if not start_time or not end_time:
            continue

        existing_event = (
            db.query(Event)
            .filter_by(
                user_id=user.id,
                google_event_id=google_event_id,
            )
            .first()
        )

        if existing_event:
            existing_event.title = title
            existing_event.start_time = start_time
            existing_event.end_time = end_time
            existing_event.source = "google"
        else:
            new_event = Event(
                user_id=user.id,
                title=title,
                start_time=start_time,
                end_time=end_time,
                source="google",
                google_event_id=google_event_id,
                recurrence_type="none",
            )

            db.add(new_event)

    db.commit()


def serialize_task_schedule_block(block, task=None):
    return {
        "id": block.id,
        "task_id": block.task_id,
        "title": f"📚 Робота над: {task.title if task else 'задачею'}",
        "start": block.start_time.isoformat() if block.start_time else None,
        "end": block.end_time.isoformat() if block.end_time else None,
        "source": block.source,
        "calendar_type": "ai_task_block",
        "generated_by_ai": block.generated_by_ai,
        "confidence_score": block.confidence_score,
        "reason": getattr(block, "reason", None),
        "color": {
            "bg": "#7c3aed",
            "bg2": "#22c55e",
        },
    }


def resolve_subject_id(db, user_id, subject_id=None, subject_name=None):
    if subject_id:
        try:
            return int(subject_id)
        except (TypeError, ValueError):
            pass

    subject = find_subject_by_name(
        db=db,
        user_id=user_id,
        subject_name=subject_name,
    )

    if subject:
        return subject.id

    return None


def get_subject_name_by_id(db, user_id, subject_id):
    if not subject_id:
        return None

    subject = (
        db.query(Subject)
        .filter(Subject.user_id == user_id)
        .filter(Subject.id == int(subject_id))
        .first()
    )

    return subject.name if subject else None


def normalize_text(value):
    return (value or "").strip().lower()


def event_matches_subject(event, subject_id=None, subject_name=None):
    if subject_id and event.subject_id == int(subject_id):
        return True

    if subject_name:
        event_title = normalize_text(event.title)
        subject_text = normalize_text(subject_name)

        if subject_text and subject_text in event_title:
            return True

    return False


def get_subject_events(db, user_id, subject_id=None, subject_name=None):
    now = datetime.now(UTC)

    if subject_id and not subject_name:
        subject_name = get_subject_name_by_id(
            db=db,
            user_id=user_id,
            subject_id=subject_id,
        )

    events = db.query(Event).filter(Event.user_id == user_id).order_by(Event.start_time.asc()).all()

    matched_events = [
        event
        for event in events
        if event_matches_subject(
            event=event,
            subject_id=subject_id,
            subject_name=subject_name,
        )
    ]

    expanded_events = []

    for event in matched_events:
        is_recurring = event.recurrence_type and event.recurrence_type != "none"

        if is_recurring:
            occurrences = get_event_occurrences(event)

            for occurrence_start, occurrence_end in occurrences:
                if occurrence_start and occurrence_start > now:
                    expanded_events.append(
                        SimpleNamespace(
                            id=event.id,
                            master_id=event.id,
                            title=event.title,
                            start_time=occurrence_start,
                            end_time=occurrence_end,
                            subject_id=event.subject_id,
                            source=event.source,
                        )
                    )
        else:
            if event.start_time and event.start_time > now:
                expanded_events.append(event)

    return sorted(
        expanded_events,
        key=lambda item: item.start_time,
    )


def get_user_calendar_events(db, user_id):
    now = datetime.now(UTC)

    events = db.query(Event).filter(Event.user_id == user_id).order_by(Event.start_time.asc()).all()

    expanded_events = []

    for event in events:
        is_recurring = event.recurrence_type and event.recurrence_type != "none"

        if is_recurring:
            occurrences = get_event_occurrences(event)

            for occurrence_start, occurrence_end in occurrences:
                if occurrence_start and occurrence_end and occurrence_start > now:
                    expanded_events.append(
                        SimpleNamespace(
                            id=event.id,
                            master_id=event.id,
                            title=event.title,
                            start_time=occurrence_start,
                            end_time=occurrence_end,
                            subject_id=event.subject_id,
                            source=event.source,
                        )
                    )
        else:
            if event.start_time and event.end_time and event.start_time > now:
                expanded_events.append(event)

    return sorted(
        expanded_events,
        key=lambda item: item.start_time,
    )


def get_existing_subject_deadline_count(
    db,
    user_id,
    subject_id=None,
    subject_name=None,
    exclude_task_id=None,
):
    now = datetime.now(UTC)

    resolved_subject_id = resolve_subject_id(
        db=db,
        user_id=user_id,
        subject_id=subject_id,
        subject_name=subject_name,
    )

    if not resolved_subject_id:
        return 0

    query = (
        db.query(Task)
        .filter(Task.user_id == user_id)
        .filter(Task.subject_id == resolved_subject_id)
        .filter(Task.due_date.isnot(None))
        .filter(Task.due_date > now)
    )

    if exclude_task_id:
        query = query.filter(Task.id != exclude_task_id)

    return query.count()


def get_existing_deadline_dates(db, user_id):
    now = datetime.now(UTC)

    tasks = (
        db.query(Task)
        .filter(Task.user_id == user_id)
        .filter(Task.due_date.isnot(None))
        .filter(Task.due_date > now)
        .all()
    )

    return [task.due_date.date() for task in tasks if task.due_date]


def build_subject_distribution_index(
    existing_count,
    task_position,
    task_total,
    subject_events_count,
):
    if task_total <= 1:
        return existing_count

    remaining_events = max(subject_events_count - existing_count, 1)

    if remaining_events >= task_total:
        offset = int(task_position * remaining_events / task_total)
        return existing_count + offset

    return existing_count + task_position


def apply_auto_deadline_to_task(
    db,
    user_id,
    task,
    mode="subject_based",
    used_event_index=None,
    subject_name=None,
    used_best_time_dates=None,
):
    subject_events = get_subject_events(
        db=db,
        user_id=user_id,
        subject_id=task.subject_id,
        subject_name=subject_name,
    )

    calendar_events = get_user_calendar_events(
        db=db,
        user_id=user_id,
    )

    if used_event_index is None:
        used_event_index = get_existing_subject_deadline_count(
            db=db,
            user_id=user_id,
            subject_id=task.subject_id,
            subject_name=subject_name,
            exclude_task_id=task.id,
        )

    prediction = safe_predict_deadline(
        task=task,
        subject_events=subject_events,
        calendar_events=calendar_events,
        mode=mode,
        used_event_index=used_event_index,
        used_best_time_dates=used_best_time_dates or [],
    )

    task.due_date = to_storage_datetime(prediction["deadline"])
    task.updated_at = to_storage_datetime(datetime.now(UTC))
    prediction["deadline"] = task.due_date

    block = task_schedule_block_service.recreate_block_for_task(
        db=db,
        user_id=user_id,
        task=task,
        deadline=prediction["deadline"],
        confidence_score=prediction["confidence"],
        reason=prediction["reason"],
    )

    return prediction, block


def normalize_deadline_mode(mode):
    if mode in ["subject", "subject_pairs", "subject_based", "by_subject"]:
        return "subject_based"

    if mode in ["free", "best_time", "best_free_time", "free_time"]:
        return "best_free_time"

    return mode or "subject_based"


def fallback_deadline_prediction(
    task,
    subject_events=None,
    calendar_events=None,
    mode="subject_based",
    used_event_index=0,
    used_best_time_dates=None,
):
    subject_events = subject_events or []
    used_best_time_dates = used_best_time_dates or []
    now = datetime.now(UTC)

    normalized_mode = normalize_deadline_mode(mode)

    if normalized_mode == "subject_based" and subject_events:
        event_index = min(
            max(int(used_event_index or 0), 0),
            len(subject_events) - 1,
        )
        target_event = subject_events[event_index]

        event_start = target_event.start_time

        if event_start.tzinfo is None:
            event_start = event_start.replace(tzinfo=UTC)

        deadline = event_start - timedelta(hours=2)

        if deadline <= now:
            deadline = event_start - timedelta(minutes=30)

        if target_event.start_time.tzinfo is None:
            deadline = deadline.replace(tzinfo=None)

        return {
            "deadline": deadline,
            "confidence": 0.72,
            "reason": "Fallback: дедлайн поставлено перед найближчою парою предмету.",
        }

    base_days = max(int(getattr(task, "difficulty_score", 3) or 3), 1)
    duration_bonus = int(float(getattr(task, "estimated_duration_hours", 1) or 1) // 2)
    deadline_date = (now + timedelta(days=base_days + duration_bonus)).date()

    blocked_dates = {item if hasattr(item, "isoformat") else item for item in used_best_time_dates}

    while deadline_date in blocked_dates:
        deadline_date = deadline_date + timedelta(days=1)

    deadline = datetime.combine(deadline_date, time(hour=20, minute=0))

    return {
        "deadline": deadline,
        "confidence": 0.55,
        "reason": "Fallback: дедлайн підібрано за складністю і завантаженням.",
    }


def safe_predict_deadline(
    task,
    subject_events=None,
    calendar_events=None,
    mode="subject_based",
    used_event_index=0,
    used_best_time_dates=None,
):
    normalized_mode = normalize_deadline_mode(mode)

    try:
        return ml_deadline_service.predict_deadline(
            task=task,
            subject_events=subject_events or [],
            calendar_events=calendar_events or [],
            mode=normalized_mode,
            used_event_index=used_event_index,
            used_best_time_dates=used_best_time_dates or [],
        )
    except Exception as error:
        print("ML deadline prediction error:", error)

        return fallback_deadline_prediction(
            task=task,
            subject_events=subject_events or [],
            calendar_events=calendar_events or [],
            mode=normalized_mode,
            used_event_index=used_event_index,
            used_best_time_dates=used_best_time_dates or [],
        )
