from backend.app.routes.common import *

event_bp = Blueprint("event", __name__)


# ---------------------------
# EVENTS
# ---------------------------


@event_bp.route("/api/events", methods=["GET"])
def get_events():
    """
    Get calendar events
    ---
    tags:
      - Events
    responses:
      200:
        description: List of calendar events
      401:
        description: Unauthorized
    """
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    db = SessionLocal()

    try:
        sync_google_events_to_db(user, db)

        events = db.query(Event).filter_by(user_id=user.id).order_by(Event.start_time.asc()).all()

        result = []

        for event in events:
            if event.recurrence_type and event.recurrence_type != "none":
                occurrences = get_event_occurrences(event)

                for occurrence_start, occurrence_end in occurrences:
                    result.append(
                        serialize_event(
                            event,
                            occurrence_start=occurrence_start,
                            occurrence_end=occurrence_end,
                        )
                    )
            else:
                result.append(serialize_event(event))

        return jsonify(result)

    finally:
        db.close()


@event_bp.route("/api/events", methods=["POST"])
def create_event_api():
    """
    Create calendar event
    ---
    tags:
      - Events
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - title
            - start
            - end
          properties:
            title:
              type: string
              example: Lecture
            start:
              type: string
              format: date-time
            end:
              type: string
              format: date-time
    responses:
      201:
        description: Event created
      400:
        description: Invalid request
      401:
        description: Unauthorized
      409:
        description: Time conflict
    """
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
    """
    Update calendar event
    ---
    tags:
      - Events
    parameters:
      - in: path
        name: event_id
        type: integer
        required: true
    responses:
      200:
        description: Event updated
      400:
        description: Invalid request
      401:
        description: Unauthorized
      404:
        description: Event not found
      409:
        description: Time conflict
    """
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
    """
    Delete calendar event
    ---
    tags:
      - Events
    parameters:
      - in: path
        name: event_id
        type: integer
        required: true
    responses:
      200:
        description: Event deleted
      400:
        description: Invalid delete scope
      401:
        description: Unauthorized
      404:
        description: Event not found
    """
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    delete_scope = data.get("scope", "all")
    occurrence_start_raw = data.get("occurrence_start")

    db = SessionLocal()

    try:
        event = db.query(Event).filter_by(id=event_id, user_id=user.id).first()

        if not event:
            return jsonify({"error": "Event not found"}), 404

        is_recurring = event.recurrence_type and event.recurrence_type != "none"

        if not is_recurring:
            if user.google_credentials and event.google_event_id:
                try:
                    schedule_service.delete_google_event(
                        json.loads(user.google_credentials),
                        event.google_event_id,
                    )
                except Exception as error:
                    print("Google delete error:", error)

            db.delete(event)
            db.commit()

            return jsonify({"message": "Event deleted"})

        occurrence_start = parse_datetime(occurrence_start_raw)

        if delete_scope == "this":
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

        if delete_scope == "future":
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

            if user.google_credentials and event.google_event_id:
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
                    print("Google update recurrence error:", error)

            db.commit()

            return jsonify(
                {
                    "message": "Future occurrences deleted",
                    "scope": "future",
                }
            )

        if delete_scope == "all":
            if user.google_credentials and event.google_event_id:
                try:
                    schedule_service.delete_google_event(
                        json.loads(user.google_credentials),
                        event.google_event_id,
                    )
                except Exception as error:
                    print("Google delete error:", error)

            db.delete(event)
            db.commit()

            return jsonify(
                {
                    "message": "Recurring event series deleted",
                    "scope": "all",
                }
            )

        return jsonify({"error": "Invalid delete scope"}), 400

    finally:
        db.close()


@event_bp.route("/api/events/search", methods=["GET"])
def search_events_api():
    """
    Search calendar events
    ---
    tags:
      - Events
    parameters:
      - in: query
        name: query
        type: string
        required: false
        example: physics
    responses:
      200:
        description: Matching events
      401:
        description: Unauthorized
    """
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    query = request.args.get("query", "").strip().lower()

    db = SessionLocal()

    try:
        events = (
            db.query(Event).filter(Event.user_id == user.id).order_by(Event.start_time.asc()).all()
        )

        result = []

        for event in events:
            if query and query not in event.title.lower():
                continue

            if event.recurrence_type and event.recurrence_type != "none":
                occurrences = get_event_occurrences(event)

                for occurrence_start, occurrence_end in occurrences:
                    result.append(
                        serialize_event(
                            event,
                            occurrence_start=occurrence_start,
                            occurrence_end=occurrence_end,
                        )
                    )
            else:
                result.append(serialize_event(event))

        return jsonify(result)

    finally:
        db.close()


@event_bp.route("/api/events/bulk-delete", methods=["POST"])
def bulk_delete_events_api():
    """
    Bulk delete calendar events
    ---
    tags:
      - Events
    responses:
      200:
        description: Events deleted
      401:
        description: Unauthorized
    """
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    event_ids = data.get("event_ids") or []
    delete_all_by_title = data.get("delete_all_by_title", False)
    title = data.get("title", "").strip().lower()

    db = SessionLocal()

    try:
        deleted_count = 0

        if delete_all_by_title and title:
            events = db.query(Event).filter(Event.user_id == user.id).all()

            events_to_delete = [event for event in events if event.title.lower() == title]

        else:
            clean_ids = []

            for event_id in event_ids:
                clean_id = str(event_id).split("__")[0]

                if clean_id.isdigit():
                    clean_ids.append(int(clean_id))

            events_to_delete = (
                db.query(Event)
                .filter(Event.user_id == user.id)
                .filter(Event.id.in_(clean_ids))
                .all()
            )

        for event in events_to_delete:
            if user.google_credentials and event.google_event_id:
                try:
                    schedule_service.delete_google_event(
                        json.loads(user.google_credentials),
                        event.google_event_id,
                    )
                except Exception as error:
                    print("Google delete error:", error)

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
    """
    Automatically plan an event
    ---
    tags:
      - Events
      - Planner
    responses:
      201:
        description: Auto plan created
      400:
        description: Invalid planning request
      401:
        description: Unauthorized
      409:
        description: No free slot
      500:
        description: Auto planning failed
    """
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
        existing_events = (
            db.query(Event).filter_by(user_id=user.id).order_by(Event.start_time.asc()).all()
        )

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

        created_events = []
        google_sync_errors = []

        for planned_item in planned.get("events", []):
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

            if user.google_credentials:
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
                    print("Google auto-plan create error:", google_error)
                    google_sync_errors.append(str(google_error))
                    event.source = "local"

            db.flush()
            created_events.append(serialize_event(event))

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
