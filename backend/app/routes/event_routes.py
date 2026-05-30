import json

from flask import Blueprint, jsonify, request

from backend.app.routes.common import (
    Event,
    SessionLocal,
    TimeSlot,
    add_excluded_date,
    build_google_rrule,
    current_user,
    get_event_occurrences,
    has_time_conflict,
    parse_datetime,
    parse_recurrence_payload,
    plan_task_with_ortools,
    schedule_service,
    serialize_event,
    sync_google_events_to_db,
)

event_bp = Blueprint("event", __name__)

GOOGLE_DELETE_ERROR = "Google delete error:"
GOOGLE_UPDATE_RECURRENCE_ERROR = "Google update recurrence error:"
GOOGLE_AUTO_PLAN_CREATE_ERROR = "Google auto-plan create error:"


def is_recurring_event(event):
    return bool(event.recurrence_type and event.recurrence_type != "none")


def serialize_event_with_occurrences(event):
    if not is_recurring_event(event):
        return [serialize_event(event)]

    return [
        serialize_event(
            event,
            occurrence_start=occurrence_start,
            occurrence_end=occurrence_end,
        )
        for occurrence_start, occurrence_end in get_event_occurrences(event)
    ]


def get_user_events(db, user_id):
    return db.query(Event).filter_by(user_id=user_id).order_by(Event.start_time.asc()).all()


def delete_google_event_if_needed(user, event):
    if not user.google_credentials or not event.google_event_id:
        return

    try:
        schedule_service.delete_google_event(
            json.loads(user.google_credentials),
            event.google_event_id,
        )
    except Exception as error:
        print(GOOGLE_DELETE_ERROR, error)


def update_google_event_recurrence_if_needed(user, event):
    if not user.google_credentials or not event.google_event_id:
        return

    try:
        schedule_service.update_google_event(
            json.loads(user.google_credentials),
            event.google_event_id,
            event.title,
            event.start_time.isoformat(),
            event.end_time.isoformat(),
            recurrence_rule=event.recurrence_rule,
        )
    except Exception as error:
        print(GOOGLE_UPDATE_RECURRENCE_ERROR, error)


def delete_non_recurring_event(db, user, event):
    delete_google_event_if_needed(user, event)

    db.delete(event)
    db.commit()

    return jsonify({"message": "Event deleted"})


def delete_single_occurrence(db, event, occurrence_start):
    if not occurrence_start:
        return jsonify({"error": "Occurrence start is required"}), 400

    add_excluded_date(event, occurrence_start)
    db.commit()

    return jsonify(
        {
            "message": "Single occurrence deleted",
            "scope": "this",
        }
    )


def delete_future_occurrences(db, user, event, occurrence_start):
    if not occurrence_start:
        return jsonify({"error": "Occurrence start is required"}), 400

    event.recurrence_end_type = "on"
    event.recurrence_end_date = occurrence_start
    event.recurrence_rule = build_google_rrule(
        recurrence_type=event.recurrence_type,
        recurrence_interval=event.recurrence_interval,
        recurrence_unit=event.recurrence_unit,
        recurrence_days=event.recurrence_days,
        recurrence_end_type=event.recurrence_end_type,
        recurrence_end_date=event.recurrence_end_date,
        recurrence_count=event.recurrence_count,
        start_time=event.start_time,
    )

    update_google_event_recurrence_if_needed(user, event)
    db.commit()

    return jsonify(
        {
            "message": "Future occurrences deleted",
            "scope": "future",
        }
    )


def delete_recurring_series(db, user, event):
    delete_google_event_if_needed(user, event)

    db.delete(event)
    db.commit()

    return jsonify(
        {
            "message": "Recurring event series deleted",
            "scope": "all",
        }
    )


def clean_event_ids(event_ids):
    clean_ids = []

    for event_id in event_ids:
        clean_id = str(event_id).split("__")[0]

        if clean_id.isdigit():
            clean_ids.append(int(clean_id))

    return clean_ids


def get_events_to_delete(db, user_id, event_ids, delete_all_by_title, title):
    if delete_all_by_title and title:
        events = db.query(Event).filter(Event.user_id == user_id).all()
        return [event for event in events if event.title.lower() == title]

    clean_ids = clean_event_ids(event_ids)

    return db.query(Event).filter(Event.user_id == user_id).filter(Event.id.in_(clean_ids)).all()


def sync_auto_planned_event_with_google(user, event, google_sync_errors):
    if not user.google_credentials:
        return

    try:
        google_event = schedule_service.create_google_event(
            json.loads(user.google_credentials),
            event.title,
            event.start_time.isoformat(),
            event.end_time.isoformat(),
        )

        event.google_event_id = google_event.get("id")
        event.source = "google"

    except Exception as google_error:
        print(GOOGLE_AUTO_PLAN_CREATE_ERROR, google_error)
        google_sync_errors.append(str(google_error))
        event.source = "local"


