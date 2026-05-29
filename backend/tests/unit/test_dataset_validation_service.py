import pandas as pd

from backend.infrastructure.ml.dataset_builder.dataset_validation_service import (
    DatasetValidationService,
)


def test_ensure_columns():
    service = DatasetValidationService()

    df = pd.DataFrame({"text": ["a"]})

    result = service._ensure_columns(df)

    assert "id" in result.columns
    assert "validation_status" in result.columns


def test_update_task(monkeypatch):
    service = DatasetValidationService()

    df = pd.DataFrame(
        {
            "id": [1],
            "text": ["old"],
            "validation_status": ["pending"],
        }
    )

    monkeypatch.setattr(service, "_load_dataset", lambda: df)
    monkeypatch.setattr(service, "_save_dataset", lambda x: None)

    result = service.update_task(
        1,
        {
            "text": "new",
            "validation_status": "approved",
        },
    )

    assert result["text"] == "new"
    assert result["validation_status"] == "approved"
