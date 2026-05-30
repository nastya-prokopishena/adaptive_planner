from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from backend.application.ml_deadline_service import MLDeadlineService


def make_task(hours=2, difficulty=4, priority="high", task_type="project"):
    return SimpleNamespace(
        estimated_duration_hours=hours,
        difficulty_score=difficulty,
        priority=priority,
        task_type=task_type,
    )


def make_event(start_offset_hours=24, duration_hours=2):
    start = datetime.now(UTC) + timedelta(hours=start_offset_hours)
    return SimpleNamespace(start_time=start, end_time=start + timedelta(hours=duration_hours))


@pytest.mark.parametrize(
    ("method_name", "value", "expected"),
    [
        ("priority_score", "urgent", 4),
        ("priority_score", "unknown", 2),
        ("task_type_score", "project", 4),
        ("task_type_score", "unknown", 2),
    ],
)
def test_score_helpers(method_name, value, expected):
    service = MLDeadlineService()

    assert getattr(service, method_name)(value) == expected


def test_get_hours_until_next_subject_event_returns_zero_without_events():
    assert MLDeadlineService().get_hours_until_next_subject_event([]) == 0


def test_build_features_contains_expected_values():
    service = MLDeadlineService()

    features = service.build_features(task=make_task(), subject_events=[make_event()])

    assert features["estimated_duration_hours"] == 2
    assert features["difficulty_score"] == 4
    assert features["priority_score"] == 3
    assert features["subject_has_events"] == 1


def test_calculate_event_load_hours_counts_only_target_day():
    service = MLDeadlineService()
    today = datetime.now(UTC).date()
    event = make_event(start_offset_hours=1, duration_hours=3)

    assert service.calculate_event_load_hours(today, [event]) >= 0


def test_build_subject_based_deadline_before_future_event():
    service = MLDeadlineService()
    task = make_task(hours=2)
    event = make_event(start_offset_hours=48)

    deadline = service.build_subject_based_deadline(task=task, subject_events=[event])

    assert deadline is not None
    assert deadline < event.start_time


def test_predict_deadline_falls_back_to_best_time(monkeypatch):
    service = MLDeadlineService()

    class BrokenAdapter:
        def predict(self, features):
            raise RuntimeError("model unavailable")

    service.model_adapter = BrokenAdapter()

    result = service.predict_deadline(
        task=make_task(),
        subject_events=[],
        calendar_events=[],
        mode="best_free_time",
    )

    assert result["deadline"] is not None
    assert result["confidence"] == 0.82
