from datetime import datetime, timedelta

from backend.infrastructure.ml.deadline_model_adapter import DeadlineModelAdapter


class MLDeadlineService:
    PRIORITY_MAP = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "urgent": 4,
    }

    TASK_TYPE_MAP = {
        "reading": 1,
        "homework": 2,
        "laboratory": 3,
        "project": 4,
        "exam_preparation": 5,
        "other": 2,
    }

    def __init__(self):
        self.model_adapter = DeadlineModelAdapter()

    def priority_score(self, priority):
        return self.PRIORITY_MAP.get(priority or "medium", 2)

    def task_type_score(self, task_type):
        return self.TASK_TYPE_MAP.get(task_type or "other", 2)

    def get_hours_until_next_subject_event(self, subject_events):
        now = datetime.utcnow()

        future_events = [
            event for event in subject_events or [] if event.start_time and event.start_time > now
        ]

        if not future_events:
            return 0

        nearest_event = sorted(
            future_events,
            key=lambda event: event.start_time,
        )[0]

        return max(
            1,
            int((nearest_event.start_time - now).total_seconds() / 3600),
        )

    def build_features(
        self,
        task,
        subject_events=None,
        day_load_score=40,
        free_hours_today=4,
    ):
        return {
            "estimated_duration_hours": float(getattr(task, "estimated_duration_hours", None) or 1),
            "difficulty_score": int(getattr(task, "difficulty_score", None) or 3),
            "priority_score": self.priority_score(getattr(task, "priority", "medium")),
            "task_type_score": self.task_type_score(getattr(task, "task_type", "other")),
            "subject_has_events": 1 if subject_events else 0,
            "hours_until_next_subject_event": self.get_hours_until_next_subject_event(
                subject_events
            ),
            "day_load_score": day_load_score,
            "free_hours_today": free_hours_today,
            "days_until_deadline": 7,
        }

    def calculate_event_load_hours(self, date_value, calendar_events):
        total = 0.0

        for event in calendar_events or []:
            if not event.start_time or not event.end_time:
                continue

            if event.start_time.date() != date_value:
                continue

            total += max(
                (event.end_time - event.start_time).total_seconds() / 3600,
                0,
            )

        return total

    def build_subject_based_deadline(
        self,
        task,
        subject_events,
        used_event_index=0,
    ):
        future_events = sorted(
            [
                event
                for event in subject_events or []
                if event.start_time and event.start_time > datetime.utcnow()
            ],
            key=lambda event: event.start_time,
        )

        if not future_events:
            return None

        if used_event_index < len(future_events):
            selected_event = future_events[used_event_index]
            extra_weeks = 0
        else:
            selected_event = future_events[-1]
            extra_weeks = used_event_index - len(future_events) + 1

        task_hours = float(getattr(task, "estimated_duration_hours", None) or 1)

        before_event_hours = min(max(task_hours, 1), 4)

        selected_start = selected_event.start_time + timedelta(weeks=extra_weeks)

        deadline = selected_start - timedelta(hours=before_event_hours)

        if deadline.hour < 7:
            deadline = (selected_start - timedelta(days=1)).replace(
                hour=20,
                minute=0,
                second=0,
                microsecond=0,
            )

        return deadline

    def build_best_time_deadline(
        self,
        predicted_hours,
        calendar_events=None,
        used_best_time_dates=None,
    ):
        now = datetime.utcnow()
        used_best_time_dates = used_best_time_dates or []

        base_days = max(2, int(max(4, predicted_hours) / 24))
        horizon_days = min(max(base_days + 21, 21), 60)

        candidates = []

        for day_offset in range(2, horizon_days + 1):
            candidate_day = (now + timedelta(days=day_offset)).date()

            load_hours = self.calculate_event_load_hours(
                candidate_day,
                calendar_events,
            )

            used_penalty = 18 if candidate_day in used_best_time_dates else 0

            near_used_penalty = 0
            for used_day in used_best_time_dates:
                day_distance = abs((candidate_day - used_day).days)

                if day_distance == 1:
                    near_used_penalty += 8
                elif day_distance == 2:
                    near_used_penalty += 4

            weekend_penalty = 2 if candidate_day.weekday() in [5, 6] else 0
            distance_penalty = abs(day_offset - base_days) * 0.2

            score = (
                load_hours * 2
                + used_penalty
                + near_used_penalty
                + weekend_penalty
                + distance_penalty
            )

            candidates.append(
                {
                    "date": candidate_day,
                    "score": score,
                    "day_offset": day_offset,
                }
            )

        candidates = sorted(
            candidates,
            key=lambda item: (item["score"], item["day_offset"]),
        )

        selected_day = candidates[0]["date"]

        return datetime.combine(
            selected_day,
            datetime.min.time(),
        ).replace(
            hour=20,
            minute=0,
            second=0,
            microsecond=0,
        )

    def predict_deadline(
        self,
        task,
        subject_events=None,
        calendar_events=None,
        mode="subject_based",
        day_load_score=40,
        free_hours_today=4,
        used_event_index=0,
        used_best_time_dates=None,
    ):
        features = self.build_features(
            task=task,
            subject_events=subject_events,
            day_load_score=day_load_score,
            free_hours_today=free_hours_today,
        )

        try:
            predicted_hours = self.model_adapter.predict(features)
        except Exception as error:
            print("Deadline model prediction fallback:", error)
            predicted_hours = 48

        if mode == "subject_based" and subject_events:
            subject_deadline = self.build_subject_based_deadline(
                task=task,
                subject_events=subject_events,
                used_event_index=used_event_index,
            )

            if subject_deadline and subject_deadline > datetime.utcnow():
                return {
                    "deadline": subject_deadline,
                    "confidence": 0.95,
                    "reason": (
                        "Дедлайн підібрано з урахуванням наступної пари предмету "
                        "та вже запланованих задач."
                    ),
                }

        best_time_deadline = self.build_best_time_deadline(
            predicted_hours=predicted_hours,
            calendar_events=calendar_events,
            used_best_time_dates=used_best_time_dates,
        )

        return {
            "deadline": best_time_deadline,
            "confidence": 0.82,
            "reason": (
                "Дедлайн підібрано ML-моделлю за найменшим навантаженням у календарі "
                "без привʼязки до пар предмету."
            ),
        }
