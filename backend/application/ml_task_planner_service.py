from datetime import datetime, timedelta

from backend.infrastructure.db.models import Event, Task, TaskScheduleBlock


class MLTaskPlannerService:
    def get_busy_intervals(self, db, user_id, start_date, end_date):
        events = (
            db.query(Event)
            .filter(Event.user_id == user_id)
            .filter(Event.start_time < end_date)
            .filter(Event.end_time > start_date)
            .all()
        )

        blocks = (
            db.query(TaskScheduleBlock)
            .filter(TaskScheduleBlock.user_id == user_id)
            .filter(TaskScheduleBlock.start_time < end_date)
            .filter(TaskScheduleBlock.end_time > start_date)
            .all()
        )

        intervals = []

        for event in events:
            intervals.append((event.start_time, event.end_time))

        for block in blocks:
            intervals.append((block.start_time, block.end_time))

        return intervals

    def overlaps(self, start, end, intervals):
        for busy_start, busy_end in intervals:
            if start < busy_end and end > busy_start:
                return True
        return False

    def find_free_slot(self, busy_intervals, start_date, end_date, duration_hours):
        current = start_date.replace(minute=0, second=0, microsecond=0)
        duration = timedelta(hours=duration_hours)

        while current + duration <= end_date:
            if 8 <= current.hour <= 21:
                slot_start = current
                slot_end = current + duration

                if not self.overlaps(slot_start, slot_end, busy_intervals):
                    return slot_start, slot_end

            current += timedelta(minutes=30)

        return None, None

    def plan_tasks(self, db, user_id, days=7):
        now = datetime.utcnow()
        end_date = now + timedelta(days=days)

        tasks = (
            db.query(Task)
            .filter(Task.user_id == user_id)
            .filter(Task.status.in_(["planned", "in_progress"]))
            .filter(Task.due_date.isnot(None))
            .order_by(Task.due_date.asc())
            .all()
        )

        if not tasks:
            return []

        created_blocks = []

        for task in tasks:
            existing_block = (
                db.query(TaskScheduleBlock)
                .filter(TaskScheduleBlock.user_id == user_id)
                .filter(TaskScheduleBlock.task_id == task.id)
                .first()
            )

            if existing_block:
                continue

            duration_hours = min(float(task.estimated_duration_hours or 1), 2)

            busy_intervals = self.get_busy_intervals(
                db=db,
                user_id=user_id,
                start_date=now,
                end_date=end_date,
            )

            slot_start, slot_end = self.find_free_slot(
                busy_intervals=busy_intervals,
                start_date=now,
                end_date=end_date,
                duration_hours=duration_hours,
            )

            if not slot_start or not slot_end:
                continue

            block = TaskScheduleBlock(
                user_id=user_id,
                task_id=task.id,
                start_time=slot_start,
                end_time=slot_end,
                generated_by_ai=True,
                source="ml_planner",
                confidence_score=0.75,
            )

            db.add(block)
            db.flush()

            created_blocks.append(block)

        db.commit()

        return created_blocks
