import pandas as pd

from backend.infrastructure.ml.dataset_builder.task_difficulty_calibrator import (
    TaskDifficultyCalibrator,
)
from backend.infrastructure.ml.model_registry import ModelRegistry


class TaskDifficultyMLService:
    def __init__(self):
        self.registry = ModelRegistry(
            model_dir="backend/infrastructure/ml/models",
        )

        self.fine_model = None
        self.group_model = None
        self.legacy_model = None
        self.metadata = None

        self.calibrator = TaskDifficultyCalibrator()

        self._load_model()

    def _load_model(self):
        try:
            loaded = self.registry.load_latest_model()
            self.metadata = self.registry.load_metadata()

            if not loaded:
                print("Task difficulty ML model not found. Fallback will be used.")
                return

            if isinstance(loaded, dict) and loaded.get("model_type") == "hybrid_hierarchical":
                self.fine_model = loaded.get("fine_model")
                self.group_model = loaded.get("group_model")

                print("Hybrid hierarchical task difficulty model loaded.")

                if self.metadata:
                    print(f"Model version: {self.metadata.get('version')}")
                    print(f"Fine accuracy: {self.metadata.get('fine_accuracy')}")
                    print(f"Group accuracy: {self.metadata.get('group_accuracy')}")

                return

            self.legacy_model = loaded
            print("Legacy task difficulty model loaded.")

        except Exception as error:
            print(f"Failed to load task difficulty model: {error}")

    def predict_difficulty(self, text, task_type="other", subject="Інше"):
        text = text or ""
        task_type = task_type or "other"
        subject = subject or "Інше"

        if self.fine_model:
            return self._predict_with_hybrid_model(
                text=text,
                task_type=task_type,
                subject=subject,
            )

        if self.legacy_model:
            return self._predict_with_legacy_model(
                text=text,
                task_type=task_type,
                subject=subject,
            )

        return self._fallback_difficulty(
            text=text,
            task_type=task_type,
        )

    def get_model_info(self):
        if self.metadata:
            return {
                "loaded": True,
                "model_type": self.metadata.get("model_type"),
                "version": self.metadata.get("version"),
                "fine_accuracy": self.metadata.get("fine_accuracy"),
                "group_accuracy": self.metadata.get("group_accuracy"),
                "dataset_size": self.metadata.get("dataset_size"),
                "saved_at": self.metadata.get("saved_at"),
            }

        if self.fine_model or self.group_model or self.legacy_model:
            return {
                "loaded": True,
                "model_type": "loaded_without_metadata",
            }

        return {
            "loaded": False,
            "model_type": None,
            "message": "ML model is not loaded",
        }

    def _predict_with_hybrid_model(self, text, task_type, subject):
        row = self._build_input_dataframe(
            text=text,
            task_type=task_type,
            subject=subject,
        )

        base_prediction = int(self.fine_model.predict(row)[0])

        group_prediction = None

        if self.group_model:
            group_prediction = self.group_model.predict(row)[0]

        calibrated = self.calibrator.calibrate(
            prediction=base_prediction,
            text=text,
            task_type=task_type,
            subject=subject,
            group_prediction=group_prediction,
        )

        return int(max(1, min(calibrated, 5)))

    def _predict_with_legacy_model(self, text, task_type, subject):
        row = self._build_input_dataframe(
            text=text,
            task_type=task_type,
            subject=subject,
        )

        try:
            prediction = int(self.legacy_model.predict(row)[0])
        except Exception:
            combined_text = row.iloc[0]["combined_text"]
            prediction = int(self.legacy_model.predict([combined_text])[0])

        calibrated = self.calibrator.calibrate(
            prediction=prediction,
            text=text,
            task_type=task_type,
            subject=subject,
            group_prediction=None,
        )

        return int(max(1, min(calibrated, 5)))

    def _build_input_dataframe(self, text, task_type, subject):
        combined_text = f"Предмет: {subject}. " f"Тип задачі: {task_type}. " f"Завдання: {text}"

        return pd.DataFrame(
            [
                {
                    "combined_text": combined_text,
                    "text": text,
                    "subject": subject,
                    "task_type": task_type,
                }
            ]
        )

    def _fallback_difficulty(self, text, task_type):
        lower_text = text.lower()
        score = 1

        if len(text) > 300:
            score += 1

        if len(text) > 900:
            score += 1

        if len(text) > 1800:
            score += 1

        hard_words = [
            "реалізувати",
            "дослідити",
            "порівняти",
            "побудувати",
            "проаналізувати",
            "розробити",
            "оптимізувати",
            "інтегрувати",
            "спроєктувати",
            "налаштувати",
            "продемонструвати",
        ]

        very_hard_words = [
            "ci/cd",
            "jenkins",
            "github actions",
            "машинне навчання",
            "архітектура",
            "програмний продукт",
        ]

        hard_count = sum(1 for word in hard_words if word in lower_text)
        very_hard_count = sum(1 for word in very_hard_words if word in lower_text)

        if hard_count >= 2:
            score += 1

        if very_hard_count >= 1:
            score += 1

        if task_type == "project":
            score = max(score, 4)

        if task_type == "laboratory":
            score = max(score, 3)

        if task_type == "reading":
            score = min(score, 2)

        return max(1, min(score, 5))
