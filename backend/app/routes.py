from flask import Blueprint, redirect, request, session, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import requests

from backend.infrastructure.db.database import SessionLocal
from backend.infrastructure.db.models import User, Event
from backend.infrastructure.google_calendar_adapter import GoogleCalendarAdapter
from backend.application.schedule_service import ScheduleService

main = Blueprint("main", __name__)

calendar_adapter = GoogleCalendarAdapter()
schedule_service = ScheduleService()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None

    db = SessionLocal()
    user = db.query(User).filter_by(id=user_id).first()
    db.close()
    return user


@main.route("/auth/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    db = SessionLocal()

    existing_user = db.query(User).filter_by(email=email).first()
    if existing_user:
        db.close()
        return jsonify({"error": "User already exists"}), 409

    user = User(
        email=email,
        password_hash=generate_password_hash(password),
        auth_provider="local"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    session["user_id"] = user.id

    result = {
        "id": user.id,
        "email": user.email,
        "authenticated": True
    }

    db.close()
    return jsonify(result)


@main.route("/auth/login", methods=["POST"])
def login_local():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    db = SessionLocal()
    user = db.query(User).filter_by(email=email).first()

    if not user or not user.password_hash or not check_password_hash(user.password_hash, password):
        db.close()
        return jsonify({"error": "Invalid credentials"}), 401

    session["user_id"] = user.id

    result = {
        "id": user.id,
        "email": user.email,
        "authenticated": True
    }

    db.close()
    return jsonify(result)


@main.route("/auth/google")
def google_login():
    flow = calendar_adapter.create_flow()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
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
        "scopes": credentials.scopes
    }

    userinfo_response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"}
    )

    google_user = userinfo_response.json()

    email = google_user.get("email")
    google_id = google_user.get("id")

    if not email:
        return jsonify({"error": "Google email not found"}), 400

    db = SessionLocal()

    user = db.query(User).filter_by(email=email).first()

    if not user:
        user = User(
            email=email,
            auth_provider="google",
            google_id=google_id,
            google_credentials=json.dumps(creds_dict)
        )
        db.add(user)
    else:
        user.auth_provider = "google"
        user.google_id = google_id
        user.google_credentials = json.dumps(creds_dict)

    db.commit()
    db.refresh(user)

    session["user_id"] = user.id

    db.close()

    return redirect("/")


@main.route("/api/user/me", methods=["GET"])
def me():
    user = current_user()

    if not user:
        return jsonify({"authenticated": False})

    return jsonify({
        "id": user.id,
        "email": user.email,
        "authenticated": True,
        "auth_provider": user.auth_provider
    })


@main.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@main.route("/api/events", methods=["GET"])
def get_events():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    db = SessionLocal()

    local_events = db.query(Event).filter_by(user_id=user.id).all()

    result = [
        {
            "id": event.id,
            "title": event.title,
            "start": event.start_time.isoformat(),
            "end": event.end_time.isoformat(),
            "source": event.source
        }
        for event in local_events
    ]

    if user.google_credentials:
        google_events = schedule_service.get_google_events(
            json.loads(user.google_credentials)
        )

        for event in google_events:
            result.append({
                "id": event.get("id"),
                "title": event.get("summary", "No title"),
                "start": event.get("start", {}).get("dateTime"),
                "end": event.get("end", {}).get("dateTime"),
                "source": "google"
            })

    db.close()
    return jsonify(result)


@main.route("/api/events", methods=["POST"])
def create_event_api():
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    start_time = datetime.fromisoformat(data["start"].replace("Z", "+00:00"))
    end_time = datetime.fromisoformat(data["end"].replace("Z", "+00:00"))

    db = SessionLocal()

    event = Event(
        user_id=user.id,
        title=data["title"],
        start_time=start_time,
        end_time=end_time,
        source="local"
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    if user.google_credentials:
        google_event = schedule_service.create_google_event(
            json.loads(user.google_credentials),
            data["title"],
            data["start"],
            data["end"]
        )

        event.google_event_id = google_event.get("id")
        event.source = "google"
        db.commit()

    result = {
        "id": event.id,
        "title": event.title,
        "start": event.start_time.isoformat(),
        "end": event.end_time.isoformat(),
        "source": event.source
    }

    db.close()
    return jsonify(result)


@main.route("/api/events/<event_id>", methods=["PUT"])
def update_event_api(event_id):
    user = current_user()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    db = SessionLocal()
    event = db.query(Event).filter_by(id=event_id, user_id=user.id).first()

    if not event:
        db.close()
        return jsonify({"error": "Event not found"}), 404

    event.start_time = datetime.fromisoformat(data["start"].replace("Z", "+00:00"))
    event.end_time = datetime.fromisoformat(data["end"].replace("Z", "+00:00"))

    if user.google_credentials and event.google_event_id:
        schedule_service.update_google_event(
            json.loads(user.google_credentials),
            event.google_event_id,
            data["start"],
            data["end"]
        )

    db.commit()

    result = {
        "id": event.id,
        "title": event.title,
        "start": event.start_time.isoformat(),
        "end": event.end_time.isoformat()
    }

    db.close()
    return jsonify(result)


@main.route("/", defaults={"path": ""})
@main.route("/<path:path>")
def serve_react(path):
    if path.startswith("api/") or path.startswith("auth/"):
        return jsonify({"error": "Not found"}), 404

    return current_app.send_static_file("index.html")