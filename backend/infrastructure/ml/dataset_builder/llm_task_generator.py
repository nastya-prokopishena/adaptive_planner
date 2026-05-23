import json
import os
import time
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


class LLMTaskGenerator:
    SUBJECTS = [
        "Програмування",
        "Бази даних",
        "Математика",
        "Економіка",
        "Право",
        "Психологія",
        "Історія",
        "Біологія",
        "Хімія",
        "Маркетинг",
        "Філологія",
        "Менеджмент",
        "Соціологія",
        "Педагогіка",
    ]

    TASK_TYPES = [
        "laboratory",
        "homework",
        "project",
        "reading",
        "exam_preparation",
        "other",
    ]

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = os.getenv("OPENAI_DATASET_MODEL", "gpt-4o-mini")

    def generate_dataset_rows(self, total_per_difficulty=80):
        if not self.client:
            print("OPENAI_API_KEY is not set. LLM generation skipped.")
            return []

        rows = []

        for difficulty in [1, 2, 3, 4, 5]:
            generated = self._generate_for_difficulty(
                difficulty=difficulty,
                count=total_per_difficulty,
            )

            rows.extend(generated)
            time.sleep(1)

        return rows

    def _generate_for_difficulty(self, difficulty, count):
        prompt = f"""
Згенеруй {count} українських навчальних задач для датасету ML-моделі.

Вимоги:
- тільки українська мова;
- тільки реальні формулювання навчальних завдань;
- без теоретичних пояснень;
- без прикладів розв'язання;
- предмети мають бути різні;
- типи задач: laboratory, homework, project, reading, exam_preparation, other;
- difficulty строго = {difficulty};
- difficulty:
  1 — легка;
  2 — нижче середньої;
  3 — середня;
  4 — складна;
  5 — дуже складна.

Поверни тільки JSON-масив.
Формат кожного об'єкта:
{{
  "text": "...",
  "subject": "...",
  "task_type": "...",
  "difficulty": {difficulty}
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ти допомагаєш створювати якісний український dataset навчальних задач.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.8,
            )

            content = response.choices[0].message.content
            content = self._clean_json_response(content)

            data = json.loads(content)

            rows = []

            for item in data:
                text = item.get("text", "").strip()

                if not text:
                    continue

                rows.append({
                    "text": text,
                    "subject": item.get("subject", "Інше"),
                    "task_type": item.get("task_type", "other"),
                    "difficulty": int(item.get("difficulty", difficulty)),
                    "language": "uk",
                    "source_url": "llm_generated",
                    "source_title": "LLM generated Ukrainian educational task",
                    "source_file": "llm_generated",
                })

            return rows

        except Exception as error:
            print(f"LLM generation error for difficulty {difficulty}: {error}")
            return []

    def _clean_json_response(self, content):
        content = content.strip()

        if content.startswith("```json"):
            content = content.replace("```json", "", 1)

        if content.startswith("```"):
            content = content.replace("```", "", 1)

        if content.endswith("```"):
            content = content[:-3]

        return content.strip()