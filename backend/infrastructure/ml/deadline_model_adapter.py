import os

import joblib
import numpy as np

MODEL_PATH = "backend/infrastructure/ml/models/deadline_model.joblib"


class DeadlineModelAdapter:
    def __init__(self):
        self.model = None

    def load_model(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                "Deadline model not found. Run: "
                "python -m backend.infrastructure.ml.dataset_builder.generate_deadline_dataset "
                "and then "
                "python -m backend.infrastructure.ml.train_deadline_model"
            )

        self.model = joblib.load(MODEL_PATH)

    def predict(self, features):
        if self.model is None:
            self.load_model()

        x = np.array(
            [
                [
                    features["estimated_duration_hours"],
                    features["difficulty_score"],
                    features["priority_score"],
                    features["task_type_score"],
                    features["subject_has_events"],
                    features["hours_until_next_subject_event"],
                    features["day_load_score"],
                    features["free_hours_today"],
                    features["days_until_deadline"],
                ]
            ]
        )

        return float(self.model.predict(x)[0])
