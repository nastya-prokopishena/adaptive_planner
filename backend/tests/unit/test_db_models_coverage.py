from datetime import datetime

from backend.infrastructure.db import models


def test_user_model_defaults():
    user = models.User(email="test@example.com", password_hash="hash")

    assert user.email == "test@example.com"
    assert user.password_hash == "hash"
    assert user.auth_provider is None or user.auth_provider == "local"


def test_event_type_subject_task_and_block_instances():
    event_type = models.EventType(user_id=1, name="Лекція", color="#fff", is_default=True)
    subject = models.Subject(user_id=1, name="Фізика", teacher="Іваненко")

    start = datetime(2026, 5, 29, 10, 0)
    end = datetime(2026, 5, 29, 11, 0)

    event = models.Event(
        user_id=1,
        title="Пара",
        start_time=start,
        end_time=end,
        event_type_id=2,
        subject_id=3,
    )

    task = models.Task(
        user_id=1,
        title="Задача",
        subject_id=3,
        status="planned",
        difficulty_score=4,
        estimated_duration_hours=2.5,
    )

    log = models.TaskActivityLog(
        user_id=1,
        task_id=1,
        action="status_changed",
        old_status="planned",
        new_status="done",
    )

    block = models.TaskScheduleBlock(
        user_id=1,
        task_id=1,
        start_time=start,
        end_time=end,
        generated_by_ai=True,
        source="test",
        confidence_score=0.9,
    )

    assert event_type.name == "Лекція"
    assert subject.name == "Фізика"
    assert event.title == "Пара"
    assert task.title == "Задача"
    assert log.new_status == "done"
    assert block.generated_by_ai is True


def test_table_names_and_constants():
    assert models.User.__tablename__ == "users"
    assert models.Event.__tablename__ == "events"
    assert models.Task.__tablename__ == "tasks"
    assert models.USERS_ID == "users.id"
    assert models.CASCADE_DELETE == "CASCADE"
    assert models.SET_NULL == "SET NULL"
