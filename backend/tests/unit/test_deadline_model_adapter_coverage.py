import numpy as np
import pytest

from backend.infrastructure.ml.deadline_model_adapter import DeadlineModelAdapter


def make_features():
    return {
        "estimated_duration_hours": 2,
        "difficulty_score": 4,
        "priority_score": 3,
        "task_type_score": 4,
        "subject_has_events": 1,
        "hours_until_next_subject_event": 12,
        "day_load_score": 30,
        "free_hours_today": 5,
        "days_until_deadline": 7,
    }


def test_predict_uses_existing_model_without_loading(monkeypatch):
    adapter = DeadlineModelAdapter()

    captured = {}

    class FakeModel:
        def predict(self, x):
            captured["shape"] = x.shape
            captured["values"] = x.tolist()
            return [42.5]

    adapter.model = FakeModel()

    result = adapter.predict(make_features())

    assert result == 42.5
    assert captured["shape"] == (1, 9)
    assert captured["values"][0][0] == 2


def test_predict_loads_model_when_missing(monkeypatch):
    adapter = DeadlineModelAdapter()

    class FakeModel:
        def predict(self, x):
            assert isinstance(x, np.ndarray)
            return [24]

    monkeypatch.setattr(adapter, "load_model", lambda: setattr(adapter, "model", FakeModel()))

    assert adapter.predict(make_features()) == 24.0


def test_load_model_raises_when_file_missing(monkeypatch):
    adapter = DeadlineModelAdapter()

    monkeypatch.setattr(
        "backend.infrastructure.ml.deadline_model_adapter.os.path.exists",
        lambda path: False,
    )

    with pytest.raises(FileNotFoundError):
        adapter.load_model()
