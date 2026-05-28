from flask import Blueprint

from backend.app.routes.common import *

auth_bp = Blueprint("auth", __name__)


# ---------------------------
# AUTH
# ---------------------------

@auth_bp.route("/auth/register", methods=["POST"])
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


@auth_bp.route("/auth/login", methods=["POST"])
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


@auth_bp.route("/auth/google")
def google_login():
    flow = calendar_adapter.create_flow()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="false",
        prompt="consent select_account",
    )

    session["state"] = state
    session["code_verifier"] = flow.code_verifier

    return redirect(authorization_url)


@auth_bp.route("/callback")
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


@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@auth_bp.route("/api/user/me", methods=["GET"])
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
