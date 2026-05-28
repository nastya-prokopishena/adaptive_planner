from datetime import timedelta

from backend.infrastructure.db.models import TaskScheduleBlock


class TaskScheduleBlockService:
    def recreate_block_for_task(
        self,
        db,
        user_id,
        task,
        deadline,
        confidence_score=0.8,
        reason=None,
    ):
        old_blocks = (
            db.query(TaskScheduleBlock)
            .filter(TaskScheduleBlock.user_id == user_id)
            .filter(TaskScheduleBlock.task_id == task.id)
            .all()
        )

        for block in old_blocks:
            db.delete(block)

        duration_hours = float(task.estimated_duration_hours or 1)
        duration_hours = min(max(duration_hours, 0.5), 3)

        start_time = deadline - timedelta(hours=duration_hours)

        block = TaskScheduleBlock(
            user_id=user_id,
            task_id=task.id,
            start_time=start_time,
            end_time=deadline,
            generated_by_ai=True,
            source="ml_deadline_planner",
            confidence_score=confidence_score,
        )

        db.add(block)
        db.flush()

        return block