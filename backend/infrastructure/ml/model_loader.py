from pathlib import Path
import joblib


class MLModelLoader:
    def __init__(self):
        self.models_dir = Path(__file__).parent / "models"
        self._cache = {}

    def get_model_path(self, model_name):
        return self.models_dir / model_name

    def load_model(self, model_name):
        if model_name in self._cache:
            return self._cache[model_name]

        model_path = self.get_model_path(model_name)

        if not model_path.exists():
            return None

        model = joblib.load(model_path)
        self._cache[model_name] = model

        return model

    def load_event_type_classifier(self):
        return self.load_model("event_type_classifier.joblib")

    def load_subject_classifier(self):
        return self.load_model("subject_classifier.joblib")

    def load_task_type_classifier(self):
        return self.load_model("task_type_classifier.joblib")

    def load_difficulty_classifier(self):
        return self.load_model("difficulty_classifier.joblib")

    def load_productivity_model(self):
        return self.load_model("productivity_model.joblib")