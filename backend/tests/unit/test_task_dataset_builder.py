from backend.infrastructure.ml.dataset_builder.task_dataset_builder import TaskDatasetBuilder


def test_looks_like_task_collection():
    builder = TaskDatasetBuilder()

    text = "лабораторна робота виконати завдання"

    assert builder._looks_like_task_collection(text)


def test_looks_like_single_task():
    builder = TaskDatasetBuilder()

    text = "Виконати лабораторну роботу та проаналізувати результати " * 10

    assert builder._looks_like_single_task(text)


def test_filter_valid_rows():
    builder = TaskDatasetBuilder()

    rows = [
        {
            "text": "test",
            "difficulty": 3,
            "task_type": "bad",
            "language": "uk",
        }
    ]

    result = builder._filter_valid_rows(rows)

    assert result[0]["task_type"] == "other"


def test_remove_duplicates():
    builder = TaskDatasetBuilder()

    rows = [
        {"text": "abc"},
        {"text": "abc"},
    ]

    result = builder._remove_duplicates(rows)

    assert len(result) == 1
