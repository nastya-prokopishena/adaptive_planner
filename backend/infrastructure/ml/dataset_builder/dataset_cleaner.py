import os
import re

import pandas as pd


class TaskDatasetCleaner:
    def __init__(self):
        self.noise_patterns = [
            "список літератури",
            "рекомендована література",
            "використана література",
            "зміст",
            "вступ",
            "передмова",
            "міністерство освіти",
            "навчальне видання",
            "удк",
            "isbn",
            "рисунок",
            "таблиця",
            "джерело:",
            "лекція",
            "курс лекцій",
            "силабус",
            "syllabus",
            "робоча програма",
            "навчальна програма",
            "анотація дисципліни",
            "опис дисципліни",
            "приклад розв'язку",
            "приклад розв’язку",
            "приклад виконання",
            "готові відповіді",
        ]

    def clean_dataset(
        self,
        input_path="backend/infrastructure/ml/datasets/processed/task_difficulty_dataset.csv",
        output_path="backend/infrastructure/ml/datasets/processed/task_difficulty_dataset_clean.csv",
    ):
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Dataset not found: {input_path}")

        df = pd.read_csv(input_path)

        required_columns = [
            "text",
            "subject",
            "task_type",
            "difficulty",
            "language",
            "source_url",
            "source_title",
            "source_file",
        ]

        for column in required_columns:
            if column not in df.columns:
                df[column] = ""

        df = df.dropna(subset=["text", "difficulty"])
        df["text"] = df["text"].astype(str).apply(self._normalize_text)
        df["subject"] = df["subject"].fillna("Інше").astype(str)
        df["task_type"] = df["task_type"].fillna("other").astype(str)
        df["language"] = df["language"].fillna("uk").astype(str)

        df = df[df["language"] == "uk"]
        df = df[df["text"].str.len() >= 60]
        df = df[df["text"].str.len() <= 3500]
        df = df[~df["text"].apply(self._is_noise)]

        df["difficulty"] = df["difficulty"].astype(int)
        df = df[df["difficulty"].isin([1, 2, 3, 4, 5])]

        df["dedup_key"] = df["text"].str.lower().str[:300]
        df = df.drop_duplicates(subset=["dedup_key"])
        df = df.drop(columns=["dedup_key"])

        df = self._normalize_task_type(df)
        df = self._normalize_subject(df)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8")

        print(f"Clean dataset saved: {output_path}")
        print(f"Samples: {len(df)}")
        print("Difficulty distribution:")
        print(df["difficulty"].value_counts().sort_index())
        print("Task type distribution:")
        print(df["task_type"].value_counts())

        return output_path

    def _normalize_text(self, text):
        text = text.replace("", "-")
        text = text.replace("–", "-")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _is_noise(self, text):
        lower = text.lower()

        if any(pattern in lower for pattern in self.noise_patterns):
            return True

        letters = re.findall(r"[а-яА-ЯіїєґІЇЄҐa-zA-Z]", text)

        if len(letters) < 40:
            return True

        digit_ratio = len(re.findall(r"\d", text)) / max(1, len(text))

        if digit_ratio > 0.35:
            return True

        return False

    def _normalize_task_type(self, df):
        allowed = {
            "laboratory",
            "homework",
            "project",
            "reading",
            "exam_preparation",
            "other",
        }

        df["task_type"] = df["task_type"].apply(
            lambda value: value if value in allowed else "other"
        )

        return df

    def _normalize_subject(self, df):
        replacements = {
            "Мова та література": "Філологія",
            "Українська мова": "Філологія",
            "Література": "Філологія",
            "Мовознавство": "Філологія",
            "Лінгвістика": "Філологія",
            "Наука": "Природничі науки",
            "Природознавство": "Природничі науки",
            "Технології": "Інформатика",
            "Економічна інформатика": "Інформатика",
            "Фінансові науки": "Економіка",
            "Фінансова грамотність": "Економіка",
            "Соціальні науки": "Соціологія",
        }

        df["subject"] = df["subject"].replace(replacements)

        return df


if __name__ == "__main__":
    cleaner = TaskDatasetCleaner()
    cleaner.clean_dataset()
