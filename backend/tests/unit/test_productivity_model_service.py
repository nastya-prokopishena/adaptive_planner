from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from backend.application.productivity_model_service import ProductivityModelService


def test_productivity_predict_day_returns_scores():
    service = ProductivityModelService()
    target_date = datetime(2026, 5, 1, 12, 0)

    tasks = [
        SimpleNamespace(
            due_date=target_date,
            created_at=target_date,
            difficulty_score=3,
            estimated_duration_hours=2,
            status="planned",
        ),
        SimpleNamespace(
            due_date=target_date,
            created_at=target_date,
            difficulty_score=4,
            estimated_duration_hours=1,
            status="done",
        ),
    ]

    events = [
        SimpleNamespace(
            start_time=target_date.replace(hour=9),
            end_time=target_date.replace(hour=11),
        )
    ]

    result = service.predict_day(
        date=target_date,
        tasks=tasks,
        events=events,
    )

    assert 0 <= result["productivity_score"] <= 100
    assert result["number_of_tasks_day"] == 2
    assert result["busy_hours"] == 2
    assert "recommendation" in result


def make_task(status="done", date=None, difficulty=3):
    date = date or datetime.now(UTC)
    return SimpleNamespace(
        status=status,
        difficulty_score=difficulty,
        estimated_duration_hours=2,
        due_date=date,
        created_at=date,
    )


def make_event(date=None, hours=2):
    start = date or datetime.now(UTC)
    return SimpleNamespace(start_time=start, end_time=start + timedelta(hours=hours))


def test_empty_row_has_default_values():
    service = ProductivityModelService()

    row = service.empty_row("2026-05-29")

    assert row["date"] == "2026-05-29"
    assert row["productivity_score"] == 70
    assert row["completion_history"] == 70


def test_build_daily_dataset_counts_done_missed_and_events():
    service = ProductivityModelService()
    now = datetime.now(UTC)

    result = service.build_daily_dataset(
        tasks=[
            make_task("done", date=now),
            make_task("missed", date=now),
        ],
        events=[make_event(date=now, hours=3)],
    )

    assert len(result) == 1
    assert result[0]["completed_tasks"] == 1
    assert result[0]["missed_tasks"] == 1
    assert result[0]["busy_hours"] == 3


def test_predict_day_returns_low_recommendation_for_busy_day():
    service = ProductivityModelService()
    date = datetime.now(UTC)

    result = service.predict_day(
        date=date,
        tasks=[make_task("done", date=date), make_task("missed", date=date)],
        events=[make_event(date=date, hours=8)],
        extra_task=SimpleNamespace(difficulty_score=5),
    )

    assert "productivity_score" in result
    assert "load_score" in result
    assert result["number_of_tasks_day"] == 3
    assert result["recommendation"]
