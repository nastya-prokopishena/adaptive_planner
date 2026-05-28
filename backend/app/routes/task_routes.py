from flask import Blueprint

from backend.app.routes.common import *

task_bp = Blueprint("task", __name__)


@task_bp.route("/api/event-types", methods=["GET"])
def get_event_types():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    db = SessionLocal()

    try:
        event_types = (
            db.query(EventType)
            .filter_by(user_id=user.id)
            .order_by(EventType.name.asc())
            .all()
        )

        return jsonify([serialize_event_type(item) for item in event_types])

    finally:
        db.close()


@task_bp.route("/api/event-types", methods=["POST"])
def create_event_type():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    name = data.get("name")
    color = data.get("color")

    if not name:
        return jsonify({"error": "Name is required"}), 400

    db = SessionLocal()

    try:
        event_type = EventType(
            user_id=user.id,
            name=name,
            color=color,
            is_default=False,
        )

        db.add(event_type)
        db.commit()
        db.refresh(event_type)

        return jsonify(serialize_event_type(event_type)), 201

    finally:
        db.close()

@task_bp.route("/api/subjects", methods=["GET"])
def get_subjects():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    db = SessionLocal()

    try:
        subjects = (
            db.query(Subject)
            .filter_by(user_id=user.id)
            .order_by(Subject.name.asc())
            .all()
        )

        return jsonify([serialize_subject(subject) for subject in subjects])

    finally:
        db.close()


@task_bp.route("/api/subjects", methods=["POST"])
def create_subject():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    name = data.get("name")
    teacher = data.get("teacher")
    description = data.get("description")
    color = data.get("color")

    if not name:
        return jsonify({"error": "Name is required"}), 400

    db = SessionLocal()

    try:
        subject = Subject(
            user_id=user.id,
            name=name,
            teacher=teacher,
            description=description,
            color=color,
        )

        db.add(subject)
        db.commit()
        db.refresh(subject)

        return jsonify(serialize_subject(subject)), 201

    finally:
        db.close()

@task_bp.route("/api/subjects/<int:subject_id>", methods=["PUT"])
def update_subject(subject_id):
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}

    db = SessionLocal()

    try:
        subject = (
            db.query(Subject)
            .filter_by(id=subject_id, user_id=user.id)
            .first()
        )

        if not subject:
            return jsonify({"error": "Subject not found"}), 404

        subject.name = data.get("name", subject.name)
        subject.teacher = data.get("teacher", subject.teacher)
        subject.description = data.get("description", subject.description)
        subject.color = data.get("color", subject.color)

        db.commit()
        db.refresh(subject)

        return jsonify(serialize_subject(subject)), 200

    finally:
        db.close()

@task_bp.route("/api/event-types/<int:event_type_id>", methods=["PUT"])
def update_event_type(event_type_id):
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}

    db = SessionLocal()

    try:
        event_type = (
            db.query(EventType)
            .filter_by(id=event_type_id, user_id=user.id)
            .first()
        )

        if not event_type:
            return jsonify({"error": "Event type not found"}), 404

        event_type.name = data.get("name", event_type.name)
        event_type.color = data.get("color", event_type.color)

        db.commit()
        db.refresh(event_type)

        return jsonify(serialize_event_type(event_type)), 200

    finally:
        db.close()

@task_bp.route("/api/tasks", methods=["GET"])
def get_tasks():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    event_id = request.args.get("event_id")
    subject_id = request.args.get("subject_id")
    status = request.args.get("status")

    db = SessionLocal()

    try:
        query = db.query(Task).filter(Task.user_id == user.id)

        if event_id:
            query = query.filter(Task.event_id == int(event_id))

        if subject_id:
            query = query.filter(Task.subject_id == int(subject_id))

        if status:
            query = query.filter(Task.status == status)

        tasks = query.order_by(Task.created_at.desc()).all()

        return jsonify([serialize_task(task) for task in tasks])

    finally:
        db.close()


