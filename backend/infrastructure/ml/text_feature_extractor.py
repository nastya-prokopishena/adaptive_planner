import re

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin


class TextFeatureExtractor(BaseEstimator, TransformerMixin):
    ACTION_WORDS = [
        "прочитати",
        "ознайомитися",
        "описати",
        "пояснити",
        "виконати",
        "розв'язати",
        "розв’язати",
        "побудувати",
        "проаналізувати",
        "порівняти",
        "дослідити",
        "обґрунтувати",
        "розробити",
        "реалізувати",
        "створити",
        "спроєктувати",
        "оптимізувати",
        "інтегрувати",
    ]

    HARD_WORDS = [
        "реалізувати",
        "розробити",
        "дослідити",
        "порівняти",
        "проаналізувати",
        "обґрунтувати",
        "оптимізувати",
        "інтегрувати",
        "спроєктувати",
        "модель",
        "система",
        "проєкт",
        "проект",
        "api",
        "backend",
        "frontend",
        "база даних",
    ]

    def fit(self, x, y=None):
        return self

    def transform(self, x):
        features = []

        for text in x:
            text = str(text)
            lower = text.lower()

            length = len(text)
            word_count = len(re.findall(r"\w+", lower))
            action_count = sum(1 for word in self.ACTION_WORDS if word in lower)
            hard_count = sum(1 for word in self.HARD_WORDS if word in lower)
            step_count = len(re.findall(r"\b\d+[\).]\s+", text))
            bullet_count = len(re.findall(r"[-•●]\s+", text))
            question_count = text.count("?")

            features.append(
                [
                    length,
                    word_count,
                    action_count,
                    hard_count,
                    step_count,
                    bullet_count,
                    question_count,
                ]
            )

        return np.array(features)
