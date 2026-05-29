from backend.infrastructure.db import database


def test_init_db_calls_create_all(monkeypatch):
    called = {}

    class FakeMetadata:
        def create_all(self, bind):
            called["bind"] = bind

    monkeypatch.setattr(
        database.Base,
        "metadata",
        FakeMetadata(),
    )

    database.init_db()

    assert called["bind"] is database.engine


def test_database_objects_exist():
    assert database.engine is not None
    assert database.SessionLocal is not None
    assert database.Base is not None
