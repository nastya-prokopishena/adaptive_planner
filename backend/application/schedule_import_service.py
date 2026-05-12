import re
import uuid
from collections import Counter, defaultdict
from typing import Any, Optional

from backend.application.schedule_file_extractor_service import ScheduleFileExtractorService
from backend.application.schedule_ai_reader_service import ScheduleAIReaderService
from backend.application.schedule_text_parser_service import ScheduleTextParserService
from backend.application.schedule_pdf_coordinate_parser_service import SchedulePDFCoordinateParserService


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

    MAX_COORDINATE_EVENTS = 40

    def __init__(self):
        self.file_extractor = ScheduleFileExtractorService()
        self.ai_reader = ScheduleAIReaderService()
        self.text_parser = ScheduleTextParserService()
        self.pdf_coordinate_parser = SchedulePDFCoordinateParserService()

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

        extension = self._get_extension(filename)

        try:
            extraction = self.file_extractor.extract(
                filename=filename,
                file_bytes=file_bytes,
                group_name=target_group,
            )

            extraction_debug = extraction.get("debug", {})

            print("\n================ EXTRACTION DEBUG ================")
            print(extraction_debug)
            print("================ END EXTRACTION DEBUG ================\n")

            raw_ai_text = ""
            events = []

            if extension == "pdf":
                coordinate_events = self.pdf_coordinate_parser.parse_pdf(
                    file_bytes=file_bytes,
                    group_name=target_group,
                    subgroup=target_subgroup,
                )

                print("\n================ PDF COORDINATE EVENTS ================")
                print(coordinate_events)
                print("================ END PDF COORDINATE EVENTS ================\n")

                if 1 <= len(coordinate_events) <= self.MAX_COORDINATE_EVENTS:
                    events = coordinate_events
                    raw_ai_text = "PDF parsed by coordinate parser."
                else:
                    print("\n================ PDF COORDINATE PARSER FALLBACK ================")
                    print(f"Coordinate events count: {len(coordinate_events)}")
                    print("================ END PDF COORDINATE PARSER FALLBACK ================\n")

                    raw_ai_text = self.ai_reader.read_schedule(
                        extraction=extraction,
                        group_name=target_group,
                        subgroup=target_subgroup,
                    )

                    print("\n================ RAW AI TEXT FALLBACK ================")
                    print(raw_ai_text)
                    print("================ END RAW AI TEXT FALLBACK ================\n")

                    events = self.text_parser.parse_ai_text(
                        ai_text=raw_ai_text,
                        target_group=target_group,
                        target_subgroup=target_subgroup,
                    )
            else:
                raw_ai_text = self.ai_reader.read_schedule(
                    extraction=extraction,
                    group_name=target_group,
                    subgroup=target_subgroup,
                )

                print("\n================ RAW AI TEXT ================")
                print(raw_ai_text)
                print("================ END RAW AI TEXT ================\n")

                events = self.text_parser.parse_ai_text(
                    ai_text=raw_ai_text,
                    target_group=target_group,
                    target_subgroup=target_subgroup,
                )

            print("\n================ EVENTS BEFORE POSTPROCESS ================")
            print(events)
            print("================ END EVENTS BEFORE POSTPROCESS ================\n")

        except Exception as exc:
            return self._error_response(str(exc))

        events = self._post_process_events(
            events=events,
            target_group=target_group,
            target_subgroup=target_subgroup,
        )

        print("\n================ EVENTS AFTER POSTPROCESS ================")
        print(events)
        print("================ END EVENTS AFTER POSTPROCESS ================\n")

        response = self._build_response(events)
        response["raw_ai_text"] = raw_ai_text
        response["extraction_debug"] = extraction_debug

        return response

    def build_preview_from_text(
        self,
        text: str,
        group_name: Optional[str] = None,
        subgroup: Optional[str] = None,
    ) -> dict[str, Any]:
        target_group = (group_name or "").strip()
        target_subgroup = (subgroup or "").strip()

        if not target_group:
            return self._error_response("Вкажи групу для розпізнавання розкладу.")

        try:
            extraction = {
                "filename": "manual_text",
                "extension": "txt",
                "text_context": text,
                "target_context": "",
                "images": [],
                "debug": {
                    "detected_groups": [],
                    "target_group_found_in_tables": False,
                    "used_extractors": ["manual_text"],
                    "is_complex_pdf": False,
                },
            }

            raw_ai_text = self.ai_reader.read_schedule(
                extraction=extraction,
                group_name=target_group,
                subgroup=target_subgroup,
            )

            events = self.text_parser.parse_ai_text(
                ai_text=raw_ai_text,
                target_group=target_group,
                target_subgroup=target_subgroup,
            )

        except Exception as exc:
            return self._error_response(str(exc))

        events = self._post_process_events(
            events=events,
            target_group=target_group,
            target_subgroup=target_subgroup,
        )

        response = self._build_response(events)
        response["raw_ai_text"] = raw_ai_text
        response["extraction_debug"] = extraction.get("debug", {})

        return response

    def _post_process_events(
        self,
        events: list[dict[str, Any]],
        target_group: str,
        target_subgroup: str = "",
    ) -> list[dict[str, Any]]:
        normalized_events = [self._normalize_event(event) for event in events]
        pair_time_map = self._build_pair_time_map(normalized_events)

        result = []

        for event in normalized_events:
            if not self._is_real_study_event(event):
                continue

            if not self._matches_group(event, target_group):
                continue

            if not self._matches_subgroup(event, target_subgroup):
                continue

            event["group_name"] = target_group
            event = self._fill_missing_time(event, pair_time_map)
            event = self._mark_review_status(event)

            result.append(event)

        result = self._remove_hidden_other_subgroup_events(
            events=result,
            target_subgroup=target_subgroup,
        )

        result = self._fix_alternating_same_time_events(result)
        result = self._deduplicate_events(result)

        result.sort(
            key=lambda item: (
                self._day_order(item.get("day_of_week")),
                item.get("start_time") or "99:99",
                item.get("subject") or "",
                item.get("event_type") or "",
            )
        )

        return result

    def _normalize_event(self, event: dict[str, Any]) -> dict[str, Any]:
        return {
            "subject": str(event.get("subject") or "").strip(),
            "event_type": self._normalize_event_type(event.get("event_type")),
            "day_of_week": str(event.get("day_of_week") or "").strip().upper(),
            "pair_number": self._safe_pair_number(event.get("pair_number")),
            "start_time": self._normalize_time(event.get("start_time")),
            "end_time": self._normalize_time(event.get("end_time")),
            "teacher": str(event.get("teacher") or "").strip(),
            "room": str(event.get("room") or "").strip(),
            "group_name": str(event.get("group_name") or "").strip(),
            "source_group_text": str(event.get("source_group_text") or "").strip(),
            "source_cell_type": str(event.get("source_cell_type") or "exact").strip(),
            "subgroup": self._normalize_subgroup_value(event.get("subgroup")),
            "week_pattern": self._normalize_week_pattern(event.get("week_pattern")),
            "scope": str(event.get("scope") or "group").strip(),
            "source_text": str(event.get("source_text") or "").strip(),
            "confidence": self._safe_confidence(event.get("confidence", 0.9)),
            "needs_review": bool(event.get("needs_review", False)),
        }

    def _matches_group(self, event: dict[str, Any], target_group: str) -> bool:
        if not target_group:
            return True

        event_group = event.get("group_name") or ""

        if not event_group:
            return True

        normalized_event_group = self._normalize_group(event_group)
        normalized_target_group = self._normalize_group(target_group)

        return normalized_event_group == normalized_target_group

    def _matches_subgroup(self, event: dict[str, Any], target_subgroup: str) -> bool:
        if not target_subgroup:
            return True

        event_subgroup = self._normalize_subgroup_value(event.get("subgroup"))
        normalized_target = self._normalize_subgroup_value(target_subgroup)
        event_type = event.get("event_type")
        source_cell_type = event.get("source_cell_type") or "exact"

        if event_subgroup:
            return event_subgroup == normalized_target

        if event_type == "lecture":
            return True

        if event_type in {"laboratory", "practice", "seminar"}:
            return source_cell_type == "exact"

        return True

    def _remove_hidden_other_subgroup_events(
        self,
        events: list[dict[str, Any]],
        target_subgroup: str,
    ) -> list[dict[str, Any]]:
        normalized_target = self._normalize_subgroup_value(target_subgroup)

        if not normalized_target:
            return events

        slot_has_target_subgroup_event: set[str] = set()

        for event in events:
            event_type = event.get("event_type")
            event_subgroup = self._normalize_subgroup_value(event.get("subgroup"))

            if event_type not in {"laboratory", "practice", "seminar"}:
                continue

            if event_subgroup != normalized_target:
                continue

            slot_has_target_subgroup_event.add(self._slot_key(event))

        if not slot_has_target_subgroup_event:
            return events

        filtered_events = []

        for event in events:
            slot_key = self._slot_key(event)
            event_type = event.get("event_type")
            event_subgroup = self._normalize_subgroup_value(event.get("subgroup"))
            source_cell_type = event.get("source_cell_type") or "exact"

            is_laboratory_or_practice = event_type in {
                "laboratory",
                "practice",
                "seminar",
            }

            has_no_subgroup = not event_subgroup
            is_not_shared_lecture = source_cell_type != "shared_lecture"

            should_remove = (
                slot_key in slot_has_target_subgroup_event
                and is_laboratory_or_practice
                and has_no_subgroup
                and is_not_shared_lecture
            )

            if should_remove:
                print("\n================ REMOVED HIDDEN OTHER SUBGROUP EVENT ================")
                print(event)
                print("================ END REMOVED HIDDEN OTHER SUBGROUP EVENT ================\n")
                continue

            filtered_events.append(event)

        return filtered_events

    def _slot_key(self, event: dict[str, Any]) -> str:
        return "|".join(
            [
                str(event.get("day_of_week") or ""),
                str(event.get("start_time") or ""),
                str(event.get("end_time") or ""),
            ]
        )

    def _is_real_study_event(self, event: dict[str, Any]) -> bool:
        subject = str(event.get("subject") or "").strip().lower()

        if not subject:
            return False

        ignored = {
            "розклад",
            "затверджую",
            "декан",
            "проректор",
            "примітки",
            "дввс",
            "вибіркова дисципліна",
            "див. розклад гум. дисциплін",
            "дисципліни загальної підготовки",
        }

        if subject in ignored:
            return False

        if re.fullmatch(r"\d{1,2}", subject):
            return False

        if re.search(r"\d{1,2}\s*:\s*\d{2}", subject):
            return False

        return True

    def _fill_missing_time(
        self,
        event: dict[str, Any],
        pair_time_map: dict[int, tuple[str, str]],
    ) -> dict[str, Any]:
        pair_number = event.get("pair_number")
        start_time = event.get("start_time") or ""
        end_time = event.get("end_time") or ""

        if pair_number and (not start_time or not end_time):
            pair_times = pair_time_map.get(pair_number) or self.DEFAULT_PAIR_TIMES.get(pair_number)

            if pair_times:
                event["start_time"] = start_time or pair_times[0]
                event["end_time"] = end_time or pair_times[1]
                event["needs_review"] = True
                event["confidence"] = min(event.get("confidence", 0.9), 0.8)

        return event

    def _build_pair_time_map(
        self,
        events: list[dict[str, Any]],
    ) -> dict[int, tuple[str, str]]:
        candidates: dict[int, Counter] = defaultdict(Counter)

        for event in events:
            pair_number = event.get("pair_number")
            start_time = event.get("start_time")
            end_time = event.get("end_time")

            if pair_number and start_time and end_time:
                candidates[pair_number][(start_time, end_time)] += 1

        result = {}

        for pair_number, counter in candidates.items():
            most_common = counter.most_common(1)

            if most_common:
                result[pair_number] = most_common[0][0]

        return result

    def _mark_review_status(self, event: dict[str, Any]) -> dict[str, Any]:
        if not event.get("subject"):
            event["needs_review"] = True
            event["confidence"] = min(event.get("confidence", 0.9), 0.4)

        if not event.get("day_of_week"):
            event["needs_review"] = True
            event["confidence"] = min(event.get("confidence", 0.9), 0.5)

        if not event.get("start_time") or not event.get("end_time"):
            event["needs_review"] = True
            event["confidence"] = min(event.get("confidence", 0.9), 0.65)

        return event

    def _fix_alternating_same_time_events(
        self,
        events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        grouped = defaultdict(list)

        for event in events:
            grouped[self._slot_key(event)].append(event)

        for items in grouped.values():
            if len(items) < 2:
                continue

            weekly_items = [
                item for item in items
                if item.get("week_pattern") == "weekly"
            ]

            if len(weekly_items) < 2:
                continue

            explicit_subgroups = {
                str(item.get("subgroup") or "").strip()
                for item in weekly_items
                if str(item.get("subgroup") or "").strip()
            }

            if len(explicit_subgroups) > 1:
                continue

            all_have_subgroup = all(
                str(item.get("subgroup") or "").strip()
                for item in weekly_items
            )

            if all_have_subgroup:
                continue

            has_shared_lecture = any(
                item.get("source_cell_type") == "shared_lecture"
                for item in weekly_items
            )

            has_exact = any(
                item.get("source_cell_type") == "exact"
                for item in weekly_items
            )

            has_any_subgroup = any(
                str(item.get("subgroup") or "").strip()
                for item in weekly_items
            )

            can_alternate = False

            if has_shared_lecture and has_exact and not has_any_subgroup:
                can_alternate = True
            elif not has_shared_lecture and not has_any_subgroup:
                can_alternate = True

            if not can_alternate:
                continue

            weekly_items.sort(
                key=lambda item: (
                    0 if item.get("source_cell_type") == "shared_lecture" else 1,
                    0 if item.get("event_type") == "lecture" else 1,
                    item.get("subject") or "",
                    item.get("teacher") or "",
                    item.get("room") or "",
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

    def _deduplicate_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique = {}

        for event in events:
            key = "|".join(
                [
                    str(event.get("day_of_week") or ""),
                    str(event.get("start_time") or ""),
                    str(event.get("end_time") or ""),
                    self._normalize_text(event.get("subject") or ""),
                    str(event.get("event_type") or ""),
                    str(event.get("subgroup") or ""),
                    str(event.get("week_pattern") or ""),
                    str(event.get("teacher") or ""),
                    str(event.get("room") or ""),
                ]
            )

            if key not in unique:
                unique[key] = event

        return list(unique.values())

    def _normalize_event_type(self, value: Any) -> str:
        text = str(value or "").lower().strip()

        allowed = {
            "lecture",
            "laboratory",
            "practice",
            "seminar",
            "consultation",
            "exam",
            "credit",
            "class",
        }

        return text if text in allowed else "class"

    def _normalize_week_pattern(self, value: Any) -> str:
        text = str(value or "").lower().strip()

        if text in {"odd", "непарні", "непарний", "чисельник", "чис", "н/пар"}:
            return "odd"

        if text in {"even", "парні", "парний", "знаменник", "знам", "пар"}:
            return "even"

        return "weekly"

    def _normalize_time(self, value: Any) -> str:
        text = str(value or "").strip().replace(".", ":")

        if not text:
            return ""

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

    def _normalize_group(self, value: Any) -> str:
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
        text = text.replace("і", "i")
        text = text.replace("ї", "i")
        text = text.replace("є", "e")
        text = text.replace("ґ", "g")

        return text.strip()

    def _normalize_subgroup_value(self, value: Any) -> str:
        text = str(value or "").lower().strip()

        if not text:
            return ""

        text = text.replace("підгр.", "")
        text = text.replace("підгр", "")
        text = text.replace("підгрупа", "")
        text = text.replace("півпара", "")
        text = text.replace("півп.", "")
        text = text.replace("півп", "")
        text = text.replace(".", "")
        text = text.replace(" ", "")

        match = re.search(r"\d+", text)

        if match:
            return match.group(0)

        return ""

    def _normalize_text(self, value: Any) -> str:
        text = str(value or "").lower()
        text = re.sub(r"\s+", "", text)
        text = text.replace("-", "")
        text = text.replace("–", "")
        text = text.replace("—", "")
        text = text.replace("`", "")
        text = text.replace("'", "")
        text = text.replace("’", "")
        text = text.replace("ʼ", "")

        return text

    def _safe_confidence(self, value: Any) -> float:
        try:
            confidence = float(value)
        except Exception:
            confidence = 0.9

        return round(max(0.0, min(confidence, 1.0)), 2)

    def _day_order(self, day_code: str) -> int:
        order = {
            "MO": 1,
            "TU": 2,
            "WE": 3,
            "TH": 4,
            "FR": 5,
            "SA": 6,
            "SU": 7,
        }

        return order.get(day_code, 99)

    def _get_extension(self, filename: str) -> str:
        if "." not in filename:
            return ""

        return filename.rsplit(".", 1)[-1].lower().strip()

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
            "error": message,
        }