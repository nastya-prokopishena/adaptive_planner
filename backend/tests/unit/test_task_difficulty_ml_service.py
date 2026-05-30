import pandas as pd

from backend.application.task_difficulty_ml_service import TaskDifficultyMLService


class FakeCalibrator:
    def __init__(self):
        self.calls = []

    def calibrate(self, **kwargs):
        self.calls.append(kwargs)
        return kwargs["prediction"]


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


def make_service():
    service = TaskDifficultyMLService.__new__(TaskDifficultyMLService)
    service.registry = None
    service.fine_model = None
    service.group_model = None
    service.legacy_model = None
    service.metadata = None
    service.calibrator = FakeCalibrator()
    return service


def test_model_info_and_input_dataframe():
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

    service.metadata = None
    service.legacy_model = FakeModel(3)

    assert service.get_model_info() == {
        "loaded": True,
        "model_type": "loaded_without_metadata",
    }

    service.legacy_model = None

    assert service.get_model_info()["loaded"] is False

    frame = service._build_input_dataframe(
        text="Зробити лабораторну",
        task_type="laboratory",
        subject="Фізика",
    )

    assert list(frame.columns) == ["combined_text", "text", "subject", "task_type"]
    assert "Предмет: Фізика" in frame.iloc[0]["combined_text"]


def test_fallback_difficulty_rules_and_no_model_prediction():
    service = make_service()

    assert service._fallback_difficulty("короткий опис", "project") == 4
    assert service._fallback_difficulty("реалізувати розробити архітектура " * 100, "reading") == 2

    hard_result = service._fallback_difficulty(
        text="реалізувати та проаналізувати ci/cd pipeline",
        task_type="other",
    )

    assert hard_result >= 3
    assert service.predict_difficulty("Лабораторна робота", "laboratory", "Фізика") == 3


def test_predict_difficulty_with_hybrid_and_legacy_models():
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

    service = make_service()
    service.fine_model = FakeModel(9)

    assert service.predict_difficulty("Складне завдання", "other", "Інше") == 5

    service = make_service()
    service.legacy_model = FakeModel(2)

    result = service.predict_difficulty("Прочитати текст", "reading", "Інше")

    assert result == 2
    assert isinstance(service.legacy_model.inputs[0], pd.DataFrame)

    service = make_service()
    service.legacy_model = FakeModel(5, fail_on_dataframe=True)

    result = service.predict_difficulty("Реалізувати систему", "project", "Програмування")

    assert result == 5
    assert isinstance(service.legacy_model.inputs[1][0], str)
    assert "Предмет: Програмування" in service.legacy_model.inputs[1][0]


def test_load_model_states():
    service = make_service()
    fine = FakeModel(3)
    group = FakeModel("medium")

    class HybridRegistry:
        def load_latest_model(self):
            return {
                "model_type": "hybrid_hierarchical",
                "fine_model": fine,
                "group_model": group,
            }

        def load_metadata(self):
            return {"version": "test"}

    service.registry = HybridRegistry()
    service._load_model()

    assert service.fine_model is fine
    assert service.group_model is group
    assert service.metadata == {"version": "test"}

    service = make_service()
    legacy = FakeModel(3)

    class LegacyRegistry:
        def load_latest_model(self):
            return legacy

        def load_metadata(self):
            return None

    service.registry = LegacyRegistry()
    service._load_model()

    assert service.legacy_model is legacy

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
