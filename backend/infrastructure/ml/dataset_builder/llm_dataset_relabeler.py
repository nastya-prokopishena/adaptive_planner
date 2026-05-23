import json
import os
import time

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


class LLMDatasetRelabeler:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = os.getenv("OPENAI_DATASET_MODEL", "gpt-4o-mini")

    def relabel_dataset(
        self,
        input_path="backend/infrastructure/ml/datasets/processed/task_difficulty_dataset_clean.csv",
        output_path="backend/infrastructure/ml/datasets/processed/task_difficulty_dataset_relabelled.csv",
        batch_size=20,
        limit=None,
    ):
        if not self.client:
            raise ValueError("OPENAI_API_KEY is not set")

        df = pd.read_csv(input_path)
        df = df.dropna(subset=["text"])
        df = df.reset_index(drop=True)

        if limit:
            df = df.head(limit)

        result_rows = []

        for start in range(0, len(df), batch_size):
            batch = df.iloc[start:start + batch_size]

            print(f"Relabeling rows {start + 1}-{start + len(batch)} / {len(df)}")

            relabelled = self._relabel_batch(batch)

            if relabelled:
                result_rows.extend(relabelled)

            time.sleep(1)

        result_df = pd.DataFrame(result_rows)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        result_df.to_csv(output_path, index=False, encoding="utf-8")

        print(f"Relabelled dataset saved: {output_path}")
        print(result_df["difficulty"].value_counts().sort_index())

        return output_path

    def _relabel_batch(self, batch):
        items = []

        for index, row in batch.iterrows():
            items.append({
                "id": int(index),
                "text": str(row.get("text", "")),
                "subject": str(row.get("subject", "Інше")),
                "task_type": str(row.get("task_type", "other")),
                "old_difficulty": int(row.get("difficulty", 3)),
            })

        prompt = f"""
Перевір і виправ розмітку українських навчальних задач.

Потрібно для кожного елемента визначити:
- subject;
- task_type;
- difficulty від 1 до 5.

task_type може бути тільки:
laboratory, homework, project, reading, exam_preparation, other.

difficulty:
1 — дуже легка: прочитати, ознайомитися, дати визначення;
2 — нижче середньої: короткі вправи, коротке есе, простий опис;
3 — середня: лабораторна, практична, аналіз, звіт, розрахунки;
4 — складна: дослідити, порівняти, обґрунтувати, комплексний аналіз;
5 — дуже складна: проєкт, система, ML-модель, повна реалізація, велика дослідницька робота.

Поверни тільки JSON-масив.
Формат:
[
  {{
    "id": 0,
    "text": "...",
    "subject": "...",
    "task_type": "...",
    "difficulty": 3
  }}
]

Дані:
{json.dumps(items, ensure_ascii=False)}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ти розмічаєш український dataset навчальних задач для ML-моделі.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.2,
            )

            content = response.choices[0].message.content.strip()
            content = self._clean_json(content)

            rows = json.loads(content)

            cleaned_rows = []

            for item in rows:
                difficulty = int(item.get("difficulty", 3))

                if difficulty not in [1, 2, 3, 4, 5]:
                    difficulty = 3

                task_type = item.get("task_type", "other")

                if task_type not in [
                    "laboratory",
                    "homework",
                    "project",
                    "reading",
                    "exam_preparation",
                    "other",
                ]:
                    task_type = "other"

                cleaned_rows.append({
                    "text": item.get("text", ""),
                    "subject": item.get("subject", "Інше"),
                    "task_type": task_type,
                    "difficulty": difficulty,
                    "language": "uk",
                    "source_url": "llm_relabelled",
                    "source_title": "LLM relabelled task",
                    "source_file": "llm_relabelled",
                })

            return cleaned_rows

        except Exception as error:
            print(f"LLM relabel error: {error}")
            return []

    def _clean_json(self, content):
        if content.startswith("```json"):
            content = content.replace("```json", "", 1)

        if content.startswith("```"):
            content = content.replace("```", "", 1)

        if content.endswith("```"):
            content = content[:-3]

        return content.strip()


if __name__ == "__main__":
    relabeler = LLMDatasetRelabeler()
    relabeler.relabel_dataset()