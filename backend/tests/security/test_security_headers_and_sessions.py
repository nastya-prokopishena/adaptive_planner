from types import SimpleNamespace

from backend.app.routes import auth_routes, task_routes


class FakeQuery:
    def __init__(self, items=None, first_item=None):
        self.items = items or []
        self.first_item = first_item

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.items)

    def first(self):
        return self.first_item or (self.items[0] if self.items else None)


class FakeDB:
    def __init__(self):
        self.tasks = []
        self.added = []
        self.commits = 0
        self.closed = False

    def query(self, model):
        if model == task_routes.Task:
            return FakeQuery(self.tasks, self.tasks[0] if self.tasks else None)

        return FakeQuery([])

    def add(self, item):
        if getattr(item, "id", None) is None:
            item.id = len(self.added) + 1

        self.added.append(item)

        if type(item).__name__ == "Task":
            self.tasks.append(item)

    def flush(self):
        pass

    def commit(self):
        self.commits += 1

    def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = 1

    def close(self):
        self.closed = True


def test_session_cookie_has_security_flags(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] in {"Lax", "Strict", None}


def test_secret_key_is_configured(app):
    assert app.config["SECRET_KEY"]
    assert app.config["SECRET_KEY"] != ""


def test_logout_clears_authenticated_session(client):
    with client.session_transaction() as session:
        session["user_id"] = 1

    logout_response = client.post("/auth/logout")

    assert logout_response.status_code == 200

    with client.session_transaction() as session:
        assert "user_id" not in session


def test_unauthorized_mutation_is_rejected(client):
    response = client.post(
        "/api/tasks",
        json={"title": "Unauthorized task"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


def test_xss_payload_is_stored_as_plain_text_not_executed(client, monkeypatch):
    db = FakeDB()
    user = SimpleNamespace(id=1)

    monkeypatch.setattr(task_routes, "current_user", lambda: user)
    monkeypatch.setattr(task_routes, "SessionLocal", lambda: db)
    monkeypatch.setattr(task_routes, "set_auto_replan_metadata", lambda db, task: task)

    payload = "<script>alert('xss')</script>"

    response = client.post(
        "/api/tasks",
        json={
            "title": payload,
            "description": payload,
        },
    )

    assert response.status_code == 201

    data = response.get_json()
    assert data["title"] == payload
    assert data["description"] == payload


def test_sql_injection_like_login_payload_does_not_authenticate(client, monkeypatch):
    class EmptyDB:
        def query(self, model):
            return self

        def filter_by(self, **kwargs):
            return self

        def first(self):
            return None

        def close(self):
            pass

    monkeypatch.setattr(auth_routes, "SessionLocal", lambda: EmptyDB())

    response = client.post(
        "/auth/login",
        json={
            "email": "' OR '1'='1",
            "password": "' OR '1'='1",
        },
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid credentials"
