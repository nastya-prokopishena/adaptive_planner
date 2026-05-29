from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from backend.application.analytics_service import AnalyticsService


def make_task(status="planned", difficulty=3, date=None):
    date = date or datetime.now(UTC)
    return SimpleNamespace(
        status=status,
        difficulty_score=difficulty,
        due_date=date,
        created_at=date,
        estimated_duration_hours=2,
    )


def make_event(hours=2, date=None):
    start = date or datetime.now(UTC)
    return SimpleNamespace(start_time=start, end_time=start + timedelta(hours=hours))


def test_filter_tasks_uses_date_range():
    service = AnalyticsService()
    now = datetime.now(UTC)

    tasks = [
        make_task("done", date=now - timedelta(days=2)),
        make_task("planned", date=now),
        make_task("missed", date=now + timedelta(days=2)),
    ]

    result = service.filter_tasks(
        tasks,
        date_from=now - timedelta(hours=1),
        date_to=now + timedelta(hours=1),
    )

    assert len(result) == 1
    assert result[0].status == "planned"


def test_filter_events_ignores_items_without_start_time():
    service = AnalyticsService()
    now = datetime.now(UTC)

    events = [
        SimpleNamespace(start_time=None, end_time=None),
        make_event(date=now),
    ]

    result = service.filter_events(
        events,
        date_from=now - timedelta(hours=1),
        date_to=now + timedelta(hours=3),
    )

    assert len(result) == 1


def test_build_weekly_load_counts_tasks_and_event_hours():
    service = AnalyticsService()
    now = datetime.now(UTC)

    result = service.build_weekly_load(
        events=[make_event(hours=3, date=now)],
        tasks=[make_task(difficulty=4, date=now)],
    )

    assert len(result) == 1
    assert result[0]["hours"] == 3
    assert result[0]["tasks"] == 1
    assert result[0]["difficulty"] == 4


def test_build_dashboard_analytics_summary():
    service = AnalyticsService()
    now = datetime.now(UTC)

    result = service.build_dashboard_analytics(
        tasks=[
            make_task("done", date=now),
            make_task("missed", date=now),
            make_task("planned", date=now),
            make_task("in_progress", date=now),
        ],
        events=[make_event(date=now)],
    )

    assert result["summary"]["completed"] == 1
    assert result["summary"]["missed"] == 1
    assert result["summary"]["planned"] == 1
    assert result["summary"]["in_progress"] == 1
    assert result["summary"]["total"] == 4


def test_build_difficulty_distribution_counts_known_scores():
    service = AnalyticsService()

    result = service.build_difficulty_distribution(
        [
            make_task(difficulty=1),
            make_task(difficulty=3),
            make_task(difficulty=3),
            make_task(difficulty=5),
        ]
    )

    assert result["1"] == 1
    assert result["3"] == 2
    assert result["5"] == 1
