import json
import os

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class LLMDifficulty5Generator:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = os.getenv("OPENAI_DATASET_MODEL", "gpt-4o-mini")

    def generate_and_append(
        self,
        input_path="backend/infrastructure/ml/datasets/processed/task_difficulty_dataset_clean.csv",
        output_path="backend/infrastructure/ml/datasets/processed/task_difficulty_dataset_enriched.csv",
        count=120,
    ):
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Dataset not found: {input_path}")

        df = pd.read_csv(input_path)

        generated_rows = self.generate_rows(count=count)

        if generated_rows:
            generated_df = pd.DataFrame(generated_rows)
            df = pd.concat([df, generated_df], ignore_index=True)

        df["dedup_key"] = df["text"].astype(str).str.lower().str[:300]
        df = df.drop_duplicates(subset=["dedup_key"])
        df = df.drop(columns=["dedup_key"])

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8")

        print(f"Enriched dataset saved: {output_path}")
        print(f"Samples: {len(df)}")
        print(df["difficulty"].value_counts().sort_index())

        return output_path

    def generate_rows(self, count=120):
        if not self.client:
            print("OPENAI_API_KEY is not set. Difficulty 5 generation skipped.")
            return []

        prompt = f"""
Згенеруй {count} українських навчальних задач для датасету ML-моделі.

Потрібні ТІЛЬКИ дуже складні задачі рівня difficulty = 5.

Вимоги:
- мова тільки українська;
- це мають бути саме навчальні завдання, лабораторні, практичні, проєктні або дослідницькі роботи;
- не пиши теорію;
- не пиши приклади розв'язання;
- різні предмети: програмування, бази даних, математика, економіка, право, психологія, історія, біологія, хімія, маркетинг, філологія, менеджмент, соціологія, педагогіка;
- task_type тільки один із: laboratory, homework, project, reading, exam_preparation, other;
- difficulty завжди 5.

Поверни тільки JSON-масив.
Формат:
[
  {{
    "text": "...",
    "subject": "...",
    "task_type": "...",
    "difficulty": 5
  }}
]
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ти створюєш якісний український dataset навчальних задач для ML-класифікації складності.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.8,
            )

            content = response.choices[0].message.content.strip()
            content = self._clean_json(content)

            data = json.loads(content)

            rows = []

            for item in data:
                text = str(item.get("text", "")).strip()

                if len(text) < 80:
                    continue

                rows.append(
                    {
                        "text": text,
                        "subject": item.get("subject", "Інше"),
                        "task_type": item.get("task_type", "project"),
                        "difficulty": 5,
                        "language": "uk",
                        "source_url": "llm_generated_difficulty_5",
                        "source_title": "LLM generated very difficult Ukrainian task",
                        "source_file": "llm_generated_difficulty_5",
                    }
                )

            return rows

        except Exception as error:
            print(f"LLM difficulty 5 generation error: {error}")
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
    generator = LLMDifficulty5Generator()
    generator.generate_and_append(count=120)
