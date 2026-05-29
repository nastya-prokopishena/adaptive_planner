import pandas as pd

from backend.infrastructure.ml.dataset_builder.dataset_cleaner import TaskDatasetCleaner


def test_normalize_text():
    cleaner = TaskDatasetCleaner()

    result = cleaner._normalize_text("Тест   текст – приклад")

    assert "  " not in result
    assert "-" in result


def test_is_noise_detects_literature():
    cleaner = TaskDatasetCleaner()

    assert cleaner._is_noise("Список літератури та джерел") is True


def test_is_noise_detects_digit_ratio():
    cleaner = TaskDatasetCleaner()

    text = "1234567890" * 20

    assert cleaner._is_noise(text) is True


def test_normalize_task_type():
    cleaner = TaskDatasetCleaner()

    df = pd.DataFrame(
        {
            "task_type": ["bad_type", "project"],
        }
    )

    result = cleaner._normalize_task_type(df)

    assert result.iloc[0]["task_type"] == "other"
    assert result.iloc[1]["task_type"] == "project"


def test_normalize_subject():
    cleaner = TaskDatasetCleaner()

    df = pd.DataFrame(
        {
            "subject": ["Українська мова", "Технології"],
        }
    )

    result = cleaner._normalize_subject(df)

    assert result.iloc[0]["subject"] == "Філологія"
    assert result.iloc[1]["subject"] == "Інформатика"
