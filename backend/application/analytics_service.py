from collections import defaultdict

from backend.application.productivity_model_service import ProductivityModelService


class AnalyticsService:
    def __init__(self):
        self.productivity_service = ProductivityModelService()

    def build_dashboard_analytics(self, tasks, events, date_from=None, date_to=None):
        filtered_tasks = self.filter_tasks(tasks, date_from, date_to)
        filtered_events = self.filter_events(events, date_from, date_to)

        completed = len([task for task in filtered_tasks if task.status == "done"])
        missed = len([task for task in filtered_tasks if task.status == "missed"])
        planned = len([task for task in filtered_tasks if task.status == "planned"])
        in_progress = len([task for task in filtered_tasks if task.status == "in_progress"])

        return {
            "summary": {
                "completed": completed,
                "missed": missed,
                "planned": planned,
                "in_progress": in_progress,
                "total": len(filtered_tasks),
            },
            "weekly_load": self.build_weekly_load(filtered_events, filtered_tasks),
            "difficulty_distribution": self.build_difficulty_distribution(filtered_tasks),
            "productivity_history": self.productivity_service.build_daily_dataset(
                filtered_tasks,
                filtered_events,
            ),
            "completed_vs_missed": [
                {"name": "Виконано", "value": completed},
                {"name": "Пропущено", "value": missed},
            ],
        }

    def filter_tasks(self, tasks, date_from, date_to):
        result = []

        for task in tasks:
            date = task.due_date or task.created_at

            if not date:
                continue

            if date_from and date < date_from:
                continue

            if date_to and date > date_to:
                continue

            result.append(task)

        return result

    def filter_events(self, events, date_from, date_to):
        result = []

        for event in events:
            if not event.start_time:
                continue

            if date_from and event.start_time < date_from:
                continue

            if date_to and event.start_time > date_to:
                continue

            result.append(event)

        return result

    def build_weekly_load(self, events, tasks):
        days = defaultdict(lambda: {"hours": 0, "tasks": 0, "difficulty": 0})

        for event in events:
            day = event.start_time.strftime("%Y-%m-%d")
            duration = (event.end_time - event.start_time).total_seconds() / 3600
            days[day]["hours"] += max(duration, 0)

        for task in tasks:
            date = task.due_date or task.created_at

            if not date:
                continue

            day = date.strftime("%Y-%m-%d")
            days[day]["tasks"] += 1
            days[day]["difficulty"] += int(task.difficulty_score or 3)

        return [
            {
                "date": day,
                "hours": round(values["hours"], 2),
                "tasks": values["tasks"],
                "difficulty": values["difficulty"],
            }
            for day, values in sorted(days.items())
        ]

    def build_difficulty_distribution(self, tasks):
        result = {
            "1": 0,
            "2": 0,
            "3": 0,
            "4": 0,
            "5": 0,
        }

        for task in tasks:
            score = str(task.difficulty_score or 3)

            if score in result:
                result[score] += 1

        return result
