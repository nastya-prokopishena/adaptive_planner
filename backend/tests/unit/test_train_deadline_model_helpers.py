import pandas as pd
import pytest

from backend.infrastructure.ml import train_deadline_model as training


def test_feature_columns_include_expected_values():
    assert "estimated_duration_hours" in training.FEATURE_COLUMNS
    assert training.TARGET_COLUMN == "recommended_deadline_hours"


def test_train_deadline_model_missing_dataset(monkeypatch):
    monkeypatch.setattr(training.os.path, "exists", lambda path: False)

    with pytest.raises(FileNotFoundError):
        training.train_deadline_model()


def test_train_deadline_model_with_mocked_dependencies(monkeypatch, tmp_path):
    dataset_path = tmp_path / "deadline.csv"

    rows = []

    for index in range(12):
        rows.append(
            {
                "estimated_duration_hours": 1 + index % 3,
                "difficulty_score": 3,
                "priority_score": 2,
                "task_type_score": 2,
                "subject_has_events": 1,
                "hours_until_next_subject_event": 12,
                "day_load_score": 30,
                "free_hours_today": 5,
                "days_until_deadline": 7,
                "recommended_deadline_hours": 24 + index,
                "data_source": "synthetic",
            }
        )

    pd.DataFrame(rows).to_csv(dataset_path, index=False)

    monkeypatch.setattr(training, "DATASET_PATH", str(dataset_path))
    monkeypatch.setattr(training, "MODEL_PATH", str(tmp_path / "model.joblib"))

    class FakeRegressor:
        def __init__(self, **kwargs):
            pass

        def fit(self, x, y):
            return self

        def predict(self, x):
            return [24 for _ in range(len(x))]

    monkeypatch.setattr(training, "RandomForestRegressor", FakeRegressor)
    monkeypatch.setattr(training.joblib, "dump", lambda model, path: None)

    training.train_deadline_model()
