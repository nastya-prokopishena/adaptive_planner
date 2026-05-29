from types import SimpleNamespace

from backend.infrastructure.db.repositories.user_repo import UserRepository


class FakeUser:
    email = "test@example.com"
    id = 1
    google_credentials = None


class FakeQuery:
    def __init__(self, result=None):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class FakeSession:
    def __init__(self, result=None):
        self.result = result
        self.added = []
        self.committed = False
        self.closed = False
        self.refreshed = []

    def query(self, model):
        return FakeQuery(self.result)

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.committed = True

    def refresh(self, value):
        self.refreshed.append(value)

    def close(self):
        self.closed = True


def test_get_by_email_closes_session(monkeypatch):
    user = FakeUser()
    session = FakeSession(result=user)

    monkeypatch.setattr(
        "backend.infrastructure.db.repositories.user_repo.SessionLocal",
        lambda: session,
    )

    result = UserRepository().get_by_email("test@example.com")

    assert result is user
    assert session.closed is True


def test_create_user_commits_and_closes(monkeypatch):
    session = FakeSession()

    monkeypatch.setattr(
        "backend.infrastructure.db.repositories.user_repo.SessionLocal",
        lambda: session,
    )

    result = UserRepository().create("new@example.com", "hash")

    assert result.email == "new@example.com"
    assert result.password_hash == "hash"
    assert session.committed is True
    assert session.closed is True
    assert len(session.added) == 1


def test_update_google_credentials_when_user_exists(monkeypatch):
    user = FakeUser()
    session = FakeSession(result=user)

    monkeypatch.setattr(
        "backend.infrastructure.db.repositories.user_repo.SessionLocal",
        lambda: session,
    )

    result = UserRepository().update_google_credentials(1, {"token": "abc"})

    assert result.google_credentials == {"token": "abc"}
    assert session.committed is True
    assert session.closed is True


def test_update_google_credentials_returns_none_when_user_missing(monkeypatch):
    session = FakeSession(result=None)

    monkeypatch.setattr(
        "backend.infrastructure.db.repositories.user_repo.SessionLocal",
        lambda: session,
    )

    result = UserRepository().update_google_credentials(999, {"token": "abc"})

    assert result is None
    assert session.closed is True


def test_get_by_id(monkeypatch):
    user = FakeUser()
    session = FakeSession(result=user)

    monkeypatch.setattr(
        "backend.infrastructure.db.repositories.user_repo.SessionLocal",
        lambda: session,
    )

    result = UserRepository().get_by_id(1)

    assert result is user
    assert session.closed is True
