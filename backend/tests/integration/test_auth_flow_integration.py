import pytest
from werkzeug.security import generate_password_hash

from backend.app.routes import auth_routes


class FakeQuery:
    def __init__(self, db):
        self.db = db
        self.filters = {}

    def filter_by(self, **kwargs):
        self.filters.update(kwargs)
        return self

    def first(self):
        email = self.filters.get("email")
        user_id = self.filters.get("id")

        for user in self.db.users:
            if email is not None and user.email == email:
                return user

            if user_id is not None and user.id == user_id:
                return user

        return None


class FakeDB:
    def __init__(self):
        self.users = []
        self.commits = 0
        self.closed = False

    def query(self, model):
        return FakeQuery(self)

    def add(self, user):
        if getattr(user, "id", None) is None:
            user.id = len(self.users) + 1
        self.users.append(user)

    def commit(self):
        self.commits += 1

    def refresh(self, user):
        if getattr(user, "id", None) is None:
            user.id = len(self.users) + 1

    def close(self):
        self.closed = True


@pytest.fixture
def fake_auth_db(monkeypatch):
    db = FakeDB()

    monkeypatch.setattr(auth_routes, "SessionLocal", lambda: db)

    return db


@pytest.mark.integration
def test_register_login_me_logout_flow(client, fake_auth_db, monkeypatch):
    monkeypatch.setattr(
        auth_routes,
        "current_user",
        lambda: fake_auth_db.users[0] if fake_auth_db.users else None,
    )

    register_response = client.post(
        "/auth/register",
        json={
            "email": "student@example.com",
            "password": "StrongPass123!",
        },
    )

    assert register_response.status_code in {200, 201}
    assert register_response.get_json()["authenticated"] is True

    logout_response = client.post("/auth/logout")

    assert logout_response.status_code == 200
    assert logout_response.get_json()["message"] == "Logged out"

    monkeypatch.setattr(auth_routes, "current_user", lambda: None)

    me_after_logout = client.get("/api/user/me")

    assert me_after_logout.status_code == 200
    assert me_after_logout.get_json()["authenticated"] is False


@pytest.mark.integration
def test_register_duplicate_user_returns_conflict(client, fake_auth_db):
    payload = {
        "email": "duplicate@example.com",
        "password": "StrongPass123!",
    }

    first_response = client.post("/auth/register", json=payload)
    second_response = client.post("/auth/register", json=payload)

    assert first_response.status_code in {200, 201}
    assert second_response.status_code == 409
    assert second_response.get_json()["error"] == "User already exists"


@pytest.mark.integration
def test_login_with_invalid_password_returns_unauthorized(client, fake_auth_db):
    from backend.infrastructure.db.models import User

    user = User(
        id=1,
        email="wrong-password@example.com",
        password_hash=generate_password_hash("StrongPass123!"),
        auth_provider="local",
    )
    fake_auth_db.users.append(user)

    response = client.post(
        "/auth/login",
        json={
            "email": user.email,
            "password": "WrongPassword",
        },
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid credentials"
