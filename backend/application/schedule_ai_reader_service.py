import json
import os
from typing import Any

from openai import OpenAI


class ScheduleAIReaderService:
    TEXT_CHUNK_LIMIT = 55_000

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise RuntimeError("OPENAI_API_KEY не знайдено. Додай ключ у .env.")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_SCHEDULE_MODEL", "gpt-4.1")

    def read_schedule(
        self,
        extraction: dict[str, Any],
        group_name: str,
        subgroup: str = "",
    ) -> dict[str, Any]:
        group_name = (group_name or "").strip()
        subgroup = (subgroup or "").strip()

        if not group_name:
            return {
                "table_pages": [],
                "warnings": ["Не вказано групу."],
                "document_analysis": {},
            }

        if extraction.get("pages"):
            return self._read_visual_pages(extraction, group_name, subgroup)

        return self._read_text_tables(extraction, group_name, subgroup)

    def _read_visual_pages(
        self,
        extraction: dict[str, Any],
        group_name: str,
        subgroup: str,
    ) -> dict[str, Any]:
        table_pages = []
        warnings = []

        for page in extraction.get("pages") or []:
            page_number = int(page.get("page") or 0)
            page_text = page.get("page_text") or ""
            image = page.get("full_image")

            if not image:
                continue

            result = self._analyze_visual_page(
                image=image,
                page_text=page_text,
                page_number=page_number,
                group_name=group_name,
                subgroup=subgroup,
            )

            table_pages.append(result)
            warnings.extend(result.get("warnings", []))

        return {
            "table_pages": table_pages,
            "warnings": list(dict.fromkeys(warnings)),
            "document_analysis": {
                "schedule_kind": "ai_coordinate_table",
                "best_strategy": "ai_table_geometry_then_backend_group_intersection",
                "target_group": group_name,
                "target_subgroup": subgroup,
            },
        }

    def _analyze_visual_page(
        self,
        image: dict[str, Any],
        page_text: str,
        page_number: int,
        group_name: str,
        subgroup: str,
    ) -> dict[str, Any]:
        prompt = f"""
Ти не просто читаєш розклад. Ти маєш побудувати структуру таблиці, як coordinate parser.

Потрібна група користувача: "{group_name}"
Потрібна підгрупа: "{subgroup or 'не вказана'}"
Сторінка: {page_number}

ГОЛОВНЕ:
Не вибирай події для групи самостійно.
Твоє завдання — повернути геометрію таблиці:
1. групи в шапці з координатами x1-x2;
2. рядки з днем, номером пари, часом і координатами y1-y2;
3. усі навчальні клітинки з координатами x1-x2-y1-y2;
4. parsed_events всередині кожної клітинки.

Backend сам перевірить:
cell.x1 < target_group.x2 AND cell.x2 > target_group.x1

Тому НЕ треба фільтрувати клітинки за групою.
Поверни всі клітинки таблиці, але з правильними координатами.

КООРДИНАТИ:
- усі координати мають бути нормалізовані від 0 до 1;
- x1=0 лівий край сторінки, x2=1 правий край;
- y1=0 верх сторінки, y2=1 низ сторінки;
- для merged/потокових клітинок x1-x2 мають охоплювати всю ширину клітинки;
- якщо лекція розтягнута через кілька груп, її x1-x2 має перетинати всі ці групи;
- якщо клітинка тільки в одній групі, її x1-x2 має бути в межах цієї групи.

ГРУПИ:
- знайди всі групи в шапці: наприклад ФЕЛ-41с, ФЕМ-41с, ФЕМ-42с, ФЕП-41с, ФЕП-42с, ФЕП-43с;
- не плутай академічну групу з "підгр. 1";
- group.name має бути рівно текстом групи з таблиці.

РЯДКИ:
- rows мають відповідати парам;
- якщо видно день — day_of_week: MO/TU/WE/TH/FR/SA/SU;
- якщо день не написаний на продовженні сторінки, визнач за логікою таблиці;
- pair_number — номер пари;
- start_time/end_time — якщо видно час;
- якщо час не видно, але видно пару, залиш start_time/end_time порожніми.

КЛІТИНКИ:
- поверни тільки навчальні клітинки, не службові заголовки;
- не додавай декан, затверджую, міністерство, розклад, семестр;
- cell.text — повний текст клітинки;
- cell.source_cell_type:
  exact — звичайна клітинка однієї групи;
  merged — клітинка розтягнута на кілька груп;
  shared_lecture — потік/спільна лекція;
  full_document — якщо весь документ для однієї групи.

PARSED_EVENTS:
У кожній клітинці може бути кілька занять.
Розбий їх на parsed_events.

subject:
- тільки назва предмета;
- без викладача, аудиторії, типу, групи, підгрупи, часу.

event_type:
lecture, laboratory, practice, seminar, consultation, exam, credit, class

subgroup:
- "1", "2", "3" тільки якщо явно написано підгр. 1 / підгрупа 1;
- "1 півпара" НЕ є підгрупою;
- півпару залиш у source_text.

week_pattern:
- чисельник / чис. / н/пар / непарні => odd
- знаменник / знам. / парні => even
- 1-15 без парності або без позначки => weekly
- якщо неясно => unknown

scope:
- subgroup, якщо подія для конкретної підгрупи;
- group, якщо для всієї групи;
- stream, якщо потік/merged лекція;
- faculty, якщо загальнофакультетська;
- elective, якщо вибіркова.

ВАЖЛИВО:
Навіть якщо користувач просить "{group_name}", не відкидай інші клітинки.
Backend сам відфільтрує їх по координатах.
Твоя відповідальність — правильні координати груп, рядків і клітинок.

OCR-текст сторінки для допомоги:
{page_text[:18000]}
""".strip()

        content = [
            {"type": "input_text", "text": prompt},
            {
                "type": "input_image",
                "image_url": f"data:{image['mime_type']};base64,{image['base64']}",
            },
        ]

        return self._call_json_schema(
            content=content,
            schema_name="ai_coordinate_table_page",
            schema=self._table_page_schema(),
        )

    def _read_text_tables(
        self,
        extraction: dict[str, Any],
        group_name: str,
        subgroup: str,
    ) -> dict[str, Any]:
        text_context = extraction.get("text_context") or ""
        chunks = self._split_text(text_context)

        table_pages = []
        warnings = []

        if not chunks:
            return {
                "table_pages": [],
                "warnings": ["У файлі не знайдено тексту для аналізу."],
                "document_analysis": {
                    "schedule_kind": "text",
                    "best_strategy": "ai_text_table_geometry",
                    "target_group": group_name,
                    "target_subgroup": subgroup,
                },
            }

        for index, chunk in enumerate(chunks, start=1):
            prompt = f"""
Ти аналізуєш текстову/Excel/DOCX таблицю розкладу.

Потрібна група користувача: "{group_name}"
Потрібна підгрупа: "{subgroup or 'не вказана'}"

Твоє завдання — побудувати логічну геометрію таблиці:
- groups з x1-x2;
- rows з y1-y2, днем, парою, часом;
- cells з x1-x2-y1-y2 і parsed_events.

Якщо це текстова таблиця з колонками через "|", задай умовні координати:
- службові колонки день/пара/час можуть бути x=0.00-0.20;
- групи розподіли рівномірно зліва направо;
- клітинка конкретної групи має перетинати тільки її колонку;
- merged/потік має перетинати всі групи, для яких він спільний.

Не фільтруй події за групою. Backend сам відфільтрує по координатах.

Текст:
{chunk}
""".strip()

            result = self._call_json_schema(
                content=[{"type": "input_text", "text": prompt}],
                schema_name=f"ai_text_coordinate_table_{index}",
                schema=self._table_page_schema(),
            )

            result["page_number"] = index
            table_pages.append(result)
            warnings.extend(result.get("warnings", []))

        return {
            "table_pages": table_pages,
            "warnings": list(dict.fromkeys(warnings)),
            "document_analysis": {
                "schedule_kind": "text_coordinate_table",
                "best_strategy": "ai_text_table_geometry_then_backend_group_intersection",
                "target_group": group_name,
                "target_subgroup": subgroup,
            },
        }

    def _call_json_schema(
        self,
        content: list[dict[str, Any]],
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        response = self.client.responses.create(
            model=self.model,
            input=[{"role": "user", "content": content}],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
            temperature=0,
        )

        return json.loads(response.output_text)

    def _table_page_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "page_number": {"type": "integer"},
                "page_analysis": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "has_table": {"type": "boolean"},
                        "target_group_found": {"type": "boolean"},
                        "detected_group_headers": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "layout_description": {"type": "string"},
                    },
                    "required": [
                        "has_table",
                        "target_group_found",
                        "detected_group_headers",
                        "layout_description",
                    ],
                },
                "groups": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "name": {"type": "string"},
                            "x1": {"type": "number"},
                            "x2": {"type": "number"},
                        },
                        "required": ["name", "x1", "x2"],
                    },
                },
                "rows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "row_id": {"type": "string"},
                            "day_of_week": {
                                "type": "string",
                                "enum": ["MO", "TU", "WE", "TH", "FR", "SA", "SU", ""],
                            },
                            "pair_number": {"type": "integer"},
                            "start_time": {"type": "string"},
                            "end_time": {"type": "string"},
                            "y1": {"type": "number"},
                            "y2": {"type": "number"},
                        },
                        "required": [
                            "row_id",
                            "day_of_week",
                            "pair_number",
                            "start_time",
                            "end_time",
                            "y1",
                            "y2",
                        ],
                    },
                },
                "cells": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "cell_id": {"type": "string"},
                            "row_id": {"type": "string"},
                            "text": {"type": "string"},
                            "x1": {"type": "number"},
                            "x2": {"type": "number"},
                            "y1": {"type": "number"},
                            "y2": {"type": "number"},
                            "source_cell_type": {
                                "type": "string",
                                "enum": [
                                    "exact",
                                    "merged",
                                    "shared_lecture",
                                    "full_document",
                                ],
                            },
                            "parsed_events": {
                                "type": "array",
                                "items": self._parsed_event_schema(),
                            },
                        },
                        "required": [
                            "cell_id",
                            "row_id",
                            "text",
                            "x1",
                            "x2",
                            "y1",
                            "y2",
                            "source_cell_type",
                            "parsed_events",
                        ],
                    },
                },
                "warnings": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "page_number",
                "page_analysis",
                "groups",
                "rows",
                "cells",
                "warnings",
            ],
        }

    def _parsed_event_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "subject": {"type": "string"},
                "event_type": {
                    "type": "string",
                    "enum": [
                        "lecture",
                        "laboratory",
                        "practice",
                        "seminar",
                        "consultation",
                        "exam",
                        "credit",
                        "class",
                    ],
                },
                "teacher": {"type": "string"},
                "room": {"type": "string"},
                "online_url": {"type": "string"},
                "subgroup": {"type": "string"},
                "subgroup_evidence": {
                    "type": "string",
                    "enum": ["explicit", "none", "uncertain"],
                },
                "week_pattern": {
                    "type": "string",
                    "enum": ["weekly", "odd", "even", "custom", "unknown"],
                },
                "week_range": {"type": "string"},
                "scope": {
                    "type": "string",
                    "enum": [
                        "subgroup",
                        "group",
                        "stream",
                        "faculty",
                        "elective",
                        "unknown",
                    ],
                },
                "source_text": {"type": "string"},
                "confidence": {"type": "number"},
                "needs_review": {"type": "boolean"},
            },
            "required": [
                "subject",
                "event_type",
                "teacher",
                "room",
                "online_url",
                "subgroup",
                "subgroup_evidence",
                "week_pattern",
                "week_range",
                "scope",
                "source_text",
                "confidence",
                "needs_review",
            ],
        }

    def _split_text(self, text: str) -> list[str]:
        text = str(text or "").strip()

        if not text:
            return []

        if len(text) <= self.TEXT_CHUNK_LIMIT:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.TEXT_CHUNK_LIMIT
            chunks.append(text[start:end])
            start = end

        return chunks
