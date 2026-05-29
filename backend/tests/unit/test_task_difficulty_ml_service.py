import pandas as pd

from backend.application.task_difficulty_ml_service import TaskDifficultyMLService


class FakeCalibrator:
    def __init__(self):
        self.calls = []

    def calibrate(self, **kwargs):
        self.calls.append(kwargs)
        return kwargs["prediction"]


def make_service():
    service = TaskDifficultyMLService.__new__(TaskDifficultyMLService)
    service.registry = None
    service.fine_model = None
    service.group_model = None
    service.legacy_model = None
    service.metadata = None
    service.calibrator = FakeCalibrator()
    return service


class FakeModel:
    def __init__(self, prediction, fail_on_dataframe=False):
        self.prediction = prediction
        self.fail_on_dataframe = fail_on_dataframe
        self.inputs = []

    def predict(self, value):
        self.inputs.append(value)
        if self.fail_on_dataframe and isinstance(value, pd.DataFrame):
            raise ValueError("dataframe is not supported")
        return [self.prediction]


def test_get_model_info_with_metadata():
    service = make_service()
    service.metadata = {
        "model_type": "hybrid_hierarchical",
        "version": "1.0",
        "fine_accuracy": 0.8,
        "group_accuracy": 0.9,
        "dataset_size": 100,
        "saved_at": "2026-05-29",
    }

    result = service.get_model_info()

    assert result["loaded"] is True
    assert result["model_type"] == "hybrid_hierarchical"
    assert result["version"] == "1.0"


def test_get_model_info_loaded_without_metadata():
    service = make_service()
    service.legacy_model = FakeModel(3)

    result = service.get_model_info()

    assert result == {"loaded": True, "model_type": "loaded_without_metadata"}


def test_get_model_info_when_model_is_not_loaded():
    service = make_service()

    result = service.get_model_info()

    assert result["loaded"] is False
    assert result["message"] == "ML model is not loaded"


def test_build_input_dataframe_contains_combined_text():
    service = make_service()

    result = service._build_input_dataframe(
        text="Зробити лабораторну",
        task_type="laboratory",
        subject="Фізика",
    )

    assert list(result.columns) == ["combined_text", "text", "subject", "task_type"]
    row = result.iloc[0]
    assert row["text"] == "Зробити лабораторну"
    assert row["subject"] == "Фізика"
    assert row["task_type"] == "laboratory"
    assert "Предмет: Фізика" in row["combined_text"]


def test_fallback_difficulty_for_project_is_at_least_four():
    service = make_service()

    assert service._fallback_difficulty(text="короткий опис", task_type="project") == 4


def test_fallback_difficulty_limits_reading_to_two():
    service = make_service()
    text = "реалізувати розробити архітектура " * 100

    assert service._fallback_difficulty(text=text, task_type="reading") == 2


def test_fallback_difficulty_counts_hard_and_very_hard_words():
    service = make_service()

    result = service._fallback_difficulty(
        text="реалізувати та проаналізувати ci/cd pipeline",
        task_type="other",
    )

    assert result >= 3


def test_predict_difficulty_uses_fallback_without_models():
    service = make_service()

    result = service.predict_difficulty(
        text="Лабораторна робота",
        task_type="laboratory",
        subject="Фізика",
    )

    assert result == 3


def test_predict_with_hybrid_model_uses_fine_and_group_models():
    service = make_service()
    service.fine_model = FakeModel(4)
    service.group_model = FakeModel("hard")

    result = service.predict_difficulty(
        text="Розробити програмний продукт",
        task_type="project",
        subject="Архітектура",
    )

    assert result == 4
    assert service.calibrator.calls[0]["group_prediction"] == "hard"


def test_predict_with_hybrid_model_clamps_result_to_range():
    service = make_service()
    service.fine_model = FakeModel(9)

    result = service.predict_difficulty(text="Складне завдання", task_type="other", subject="Інше")

    assert result == 5


def test_predict_with_legacy_model_uses_dataframe_prediction():
    service = make_service()
    service.legacy_model = FakeModel(2)

    result = service.predict_difficulty(text="Прочитати текст", task_type="reading", subject="Інше")

    assert result == 2
    assert isinstance(service.legacy_model.inputs[0], pd.DataFrame)


def test_predict_with_legacy_model_falls_back_to_combined_text_prediction():
    service = make_service()
    service.legacy_model = FakeModel(5, fail_on_dataframe=True)

    result = service.predict_difficulty(
        text="Реалізувати систему",
        task_type="project",
        subject="Програмування",
    )

    assert result == 5
    assert isinstance(service.legacy_model.inputs[1][0], str)
    assert "Предмет: Програмування" in service.legacy_model.inputs[1][0]


def test_load_model_sets_hybrid_models_and_metadata():
    service = make_service()
    fine = FakeModel(3)
    group = FakeModel("medium")

    class FakeRegistry:
        def load_latest_model(self):
            return {"model_type": "hybrid_hierarchical", "fine_model": fine, "group_model": group}

        def load_metadata(self):
            return {"version": "test"}

    service.registry = FakeRegistry()
    service._load_model()

    assert service.fine_model is fine
    assert service.group_model is group
    assert service.metadata == {"version": "test"}


def test_load_model_sets_legacy_model():
    service = make_service()
    legacy = FakeModel(3)

    class FakeRegistry:
        def load_latest_model(self):
            return legacy

        def load_metadata(self):
            return None

    service.registry = FakeRegistry()
    service._load_model()

    assert service.legacy_model is legacy


def test_load_model_keeps_empty_state_on_registry_error():
    service = make_service()

    class BrokenRegistry:
        def load_latest_model(self):
            raise RuntimeError("broken")

        def load_metadata(self):
            return None

    service.registry = BrokenRegistry()
    service._load_model()

    assert service.fine_model is None
    assert service.group_model is None
    assert service.legacy_model is None
