from backend.infrastructure.ml.dataset_builder.ukrainian_text_filter import UkrainianTextFilter
from backend.infrastructure.ml.dataset_builder.weak_labeler import WeakTaskLabeler


def test_ukrainian_filter():
    service = UkrainianTextFilter()

    text = "Виконати лабораторну роботу та підготувати звіт " * 10

    assert service.is_ukrainian(text)


def test_clean_text():
    service = WeakTaskLabeler()

    assert service.clean_text("a   b") == "a b"


def test_detect_subject():
    service = WeakTaskLabeler()

    result = service.detect_subject("Написати SQL запит до бази даних")

    assert result == "Бази даних"


def test_detect_task_type():
    service = WeakTaskLabeler()

    assert service.detect_task_type("Лабораторна робота №1") == "laboratory"


def test_estimate_difficulty():
    service = WeakTaskLabeler()

    result = service.estimate_difficulty(
        "реалізувати систему та проаналізувати результати " * 10,
        "project",
    )

    assert result >= 4
