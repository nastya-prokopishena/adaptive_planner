from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from backend.application.task_file_extractor_service import TaskFileExtractorService
from backend.application.task_schedule_block_service import TaskScheduleBlockService


def test_task_file_extractor_reads_txt_and_cleans_noise():
    service = TaskFileExtractorService()

    result = service.extract_text(
        "task.txt",
        "123\nКорисний текст завдання\n\nЩе один рядок".encode("utf-8"),
    )

    assert "Корисний текст завдання" in result
    assert "123" not in result


def test_task_file_extractor_rejects_unknown_extension():
    service = TaskFileExtractorService()

    with pytest.raises(ValueError):
        service.extract_text("task.exe", b"bad")


def test_recreate_block_for_task_deletes_old_blocks_and_creates_new():
    service = TaskScheduleBlockService()
    old_block = SimpleNamespace(id=1)

    class Query:
        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return [old_block]

    deleted = []
    added = []

    db = SimpleNamespace(
        query=lambda model: Query(),
        delete=lambda item: deleted.append(item),
        add=lambda item: added.append(item),
        flush=lambda: None,
    )

    task = SimpleNamespace(id=10, estimated_duration_hours=2)
    deadline = datetime.now(UTC) + timedelta(days=1)

    block = service.recreate_block_for_task(
        db=db,
        user_id=1,
        task=task,
        deadline=deadline,
    )

    assert deleted == [old_block]
    assert len(added) == 1
    assert block.task_id == 10
    assert block.end_time == deadline