@task_bp.route("/api/tasks", methods=["POST"])
def create_task():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    title = data.get("title")

    if not title:
        return jsonify({"error": "Task title is required"}), 400

    db = SessionLocal()

    try:
        due_date = parse_optional_datetime(
            data.get("due_date") or data.get("deadline")
        )

        task = Task(
            user_id=user.id,
            event_id=data.get("event_id"),
            subject_id=data.get("subject_id"),
            title=title,
            description=data.get("description"),
            status=data.get("status", "planned"),
            priority=data.get("priority", "medium"),
            due_date=due_date,
            task_type=data.get("task_type", "other"),
            keywords=json.dumps(data.get("keywords", []), ensure_ascii=False),
            estimated_duration_hours=float(
                data.get("estimated_duration_hours") or 1
            ),
            difficulty_score=int(data.get("difficulty_score") or 3),
            nlp_source=data.get("nlp_source", "manual"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(task)
        db.flush()

        if not task.due_date and bool(data.get("auto_plan_deadline", False)):
            try:
                apply_auto_deadline_to_task(
                    db=db,
                    user_id=user.id,
                    task=task,
                    mode=data.get("auto_deadline_mode", "subject_based"),
                )
            except Exception as planning_error:
                print("Auto deadline planning error:", planning_error)

        db.commit()
        db.refresh(task)

        create_task_log(
            db=db,
            user_id=user.id,
            task_id=task.id,
            action="task_created",
            new_status=task.status,
            details=f"Task created: {task.title}",
        )

        db.commit()

        return jsonify(serialize_task(task)), 201

    finally:
        db.close()

@task_bp.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    db = SessionLocal()

    try:
        task = (
            db.query(Task)
            .filter_by(id=task_id, user_id=user.id)
            .first()
        )

        if not task:
            return jsonify({"error": "Task not found"}), 404

        task.title = data.get("title", task.title)
        task.description = data.get("description", task.description)
        task.subject_id = data.get("subject_id", task.subject_id)
        task.event_id = data.get("event_id", task.event_id)
        task.priority = data.get("priority", task.priority)
        task.task_type = data.get("task_type", task.task_type)

        if "due_date" in data:
            task.due_date = parse_optional_datetime(data.get("due_date"))

        task.estimated_duration_hours = float(
            data.get(
                "estimated_duration_hours",
                task.estimated_duration_hours or 1,
            )
        )

        task.difficulty_score = int(
            data.get(
                "difficulty_score",
                task.difficulty_score or 3,
            )
        )

        keywords = data.get("keywords")

        if isinstance(keywords, list):
            task.keywords = json.dumps(keywords, ensure_ascii=False)

        task.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(task)

        return jsonify(serialize_task(task)), 200

    finally:
        db.close()

@task_bp.route("/api/tasks/<int:task_id>/deadline", methods=["PUT"])
def update_task_deadline(task_id):
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    due_date = parse_optional_datetime(data.get("due_date"))

    if not due_date:
        return jsonify({"error": "Invalid due_date"}), 400

    db = SessionLocal()

    try:
        task = (
            db.query(Task)
            .filter_by(id=task_id, user_id=user.id)
            .first()
        )

        if not task:
            return jsonify({"error": "Task not found"}), 404

        task.due_date = due_date
        task.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(task)

        return jsonify(serialize_task(task)), 200

    finally:
        db.close()


@task_bp.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    db = SessionLocal()

    try:
        task = (
            db.query(Task)
            .filter_by(id=task_id, user_id=user.id)
            .first()
        )

        if not task:
            return jsonify({"error": "Task not found"}), 404

        create_task_log(
            db=db,
            user_id=user.id,
            task_id=task.id,
            action="task_deleted",
            old_status=task.status,
            details=f"Task deleted: {task.title}",
        )

        db.delete(task)
        db.commit()

        return jsonify({"message": "Task deleted"})

    finally:
        db.close()


@task_bp.route("/api/tasks/<int:task_id>/status", methods=["PUT"])
def update_task_status(task_id):
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    new_status = data.get("status")

    allowed_statuses = ["planned", "in_progress", "done", "missed"]

    if new_status not in allowed_statuses:
        return jsonify({"error": "Invalid task status"}), 400

    db = SessionLocal()

    try:
        task = (
            db.query(Task)
            .filter_by(id=task_id, user_id=user.id)
            .first()
        )

        if not task:
            return jsonify({"error": "Task not found"}), 404

        old_status = task.status

        task.status = new_status
        task.updated_at = datetime.utcnow()

        if new_status == "done":
            task.completed_at = datetime.utcnow()
            task.missed_at = None

        elif new_status == "missed":
            task.missed_at = datetime.utcnow()
            task.completed_at = None
            auto_replan = bool(data.get("auto_replan", False))

        else:
            task.completed_at = None
            task.missed_at = None

        create_task_log(
            db=db,
            user_id=user.id,
            task_id=task.id,
            action="status_changed",
            old_status=old_status,
            new_status=new_status,
            details=f"Task status changed from {old_status} to {new_status}",
        )

        db.commit()
        db.refresh(task)

        return jsonify(serialize_task(task))

    finally:
        db.close()

@task_bp.route("/api/activity-logs", methods=["GET"])
def get_activity_logs():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    task_id = request.args.get("task_id")

    db = SessionLocal()

    try:
        query = db.query(TaskActivityLog).filter(TaskActivityLog.user_id == user.id)

        if task_id:
            query = query.filter(TaskActivityLog.task_id == int(task_id))

        logs = query.order_by(TaskActivityLog.created_at.desc()).limit(100).all()

        return jsonify([serialize_activity_log(log) for log in logs])

    finally:
        db.close()




# ---------------------------
# TASK DEADLINE ML PLANNING
# ---------------------------

@task_bp.route("/api/tasks/auto-deadline", methods=["POST"], strict_slashes=False)
def auto_deadline_for_manual_task():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    title = data.get("title")

    if not title:
        return jsonify({"error": "Task title is required"}), 400

    db = SessionLocal()

    try:
        subject_id = resolve_subject_id(
            db=db,
            user_id=user.id,
            subject_id=data.get("subject_id"),
            subject_name=data.get("subject"),
        )

        temp_task = Task(
            user_id=user.id,
            title=title,
            description=data.get("description"),
            priority=data.get("priority", "medium"),
            task_type=data.get("task_type", "other"),
            estimated_duration_hours=float(
                data.get("estimated_duration_hours") or 1
            ),
            difficulty_score=int(data.get("difficulty_score") or 3),
            subject_id=subject_id,
            status="planned",
        )

        subject_events = get_subject_events(
            db=db,
            user_id=user.id,
            subject_id=temp_task.subject_id,
            subject_name=data.get("subject"),
        )

        calendar_events = get_user_calendar_events(
            db=db,
            user_id=user.id,
        )

        existing_count = get_existing_subject_deadline_count(
            db=db,
            user_id=user.id,
            subject_id=temp_task.subject_id,
            subject_name=data.get("subject"),
        )

        prediction = safe_predict_deadline(
            task=temp_task,
            subject_events=subject_events,
            calendar_events=calendar_events,
            mode=data.get("mode", "subject_based"),
            used_event_index=existing_count,
            used_best_time_dates=get_existing_deadline_dates(db, user.id),
        )

        return jsonify({
            "due_date": prediction["deadline"].isoformat(),
            "confidence_score": prediction["confidence"],
            "reason": prediction["reason"],
        })

    finally:
        db.close()


@task_bp.route("/api/tasks/auto-plan-deadlines-preview", methods=["POST"], strict_slashes=False)
def auto_plan_deadlines_preview():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    raw_tasks = data.get("tasks", [])
    mode = normalize_deadline_mode(data.get("mode", "subject_based"))

    db = SessionLocal()

    try:
        planned_tasks = []
        normalized_tasks = []
        subject_batch_counts = {}

        for raw_task in raw_tasks:
            subject_name = raw_task.get("subject")
            subject_id = resolve_subject_id(
                db=db,
                user_id=user.id,
                subject_id=raw_task.get("subject_id"),
                subject_name=subject_name,
            )

            if subject_id and not subject_name:
                subject_name = get_subject_name_by_id(
                    db=db,
                    user_id=user.id,
                    subject_id=subject_id,
                )

            subject_key = subject_id or subject_name or "general"

            normalized_tasks.append({
                "raw_task": raw_task,
                "subject_id": subject_id,
                "subject_name": subject_name,
                "subject_key": subject_key,
            })

            subject_batch_counts[subject_key] = (
                subject_batch_counts.get(subject_key, 0) + 1
            )

        subject_positions = {}
        used_best_time_dates = get_existing_deadline_dates(db, user.id)
        calendar_events = get_user_calendar_events(db, user.id)

        for item in normalized_tasks:
            raw_task = item["raw_task"]
            subject_id = item["subject_id"]
            subject_name = item["subject_name"]
            subject_key = item["subject_key"]

            current_position = subject_positions.get(subject_key, 0)
            subject_positions[subject_key] = current_position + 1

            temp_task = Task(
                user_id=user.id,
                title=raw_task.get("title") or "Без назви",
                description=raw_task.get("description"),
                priority=raw_task.get("priority", "medium"),
                task_type=raw_task.get("task_type", "other"),
                estimated_duration_hours=float(
                    raw_task.get("estimated_duration_hours") or 1
                ),
                difficulty_score=int(raw_task.get("difficulty_score") or 3),
                subject_id=subject_id,
                status="planned",
            )

            subject_events = get_subject_events(
                db=db,
                user_id=user.id,
                subject_id=subject_id,
                subject_name=subject_name,
            )

            existing_count = get_existing_subject_deadline_count(
                db=db,
                user_id=user.id,
                subject_id=subject_id,
                subject_name=subject_name,
            )

            used_event_index = build_subject_distribution_index(
                existing_count=existing_count,
                task_position=current_position,
                task_total=subject_batch_counts[subject_key],
                subject_events_count=len(subject_events),
            )

            prediction = safe_predict_deadline(
                task=temp_task,
                subject_events=subject_events,
                calendar_events=calendar_events,
                mode=mode,
                used_event_index=used_event_index,
                used_best_time_dates=used_best_time_dates,
            )

            used_best_time_dates.append(prediction["deadline"].date())

            planned_tasks.append({
                "title": temp_task.title,
                "due_date": prediction["deadline"].isoformat(),
                "confidence_score": prediction["confidence"],
                "reason": prediction["reason"],
                "subject_id": temp_task.subject_id,
                "subject_events_count": len(subject_events),
                "used_event_index": used_event_index,
                "mode": mode,
            })

        return jsonify({"tasks": planned_tasks})

    finally:
        db.close()


@task_bp.route("/api/tasks/<int:task_id>/auto-plan", methods=["POST"])
def auto_plan_existing_task(task_id):
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    db = SessionLocal()

    try:
        task = (
            db.query(Task)
            .filter(Task.id == task_id)
            .filter(Task.user_id == user.id)
            .first()
        )

        if not task:
            return jsonify({"error": "Task not found"}), 404

        prediction, block = apply_auto_deadline_to_task(
            db=db,
            user_id=user.id,
            task=task,
            mode=data.get("mode", "subject_based"),
        )

        db.commit()
        db.refresh(task)
        db.refresh(block)

        return jsonify({
            "task": serialize_task(task),
            "schedule_block": serialize_task_schedule_block(block, task),
            "reason": prediction["reason"],
        })

    finally:
        db.close()


@task_bp.route("/api/task-schedule-blocks", methods=["GET"])
def get_task_schedule_blocks():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    db = SessionLocal()

    try:
        blocks = (
            db.query(TaskScheduleBlock)
            .filter(TaskScheduleBlock.user_id == user.id)
            .order_by(TaskScheduleBlock.start_time.asc())
            .all()
        )

        result = []

        for block in blocks:
            task = db.query(Task).filter(Task.id == block.task_id).first()
            result.append(serialize_task_schedule_block(block, task))

        return jsonify(result)

    finally:
        db.close()


@task_bp.route("/api/ml/deadline-dataset/generate", methods=["POST"])
def generate_synthetic_deadline_dataset():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    path = synthetic_deadline_dataset_service.save_csv()

    return jsonify({
        "message": "Synthetic deadline dataset generated",
        "path": path,
    })


# ---------------------------
# TASK NLP IMPORT
# ---------------------------

@task_bp.route("/api/task-import/model-info", methods=["GET"], strict_slashes=False)
def task_model_info_api():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        info = task_nlp_service.difficulty_ml_service.get_model_info()
        return jsonify(info), 200

    except Exception as error:
        return jsonify({
            "loaded": False,
            "error": str(error),
        }), 500


@task_bp.route("/api/task-import/analyze-text", methods=["POST"], strict_slashes=False)
def analyze_task_text_api():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json() or {}

        text = data.get("text", "")
        subject_name = data.get("subject")

        if not text.strip():
            return jsonify({"error": "Текст завдання порожній"}), 400

        db = SessionLocal()

        try:
            results = task_nlp_service.analyze_many(
                text=text,
                subject_name=subject_name or None,
            )

            tasks = []

            for result in results:
                subject = find_subject_by_name(
                    db=db,
                    user_id=user.id,
                    subject_name=result.get("subject"),
                )

                result["subject_id"] = subject.id if subject else None
                result["subject_exists"] = subject is not None
                result["should_create_subject"] = (
                    bool(result.get("subject")) and subject is None
                )
                result["source_filename"] = None

                tasks.append(result)

            return jsonify({
                "tasks": tasks,
                "count": len(tasks),
            }), 200

        finally:
            db.close()

    except Exception as error:
        return jsonify({
            "error": "Не вдалося проаналізувати текст",
            "details": str(error),
        }), 500


@task_bp.route("/api/task-import/analyze-file", methods=["POST"], strict_slashes=False)
@task_bp.route("/api/task-import/analyze-files", methods=["POST"], strict_slashes=False)
def analyze_task_file_api():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        subject_name = request.form.get("subject")

        uploaded_files = request.files.getlist("files")

        if not uploaded_files:
            single_file = request.files.get("file")

            if single_file:
                uploaded_files = [single_file]

        if not uploaded_files:
            return jsonify({"error": "Файли не передано"}), 400

        db = SessionLocal()
        tasks = []

        try:
            for file in uploaded_files:
                file_bytes = file.read()

                extracted_text = task_file_extractor_service.extract_text(
                    file.filename,
                    file_bytes,
                )

                if not extracted_text or len(extracted_text.strip()) < 20:
                    continue

                results = task_nlp_service.analyze_many(
                    text=extracted_text,
                    subject_name=subject_name or None,
                )

                for result in results:
                    subject = find_subject_by_name(
                        db=db,
                        user_id=user.id,
                        subject_name=result.get("subject"),
                    )

                    result["subject_id"] = subject.id if subject else None
                    result["subject_exists"] = subject is not None
                    result["should_create_subject"] = (
                            bool(result.get("subject")) and subject is None
                    )
                    result["source_filename"] = file.filename

                    tasks.append(result)

            return jsonify({
                "tasks": tasks,
                "count": len(tasks),
            }), 200

        finally:
            db.close()

    except Exception as error:
        return jsonify({
            "error": "Не вдалося проаналізувати файл",
            "details": str(error),
        }), 500


@task_bp.route("/api/task-import/create-subject", methods=["POST"], strict_slashes=False)
def create_subject_from_task_import_api():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    name = data.get("name")

    if not name:
        return jsonify({"error": "Назва предмету обов'язкова"}), 400

    db = SessionLocal()

    try:
        existing_subject = find_subject_by_name(db, user.id, name)

        if existing_subject:
            return jsonify(serialize_subject(existing_subject)), 200

        subject = Subject(
            user_id=user.id,
            name=name,
            teacher=data.get("teacher"),
            description=data.get("description"),
            color=data.get("color"),
        )

        db.add(subject)
        db.commit()
        db.refresh(subject)

        return jsonify(serialize_subject(subject)), 201

    finally:
        db.close()

@task_bp.route("/api/task-import/create-tasks", methods=["POST"], strict_slashes=False)
def create_tasks_from_import_api():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    tasks_data = data.get("tasks") or []
    mode = normalize_deadline_mode(data.get("mode", "subject_based"))

    if not tasks_data:
        return jsonify({"error": "Немає задач для створення"}), 400

    db = SessionLocal()

    try:
        created_tasks = []
        normalized_tasks = []
        subject_batch_counts = {}

        for item in tasks_data:
            title = item.get("title")

            if not title:
                continue

            subject_id = item.get("subject_id")
            subject_name = item.get("subject")

            if not subject_id and subject_name:
                subject = find_subject_by_name(db, user.id, subject_name)

                if subject:
                    subject_id = subject.id
                else:
                    subject = Subject(
                        user_id=user.id,
                        name=subject_name,
                    )
                    db.add(subject)
                    db.flush()
                    subject_id = subject.id

            if subject_id and not subject_name:
                subject_name = get_subject_name_by_id(
                    db=db,
                    user_id=user.id,
                    subject_id=subject_id,
                )

            subject_key = subject_id or subject_name or "general"

            normalized_tasks.append({
                "item": item,
                "subject_id": subject_id,
                "subject_name": subject_name,
                "subject_key": subject_key,
            })

            subject_batch_counts[subject_key] = (
                subject_batch_counts.get(subject_key, 0) + 1
            )

        subject_positions = {}
        used_best_time_dates = get_existing_deadline_dates(db, user.id)

        for normalized in normalized_tasks:
            item = normalized["item"]
            subject_id = normalized["subject_id"]
            subject_name = normalized["subject_name"]
            subject_key = normalized["subject_key"]

            current_position = subject_positions.get(subject_key, 0)
            subject_positions[subject_key] = current_position + 1

            task = Task(
                user_id=user.id,
                subject_id=subject_id,
                title=item.get("title"),
                description=item.get("description"),
                status="planned",
                priority=item.get("priority", "medium"),
                due_date=parse_optional_datetime(
                    item.get("due_date") or item.get("deadline")
                ),
                task_type=item.get("task_type", "other"),
                keywords=json.dumps(item.get("keywords") or [], ensure_ascii=False),
                estimated_duration_hours=item.get("estimated_duration_hours", 1),
                difficulty_score=item.get("difficulty_score", 3),
                nlp_source=item.get("nlp_source", "import"),
            )

            db.add(task)
            db.flush()

            if not task.due_date:
                try:
                    subject_events = get_subject_events(
                        db=db,
                        user_id=user.id,
                        subject_id=subject_id,
                        subject_name=subject_name,
                    )

                    existing_count = get_existing_subject_deadline_count(
                        db=db,
                        user_id=user.id,
                        subject_id=subject_id,
                        subject_name=subject_name,
                        exclude_task_id=task.id,
                    )

                    used_event_index = build_subject_distribution_index(
                        existing_count=existing_count,
                        task_position=current_position,
                        task_total=subject_batch_counts[subject_key],
                        subject_events_count=len(subject_events),
                    )

                    prediction, block = apply_auto_deadline_to_task(
                        db=db,
                        user_id=user.id,
                        task=task,
                        mode=item.get("auto_deadline_mode") or mode,
                        used_event_index=used_event_index,
                        subject_name=subject_name,
                        used_best_time_dates=used_best_time_dates,
                    )

                    used_best_time_dates.append(prediction["deadline"].date())

                except Exception as planning_error:
                    print("Auto deadline planning error:", planning_error)

            create_task_log(
                db=db,
                user_id=user.id,
                task_id=task.id,
                action="task_created_from_import",
                new_status=task.status,
                details=f"Task imported: {task.title}",
            )

            created_tasks.append(task)

        db.commit()

        return jsonify({
            "tasks": [serialize_task(task) for task in created_tasks],
            "count": len(created_tasks),
        }), 201

    except Exception as error:
        db.rollback()
        return jsonify({
            "error": "Не вдалося створити задачі",
            "details": str(error),
        }), 500

    finally:
        db.close()
