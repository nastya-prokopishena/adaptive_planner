import pytest

from backend.infrastructure.ml.dataset_builder.google_dork_collector import GoogleDorkCollector
from backend.infrastructure.ml.dataset_builder.moodle_collector import MoodleCollector


@pytest.mark.parametrize(
    ("collector", "method_name", "args", "expected"),
    [
        (
            GoogleDorkCollector(),
            "_is_valid_task_material",
            ("лабораторна робота", "file.pdf"),
            True,
        ),
        (GoogleDorkCollector(), "_is_valid_task_material", ("курс лекцій", "file.pdf"), False),
        (
            MoodleCollector(),
            "_looks_like_public_task_page",
            ("лабораторна moodle", "https://moodle.test"),
            True,
        ),
        (
            MoodleCollector(),
            "_looks_like_public_task_page",
            ("login page", "https://login.test"),
            False,
        ),
    ],
)
def test_collectors_validation_rules(collector, method_name, args, expected):
    assert getattr(collector, method_name)(*args) is expected