def create_auto_planned_event(db, user, planned_item, google_sync_errors):
    event = Event(
        user_id=user.id,
        title=planned_item["title"],
        start_time=planned_item["start"],
        end_time=planned_item["end"],
        source="local",
        recurrence_type="none",
    )

    db.add(event)
    db.flush()

    sync_auto_planned_event_with_google(user, event, google_sync_errors)

    db.flush()

    return serialize_event(event)


@event_bp.route("/api/events", methods=["GET"])
def get_events():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    db = SessionLocal()

    try:
        sync_google_events_to_db(user, db)

        events = get_user_events(db, user.id)
        result = []

        for event in events:
            result.extend(serialize_event_with_occurrences(event))

        return jsonify(result)

    finally:
        db.close()


@event_bp.route("/api/events", methods=["POST"])
def create_event_api():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    title = data.get("title")
    start = data.get("start")
    end = data.get("end")

    if not title or not start or not end:
        return jsonify({"error": "Title, start and end are required"}), 400

    start_time = parse_datetime(start)
    end_time = parse_datetime(end)

    if not start_time or not end_time:
        return jsonify({"error": "Invalid datetime format"}), 400

    try:
        TimeSlot(start_time, end_time)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    recurrence_data = parse_recurrence_payload(data, start_time)

    db = SessionLocal()

    try:
        conflict_event = has_time_conflict(
            db=db,
            user_id=user.id,
            start_time=start_time,
            end_time=end_time,
            recurrence_data=recurrence_data,
        )

        if conflict_event:
            return (
                jsonify(
                    {
                        "error": "Time conflict",
                        "message": "This event overlaps with another event",
                        "conflict_event": serialize_event(conflict_event),
                    }
                ),
                409,
            )

        event = Event(
            user_id=user.id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            source="local",
            event_type_id=data.get("event_type_id"),
            subject_id=data.get("subject_id"),
            recurrence_type=recurrence_data["recurrence_type"],
            recurrence_interval=recurrence_data["recurrence_interval"],
            recurrence_unit=recurrence_data["recurrence_unit"],
            recurrence_days=recurrence_data["recurrence_days"],
            recurrence_end_type=recurrence_data["recurrence_end_type"],
            recurrence_end_date=recurrence_data["recurrence_end_date"],
            recurrence_count=recurrence_data["recurrence_count"],
            recurrence_rule=recurrence_data["recurrence_rule"],
        )

        db.add(event)
        db.commit()
        db.refresh(event)

        google_sync_error = None

        if user.google_credentials:
            try:
                google_event = schedule_service.create_google_event(
                    json.loads(user.google_credentials),
                    title,
                    event.start_time.isoformat(),
                    event.end_time.isoformat(),
                    recurrence_rule=event.recurrence_rule,
                )

                event.google_event_id = google_event.get("id")
                event.source = "google"

                db.commit()
                db.refresh(event)

            except Exception as google_error:
                print("Google event create error:", google_error)
                google_sync_error = str(google_error)
                event.source = "local"
                db.commit()
                db.refresh(event)

        response = serialize_event(event)
        response["google_sync_failed"] = google_sync_error is not None
        response["google_sync_error"] = google_sync_error

        return jsonify(response), 201

    finally:
        db.close()


@event_bp.route("/api/events/<int:event_id>", methods=["PUT"])
def update_event_api(event_id):
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    db = SessionLocal()

    try:
        event = db.query(Event).filter_by(id=event_id, user_id=user.id).first()

        if not event:
            return jsonify({"error": "Event not found"}), 404

        title = data.get("title", event.title)

        start = data.get("start")
        end = data.get("end")

        start_time = parse_datetime(start) if start else event.start_time
        end_time = parse_datetime(end) if end else event.end_time

        if not start_time or not end_time:
            return jsonify({"error": "Invalid datetime format"}), 400

        try:
            TimeSlot(start_time, end_time)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        recurrence_data = parse_recurrence_payload(
            data=data,
            start_time=start_time,
            existing_event=event,
        )

        conflict_event = has_time_conflict(
            db=db,
            user_id=user.id,
            start_time=start_time,
            end_time=end_time,
            recurrence_data=recurrence_data,
            exclude_event_id=event.id,
        )

        if conflict_event:
            return (
                jsonify(
                    {
                        "error": "Time conflict",
                        "message": "This event overlaps with another event",
                        "conflict_event": serialize_event(conflict_event),
                    }
                ),
                409,
            )

        event.title = title
        event.start_time = start_time
        event.end_time = end_time
        event.recurrence_type = recurrence_data["recurrence_type"]
        event.recurrence_interval = recurrence_data["recurrence_interval"]
        event.recurrence_unit = recurrence_data["recurrence_unit"]
        event.recurrence_days = recurrence_data["recurrence_days"]
        event.recurrence_end_type = recurrence_data["recurrence_end_type"]
        event.recurrence_end_date = recurrence_data["recurrence_end_date"]
        event.recurrence_count = recurrence_data["recurrence_count"]
        event.recurrence_rule = recurrence_data["recurrence_rule"]

        if user.google_credentials and event.google_event_id:
            schedule_service.update_google_event(
                json.loads(user.google_credentials),
                event.google_event_id,
                event.title,
                event.start_time.isoformat(),
                event.end_time.isoformat(),
                recurrence_rule=event.recurrence_rule,
            )

            event.source = "google"

        if "event_type_id" in data:
            event.event_type_id = data.get("event_type_id")

        if "subject_id" in data:
            event.subject_id = data.get("subject_id")

        db.commit()
        db.refresh(event)

        return jsonify(serialize_event(event))

    finally:
        db.close()


