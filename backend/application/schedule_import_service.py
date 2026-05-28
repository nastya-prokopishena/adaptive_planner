import re
import uuid
from collections import defaultdict
from typing import Any, Optional

from backend.application.schedule_ai_reader_service import ScheduleAIReaderService
from backend.application.schedule_file_extractor_service import ScheduleFileExtractorService


class ScheduleImportService:
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

    MIN_CELL_GROUP_OVERLAP_RATIO = 0.12

    def __init__(self):
        self.file_extractor = ScheduleFileExtractorService()
        self.ai_reader = ScheduleAIReaderService()

    def build_preview_from_file(
        self,
        filename: str,
        file_bytes: bytes,
        group_name: Optional[str] = None,
        subgroup: Optional[str] = None,
    ) -> dict[str, Any]:
        target_group = (group_name or "").strip()
        target_subgroup = (subgroup or "").strip()

        if not target_group:
            return self._error_response("Вкажи групу для розпізнавання розкладу.")

        try:
            extraction = self.file_extractor.extract(
                filename=filename,
                file_bytes=file_bytes,
                group_name=target_group,
            )

            ai_result = self.ai_reader.read_schedule(
                extraction=extraction,
                group_name=target_group,
                subgroup=target_subgroup,
            )

            events = self._events_from_ai_table_geometry(
                ai_result=ai_result,
                target_group=target_group,
                target_subgroup=target_subgroup,
            )

            response = self._build_response(events)
            response["warnings"] = self._build_warnings(ai_result, events)
            response["extraction_debug"] = extraction.get("debug", {})
            response["document_analysis"] = ai_result.get("document_analysis", {})
            response["parser_mode"] = "ai_table_geometry_backend_group_intersection"
            response["raw_ai_result"] = ai_result

            return response

        except Exception as exc:
            return self._error_response(str(exc))

    def build_preview_from_text(
        self,
        raw_text: str,
        group_name: Optional[str] = None,
        subgroup: Optional[str] = None,
    ) -> dict[str, Any]:
        target_group = (group_name or "").strip()
        target_subgroup = (subgroup or "").strip()

        if not target_group:
            return self._error_response("Вкажи групу для розпізнавання розкладу.")

        try:
            extraction = self.file_extractor.extract_text_input(raw_text)

            ai_result = self.ai_reader.read_schedule(
                extraction=extraction,
                group_name=target_group,
                subgroup=target_subgroup,
            )

            events = self._events_from_ai_table_geometry(
                ai_result=ai_result,
                target_group=target_group,
                target_subgroup=target_subgroup,
            )

            response = self._build_response(events)
            response["warnings"] = self._build_warnings(ai_result, events)
            response["extraction_debug"] = extraction.get("debug", {})
            response["document_analysis"] = ai_result.get("document_analysis", {})
            response["parser_mode"] = "ai_text_table_geometry_backend_group_intersection"
            response["raw_ai_result"] = ai_result

            return response

        except Exception as exc:
            return self._error_response(str(exc))

    def _events_from_ai_table_geometry(
        self,
        ai_result: dict[str, Any],
        target_group: str,
        target_subgroup: str,
    ) -> list[dict[str, Any]]:
        result = []
        previous_target_group_box = None

        for page in ai_result.get("table_pages", []):
            page_number = int(page.get("page_number") or 0)

            target_group_box = self._find_target_group_box(
                groups=page.get("groups", []),
                target_group=target_group,
            )

            if target_group_box:
                previous_target_group_box = target_group_box
            elif previous_target_group_box:
                target_group_box = previous_target_group_box
            else:
                continue

            rows_by_id = {str(row.get("row_id")): row for row in page.get("rows", [])}

            for cell in page.get("cells", []):
                if not self._cell_intersects_group(cell, target_group_box):
                    continue

                row = rows_by_id.get(str(cell.get("row_id")), {})

                for parsed_event in cell.get("parsed_events", []):
                    event = self._build_event_from_cell(
                        parsed_event=parsed_event,
                        cell=cell,
                        row=row,
                        page_number=page_number,
                        target_group=target_group,
                        target_group_box=target_group_box,
                    )

                    if not self._is_real_study_event(event):
                        continue

                    if not self._matches_subgroup(event, target_subgroup):
                        continue

                    event = self._fill_missing_time(event)
                    event = self._mark_review_status(event)

                    result.append(event)

        result = self._resolve_same_slot_alternation(result)
        result = self._deduplicate_events(result)

        result.sort(
            key=lambda item: (
                self._day_order(item.get("day_of_week")),
                item.get("start_time") or "99:99",
                item.get("pair_number") or 99,
                item.get("subject") or "",
                item.get("event_type") or "",
                item.get("week_pattern") or "",
                item.get("subgroup") or "",
            )
        )

        return result

    def _find_target_group_box(
        self,
        groups: list[dict[str, Any]],
        target_group: str,
    ) -> dict[str, Any] | None:
        target_norm = self._normalize_group(target_group)

        for group in groups:
            group_name = group.get("name") or ""
            if self._normalize_group(group_name) == target_norm:
                return {
                    "name": group_name,
                    "x1": self._safe_coord(group.get("x1")),
                    "x2": self._safe_coord(group.get("x2")),
                }

        return None

    def _cell_intersects_group(
        self,
        cell: dict[str, Any],
        group_box: dict[str, Any],
    ) -> bool:
        cell_x1 = self._safe_coord(cell.get("x1"))
        cell_x2 = self._safe_coord(cell.get("x2"))
        group_x1 = self._safe_coord(group_box.get("x1"))
        group_x2 = self._safe_coord(group_box.get("x2"))

        if cell_x2 <= cell_x1 or group_x2 <= group_x1:
            return False

        overlap_left = max(cell_x1, group_x1)
        overlap_right = min(cell_x2, group_x2)
        overlap = max(0.0, overlap_right - overlap_left)

        group_width = max(group_x2 - group_x1, 0.0001)
        overlap_ratio = overlap / group_width

        return overlap_ratio >= self.MIN_CELL_GROUP_OVERLAP_RATIO

    def _build_event_from_cell(
        self,
        parsed_event: dict[str, Any],
        cell: dict[str, Any],
        row: dict[str, Any],
        page_number: int,
        target_group: str,
        target_group_box: dict[str, Any],
    ) -> dict[str, Any]:
        source_cell_type = self._normalize_source_cell_type(cell.get("source_cell_type"))

        if source_cell_type == "exact":
            group_evidence = "target_group_column"
        elif source_cell_type in {"merged", "shared_lecture"}:
            group_evidence = "stream_or_shared_cell"
        else:
            group_evidence = "single_group_document"

        pair_number = self._safe_pair_number(row.get("pair_number"))
        start_time = self._normalize_time(row.get("start_time"))
        end_time = self._normalize_time(row.get("end_time"))

        event = {
            "id": str(uuid.uuid4()),
            "subject": self._clean_subject(parsed_event.get("subject")),
            "event_type": self._normalize_event_type(parsed_event.get("event_type")),
            "day_of_week": self._normalize_day(row.get("day_of_week")),
            "pair_number": pair_number or 0,
            "start_time": start_time,
            "end_time": end_time,
            "teacher": self._clean_text(parsed_event.get("teacher")),
            "room": self._clean_text(parsed_event.get("room")),
            "online_url": self._clean_text(parsed_event.get("online_url")),
            "group_name": target_group,
            "source_group_text": self._clean_text(target_group_box.get("name")),
            "source_cell_type": source_cell_type,
            "group_evidence": group_evidence,
            "subgroup": self._normalize_subgroup_value(parsed_event.get("subgroup")),
            "subgroup_evidence": self._normalize_subgroup_evidence(
                parsed_event.get("subgroup_evidence")
            ),
            "week_pattern": self._normalize_week_pattern(parsed_event.get("week_pattern")),
            "week_range": self._clean_text(parsed_event.get("week_range")),
            "scope": self._normalize_scope(parsed_event.get("scope")),
            "source_text": self._clean_text(
                parsed_event.get("source_text") or cell.get("text") or ""
            ),
            "source_page": page_number,
            "cell_coordinates": {
                "x1": self._safe_coord(cell.get("x1")),
                "x2": self._safe_coord(cell.get("x2")),
                "y1": self._safe_coord(cell.get("y1")),
                "y2": self._safe_coord(cell.get("y2")),
                "target_group_x1": self._safe_coord(target_group_box.get("x1")),
                "target_group_x2": self._safe_coord(target_group_box.get("x2")),
            },
            "confidence": self._safe_confidence(parsed_event.get("confidence")),
            "needs_review": bool(parsed_event.get("needs_review", False)),
        }

        return event

    def _matches_subgroup(self, event: dict[str, Any], target_subgroup: str) -> bool:
        target = self._normalize_subgroup_value(target_subgroup)

        if not target:
            return True

        event_subgroup = self._normalize_subgroup_value(event.get("subgroup"))
        event_type = event.get("event_type")
        scope = event.get("scope")
        subgroup_evidence = event.get("subgroup_evidence")

        if event_subgroup:
            return event_subgroup == target

        if event_type == "lecture":
            return True

        if scope in {"group", "stream", "faculty", "elective"}:
            return True

        if subgroup_evidence == "none":
            event["needs_review"] = True
            event["confidence"] = min(event.get("confidence", 0.9), 0.75)
            return True

        return False

    def _resolve_same_slot_alternation(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped = defaultdict(list)

        for event in events:
            key = "|".join(
                [
                    event.get("day_of_week") or "",
                    event.get("start_time") or "",
                    event.get("end_time") or "",
                    str(event.get("pair_number") or ""),
                    event.get("subgroup") or "",
                ]
            )

            grouped[key].append(event)

        for items in grouped.values():
            weekly_items = [item for item in items if item.get("week_pattern") == "weekly"]

            if len(weekly_items) < 2:
                continue

            explicit_subgroups = {
                item.get("subgroup") for item in weekly_items if item.get("subgroup")
            }

            if len(explicit_subgroups) > 1:
                continue

            weekly_items.sort(
                key=lambda item: (
                    0 if item.get("source_cell_type") == "shared_lecture" else 1,
                    0 if item.get("event_type") == "lecture" else 1,
                    item.get("subject") or "",
                    item.get("teacher") or "",
                )
            )

            weekly_items[0]["week_pattern"] = "odd"
            weekly_items[0]["needs_review"] = True
            weekly_items[0]["confidence"] = min(weekly_items[0].get("confidence", 0.9), 0.8)

            weekly_items[1]["week_pattern"] = "even"
            weekly_items[1]["needs_review"] = True
            weekly_items[1]["confidence"] = min(weekly_items[1].get("confidence", 0.9), 0.8)

            for item in weekly_items[2:]:
                item["needs_review"] = True
                item["confidence"] = min(item.get("confidence", 0.9), 0.7)

        return events

    def _fill_missing_time(self, event: dict[str, Any]) -> dict[str, Any]:
        pair_number = event.get("pair_number")

        if pair_number and (not event.get("start_time") or not event.get("end_time")):
            pair_time = self.DEFAULT_PAIR_TIMES.get(pair_number)

            if pair_time:
                event["start_time"] = event.get("start_time") or pair_time[0]
                event["end_time"] = event.get("end_time") or pair_time[1]
                event["needs_review"] = True
                event["confidence"] = min(event.get("confidence", 0.9), 0.85)

        return event

    def _mark_review_status(self, event: dict[str, Any]) -> dict[str, Any]:
        if not event.get("day_of_week"):
            event["needs_review"] = True
            event["confidence"] = min(event.get("confidence", 0.9), 0.55)

        if not event.get("start_time") or not event.get("end_time"):
            event["needs_review"] = True
            event["confidence"] = min(event.get("confidence", 0.9), 0.65)

        if event.get("week_pattern") in {"unknown", "custom"}:
            event["needs_review"] = True

        return event

    def _deduplicate_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique = {}

        for event in events:
            key = "|".join(
                [
                    event.get("day_of_week") or "",
                    event.get("start_time") or "",
                    event.get("end_time") or "",
                    str(event.get("pair_number") or ""),
                    self._normalize_text(event.get("subject") or ""),
                    event.get("event_type") or "",
                    event.get("subgroup") or "",
                    event.get("week_pattern") or "",
                    event.get("week_range") or "",
                    self._normalize_text(event.get("teacher") or ""),
                    self._normalize_text(event.get("room") or ""),
                ]
            )

            if key not in unique:
                unique[key] = event
            elif event.get("confidence", 0) > unique[key].get("confidence", 0):
                unique[key] = event

        return list(unique.values())

    def _is_real_study_event(self, event: dict[str, Any]) -> bool:
        subject = self._clean_text(event.get("subject")).lower()

        if not subject or len(subject) < 3:
            return False

        ignored = {
            "розклад",
            "розклад занять",
            "затверджую",
            "декан",
            "проректор",
            "директор",
            "начальник",
            "примітки",
            "день",
            "пара",
            "час",
            "учбові групи",
            "дввс",
        }

        if subject in ignored:
            return False

        bad_parts = [
            "міністерство освіти",
            "навчальний рік",
            "семестр",
            "декан факультету",
            "львівський національний",
        ]

        if any(part in subject for part in bad_parts):
            return False

        return True

    def _build_warnings(self, ai_result: dict[str, Any], events: list[dict[str, Any]]) -> list[str]:
        warnings = []

        warnings.extend(ai_result.get("warnings", []))

        document_analysis = ai_result.get("document_analysis", {})
        warnings.extend(document_analysis.get("warnings", []))

        if not events:
            warnings.append("Не знайдено подій, які перетинають колонку потрібної групи.")

        review_count = len([event for event in events if event.get("needs_review")])

        if review_count:
            warnings.append(f"{review_count} подій потребують перевірки перед імпортом.")

        return list(dict.fromkeys([item for item in warnings if item]))

    def _normalize_event_type(self, value: Any) -> str:
        text = str(value or "").lower().strip().replace(".", "")

        if "лек" in text or text == "л":
            return "lecture"

        if "лаб" in text:
            return "laboratory"

        if "практ" in text or "прс" in text or text == "пр":
            return "practice"

        if "сем" in text:
            return "seminar"

        if "конс" in text:
            return "consultation"

        if "іспит" in text or "екзамен" in text:
            return "exam"

        if "залік" in text:
            return "credit"

        return "class"

    def _normalize_week_pattern(self, value: Any) -> str:
        text = str(value or "").lower().strip()

        if "непар" in text or "н/пар" in text or "чис" in text or text == "odd":
            return "odd"

        if "парн" in text or "знам" in text or text == "even":
            return "even"

        if text in {"custom", "unknown"}:
            return text

        return "weekly"

    def _normalize_scope(self, value: Any) -> str:
        text = str(value or "").lower().strip()
        allowed = {"subgroup", "group", "stream", "faculty", "elective", "unknown"}
        return text if text in allowed else "group"

    def _normalize_source_cell_type(self, value: Any) -> str:
        text = str(value or "").lower().strip()
        allowed = {"exact", "merged", "shared_lecture", "full_document"}
        return text if text in allowed else "exact"

    def _normalize_subgroup_evidence(self, value: Any) -> str:
        text = str(value or "").lower().strip()
        allowed = {"explicit", "none", "uncertain"}
        return text if text in allowed else "none"

    def _normalize_day(self, value: Any) -> str:
        text = str(value or "").upper().strip()

        if text in {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}:
            return text

        lowered = str(value or "").lower()
        lowered = lowered.replace("’", "'").replace("ʼ", "'").replace("`", "'")

        if "понед" in lowered or lowered == "пн":
            return "MO"

        if "вівт" in lowered or "вiвт" in lowered or lowered == "вт":
            return "TU"

        if "серед" in lowered or lowered == "ср":
            return "WE"

        if "четв" in lowered or lowered == "чт":
            return "TH"

        if "п'ят" in lowered or "пят" in lowered or lowered == "пт":
            return "FR"

        if "суб" in lowered or lowered == "сб":
            return "SA"

        if "нед" in lowered or lowered == "нд":
            return "SU"

        return ""

    def _normalize_time(self, value: Any) -> str:
        text = str(value or "").strip().replace(".", ":").replace(" ", "")

        if not text:
            return ""

        compact_match = re.fullmatch(r"(\d{1,2})(\d{2})", text)

        if compact_match:
            text = f"{compact_match.group(1)}:{compact_match.group(2)}"

        match = re.fullmatch(r"(\d{1,2}):(\d{2})", text)

        if not match:
            return ""

        hours = int(match.group(1))
        minutes = int(match.group(2))

        if hours > 23 or minutes > 59:
            return ""

        return f"{hours:02d}:{minutes:02d}"

    def _safe_pair_number(self, value: Any) -> int | None:
        match = re.search(r"\d+", str(value or ""))

        if not match:
            return None

        number = int(match.group(0))
        return number if 1 <= number <= 12 else None

    def _normalize_group(self, value: Any) -> str:
        text = str(value or "").lower()
        text = re.sub(r"[\s\-–—_.'’ʼ`]", "", text)
        text = text.replace("і", "i").replace("ї", "i").replace("є", "e").replace("ґ", "g")
        return text.strip()

    def _normalize_subgroup_value(self, value: Any) -> str:
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
        return match.group(0) if match else ""

    def _clean_subject(self, value: Any) -> str:
        text = self._clean_text(value)

        text = re.sub(
            r"^\(?\s*(лаб|лек|лекція|практ|практика|сем|прс|потік)\.?\s*\)?",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\b(лаб|лек|лекція|практ|практика|сем|прс)\.?\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        )

        return self._clean_text(text).strip(" .,:;-")

    def _clean_text(self, value: Any) -> str:
        text = str(value or "")
        text = text.replace("\r", " ").replace("\n", " ").replace("\u00a0", " ")
        text = text.replace("￾", "-")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _normalize_text(self, value: Any) -> str:
        text = str(value or "").lower()
        text = re.sub(r"[\s\-–—_.'’ʼ`]", "", text)
        text = text.replace("і", "i").replace("ї", "i").replace("є", "e").replace("ґ", "g")
        return text.strip()

    def _safe_confidence(self, value: Any) -> float:
        try:
            confidence = float(value)
        except Exception:
            confidence = 0.8

        return round(max(0.0, min(confidence, 1.0)), 2)

    def _safe_coord(self, value: Any) -> float:
        try:
            coord = float(value)
        except Exception:
            coord = 0.0

        return max(0.0, min(coord, 1.0))

    def _day_order(self, day_code: str) -> int:
        return {
            "MO": 1,
            "TU": 2,
            "WE": 3,
            "TH": 4,
            "FR": 5,
            "SA": 6,
            "SU": 7,
        }.get(day_code, 99)

    def _build_response(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "import_id": str(uuid.uuid4()),
            "total_found": len(events),
            "events": events,
        }

    def _error_response(self, message: str) -> dict[str, Any]:
        return {
            "import_id": str(uuid.uuid4()),
            "total_found": 0,
            "events": [],
            "warnings": [message],
            "error": message,
            "details": message,
        }
