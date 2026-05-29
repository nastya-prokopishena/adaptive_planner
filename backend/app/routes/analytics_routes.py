from backend.app.routes.common import *

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/api/analytics/dashboard", methods=["GET"])
def analytics_dashboard_api():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    date_from = parse_optional_datetime(request.args.get("date_from"))
    date_to = parse_optional_datetime(request.args.get("date_to"))

    db = SessionLocal()

    try:
        tasks = db.query(Task).filter(Task.user_id == user.id).all()
        events = db.query(Event).filter(Event.user_id == user.id).all()

        result = analytics_service.build_dashboard_analytics(
            tasks=tasks,
            events=events,
            date_from=date_from,
            date_to=date_to,
        )

        return jsonify(result), 200

    finally:
        db.close()


@analytics_bp.route("/api/ml/productivity/predict", methods=["POST"])
def productivity_predict_api():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    date_value = parse_optional_datetime(data.get("date"))

    if not date_value:
        return jsonify({"error": "Date is required"}), 400

    db = SessionLocal()

    try:
        tasks = db.query(Task).filter(Task.user_id == user.id).all()
        events = db.query(Event).filter(Event.user_id == user.id).all()

        prediction = productivity_model_service.predict_day(
            date=date_value,
            tasks=tasks,
            events=events,
        )

        return jsonify(prediction), 200

    finally:
        db.close()


@analytics_bp.route("/api/tasks/<int:task_id>/replan", methods=["POST"])
def replan_task_api(task_id):
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    db = SessionLocal()

    try:
        task = db.query(Task).filter_by(id=task_id, user_id=user.id).first()

        if not task:
            return jsonify({"error": "Task not found"}), 404

        now = datetime.utcnow()

        date_from = data.get("date_from") or now.date().isoformat()
        date_to = data.get("date_to")

        if not date_to:
            fallback_date = now + timedelta(days=7)
            date_to = fallback_date.date().isoformat()

        duration_minutes = int((task.estimated_duration_hours or 1) * 60)

        existing_events = (
            db.query(Event).filter_by(user_id=user.id).order_by(Event.start_time.asc()).all()
        )

        planned = plan_task_with_ortools(
            existing_events=existing_events,
            title=task.title,
            duration_minutes=duration_minutes,
            date_from=date_from,
            date_to=date_to,
            day_start=data.get("day_start", "08:00"),
            day_end=data.get("day_end", "22:00"),
            preferred_time=data.get("preferred_time", "10:00"),
            repeat_enabled=False,
            times_per_week=1,
            allowed_days=data.get("allowed_days") or [],
        )

        if not planned:
            return (
                jsonify(
                    {
                        "error": "No free slot",
                        "message": "Не вдалося знайти новий слот для задачі",
                    }
                ),
                409,
            )

        planned_item = planned["events"][0]

        event = Event(
            user_id=user.id,
            title=f"Переплановано: {task.title}",
            start_time=planned_item["start"],
            end_time=planned_item["end"],
            source="local",
            recurrence_type="none",
            subject_id=task.subject_id,
        )

        db.add(event)
        db.commit()
        db.refresh(event)

        old_status = task.status

        task.status = "planned"
        task.event_id = event.id
        task.updated_at = datetime.utcnow()
        task.missed_at = None

        create_task_log(
            db=db,
            user_id=user.id,
            task_id=task.id,
            action="task_replanned",
            old_status=old_status,
            new_status="planned",
            details=f"Task replanned to {event.start_time.isoformat()}",
        )

        db.commit()
        db.refresh(task)

        return (
            jsonify(
                {
                    "task": serialize_task(task),
                    "event": serialize_event(event),
                    "message": "Задачу переплановано",
                }
            ),
            201,
        )

    finally:
        db.close()


@analytics_bp.route("/api/ml/plan-tasks", methods=["POST"])
def generate_ml_task_plan():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    days = int(data.get("days", 7))

    db = SessionLocal()

    try:
        blocks = ml_task_planner_service.plan_tasks(
            db=db,
            user_id=user.id,
            days=days,
        )

        result = []

        for block in blocks:
            task = db.query(Task).filter_by(id=block.task_id).first()
            result.append(serialize_task_schedule_block(block, task))

        return jsonify(
            {
                "message": "ML task plan generated",
                "blocks": result,
            }
        )

    finally:
        db.close()


@analytics_bp.route("/api/unified-calendar", methods=["GET"])
def get_unified_calendar():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    db = SessionLocal()

    try:
        events = db.query(Event).filter(Event.user_id == user.id).all()

        tasks = (
            db.query(Task).filter(Task.user_id == user.id).filter(Task.due_date.isnot(None)).all()
        )

        blocks = db.query(TaskScheduleBlock).filter(TaskScheduleBlock.user_id == user.id).all()

        calendar_items = []

        for event in events:
            item = serialize_event(event)
            item["calendar_type"] = "fixed_event"
            item["color"] = {
                "bg": "#2563eb",
                "bg2": "#38bdf8",
            }
            calendar_items.append(item)

        for task in tasks:
            calendar_items.append(
                {
                    "id": f"deadline-{task.id}",
                    "task_id": task.id,
                    "title": f"🔥 Deadline: {task.title}",
                    "start": task.due_date.isoformat(),
                    "end": (task.due_date + timedelta(minutes=30)).isoformat(),
                    "calendar_type": "task_deadline",
                    "source": "task_deadline",
                    "color": {
                        "bg": "#ea580c",
                        "bg2": "#ef4444",
                    },
                }
            )

        for block in blocks:
            task = db.query(Task).filter_by(id=block.task_id).first()
            calendar_items.append(serialize_task_schedule_block(block, task))

        return jsonify(calendar_items)

    finally:
        db.close()
