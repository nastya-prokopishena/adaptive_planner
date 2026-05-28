from datetime import datetime, timedelta
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
