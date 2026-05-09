from flask import Blueprint, redirect, request, session, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, time
import json
import requests

from backend.domain.models.time_slot import TimeSlot
from backend.infrastructure.db.database import SessionLocal
from backend.infrastructure.db.models import User, Event
from backend.infrastructure.google_calendar_adapter import GoogleCalendarAdapter
from backend.application.schedule_service import ScheduleService
from backend.domain.recurrence import (
    build_google_rrule,
    generate_occurrences,
    time_ranges_overlap,
)


main = Blueprint("main", __name__)

calendar_adapter = GoogleCalendarAdapter()
schedule_service = ScheduleService()


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


def get_event_occurrences(event):
    return generate_occurrences(
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


# ---------------------------
# AUTH
# ---------------------------

@main.route("/auth/register", methods=["POST"])
def register():
    data = request.json or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    db = SessionLocal()

    try:
        existing_user = db.query(User).filter_by(email=email).first()

        if existing_user:
            return jsonify({"error": "User already exists"}), 409

        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            auth_provider="local",
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        session["user_id"] = user.id

        return jsonify({
            "id": user.id,
            "email": user.email,
            "authenticated": True,
            "auth_provider": user.auth_provider,
        })

    finally:
        db.close()


@main.route("/auth/login", methods=["POST"])
def login_local():
    data = request.json or {}

    email = data.get("email")
    password = data.get("password")

    db = SessionLocal()

    try:
        user = db.query(User).filter_by(email=email).first()

        if not user or not user.password_hash:
            return jsonify({"error": "Invalid credentials"}), 401

        if not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid credentials"}), 401

        session["user_id"] = user.id

        return jsonify({
            "id": user.id,
            "email": user.email,
            "authenticated": True,
            "auth_provider": user.auth_provider,
        })

    finally:
        db.close()


@main.route("/auth/google")
def google_login():
    flow = calendar_adapter.create_flow()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="select_account",
    )

    session["state"] = state
    session["code_verifier"] = flow.code_verifier

    return redirect(authorization_url)


@main.route("/callback")
def google_callback():
    state = session.get("state")
    code_verifier = session.get("code_verifier")

    flow = calendar_adapter.create_flow()
    flow.code_verifier = code_verifier
    flow.state = state

    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials

    creds_dict = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

    userinfo_response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={
            "Authorization": f"Bearer {credentials.token}",
        },
        timeout=15,
    )

    google_user = userinfo_response.json()

    email = google_user.get("email")
    google_id = google_user.get("id")

    if not email:
        return jsonify({"error": "Google email not found"}), 400

    db = SessionLocal()

    try:
        user = db.query(User).filter_by(email=email).first()

        if not user:
            user = User(
                email=email,
                auth_provider="google",
                google_id=google_id,
                google_credentials=json.dumps(creds_dict),
            )
            db.add(user)
        else:
            user.auth_provider = "google"
            user.google_id = google_id
            user.google_credentials = json.dumps(creds_dict)

        db.commit()
        db.refresh(user)

        session["user_id"] = user.id

        sync_google_events_to_db(user, db)

        return redirect("/")

    finally:
        db.close()


@main.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@main.route("/api/user/me", methods=["GET"])
def me():
    user = current_user()

    if not user:
        return jsonify({"authenticated": False})

    return jsonify({
        "id": user.id,
        "email": user.email,
        "authenticated": True,
        "auth_provider": user.auth_provider,
    })


# ---------------------------
# EVENTS
# ---------------------------

@main.route("/api/events", methods=["GET"])
def get_events():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    db = SessionLocal()

    try:
        sync_google_events_to_db(user, db)

        events = (
            db.query(Event)
            .filter_by(user_id=user.id)
            .order_by(Event.start_time.asc())
            .all()
        )

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


@main.route("/api/events", methods=["POST"])
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
            return jsonify({
                "error": "Time conflict",
                "message": "This event overlaps with another event",
                "conflict_event": serialize_event(conflict_event),
            }), 409

        event = Event(
            user_id=user.id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            source="local",
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

        if user.google_credentials:
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

        return jsonify(serialize_event(event)), 201

    finally:
        db.close()


@main.route("/api/events/<int:event_id>", methods=["PUT"])
def update_event_api(event_id):
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}

    db = SessionLocal()

    try:
        event = (
            db.query(Event)
            .filter_by(id=event_id, user_id=user.id)
            .first()
        )

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
            return jsonify({
                "error": "Time conflict",
                "message": "This event overlaps with another event",
                "conflict_event": serialize_event(conflict_event),
            }), 409

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

        db.commit()
        db.refresh(event)

        return jsonify(serialize_event(event))

    finally:
        db.close()


@main.route("/api/events/<int:event_id>", methods=["DELETE"])
def delete_event_api(event_id):
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    db = SessionLocal()

    try:
        event = (
            db.query(Event)
            .filter_by(id=event_id, user_id=user.id)
            .first()
        )

        if not event:
            return jsonify({"error": "Event not found"}), 404

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

    finally:
        db.close()


# ---------------------------
# REACT
# ---------------------------

@main.route("/", defaults={"path": ""})
@main.route("/<path:path>")
def serve_react(path):
    if path.startswith("api/") or path.startswith("auth/"):
        return jsonify({"error": "Not found"}), 404

    return current_app.send_static_file("index.html")