from datetime import timedelta

from backend.infrastructure.db.models import (
    Event,
    TaskScheduleBlock,
)


class TaskSchedulerService:
    def generate_task_blocks(
        self,
        db,
        user_id,
        task,
        deadline,
    ):
        existing_events = (
            db.query(Event)
            .filter(Event.user_id == user_id)
            .all()
        )

        start_time = deadline - timedelta(
            hours=task.estimated_duration_hours or 1
        )

        for event in existing_events:
            overlaps = (
                start_time < event.end_time
                and deadline > event.start_time
            )

            if overlaps:
                start_time = event.end_time + timedelta(minutes=30)
                deadline = (
                    start_time
                    + timedelta(
                        hours=task.estimated_duration_hours or 1
                    )
                )

        block = TaskScheduleBlock(
            user_id=user_id,
            task_id=task.id,
            start_time=start_time,
            end_time=deadline,
            generated_by_ai=True,
            source="ml_scheduler",
            confidence_score=0.91,
        )

        db.add(block)

        return block