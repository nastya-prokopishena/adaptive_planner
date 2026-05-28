import re


class WeakTaskLabeler:
    SUBJECT_KEYWORDS = {
        "Програмування": ["програмування", "python", "javascript", "код", "алгоритм"],
        "Бази даних": ["база даних", "sql", "таблиця", "запит"],
        "Математика": ["рівняння", "похідна", "інтеграл", "матриця", "обчислити"],
        "Економіка": ["економіка", "ринок", "прибуток", "витрати"],
        "Право": ["право", "закон", "кодекс", "договір"],
        "Психологія": ["психологія", "особистість", "поведінка", "емоції"],
        "Історія": ["історія", "історичний", "держава", "культура"],
        "Біологія": ["біологія", "клітина", "організм", "екосистема"],
        "Хімія": ["хімія", "реакція", "речовина", "розчин"],
        "Маркетинг": ["маркетинг", "бренд", "реклама", "споживач"],
        "Філологія": ["мова", "література", "текст", "граматика"],
    }

    def clean_text(self, text):
        text = text or ""
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def split_into_task_candidates(self, text):
        text = self.clean_text(text)

        pattern = (
            r"(?=(?:Завдання|Задача|Вправа|Практичне завдання|"
            r"Практична робота|Лабораторна робота|Самостійна робота|"
            r"Семінарське заняття)\s*№?\s*\d*)"
        )

        parts = re.split(pattern, text)
        candidates = []

        for part in parts:
            cleaned = self.clean_text(part)

            if 80 <= len(cleaned) <= 3500 and self._has_task_action(cleaned):
                candidates.append(cleaned)

        return candidates

    def label_task(self, task_text):
        task_text = self.clean_text(task_text)
        task_type = self.detect_task_type(task_text)
        subject = self.detect_subject(task_text)
        difficulty = self.estimate_difficulty(task_text, task_type)

        return {
            "text": task_text,
            "subject": subject,
            "task_type": task_type,
            "difficulty": difficulty,
        }

    def detect_subject(self, text):
        lower_text = text.lower()
        scores = {}

        for subject, keywords in self.SUBJECT_KEYWORDS.items():
            scores[subject] = sum(1 for keyword in keywords if keyword in lower_text)

        best_subject = max(scores, key=scores.get)

        if scores[best_subject] == 0:
            return "Інше"

        return best_subject

    def detect_task_type(self, text):
        lower_text = text.lower()

        if any(
            word in lower_text
            for word in ["лабораторна робота", "лабораторні роботи", "хід роботи"]
        ):
            return "laboratory"

        if any(
            word in lower_text for word in ["проєкт", "проект", "розробити", "реалізувати систему"]
        ):
            return "project"

        if any(word in lower_text for word in ["прочитати", "ознайомитися", "опрацювати"]):
            return "reading"

        if any(
            word in lower_text for word in ["контрольні питання", "питання до іспиту", "модуль"]
        ):
            return "exam_preparation"

        if any(
            word in lower_text
            for word in [
                "вправа",
                "задача",
                "розв'язати",
                "розв’язати",
                "самостійна робота",
            ]
        ):
            return "homework"

        return "other"

    def estimate_difficulty(self, text, task_type):
        lower_text = text.lower()
        score = 1

        if len(text) > 300:
            score += 1

        if len(text) > 800:
            score += 1

        if len(text) > 1600:
            score += 1

        hard_words = [
            "проаналізувати",
            "порівняти",
            "дослідити",
            "обґрунтувати",
            "розробити",
            "реалізувати",
            "спроєктувати",
            "оптимізувати",
        ]

        hard_count = sum(1 for word in hard_words if word in lower_text)

        if hard_count >= 2:
            score += 1

        if task_type == "laboratory":
            score = max(score, 3)

        if task_type == "project":
            score = max(score, 4)

        return max(1, min(score, 5))

    def _has_task_action(self, text):
        lower_text = text.lower()

        markers = [
            "завдання",
            "задача",
            "вправа",
            "виконати",
            "розв'язати",
            "розв’язати",
            "побудувати",
            "проаналізувати",
            "порівняти",
            "дослідити",
            "описати",
            "обґрунтувати",
            "підготувати",
            "скласти",
            "розробити",
            "створити",
            "визначити",
            "обчислити",
        ]

        return any(marker in lower_text for marker in markers)
