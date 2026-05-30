import importlib
import sys

import pytest

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
    adapter = load_adapter_module(monkeypatch).ScheduleModelAdapter()

    assert adapter.normalize_text("  Лекція — тест  ") == "лекція - тест"


@pytest.mark.parametrize(
    ("method_name", "text", "expected_key", "expected_value", "expected_source"),
    [
        ("predict_event_type_by_rules", "лабораторна робота", "event_type", "laboratory", "rules"),
        ("predict_event_type", "незрозумілий текст", "event_type", "unknown", "fallback"),
        ("predict_subject", "будь-який текст", "subject", None, "fallback"),
    ],
)
def test_rule_and_fallback_predictions(
    monkeypatch,
    method_name,
    text,
    expected_key,
    expected_value,
    expected_source,
):
    adapter = load_adapter_module(monkeypatch).ScheduleModelAdapter()

    result = getattr(adapter, method_name)(text)

    assert result[expected_key] == expected_value
    assert result["source"] == expected_source


def test_predict_event_type_with_fake_model(monkeypatch):
    adapter = load_adapter_module(monkeypatch).ScheduleModelAdapter()

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
    adapter = load_adapter_module(monkeypatch).ScheduleModelAdapter()

    class FakeModel:
        def predict(self, values):
            return ["Програмування"]

    adapter.subject_model = FakeModel()

    result = adapter.predict_subject("python")

    assert result["subject"] == "Програмування"
    assert result["source"] == "ml"
