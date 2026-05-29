import json
import os

from backend.infrastructure.ml import model_registry
from backend.infrastructure.ml.model_registry import ModelRegistry, get_model_metadata


def test_save_and_load_model_and_metadata(tmp_path):
    registry = ModelRegistry(model_dir=str(tmp_path))

    result = registry.save_model(
        model_bundle={"model": "fake"},
        metadata={"model_type": "unit_test"},
    )

    assert os.path.exists(result["latest_model_path"])
    assert os.path.exists(result["metadata_path"])

    loaded_model = registry.load_latest_model()
    metadata = registry.load_metadata()

    assert loaded_model == {"model": "fake"}
    assert metadata["model_type"] == "unit_test"
    assert "saved_at" in metadata


def test_load_returns_none_when_files_missing(tmp_path):
    registry = ModelRegistry(model_dir=str(tmp_path))

    assert registry.load_latest_model() is None
    assert registry.load_metadata() is None


def test_get_model_metadata_without_metadata(monkeypatch, tmp_path):
    monkeypatch.setattr(
        model_registry,
        "ModelRegistry",
        lambda: ModelRegistry(model_dir=str(tmp_path)),
    )

    result = get_model_metadata()

    assert result["loaded"] is False
    assert result["message"] == "Metadata file not found"


def test_register_pickle_compatibility_aliases():
    ModelRegistry._register_pickle_compatibility_aliases()

    import __main__

    assert hasattr(__main__, "TextFeatureExtractor")
