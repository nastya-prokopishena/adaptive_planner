from backend.infrastructure.ml.dataset_builder.google_dork_collector import GoogleDorkCollector
from backend.infrastructure.ml.dataset_builder.moodle_collector import MoodleCollector


def test_google_dork_validation():
    collector = GoogleDorkCollector()

    assert collector._is_valid_task_material(
        "лабораторна робота",
        "file.pdf",
    )

    assert not collector._is_valid_task_material(
        "курс лекцій",
        "file.pdf",
    )


def test_moodle_validation():
    collector = MoodleCollector()

    assert collector._looks_like_public_task_page(
        "лабораторна moodle",
        "https://moodle.test",
    )

    assert not collector._looks_like_public_task_page(
        "login page",
        "https://login.test",
    )
