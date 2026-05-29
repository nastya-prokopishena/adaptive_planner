import pandas as pd
import pytest

from backend.infrastructure.ml import train_task_difficulty_model as training


def test_to_group():
    assert training.to_group(1) == "easy"
    assert training.to_group(2) == "easy"
    assert training.to_group(3) == "medium"
    assert training.to_group(5) == "hard"


def test_choose_best_model():
    results = [
        {"name": "bad", "accuracy": 0.4},
        {"name": "good", "accuracy": 0.8},
    ]

    assert training.choose_best_model(results)["name"] == "good"


def test_find_dataset_path_raises_when_missing(monkeypatch):
    monkeypatch.setattr(training.os.path, "exists", lambda path: False)

    with pytest.raises(FileNotFoundError):
        training.find_dataset_path()


def test_load_dataset_filters_rows(monkeypatch, tmp_path):
    dataset_path = tmp_path / "dataset.csv"

    pd.DataFrame(
        [
            {
                "text": "а" * 80,
                "subject": "Програмування",
                "task_type": "project",
                "difficulty": 5,
            },
            {
                "text": "short",
                "subject": "Інше",
                "task_type": "reading",
                "difficulty": 1,
            },
            {
                "text": "б" * 80,
                "subject": "Інше",
                "task_type": "other",
                "difficulty": 99,
            },
        ]
    ).to_csv(dataset_path, index=False)

    monkeypatch.setattr(training, "DATASET_CANDIDATES", [str(dataset_path)])

    df = training.load_dataset()

    assert len(df) == 1
    assert df.iloc[0]["difficulty_group"] == "hard"
    assert "combined_text" in df.columns
