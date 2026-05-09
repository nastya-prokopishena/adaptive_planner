import os
import uuid
from flask import Blueprint, redirect, request, session, jsonify, current_app
from google_auth_oauthlib.flow import Flow

from backend.application.schedule_service import ScheduleService
from backend.application.auth_service import AuthService
from backend.infrastructure.db.repositories.user_repo import UserRepository
from backend.infrastructure.google_calendar_adapter import GoogleCalendarAdapter

main = Blueprint("main", __name__)

schedule_service = ScheduleService()
user_repo = UserRepository()
calendar_adapter = GoogleCalendarAdapter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
credentials_path = os.path.join(BASE_DIR, "..", "infrastructure", "credentials.json")

REDIRECT_URI = "http://localhost:5000/callback"

# 🔥 ГЛОБАЛЬНЕ СХОВИЩЕ (замість session)
OAUTH_STORE = {}


# =========================
# GOOGLE AUTH (STABLE)
# =========================
@main.route("/auth/google")
def login_google():

    flow = Flow.from_client_secrets_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/calendar"],
        redirect_uri=REDIRECT_URI
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )

    # 🔥 ЗБЕРІГАЄМО НЕ В SESSION
    OAUTH_STORE[state] = {
        "code_verifier": flow.code_verifier
    }

    print("NEW STATE:", state)
    print("STORE:", OAUTH_STORE)

    return redirect(auth_url)


@main.route("/callback")
def callback():

    request_state = request.args.get("state")
    print("REQUEST STATE:", request_state)

    data = OAUTH_STORE.get(request_state)

    if not data:
        return "State mismatch or expired", 400

    flow = Flow.from_client_secrets_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/calendar"],
        redirect_uri=REDIRECT_URI
    )

    flow.state = request_state
    flow.code_verifier = data["code_verifier"]

    flow.fetch_token(
        authorization_response=request.url,
        code_verifier=data["code_verifier"]
    )

    credentials = flow.credentials

    creds_dict = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }

    # 🔥 створення користувача
    temp_email = f"google_{uuid.uuid4().hex}@temp.com"
    user = user_repo.create(temp_email)
    user_repo.update_google_credentials(user.id, creds_dict)

    # 🔥 МОЖЕШ ЗАЛИШИТИ session тільки для user_id
    session["user_id"] = user.id

    print("LOGIN SUCCESS:", user.id)

    # 🔥 очищаємо state після використання
    OAUTH_STORE.pop(request_state, None)

    return redirect("/")


# =========================
# USER INFO
# =========================
@main.route("/api/user/me")
def me():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"authenticated": False})

    user = user_repo.get_by_id(user_id)

    if not user:
        session.clear()
        return jsonify({"authenticated": False})

    return jsonify({
        "authenticated": True,
        "id": user.id,
        "email": user.email
    })


# =========================
# EVENTS
# =========================
@main.route("/api/events", methods=["GET"])
def get_events():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify([])

    user = user_repo.get_by_id(user_id)
    if not user or not user.google_credentials:
        return jsonify([])

    events = schedule_service.get_google_events(user.google_credentials)

    formatted = []
    for e in events:
        start = e.get("start", {}).get("dateTime") or e.get("start", {}).get("date")
        end = e.get("end", {}).get("dateTime") or e.get("end", {}).get("date")

        if not start or not end:
            continue

        formatted.append({
            "id": str(e.get("id")),
            "title": str(e.get("summary", "No title")),
            "start": start,
            "end": end
        })

    return jsonify(formatted)


# =========================
# SERVE REACT
# =========================
@main.route("/", defaults={"path": ""})
@main.route("/<path:path>")
def serve_react(path):

    if path.startswith("api") or path.startswith("auth"):
        return jsonify({"error": "Not found"}), 404

    return current_app.send_static_file("index.html")