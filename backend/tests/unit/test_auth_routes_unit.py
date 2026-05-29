from types import SimpleNamespace

from werkzeug.security import generate_password_hash

from backend.app.routes import auth_routes as routes


class FakeQuery:
    def __init__(self, first_item=None):
        self.first_item = first_item

    def filter_by(self, **kwargs):
        return self

    def first(self):
        return self.first_item


class FakeDB:
    def __init__(self, user=None):
        self.user = user
        self.added = []
        self.committed = False
        self.refreshed = []
        self.closed = False

    def query(self, model):
        return FakeQuery(self.user)

    def add(self, value):
        if getattr(value, "id", None) is None:
            value.id = 10
        self.added.append(value)
        self.user = value

    def commit(self):
        self.committed = True

    def refresh(self, value):
        if getattr(value, "id", None) is None:
            value.id = 10
        self.refreshed.append(value)

    def close(self):
        self.closed = True


def patch_db(monkeypatch, db):
    monkeypatch.setattr(routes, "SessionLocal", lambda: db)


def test_register_success(app, monkeypatch):
    db = FakeDB(user=None)
    patch_db(monkeypatch, db)

    with app.test_request_context(
        "/auth/register",
        method="POST",
        json={"email": "new@test.com", "password": "pass123"},
    ):
        response = routes.register()

    data = response.get_json()

    assert data["email"] == "new@test.com"
    assert data["authenticated"] is True
    assert db.committed is True
    assert db.closed is True


def test_register_rejects_missing_fields(app):
    with app.test_request_context("/auth/register", method="POST", json={"email": ""}):
        response, status = routes.register()

    assert status == 400
    assert response.get_json()["error"] == "Email and password are required"


def test_register_rejects_existing_user(app, monkeypatch):
    db = FakeDB(user=SimpleNamespace(id=1, email="old@test.com"))
    patch_db(monkeypatch, db)

    with app.test_request_context(
        "/auth/register",
        method="POST",
        json={"email": "old@test.com", "password": "pass123"},
    ):
        response, status = routes.register()

    assert status == 409
    assert response.get_json()["error"] == "User already exists"
    assert db.closed is True


def test_login_success(app, monkeypatch):
    user = SimpleNamespace(
        id=5,
        email="user@test.com",
        password_hash=generate_password_hash("correct"),
        auth_provider="local",
    )
    db = FakeDB(user=user)
    patch_db(monkeypatch, db)

    with app.test_request_context(
        "/auth/login",
        method="POST",
        json={"email": "user@test.com", "password": "correct"},
    ):
        response = routes.login_local()

    data = response.get_json()

    assert data["id"] == 5
    assert data["authenticated"] is True
    assert db.closed is True


def test_login_rejects_missing_or_wrong_credentials(app, monkeypatch):
    db = FakeDB(user=None)
    patch_db(monkeypatch, db)

    with app.test_request_context(
        "/auth/login",
        method="POST",
        json={"email": "missing@test.com", "password": "bad"},
    ):
        response, status = routes.login_local()

    assert status == 401

    user = SimpleNamespace(
        id=5,
        email="user@test.com",
        password_hash=generate_password_hash("correct"),
        auth_provider="local",
    )
    db = FakeDB(user=user)
    patch_db(monkeypatch, db)

    with app.test_request_context(
        "/auth/login",
        method="POST",
        json={"email": "user@test.com", "password": "wrong"},
    ):
        response, status = routes.login_local()

    assert status == 401
    assert response.get_json()["error"] == "Invalid credentials"


def test_logout_clears_session(app):
    with app.test_request_context("/auth/logout", method="POST"):
        from flask import session

        session["user_id"] = 123
        response = routes.logout()

    assert response.get_json()["message"] == "Logged out"


def test_me_returns_authenticated_false(app, monkeypatch):
    monkeypatch.setattr(routes, "current_user", lambda: None)

    with app.test_request_context("/api/user/me"):
        response = routes.me()

    assert response.get_json() == {"authenticated": False}


def test_me_returns_current_user(app, monkeypatch):
    user = SimpleNamespace(id=1, email="user@test.com", auth_provider="local")
    monkeypatch.setattr(routes, "current_user", lambda: user)

    with app.test_request_context("/api/user/me"):
        response = routes.me()

    data = response.get_json()

    assert data["authenticated"] is True
    assert data["email"] == "user@test.com"


def test_google_login_redirects_and_stores_flow_state(app, monkeypatch):
    class FakeFlow:
        code_verifier = "verifier"

        def authorization_url(self, **kwargs):
            return "https://google.test/auth", "state-123"

    monkeypatch.setattr(
        routes.calendar_adapter,
        "create_flow",
        lambda: FakeFlow(),
    )

    with app.test_request_context("/auth/google"):
        response = routes.google_login()
        from flask import session

        assert session["state"] == "state-123"
        assert session["code_verifier"] == "verifier"

    assert response.status_code == 302
    assert response.location == "https://google.test/auth"


def test_google_callback_rejects_missing_email(app, monkeypatch):
    class FakeCredentials:
        token = "token"
        refresh_token = "refresh"
        token_uri = "uri"
        client_id = "client"
        client_secret = "secret"
        scopes = ["calendar"]

    class FakeFlow:
        credentials = FakeCredentials()

        def fetch_token(self, authorization_response):
            self.authorization_response = authorization_response

    class FakeResponse:
        def json(self):
            return {"id": "google-1"}

    monkeypatch.setattr(routes.calendar_adapter, "create_flow", lambda: FakeFlow())
    monkeypatch.setattr(routes.requests, "get", lambda *args, **kwargs: FakeResponse())

    with app.test_request_context("/callback?code=abc"):
        from flask import session

        session["state"] = "state"
        session["code_verifier"] = "verifier"
        response, status = routes.google_callback()

    assert status == 400
    assert response.get_json()["error"] == "Google email not found"


def test_google_callback_creates_google_user(app, monkeypatch):
    db = FakeDB(user=None)
    patch_db(monkeypatch, db)

    class FakeCredentials:
        token = "token"
        refresh_token = "refresh"
        token_uri = "uri"
        client_id = "client"
        client_secret = "secret"
        scopes = ["calendar"]

    class FakeFlow:
        credentials = FakeCredentials()

        def fetch_token(self, authorization_response):
            self.authorization_response = authorization_response

    class FakeResponse:
        def json(self):
            return {"id": "google-1", "email": "google@test.com"}

    monkeypatch.setattr(routes.calendar_adapter, "create_flow", lambda: FakeFlow())
    monkeypatch.setattr(routes.requests, "get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(routes, "sync_google_events_to_db", lambda user, db: None)

    with app.test_request_context("/callback?code=abc"):
        from flask import session

        session["state"] = "state"
        session["code_verifier"] = "verifier"
        response = routes.google_callback()

    assert response.status_code == 302
    assert response.location == "/"
    assert db.user.email == "google@test.com"
    assert db.user.auth_provider == "google"
    assert db.committed is True
