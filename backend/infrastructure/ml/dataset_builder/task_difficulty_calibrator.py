import re


class TaskDifficultyCalibrator:
    HARD_ACTIONS = [
        "реалізувати",
        "розробити",
        "спроєктувати",
        "інтегрувати",
        "оптимізувати",
        "дослідити",
        "проаналізувати",
        "порівняти",
        "обґрунтувати",
        "побудувати модель",
        "створити систему",
    ]

    VERY_HARD_MARKERS = [
        "повноцінний проєкт",
        "програмний продукт",
        "інформаційна система",
        "ml-модель",
        "машинне навчання",
        "база даних",
        "backend",
        "frontend",
        "api",
        "тестування",
        "документація",
        "архітектура",
    ]

    EASY_MARKERS = [
        "прочитати",
        "ознайомитися",
        "ознайомитись",
        "дати визначення",
        "законспектувати",
        "переглянути",
    ]

    def calibrate(self, prediction, text, task_type="other", subject="", group_prediction=None):
        text = text or ""
        lower = text.lower()

        final_score = int(prediction)

        hard_count = sum(1 for word in self.HARD_ACTIONS if word in lower)
        very_hard_count = sum(1 for word in self.VERY_HARD_MARKERS if word in lower)
        easy_count = sum(1 for word in self.EASY_MARKERS if word in lower)

        step_count = self._count_steps(text)
        text_length = len(text)

        if group_prediction == "easy":
            final_score = min(final_score, 2)

        if group_prediction == "medium":
            final_score = max(2, min(final_score, 4))

        if group_prediction == "hard":
            final_score = max(final_score, 4)

        if task_type == "reading" and hard_count == 0:
            final_score = min(final_score, 2)

        if task_type == "homework" and text_length < 500 and hard_count <= 1:
            final_score = min(final_score, 3)

        if task_type == "laboratory":
            final_score = max(final_score, 3)

        if task_type == "project":
            final_score = max(final_score, 4)

        if hard_count >= 2:
            final_score = max(final_score, 4)

        if very_hard_count >= 3:
            final_score = max(final_score, 5)

        if step_count >= 5:
            final_score = max(final_score, 4)

        if step_count >= 8:
            final_score = max(final_score, 5)

        if text_length > 1800 and hard_count >= 2:
            final_score = max(final_score, 5)

        if easy_count >= 1 and text_length < 300 and hard_count == 0:
            final_score = min(final_score, 2)

        return max(1, min(final_score, 5))

    def _count_steps(self, text):
        numbered = re.findall(r"\b\d+[\).]\s+", text)
        bullets = re.findall(r"[-•●]\s+", text)

        action_words = [
            "виконати",
            "створити",
            "реалізувати",
            "додати",
            "описати",
            "проаналізувати",
            "побудувати",
            "порівняти",
            "дослідити",
            "обґрунтувати",
        ]

        action_count = sum(1 for word in action_words if word in text.lower())

        return len(numbered) + len(bullets) + action_count
