import os
from typing import Any

from openai import OpenAI


class ScheduleAIReaderService:
    MAX_TEXT_CONTEXT_CHARS = 60000
    MAX_IMAGES_PER_REQUEST = 6

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_SCHEDULE_MODEL", "gpt-4o")

    def read_schedule(
        self,
        extraction: dict[str, Any],
        group_name: str,
        subgroup: str = "",
    ) -> str:
        target_context = extraction.get("target_context") or ""
        text_context = extraction.get("text_context") or ""
        images = extraction.get("images") or []
        extension = extraction.get("extension") or ""

        if extension in {"pdf", "jpg", "jpeg", "png", "webp"} and images:
            visual_result = self._read_from_images_with_optional_context(
                images=images,
                target_context=target_context,
                text_context=text_context,
                group_name=group_name,
                subgroup=subgroup,
                source_hint=extraction.get("filename", ""),
            )

            if visual_result and "ПОДІЙ НЕ ЗНАЙДЕНО" not in visual_result:
                return visual_result

        if target_context.strip():
            result = self._read_from_text_context(
                text_context=target_context,
                group_name=group_name,
                subgroup=subgroup,
                source_hint="TARGET GROUP CONTEXT",
                strict_target_context=True,
            )

            if result and "ПОДІЙ НЕ ЗНАЙДЕНО" not in result:
                return result

        if text_context.strip():
            result = self._read_from_text_context(
                text_context=text_context,
                group_name=group_name,
                subgroup=subgroup,
                source_hint="FULL TEXT/TABLE CONTEXT",
                strict_target_context=False,
            )

            if result and "ПОДІЙ НЕ ЗНАЙДЕНО" not in result:
                return result

        if images:
            return self._read_from_images(
                images=images,
                group_name=group_name,
                subgroup=subgroup,
                source_hint=extraction.get("filename", ""),
            )

        return "ПОДІЙ НЕ ЗНАЙДЕНО"

    def _read_from_images_with_optional_context(
        self,
        images: list[dict[str, Any]],
        target_context: str,
        text_context: str,
        group_name: str,
        subgroup: str,
        source_hint: str,
    ) -> str:
        batches = [
            images[index:index + self.MAX_IMAGES_PER_REQUEST]
            for index in range(0, len(images), self.MAX_IMAGES_PER_REQUEST)
        ]

        results = []

        for batch_index, batch in enumerate(batches, start=1):
            prompt = self._build_prompt(
                group_name=group_name,
                subgroup=subgroup,
                source_hint=f"{source_hint}; VISUAL FIRST batch {batch_index}/{len(batches)}",
                strict_target_context=False,
                visual_mode=True,
            )

            helper_context = ""

            if target_context.strip():
                helper_context += (
                    "\n\nДОДАТКОВА ПІДКАЗКА З ТАБЛИЧНОГО ПАРСЕРА:\n"
                    "Цей текст може бути неповним або мати неправильний день, тому НЕ довіряй йому для дня тижня.\n"
                    "Використовуй його тільки як підказку для можливих предметів потрібної групи.\n"
                    f"{target_context[:12000]}"
                )

            if text_context.strip():
                helper_context += (
                    "\n\nДОДАТКОВИЙ ТЕКСТ PDF/OCR:\n"
                    "Цей текст може мати поламаний порядок колонок, тому НЕ використовуй його замість візуальної таблиці.\n"
                    f"{text_context[:12000]}"
                )

            content = [
                {
                    "type": "input_text",
                    "text": (
                        f"{prompt}\n\n"
                        "ГОЛОВНЕ ДЖЕРЕЛО — зображення сторінок нижче.\n"
                        f"Потрібно ВІЗУАЛЬНО знайти колонку або блок групи {group_name}.\n"
                        f"Випиши ВСІ пари цієї групи з усіх сторінок.\n"
                        "День тижня визначай тільки за візуальним розміщенням у таблиці, а не з target_context.\n"
                        "Не бери предмети з сусідніх груп.\n"
                        f"{helper_context}"
                    ),
                }
            ]

            for image in batch:
                mime_type = image.get("mime_type") or "image/png"
                image_base64 = image.get("base64") or ""
                page_number = image.get("page_number", "")

                content.append(
                    {
                        "type": "input_text",
                        "text": f"Сторінка / фото №{page_number}:",
                    }
                )

                content.append(
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime_type};base64,{image_base64}",
                    }
                )

            results.append(self._request(content))

        return "\n\n".join(item for item in results if item.strip()).strip() or "ПОДІЙ НЕ ЗНАЙДЕНО"

    def _read_from_text_context(
        self,
        text_context: str,
        group_name: str,
        subgroup: str,
        source_hint: str,
        strict_target_context: bool,
    ) -> str:
        chunks = self._split_text(text_context, self.MAX_TEXT_CONTEXT_CHARS)
        results = []

        for index, chunk in enumerate(chunks, start=1):
            prompt = self._build_prompt(
                group_name=group_name,
                subgroup=subgroup,
                source_hint=f"{source_hint}; chunk {index}/{len(chunks)}",
                strict_target_context=strict_target_context,
                visual_mode=False,
            )

            content = [
                {
                    "type": "input_text",
                    "text": f"{prompt}\n\nДАНІ ДЛЯ АНАЛІЗУ:\n{chunk}",
                }
            ]

            results.append(self._request(content))

        return "\n\n".join(item for item in results if item.strip()).strip() or "ПОДІЙ НЕ ЗНАЙДЕНО"

    def _read_from_images(
        self,
        images: list[dict[str, Any]],
        group_name: str,
        subgroup: str,
        source_hint: str,
    ) -> str:
        batches = [
            images[index:index + self.MAX_IMAGES_PER_REQUEST]
            for index in range(0, len(images), self.MAX_IMAGES_PER_REQUEST)
        ]

        results = []

        for batch_index, batch in enumerate(batches, start=1):
            prompt = self._build_prompt(
                group_name=group_name,
                subgroup=subgroup,
                source_hint=f"{source_hint}; image batch {batch_index}/{len(batches)}",
                strict_target_context=False,
                visual_mode=True,
            )

            content = [
                {
                    "type": "input_text",
                    "text": (
                        f"{prompt}\n\n"
                        "Перед тобою сторінки або фото розкладу як зображення. "
                        "Працюй саме з візуальною структурою: заголовки груп, дні, пари, час, клітинки."
                    ),
                }
            ]

            for image in batch:
                mime_type = image.get("mime_type") or "image/png"
                image_base64 = image.get("base64") or ""
                page_number = image.get("page_number", "")

                content.append(
                    {
                        "type": "input_text",
                        "text": f"Зображення / сторінка №{page_number}:",
                    }
                )

                content.append(
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime_type};base64,{image_base64}",
                    }
                )

            results.append(self._request(content))

        return "\n\n".join(item for item in results if item.strip()).strip() or "ПОДІЙ НЕ ЗНАЙДЕНО"

    def _request(self, content: list[dict[str, Any]]) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
        )

        output = (response.output_text or "").strip()

        if self._valid_output(output):
            return output

        retry_content = [
            {
                "type": "input_text",
                "text": (
                    "Попередня відповідь була неправильною. "
                    "Поверни тільки структурований розклад у дозволеному форматі. "
                    "Не використовуй JSON. Не пиши пояснень. "
                    "Якщо подій немає, поверни рівно: ПОДІЙ НЕ ЗНАЙДЕНО."
                ),
            }
        ] + content

        retry_response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": retry_content,
                }
            ],
        )

        retry_output = (retry_response.output_text or "").strip()

        if self._valid_output(retry_output):
            return retry_output

        return "ПОДІЙ НЕ ЗНАЙДЕНО"

    def _valid_output(self, text: str) -> bool:
        if not text:
            return False

        lowered = text.lower()

        if "i'm sorry" in lowered:
            return False

        if "can't assist" in lowered:
            return False

        if "cannot assist" in lowered:
            return False

        if "подій не знайдено" in lowered:
            return True

        if "подія:" in lowered:
            return True

        if "|" in text and ("предмет" in lowered or "день" in lowered or "пара" in lowered):
            return True

        return False

    def _build_prompt(
        self,
        group_name: str,
        subgroup: str = "",
        source_hint: str = "",
        strict_target_context: bool = False,
        visual_mode: bool = False,
    ) -> str:
        strict_text = (
            """
ВАЖЛИВО:
Тобі вже передано TARGET CONTEXT, де є технічно витягнуті клітинки потрібної групи.
Це основне джерело для предметів.
"""
            if strict_target_context
            else ""
        )

        mode_text = (
            "Потрібно аналізувати візуальну структуру файлу."
            if visual_mode
            else "Потрібно аналізувати текст/таблиці, витягнуті з файлу."
        )

        return f"""
Ти модуль розпізнавання університетського розкладу.

{mode_text}

Користувач:
Група: {group_name}
Підгрупа: {subgroup}

Завдання:
Випиши всі пари саме для групи "{group_name}".

Якщо підгрупа "{subgroup}" вказана:
- включай пари всієї групи без підгрупи;
- включай пари саме підгрупи "{subgroup}";
- не включай пари інших підгруп.

{strict_text}

Правила:
- Не плутай схожі групи.
- Не бери пари сусідніх груп.
- День визначай за візуальним положенням рядка у таблиці.
- Випиши всі пари групи з усіх сторінок.
- Якщо заняття без підгрупи, воно для всієї групи.
- Якщо вказана підгрупа 1, не включай підгрупу 2 або 3.
- Не вигадуй предмети, викладачів, аудиторії, дні або час.

Час:
1 пара = 08:30-09:50
2 пара = 10:10-11:30
3 пара = 11:50-13:10
4 пара = 13:30-14:50
5 пара = 15:05-16:25
6 пара = 16:40-18:00
7 пара = 18:10-19:30
8 пара = 19:40-21:00

Тижні:
- непарні / н/пар / чис. / чисельник = непарні.
- парні / пар. / знам. / знаменник = парні.
- якщо не вказано = щотижня.

Формат 1:

ПОДІЯ:
День: Понеділок
Пара: 1
Час: 08:30-09:50
Предмет: Назва предмета
Тип: Лекція
Викладач: викладач
Аудиторія: аудиторія
Група: {group_name}
Підгрупа: 1
Тижні: щотижня
Джерело: короткий фрагмент з файлу

Формат 2:

День | Пара | Час | Предмет | Тип | Викладач | Аудиторія | Група | Підгрупа | Тижні | Джерело

Не використовуй JSON.
Не додавай пояснення.
Якщо не знайдено жодної пари, поверни рівно:
ПОДІЙ НЕ ЗНАЙДЕНО

Контекст джерела: {source_hint}
""".strip()

    def _split_text(self, text: str, max_chars: int) -> list[str]:
        if len(text) <= max_chars:
            return [text]

        chunks = []
        current = []
        current_size = 0

        for line in text.splitlines():
            line_size = len(line) + 1

            if current and current_size + line_size > max_chars:
                chunks.append("\n".join(current))
                current = []
                current_size = 0

            current.append(line)
            current_size += line_size

        if current:
            chunks.append("\n".join(current))

        return chunks