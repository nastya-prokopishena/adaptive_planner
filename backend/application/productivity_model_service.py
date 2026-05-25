from datetime import datetime
from statistics import mean


class ProductivityModelService:
    def build_daily_dataset(self, tasks, events):
        days = {}

        def get_day(date):
            return date.date().isoformat()

        for task in tasks:
            date = task.due_date or task.created_at or datetime.utcnow()
            day = get_day(date)

            if day not in days:
                days[day] = self.empty_row(day)

            days[day]["number_of_tasks_day"] += 1
            days[day]["total_difficulty_day"] += int(task.difficulty_score or 3)
            days[day]["total_duration_hours"] += float(task.estimated_duration_hours or 1)

            if task.status == "done":
                days[day]["completed_tasks"] += 1

            if task.status == "missed":
                days[day]["missed_tasks"] += 1

        for event in events:
            if not event.start_time or not event.end_time:
                continue

            day = get_day(event.start_time)

            if day not in days:
                days[day] = self.empty_row(day)

            duration = (event.end_time - event.start_time).total_seconds() / 3600
            days[day]["event_count"] += 1
            days[day]["busy_hours"] += max(duration, 0)

        rows = sorted(days.values(), key=lambda item: item["date"])
        history = []

        for row in rows:
            total = row["number_of_tasks_day"]
            completed = row["completed_tasks"]
            missed = row["missed_tasks"]

            if total > 0:
                productivity = completed / total * 100 - missed * 10
            else:
                productivity = 70

            row["productivity_score"] = round(max(0, min(100, productivity)), 2)
            row["completion_history"] = round(mean(history[-7:]), 2) if history else 70

            history.append(row["productivity_score"])

        return rows

    def predict_day(self, date, tasks, events, extra_task=None):
        day_tasks = []
        day_events = []

        for task in tasks:
            task_date = task.due_date or task.created_at
            if task_date and task_date.date() == date.date():
                day_tasks.append(task)

        for event in events:
            if event.start_time and event.start_time.date() == date.date():
                day_events.append(event)

        task_count = len(day_tasks)
        difficulty = sum(int(task.difficulty_score or 3) for task in day_tasks)

        if extra_task:
            task_count += 1
            difficulty += int(extra_task.difficulty_score or 3)

        busy_hours = sum(
            max((event.end_time - event.start_time).total_seconds() / 3600, 0)
            for event in day_events
        )

        completed = len([task for task in tasks if task.status == "done"])
        finished = len([task for task in tasks if task.status in ["done", "missed"]])

        completion_history = completed / finished * 100 if finished else 70

        load_score = min(100, busy_hours * 8 + task_count * 10 + difficulty * 6)

        productivity_score = (
            completion_history
            - busy_hours * 3
            - task_count * 4
            - difficulty * 2
        )

        productivity_score = max(0, min(100, productivity_score))

        if productivity_score >= 75:
            recommendation = "добрий день для складних задач"
        elif productivity_score >= 50:
            recommendation = "краще ставити задачі середньої складності"
        else:
            recommendation = "день перевантажений, краще не планувати важкі задачі"

        return {
            "productivity_score": round(productivity_score, 2),
            "load_score": round(load_score, 2),
            "completion_history": round(completion_history, 2),
            "number_of_tasks_day": task_count,
            "total_difficulty_day": difficulty,
            "busy_hours": round(busy_hours, 2),
            "recommendation": recommendation,
        }

    def empty_row(self, day):
        return {
            "date": day,
            "number_of_tasks_day": 0,
            "total_difficulty_day": 0,
            "total_duration_hours": 0,
            "event_count": 0,
            "busy_hours": 0,
            "completed_tasks": 0,
            "missed_tasks": 0,
            "completion_history": 70,
            "productivity_score": 70,
        }