import re

from backend.infrastructure.ml.model_loader import MLModelLoader


class ScheduleModelAdapter:
    def __init__(self):
        self.loader = MLModelLoader()
        self.event_type_model = self.loader.load_event_type_classifier()
        self.subject_model = self.loader.load_subject_classifier()

    def normalize_text(self, text):
        text = text or ""
        text = text.lower()
        text = text.replace("–", "-").replace("—", "-")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def predict_event_type(self, text):
        normalized = self.normalize_text(text)

        if self.event_type_model:
            try:
                prediction = self.event_type_model.predict([normalized])[0]

                confidence = 0.75

                if hasattr(self.event_type_model, "predict_proba"):
                    confidence = float(max(self.event_type_model.predict_proba([normalized])[0]))

                return {
                    "event_type": prediction,
                    "confidence": confidence,
                    "source": "ml",
                }

            except Exception:
                pass

        return self.predict_event_type_by_rules(normalized)

    def predict_event_type_by_rules(self, text):
        rules = {
            "lecture": ["лекція", "лек.", "лек", " л ", "lecture", "lec"],
            "laboratory": ["лабораторна", "лабораторне", "лаб.", "лаб", "лр", "lab"],
            "practice": ["практика", "практичне", "практ.", "пр.", "practice"],
            "seminar": ["семінар", "сем.", "seminar"],
            "exam": ["іспит", "екзамен", "exam"],
            "consultation": ["консультація", "конс."],
            "elective": ["дввс", "внд", "дв1", "дв2", "дв3", "вибіркова"],
        }

        checked_text = f" {text} "

        for event_type, variants in rules.items():
            for variant in variants:
                if variant in checked_text:
                    return {
                        "event_type": event_type,
                        "confidence": 0.7,
                        "source": "rules",
                    }

        return {
            "event_type": "unknown",
            "confidence": 0.2,
            "source": "fallback",
        }

    def predict_subject(self, text):
        normalized = self.normalize_text(text)

        if self.subject_model:
            try:
                prediction = self.subject_model.predict([normalized])[0]

                confidence = 0.75

                if hasattr(self.subject_model, "predict_proba"):
                    confidence = float(max(self.subject_model.predict_proba([normalized])[0]))

                return {
                    "subject": prediction,
                    "confidence": confidence,
                    "source": "ml",
                }

            except Exception:
                pass

        return {
            "subject": None,
            "confidence": 0.0,
            "source": "fallback",
        }