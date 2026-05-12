import re
from typing import Any


class ScheduleTextParserService:
    DEFAULT_PAIR_TIMES = {
        1: ("08:30", "09:50"),
        2: ("10:10", "11:30"),
        3: ("11:50", "13:10"),
        4: ("13:30", "14:50"),
        5: ("15:05", "16:25"),
        6: ("16:40", "18:00"),
        7: ("18:10", "19:30"),
        8: ("19:40", "21:00"),
    }

    DAY_MAP = {
        "понеділок": "MO",
        "пн": "MO",
        "вівторок": "TU",
        "вт": "TU",
        "середа": "WE",
        "ср": "WE",
        "четвер": "TH",
        "чт": "TH",
        "п’ятниця": "FR",
        "п'ятниця": "FR",
        "п`ятниця": "FR",
        "пятниця": "FR",
        "пт": "FR",
        "субота": "SA",
        "сб": "SA",
        "неділя": "SU",
        "нд": "SU",
        "mo": "MO",
        "tu": "TU",
        "we": "WE",
        "th": "TH",
        "fr": "FR",
        "sa": "SA",
        "su": "SU",
    }

    TYPE_MAP = {
        "лекція": "lecture",
        "лекцiя": "lecture",
        "лек": "lecture",
        "л": "lecture",
        "lecture": "lecture",
        "лабораторна": "laboratory",
        "лабораторне": "laboratory",
        "лаб": "laboratory",
        "laboratory": "laboratory",
        "практична": "practice",
        "практика": "practice",
        "прс": "practice",
        "пр": "practice",
        "practice": "practice",
        "семінар": "seminar",
        "семiнар": "seminar",
        "сем": "seminar",
        "seminar": "seminar",
        "консультація": "consultation",
        "іспит": "exam",
        "екзамен": "exam",
        "залік": "credit",
        "class": "class",
    }

    WEEK_MAP = {
        "щотижня": "weekly",
        "кожного тижня": "weekly",
        "weekly": "weekly",
        "парні": "even",
        "парний": "even",
        "знаменник": "even",
        "знам": "even",
        "even": "even",
        "непарні": "odd",
        "непарний": "odd",
        "чисельник": "odd",
        "чис": "odd",
        "odd": "odd",
    }

    def parse_ai_text(
        self,
        ai_text: str,
        target_group: str,
        target_subgroup: str = "",
    ) -> list[dict[str, Any]]:
        if not ai_text or not ai_text.strip():
            return []

        lowered = ai_text.lower()

        if "подій не знайдено" in lowered and "подія:" not in lowered and "|" not in ai_text:
            return []

        events = []
        events.extend(self._parse_block_format(ai_text, target_group, target_subgroup))
        events.extend(self._parse_pipe_table_format(ai_text, target_group, target_subgroup))

        return self._deduplicate(events)

    def _parse_block_format(
        self,
        ai_text: str,
        target_group: str,
        target_subgroup: str,
    ) -> list[dict[str, Any]]:
        blocks = self._split_event_blocks(ai_text)
        events = []

        for block in blocks:
            event = self._parse_block(block, target_group, target_subgroup)
            if event:
                events.append(event)

        return events

    def _split_event_blocks(self, text: str) -> list[str]:
        normalized = text.replace("\r", "\n")
        parts = re.split(r"(?i)\bПОДІЯ\s*:", normalized)
        return [part.strip() for part in parts if part.strip()]

    def _parse_block(
        self,
        block: str,
        target_group: str,
        target_subgroup: str,
    ) -> dict[str, Any] | None:
        fields = self._extract_fields(block)
        subject = fields.get("предмет", "").strip()

        if not subject:
            return None

        return self._build_event_from_fields(fields, block, target_group, target_subgroup)

    def _extract_fields(self, block: str) -> dict[str, str]:
        result = {}

        aliases = {
            "день": "день",
            "пара": "пара",
            "час": "час",
            "предмет": "предмет",
            "тип": "тип",
            "викладач": "викладач",
            "аудиторія": "аудиторія",
            "аудиторiя": "аудиторія",
            "ауд": "аудиторія",
            "група": "група",
            "підгрупа": "підгрупа",
            "пiдгрупа": "підгрупа",
            "тижні": "тижні",
            "тижнi": "тижні",
            "джерело": "джерело",
        }

        lines = [line.strip() for line in block.splitlines() if line.strip()]
        current_key = None

        for line in lines:
            match = re.match(r"^([^:]+):\s*(.*)$", line)

            if match:
                raw_key = match.group(1).strip().lower()
                value = match.group(2).strip()
                key = aliases.get(raw_key)

                if key:
                    result[key] = value
                    current_key = key
                else:
                    current_key = None
            elif current_key:
                result[current_key] += " " + line.strip()

        return result

    def _parse_pipe_table_format(
        self,
        ai_text: str,
        target_group: str,
        target_subgroup: str,
    ) -> list[dict[str, Any]]:
        events = []
        lines = [line.strip() for line in ai_text.splitlines() if line.strip()]

        for line in lines:
            if "|" not in line:
                continue

            if self._is_separator_line(line):
                continue

            lowered = line.lower()

            if "день" in lowered and "предмет" in lowered:
                continue

            parts = [part.strip() for part in line.split("|")]

            if len(parts) < 8:
                continue

            fields = {
                "день": parts[0] if len(parts) > 0 else "",
                "пара": parts[1] if len(parts) > 1 else "",
                "час": parts[2] if len(parts) > 2 else "",
                "предмет": parts[3] if len(parts) > 3 else "",
                "тип": parts[4] if len(parts) > 4 else "",
                "викладач": parts[5] if len(parts) > 5 else "",
                "аудиторія": parts[6] if len(parts) > 6 else "",
                "група": parts[7] if len(parts) > 7 else target_group,
                "підгрупа": parts[8] if len(parts) > 8 else "",
                "тижні": parts[9] if len(parts) > 9 else "щотижня",
                "джерело": parts[10] if len(parts) > 10 else line,
            }

            event = self._build_event_from_fields(fields, line, target_group, target_subgroup)

            if event:
                events.append(event)

        return events

    def _is_separator_line(self, line: str) -> bool:
        cleaned = line.replace("|", "").replace("-", "").replace("—", "").replace(":", "").strip()
        return not cleaned

    def _build_event_from_fields(
        self,
        fields: dict[str, str],
        source_block: str,
        target_group: str,
        target_subgroup: str,
    ) -> dict[str, Any] | None:
        subject = fields.get("предмет", "").strip()

        if not subject or subject.lower() in {"предмет", "-", "—"}:
            return None

        group_name = fields.get("група", "").strip() or target_group

        if target_group and group_name and not self._groups_equivalent(group_name, target_group):
            return None

        event_subgroup = self._normalize_subgroup(fields.get("підгрупа", ""))
        normalized_target_subgroup = self._normalize_subgroup(target_subgroup)

        if normalized_target_subgroup and event_subgroup and event_subgroup != normalized_target_subgroup:
            return None

        day_of_week = self._normalize_day(fields.get("день", ""))
        pair_number = self._safe_pair_number(fields.get("пара", ""))
        start_time, end_time = self._parse_time(fields.get("час", ""), pair_number)

        return {
            "subject": subject,
            "event_type": self._normalize_event_type(fields.get("тип", "")),
            "day_of_week": day_of_week,
            "pair_number": pair_number,
            "start_time": start_time,
            "end_time": end_time,
            "teacher": fields.get("викладач", "").strip(),
            "room": fields.get("аудиторія", "").strip(),
            "group_name": target_group or group_name,
            "source_group_text": group_name,
            "subgroup": event_subgroup,
            "week_pattern": self._normalize_week_pattern(fields.get("тижні", "")),
            "scope": "subgroup" if event_subgroup else "group",
            "source_text": fields.get("джерело", source_block).strip(),
            "confidence": 0.9,
            "needs_review": False if day_of_week and start_time and end_time else True,
        }

    def _normalize_day(self, value: str) -> str:
        text = str(value or "").lower().strip()
        text = text.replace("’", "'").replace("`", "'")

        for raw, code in self.DAY_MAP.items():
            if raw in text:
                return code

        return ""

    def _normalize_event_type(self, value: str) -> str:
        text = str(value or "").lower().strip()
        text = text.replace(".", "")

        for raw, code in self.TYPE_MAP.items():
            if raw in text:
                return code

        return "class"

    def _normalize_week_pattern(self, value: str) -> str:
        text = str(value or "").lower().strip()

        for raw, code in self.WEEK_MAP.items():
            if raw in text:
                return code

        return "weekly"

    def _parse_time(self, value: str, pair_number: int | None) -> tuple[str, str]:
        text = str(value or "").strip()
        text = text.replace("—", "-").replace("–", "-")
        text = text.replace(".", ":")

        match = re.search(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", text)

        if match:
            return self._normalize_time(match.group(1)), self._normalize_time(match.group(2))

        compact_match = re.search(r"(\d{1,2})(\d{2})\s*-\s*(\d{1,2})(\d{2})", text)

        if compact_match:
            start = f"{compact_match.group(1)}:{compact_match.group(2)}"
            end = f"{compact_match.group(3)}:{compact_match.group(4)}"
            return self._normalize_time(start), self._normalize_time(end)

        if pair_number and pair_number in self.DEFAULT_PAIR_TIMES:
            return self.DEFAULT_PAIR_TIMES[pair_number]

        return "", ""

    def _normalize_time(self, value: str) -> str:
        text = str(value or "").strip().replace(".", ":")

        match = re.fullmatch(r"(\d{1,2}):(\d{2})", text)

        if not match:
            return ""

        hours = int(match.group(1))
        minutes = int(match.group(2))

        if hours > 23 or minutes > 59:
            return ""

        return f"{hours:02d}:{minutes:02d}"

    def _safe_pair_number(self, value: Any) -> int | None:
        text = str(value or "").strip()
        match = re.search(r"\d+", text)

        if not match:
            return None

        number = int(match.group(0))
        return number if 1 <= number <= 12 else None

    def _normalize_subgroup(self, value: Any) -> str:
        text = str(value or "").lower().strip()

        if not text or text in {"-", "—", "немає", "вся група", "усі", "всі"}:
            return ""

        text = text.replace("підгр.", "")
        text = text.replace("підгр", "")
        text = text.replace("підгрупа", "")
        text = text.replace("гр.", "")
        text = text.replace("гр", "")
        text = text.replace("група", "")
        text = text.replace("півпара", "")
        text = text.replace("півп.", "")
        text = text.replace("півп", "")
        text = text.replace(".", "")
        text = text.replace(" ", "")

        match = re.search(r"\d+", text)

        if match:
            return match.group(0)

        return text

    def _groups_equivalent(self, first: str, second: str) -> bool:
        return self._normalize_group(first) == self._normalize_group(second)

    def _normalize_group(self, value: str) -> str:
        text = str(value or "").lower()
        text = text.replace(" ", "")
        text = text.replace("-", "")
        text = text.replace("–", "")
        text = text.replace("—", "")
        text = text.replace("_", "")
        text = text.replace(".", "")
        text = text.replace("`", "")
        text = text.replace("'", "")
        text = text.replace("’", "")
        text = text.replace("ʼ", "")

        replacements = {
            "і": "i",
            "ї": "i",
            "є": "e",
            "ґ": "g",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text.strip()

    def _deduplicate(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique = {}

        for event in events:
            key = "|".join(
                [
                    event.get("day_of_week") or "",
                    str(event.get("pair_number") or ""),
                    event.get("start_time") or "",
                    event.get("end_time") or "",
                    self._normalize_text(event.get("subject") or ""),
                    event.get("subgroup") or "",
                    event.get("week_pattern") or "",
                ]
            )

            if key not in unique:
                unique[key] = event

        return list(unique.values())

    def _normalize_text(self, value: str) -> str:
        text = str(value or "").lower()
        text = re.sub(r"\s+", "", text)
        text = text.replace("-", "").replace("–", "").replace("—", "")
        return text