@event_bp.route("/api/events/<int:event_id>", methods=["DELETE"])
def delete_event_api(event_id):
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    delete_scope = data.get("scope", "all")
    occurrence_start = parse_datetime(data.get("occurrence_start"))

    db = SessionLocal()

    try:
        event = db.query(Event).filter_by(id=event_id, user_id=user.id).first()

        if not event:
            return jsonify({"error": "Event not found"}), 404

        if not is_recurring_event(event):
            return delete_non_recurring_event(db, user, event)

        if delete_scope == "this":
            return delete_single_occurrence(db, event, occurrence_start)

        if delete_scope == "future":
            return delete_future_occurrences(db, user, event, occurrence_start)

        if delete_scope == "all":
            return delete_recurring_series(db, user, event)

        return jsonify({"error": "Invalid delete scope"}), 400

    finally:
        db.close()


@event_bp.route("/api/events/search", methods=["GET"])
def search_events_api():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    query = request.args.get("query", "").strip().lower()

    db = SessionLocal()

    try:
        events = get_user_events(db, user.id)
        result = []

        for event in events:
            if query and query not in event.title.lower():
                continue

            result.extend(serialize_event_with_occurrences(event))

        return jsonify(result)

    finally:
        db.close()


@event_bp.route("/api/events/bulk-delete", methods=["POST"])
def bulk_delete_events_api():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    event_ids = data.get("event_ids") or []
    delete_all_by_title = data.get("delete_all_by_title", False)
    title = data.get("title", "").strip().lower()

    db = SessionLocal()

    try:
        events_to_delete = get_events_to_delete(
            db=db,
            user_id=user.id,
            event_ids=event_ids,
            delete_all_by_title=delete_all_by_title,
            title=title,
        )

        deleted_count = 0

        for event in events_to_delete:
            delete_google_event_if_needed(user, event)
            db.delete(event)
            deleted_count += 1

        db.commit()

        return jsonify(
            {
                "message": "Events deleted",
                "deleted_count": deleted_count,
            }
        )

    finally:
        db.close()


@event_bp.route("/api/planner/auto-plan", methods=["POST"], strict_slashes=False)
def auto_plan_event_api():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    title = data.get("title")
    duration_minutes = int(data.get("duration_minutes") or 60)
    date_from = data.get("date_from")
    date_to = data.get("date_to")
    day_start = data.get("day_start", "08:00")
    day_end = data.get("day_end", "22:00")
    preferred_time = data.get("preferred_time", "10:00")
    repeat_enabled = bool(data.get("repeat_enabled", False))
    times_per_week = int(data.get("times_per_week") or 1)
    allowed_days = data.get("allowed_days") or []

    db = SessionLocal()

    try:
        existing_events = get_user_events(db, user.id)

        planned = plan_task_with_ortools(
            existing_events=existing_events,
            title=title,
            duration_minutes=duration_minutes,
            date_from=date_from,
            date_to=date_to,
            day_start=day_start,
            day_end=day_end,
            preferred_time=preferred_time,
            repeat_enabled=repeat_enabled,
            times_per_week=times_per_week,
            allowed_days=allowed_days,
        )

        if not planned:
            return (
                jsonify(
                    {
                        "error": "No free slot",
                        "message": "No available time slot was found for this task",
                    }
                ),
                409,
            )

        google_sync_errors = []
        created_events = [
            create_auto_planned_event(db, user, planned_item, google_sync_errors)
            for planned_item in planned.get("events", [])
        ]

        db.commit()

        return (
            jsonify(
                {
                    "message": "Auto plan created",
                    "events": created_events,
                    "planned_count": len(created_events),
                    "candidates_count": planned.get("candidates_count", 0),
                    "google_sync_failed": len(google_sync_errors) > 0,
                    "google_sync_errors": google_sync_errors[:3],
                }
            ),
            201,
        )

    except ValueError as error:
        db.rollback()
        return jsonify({"error": str(error)}), 400

    except Exception as error:
        db.rollback()
        print("Auto plan error:", error)
        return (
            jsonify(
                {
                    "error": "Auto planning failed",
                    "details": str(error),
                }
            ),
            500,
        )

    finally:
        db.close()
