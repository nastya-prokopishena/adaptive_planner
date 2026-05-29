import importlib
import sys
from types import SimpleNamespace

from backend.infrastructure.ml import model_registry


class FakeLoader:
    def load_event_type_classifier(self):
        return None

    def load_subject_classifier(self):
        return None


def load_adapter_module(monkeypatch):
    monkeypatch.setattr(model_registry, "MLModelLoader", FakeLoader, raising=False)

    sys.modules.pop("backend.infrastructure.ml.schedule_model_adapter", None)

    return importlib.import_module("backend.infrastructure.ml.schedule_model_adapter")


def test_normalize_text(monkeypatch):
    module = load_adapter_module(monkeypatch)
    adapter = module.ScheduleModelAdapter()

    assert adapter.normalize_text("  Лекція — тест  ") == "лекція - тест"


def test_predict_event_type_by_rules(monkeypatch):
    module = load_adapter_module(monkeypatch)
    adapter = module.ScheduleModelAdapter()

    result = adapter.predict_event_type_by_rules("лабораторна робота")

    assert result["event_type"] == "laboratory"
    assert result["source"] == "rules"


def test_predict_event_type_fallback(monkeypatch):
    module = load_adapter_module(monkeypatch)
    adapter = module.ScheduleModelAdapter()

    result = adapter.predict_event_type("незрозумілий текст")

    assert result["event_type"] == "unknown"
    assert result["source"] == "fallback"


def test_predict_subject_fallback(monkeypatch):
    module = load_adapter_module(monkeypatch)
    adapter = module.ScheduleModelAdapter()

    result = adapter.predict_subject("будь-який текст")

    assert result["subject"] is None
    assert result["source"] == "fallback"


def test_predict_event_type_with_fake_model(monkeypatch):
    module = load_adapter_module(monkeypatch)
    adapter = module.ScheduleModelAdapter()

    class FakeModel:
        def predict(self, values):
            return ["lecture"]

        def predict_proba(self, values):
            return [[0.1, 0.9]]

    adapter.event_type_model = FakeModel()

    result = adapter.predict_event_type("лекція")

    assert result["event_type"] == "lecture"
    assert result["confidence"] == 0.9
    assert result["source"] == "ml"


def test_predict_subject_with_fake_model(monkeypatch):
    module = load_adapter_module(monkeypatch)
    adapter = module.ScheduleModelAdapter()

    class FakeModel:
        def predict(self, values):
            return ["Програмування"]

    adapter.subject_model = FakeModel()

    result = adapter.predict_subject("python")

    assert result["subject"] == "Програмування"
    assert result["source"] == "ml"
