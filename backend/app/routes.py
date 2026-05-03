import os
import uuid
from flask import Blueprint, redirect, request, session, jsonify, current_app
from google_auth_oauthlib.flow import Flow

from backend.application.schedule_service import ScheduleService
from backend.application.auth_service import AuthService
from backend.infrastructure.db.repositories.user_repo import UserRepository

main = Blueprint("main", __name__)
schedule_service = ScheduleService()
user_repo = UserRepository()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

credentials_path = os.path.join(
    BASE_DIR,
    "..",
    "infrastructure",
    "credentials.json"
)


@main.route("/login")
def login():
    flow = Flow.from_client_secrets_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/calendar"],
        redirect_uri="http://127.0.0.1:5000/callback"
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )

    session["state"] = state
    session["code_verifier"] = flow.code_verifier
    print("Login session:", session)  # <-- add this
    return redirect(auth_url)


@main.route("/callback")
def callback():
    flow = Flow.from_client_secrets_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/calendar"],
        state=session.get("state"),
        redirect_uri="http://127.0.0.1:5000/callback"
    )
    code_verifier = session.get("code_verifier")
    flow.code_verifier = code_verifier

    # ТУТ ВАЖЛИВО: передаємо code_verifier
    flow.fetch_token(
        authorization_response=request.url,
        code_verifier=code_verifier
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

    user_id = session.get("user_id")
    if user_id:
        user_repo.update_google_credentials(user_id, creds_dict)
    else:
        import uuid
        temp_email = f"google_{uuid.uuid4().hex}@temp.com"
        user = user_repo.create(temp_email)
        user_repo.update_google_credentials(user.id, creds_dict)
        session["user_id"] = user.id

    return redirect("/")


# 🔥 ОСЬ ГОЛОВНЕ
@main.route("/api/events", methods=["GET"])
def get_events():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify([])  # або 401

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
            "id": e.get("id"),
            "title": e.get("summary", "No title"),
            "start": start,
            "end": end
        })
    return jsonify(formatted)


@main.route("/api/events", methods=["POST"])
def create_event_api():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    user = user_repo.get_by_id(user_id)
    if not user or not user.google_credentials:
        return jsonify({"error": "Google Calendar not connected"}), 400

    data = request.json
    event = schedule_service.create_google_event(
        user.google_credentials,
        data["title"],
        data["start"],
        data["end"]
    )
    return jsonify(event)

@main.route("/auth/register", methods=["POST"])
def register():
    """Реєстрація з email та паролем."""
    data = request.json
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user, error = AuthService.register(email, password)
    if error:
        return jsonify({"error": error}), 400

    session["user_id"] = user.id
    return jsonify({"id": user.id, "email": user.email})


@main.route("/auth/login", methods=["POST"])
def login():
    """Вхід з email та паролем."""
    data = request.json
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user, error = AuthService.login(email, password)
    if error:
        return jsonify({"error": error}), 401

    session["user_id"] = user.id
    return jsonify({"id": user.id, "email": user.email})


@main.route("/auth/logout", methods=["POST"])
def logout():
    """Вихід з системи."""
    session.clear()
    return jsonify({"message": "Logged out"})


@main.route("/api/user/me")
def me():
    """Отримати дані поточного користувача."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    user = user_repo.get_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"id": user.id, "email": user.email})


# ---------- GOOGLE OAUTH ----------
@main.route("/auth/google")
def login_google():
    """Початок OAuth потоку Google."""
    flow = Flow.from_client_secrets_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/calendar"],
        redirect_uri="http://127.0.0.1:5000/callback"
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    session["state"] = state
    session["code_verifier"] = flow.code_verifier
    return redirect(auth_url)


@main.route("/callback")
def callback():
    """Callback після успішної авторизації Google."""
    flow = Flow.from_client_secrets_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/calendar"],
        state=session.get("state"),
        redirect_uri="http://127.0.0.1:5000/callback"
    )
    code_verifier = session.get("code_verifier")
    flow.code_verifier = code_verifier

    # Обов'язково передаємо code_verifier в fetch_token
    flow.fetch_token(
        authorization_response=request.url,
        code_verifier=code_verifier
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

    # Якщо користувач уже залогінений через email/пароль — оновлюємо токени
    user_id = session.get("user_id")
    if user_id:
        user_repo.update_google_credentials(user_id, creds_dict)
    else:
        # Якщо немає сесії — створюємо нового користувача (без пароля)
        # Можна отримати email через Google People API, але для простоти робимо тимчасовий email
        temp_email = f"google_{uuid.uuid4().hex}@temp.com"
        user = user_repo.create(temp_email)
        user_repo.update_google_credentials(user.id, creds_dict)
        session["user_id"] = user.id

    return redirect("/")


# ---------- EVENTS ----------
@main.route("/api/events", methods=["GET"])
def get_events():
    """Отримати події Google Calendar поточного користувача."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify([])   # або 401, але краще пустий масив

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
            "id": e.get("id"),
            "title": e.get("summary", "No title"),
            "start": start,
            "end": end
        })
    return jsonify(formatted)


@main.route("/api/events", methods=["POST"])
def create_event_api():
    """Створити подію в Google Calendar поточного користувача."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    user = user_repo.get_by_id(user_id)
    if not user or not user.google_credentials:
        return jsonify({"error": "Google Calendar not connected"}), 400

    data = request.json
    event = schedule_service.create_google_event(
        user.google_credentials,
        data["title"],
        data["start"],
        data["end"]
    )
    return jsonify(event)


@main.route("/api/events/<event_id>", methods=["PUT"])
def update_event_api(event_id):
    """Оновити подію (зміна часу через drag & drop)."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    user = user_repo.get_by_id(user_id)
    if not user or not user.google_credentials:
        return jsonify({"error": "Google Calendar not connected"}), 400

    data = request.json
    # Використовуємо адаптер для оновлення
    from backend.infrastructure.google_calendar_adapter import GoogleCalendarAdapter
    adapter = GoogleCalendarAdapter()
    updated = adapter.update_event(
        user.google_credentials,
        event_id,
        data["start"],
        data["end"]
    )
    return jsonify(updated)

@main.route("/", defaults={"path": ""})
@main.route("/<path:path>")
def serve_react(path):
    if not session.get("creds"):
        return redirect("/login")

    return current_app.send_static_file("index.html")