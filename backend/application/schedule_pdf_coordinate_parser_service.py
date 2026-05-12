import re
from typing import Any

import fitz


class SchedulePDFCoordinateParserService:
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

    DAY_SEQUENCE = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]

    EVENT_TYPES = {
        "лаб": "laboratory",
        "лаборатор": "laboratory",
        "лек": "lecture",
        "(л)": "lecture",
        "лекція": "lecture",
        "лекц": "lecture",
        "практ": "practice",
        "практи": "practice",
        "прс": "practice",
        "пр.": "practice",
        "сем": "seminar",
        "залік": "credit",
        "іспит": "exam",
        "екзамен": "exam",
    }

    TYPE_MARKER_RE = re.compile(
        r"\((?:лаб|л|лек|прс|практ|сем).*?\)|"
        r"\b(?:лаб\.?|лекція|лекц\.?|практика|практ\.?|прс|сем\.?)\b",
        flags=re.IGNORECASE,
    )

    ROOM_RE = re.compile(
        r"("
        r"№\s*\d+\s*/\s*[А-Яа-яA-Za-zІіЇїЄєҐґ]+|"
        r"N\s*\d+\s*/\s*[А-Яа-яA-Za-zІіЇїЄєҐґ]+|"
        r"\d+\s*/\s*[А-Яа-яA-Za-zІіЇїЄєҐґ]+|"
        r"[А-Яа-яA-Za-zІіЇїЄєҐґ]\s*\d{1,4}|"
        r"ч\s*\d{1,4}|"
        r"ауд\.?\s*[^,;]+|"
        r"PLAY|Zoom|Meet|Teams|Google\s*Meet|Classroom"
        r")",
        flags=re.IGNORECASE,
    )

    TEACHER_RE = re.compile(
        r"("
        r"зав\.?\s*кафедрою|"
        r"доцент|доц\.?|"
        r"професор|проф\.?|"
        r"асистент|асис\.?|асист\.?|"
        r"старший\s*викладач|ст\.?\s*викл\.?|"
        r"викладач|викл\.?"
        r")\s+(.+)",
        flags=re.IGNORECASE | re.DOTALL,
    )

    def parse_pdf(
        self,
        file_bytes: bytes,
        group_name: str,
        subgroup: str = "",
    ) -> list[dict[str, Any]]:
        target_group = (group_name or "").strip()
        target_subgroup = self._normalize_subgroup(subgroup)

        if not target_group:
            return []

        document = fitz.open(stream=file_bytes, filetype="pdf")

        all_events: list[dict[str, Any]] = []
        previous_layout: dict[str, Any] | None = None

        try:
            for page_index, page in enumerate(document, start=1):
                page_events, previous_layout = self._parse_page(
                    page=page,
                    page_index=page_index,
                    group_name=target_group,
                    subgroup=target_subgroup,
                    previous_layout=previous_layout,
                )

                all_events.extend(page_events)
        finally:
            document.close()

        all_events = self._deduplicate_events(all_events)
        all_events = self._fix_alternating_same_time_events(all_events)

        return all_events

    def _parse_page(
        self,
        page: fitz.Page,
        page_index: int,
        group_name: str,
        subgroup: str,
        previous_layout: dict[str, Any] | None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        words = self._extract_words(page)

        if not words:
            return [], previous_layout

        grid = self._extract_grid(page)

        if len(grid["horizontal"]) < 2 or len(grid["vertical_segments"]) < 2:
            return [], previous_layout

        layout = self._detect_layout_from_group_header(
            words=words,
            grid=grid,
            page=page,
            group_name=group_name,
        )

        if not layout and previous_layout:
            layout = self._reuse_layout_for_page(
                previous_layout=previous_layout,
                page=page,
            )

        if not layout:
            return [], previous_layout

        events = self._parse_layout_page(
            words=words,
            grid=grid,
            layout=layout,
            page_index=page_index,
            group_name=group_name,
            subgroup=subgroup,
        )

        return events, layout

    def _extract_grid(self, page: fitz.Page) -> dict[str, Any]:
        vertical_segments: list[dict[str, float]] = []
        horizontal_segments: list[dict[str, float]] = []
        horizontal_values: list[float] = []
        vertical_values: list[float] = []

        drawings = page.get_drawings()

        for drawing in drawings:
            for item in drawing.get("items", []):
                kind = item[0]

                if kind == "l":
                    p1 = item[1]
                    p2 = item[2]

                    x1, y1 = float(p1.x), float(p1.y)
                    x2, y2 = float(p2.x), float(p2.y)

                    if abs(x1 - x2) <= 1.5 and abs(y1 - y2) > 8:
                        x = (x1 + x2) / 2
                        y0 = min(y1, y2)
                        y1_ = max(y1, y2)

                        vertical_segments.append({"x": x, "y0": y0, "y1": y1_})
                        vertical_values.append(x)

                    elif abs(y1 - y2) <= 1.5 and abs(x1 - x2) > 8:
                        y = (y1 + y2) / 2
                        x0 = min(x1, x2)
                        x1_ = max(x1, x2)

                        horizontal_segments.append({"y": y, "x0": x0, "x1": x1_})
                        horizontal_values.append(y)

                elif kind == "re":
                    rect = item[1]
                    x0 = float(rect.x0)
                    x1 = float(rect.x1)
                    y0 = float(rect.y0)
                    y1 = float(rect.y1)

                    vertical_segments.append({"x": x0, "y0": y0, "y1": y1})
                    vertical_segments.append({"x": x1, "y0": y0, "y1": y1})
                    horizontal_segments.append({"y": y0, "x0": x0, "x1": x1})
                    horizontal_segments.append({"y": y1, "x0": x0, "x1": x1})

                    vertical_values.extend([x0, x1])
                    horizontal_values.extend([y0, y1])

        vertical_segments = self._merge_vertical_segments(vertical_segments)
        horizontal_values = self._merge_close_numbers(horizontal_values, tolerance=3)
        vertical_values = self._merge_close_numbers(vertical_values, tolerance=3)

        return {
            "vertical_segments": vertical_segments,
            "horizontal_segments": horizontal_segments,
            "horizontal": horizontal_values,
            "vertical": vertical_values,
        }

    def _merge_vertical_segments(
        self,
        segments: list[dict[str, float]],
        x_tolerance: float = 3,
        y_tolerance: float = 4,
    ) -> list[dict[str, float]]:
        if not segments:
            return []

        segments = sorted(segments, key=lambda item: (item["x"], item["y0"], item["y1"]))
        grouped_by_x: list[list[dict[str, float]]] = []

        for segment in segments:
            if not grouped_by_x or abs(segment["x"] - grouped_by_x[-1][0]["x"]) > x_tolerance:
                grouped_by_x.append([segment])
            else:
                grouped_by_x[-1].append(segment)

        result: list[dict[str, float]] = []

        for group in grouped_by_x:
            avg_x = sum(item["x"] for item in group) / len(group)
            group = sorted(group, key=lambda item: item["y0"])

            merged: list[dict[str, float]] = []

            for segment in group:
                current = {
                    "x": avg_x,
                    "y0": segment["y0"],
                    "y1": segment["y1"],
                }

                if not merged:
                    merged.append(current)
                    continue

                last = merged[-1]

                if current["y0"] <= last["y1"] + y_tolerance:
                    last["y1"] = max(last["y1"], current["y1"])
                else:
                    merged.append(current)

            result.extend(merged)

        return result

    def _merge_close_numbers(self, values: list[float], tolerance: float = 3) -> list[float]:
        if not values:
            return []

        values = sorted(values)
        groups: list[list[float]] = []

        for value in values:
            if not groups or abs(value - groups[-1][-1]) > tolerance:
                groups.append([value])
            else:
                groups[-1].append(value)

        return [sum(group) / len(group) for group in groups]

    def _detect_layout_from_group_header(
        self,
        words: list[dict[str, Any]],
        grid: dict[str, Any],
        page: fitz.Page,
        group_name: str,
    ) -> dict[str, Any] | None:
        target_group_norm = self._normalize_group(group_name)

        group_like_words = [
            word for word in words
            if self._looks_like_group(word["text"])
        ]

        if not group_like_words:
            return None

        rows = self._cluster_words_by_y(group_like_words, tolerance=10)
        rows = [row for row in rows if len(row) >= 2]

        for row in rows:
            row.sort(key=lambda word: word["cx"])

            target_word = None

            for word in row:
                if self._normalize_group(word["text"]) == target_group_norm:
                    target_word = word
                    break

            if not target_word:
                continue

            active_x = self._active_vertical_lines_at_y(
                grid=grid,
                y=target_word["cy"],
                page_width=float(page.rect.width),
            )

            group_interval = self._find_interval_for_value(active_x, target_word["cx"])

            if not group_interval:
                group_interval = self._estimate_interval_by_neighbor_group_headers(
                    row=row,
                    target_word=target_word,
                    page_width=float(page.rect.width),
                )

            if not group_interval:
                continue

            first_group_x = min(word["x0"] for word in row)

            header_bottom = self._find_next_horizontal_after(
                grid["horizontal"],
                target_word["cy"],
            )

            if header_bottom is None:
                header_bottom = target_word["y1"] + 5

            return {
                "group_left": group_interval[0],
                "group_right": group_interval[1],
                "group_center": target_word["cx"],
                "group_width": group_interval[1] - group_interval[0],
                "first_group_x": first_group_x,
                "table_top": header_bottom,
                "table_bottom": float(page.rect.height),
                "page_width": float(page.rect.width),
            }

        return None

    def _reuse_layout_for_page(
        self,
        previous_layout: dict[str, Any],
        page: fitz.Page,
    ) -> dict[str, Any]:
        return {
            "group_left": previous_layout["group_left"],
            "group_right": previous_layout["group_right"],
            "group_center": previous_layout["group_center"],
            "group_width": previous_layout["group_width"],
            "first_group_x": previous_layout["first_group_x"],
            "table_top": 0,
            "table_bottom": float(page.rect.height),
            "page_width": float(page.rect.width),
        }

    def _estimate_interval_by_neighbor_group_headers(
        self,
        row: list[dict[str, Any]],
        target_word: dict[str, Any],
        page_width: float,
    ) -> tuple[float, float] | None:
        row = sorted(row, key=lambda word: word["cx"])
        index = row.index(target_word)

        if len(row) < 2:
            return None

        if index > 0:
            left_mid = (row[index - 1]["cx"] + target_word["cx"]) / 2
        else:
            next_mid = (target_word["cx"] + row[index + 1]["cx"]) / 2
            left_mid = target_word["cx"] - (next_mid - target_word["cx"])

        if index + 1 < len(row):
            right_mid = (target_word["cx"] + row[index + 1]["cx"]) / 2
        else:
            prev_mid = (row[index - 1]["cx"] + target_word["cx"]) / 2
            right_mid = target_word["cx"] + (target_word["cx"] - prev_mid)

        left_mid = max(0, left_mid)
        right_mid = min(page_width, right_mid)

        if right_mid - left_mid < 10:
            return None

        return left_mid, right_mid

    def _find_next_horizontal_after(
        self,
        horizontal: list[float],
        y: float,
    ) -> float | None:
        for value in sorted(horizontal):
            if value > y:
                return value

        return None

    def _parse_layout_page(
        self,
        words: list[dict[str, Any]],
        grid: dict[str, Any],
        layout: dict[str, Any],
        page_index: int,
        group_name: str,
        subgroup: str,
    ) -> list[dict[str, Any]]:
        rows = self._build_rows(
            words=words,
            grid=grid,
            layout=layout,
        )

        if not rows:
            return []

        day_labels = self._detect_day_labels(
            words=words,
            layout=layout,
        )

        self._assign_days_to_rows(rows, day_labels)

        events: list[dict[str, Any]] = []

        for row in rows:
            is_continuation = bool(row.get("is_continuation"))

            if not is_continuation:
                cell_rect = self._find_target_cell_rect_for_row(
                    grid=grid,
                    layout=layout,
                    row=row,
                )

                if cell_rect:
                    cell_text = self._extract_text_in_rect(
                        words=words,
                        left=cell_rect["left"],
                        right=cell_rect["right"],
                        top=row["top"],
                        bottom=row["bottom"],
                    )

                    cell_text = self._remove_group_headers_from_text(cell_text)

                    if cell_text and not self._is_non_study_text(cell_text):
                        row_events = self._events_from_cell(
                            cell_text=cell_text,
                            group_name=group_name,
                            subgroup=subgroup,
                            day_of_week=row.get("day_of_week", ""),
                            pair_number=row.get("pair_number"),
                            start_time=row.get("start_time", ""),
                            end_time=row.get("end_time", ""),
                            page_index=page_index,
                            row_y=row["top"],
                            cell_left=cell_rect["left"],
                            cell_right=cell_rect["right"],
                            is_merged_cell=cell_rect["is_merged"],
                            source_cell_type="merged" if cell_rect["is_merged"] else "exact",
                        )

                        events.extend(row_events)

            shared_lecture_text = self._extract_shared_lecture_text_for_row(
                words=words,
                row=row,
                layout=layout,
            )

            if shared_lecture_text and not self._is_non_study_text(shared_lecture_text):
                shared_events = self._events_from_cell(
                    cell_text=shared_lecture_text,
                    group_name=group_name,
                    subgroup=subgroup,
                    day_of_week=row.get("day_of_week", ""),
                    pair_number=row.get("pair_number"),
                    start_time=row.get("start_time", ""),
                    end_time=row.get("end_time"),
                    page_index=page_index,
                    row_y=row["top"],
                    cell_left=layout["group_left"],
                    cell_right=layout["group_right"],
                    is_merged_cell=True,
                    source_cell_type="shared_lecture",
                )

                events.extend(shared_events)

        return events

    def _build_rows(
        self,
        words: list[dict[str, Any]],
        grid: dict[str, Any],
        layout: dict[str, Any],
    ) -> list[dict[str, Any]]:
        horizontal = [
            y for y in grid["horizontal"]
            if layout["table_top"] - 2 <= y <= layout["table_bottom"] + 2
        ]

        horizontal = sorted(horizontal)

        if len(horizontal) < 2:
            return []

        rows: list[dict[str, Any]] = []

        last_pair_number = None
        last_start_time = ""
        last_end_time = ""

        for index in range(len(horizontal) - 1):
            top = horizontal[index]
            bottom = horizontal[index + 1]

            if bottom - top < 8:
                continue

            service_text = self._extract_text_in_rect(
                words=words,
                left=0,
                right=layout["first_group_x"],
                top=top,
                bottom=bottom,
            )

            pair_number = self._extract_pair_number(service_text)
            start_time, end_time = self._extract_time(service_text)

            is_continuation = False

            if pair_number is None and not start_time:
                row_text_after_service = self._extract_text_in_rect(
                    words=words,
                    left=layout["first_group_x"],
                    right=layout["page_width"],
                    top=top,
                    bottom=bottom,
                )

                row_text_after_service_clean = self._clean_text(row_text_after_service)

                has_study_text = (
                    row_text_after_service_clean
                    and not self._is_non_study_text(row_text_after_service_clean)
                    and not self._is_bad_fragment(row_text_after_service_clean)
                )

                has_previous_time = bool(last_pair_number and last_start_time and last_end_time)

                if has_study_text and has_previous_time:
                    pair_number = last_pair_number
                    start_time = last_start_time
                    end_time = last_end_time
                    is_continuation = True
                else:
                    continue

            if pair_number and (not start_time or not end_time):
                default_time = self.DEFAULT_PAIR_TIMES.get(pair_number)

                if default_time:
                    start_time = start_time or default_time[0]
                    end_time = end_time or default_time[1]

            if pair_number and start_time and end_time and not is_continuation:
                last_pair_number = pair_number
                last_start_time = start_time
                last_end_time = end_time

            rows.append(
                {
                    "key": f"row_{index}_{round(top, 2)}",
                    "top": top,
                    "bottom": bottom,
                    "center_y": (top + bottom) / 2,
                    "pair_number": pair_number,
                    "start_time": start_time,
                    "end_time": end_time,
                    "service_text": service_text,
                    "day_of_week": "",
                    "is_continuation": is_continuation,
                }
            )

        return rows

    def _find_target_cell_rect_for_row(
        self,
        grid: dict[str, Any],
        layout: dict[str, Any],
        row: dict[str, Any],
    ) -> dict[str, Any] | None:
        center_y = row["center_y"]
        group_center = layout["group_center"]

        active_x = self._active_vertical_lines_at_y(
            grid=grid,
            y=center_y,
            page_width=layout["page_width"],
        )

        interval = self._find_interval_for_value(active_x, group_center)

        if not interval:
            interval = (layout["group_left"], layout["group_right"])

        left, right = interval

        normal_width = max(layout["group_width"], 1)
        current_width = right - left

        is_merged = current_width >= normal_width * 1.35

        return {
            "left": left,
            "right": right,
            "is_merged": is_merged,
        }

    def _extract_shared_lecture_text_for_row(
        self,
        words: list[dict[str, Any]],
        row: dict[str, Any],
        layout: dict[str, Any],
    ) -> str:
        row_words = [
            word
            for word in words
            if row["top"] <= word["cy"] <= row["bottom"]
        ]

        if not row_words:
            return ""

        lines = self._cluster_words_by_y(row_words, tolerance=4)
        selected_lines: list[str] = []

        target_left = layout["group_left"]
        target_right = layout["group_right"]
        target_width = max(layout["group_width"], 1)
        first_group_x = layout["first_group_x"]

        for line in lines:
            line.sort(key=lambda word: word["cx"])
            line_text = self._join_words(line)

            if not line_text:
                continue

            lowered = self._clean_text(line_text).lower()

            if self._is_non_study_text(line_text):
                continue

            if self._is_bad_fragment(line_text):
                continue

            event_type = self._extract_event_type(line_text)

            if event_type != "lecture":
                continue

            if re.search(r"підгр\.?\s*\d|підгрупа\s*\d", lowered, flags=re.IGNORECASE):
                continue

            if "зб.груп" in lowered or "зб. груп" in lowered or "зб груп" in lowered:
                continue

            if "(прс" in lowered or "прс)" in lowered:
                continue

            if "практ" in lowered or "практи" in lowered:
                continue

            if "лаб" in lowered or "лаборатор" in lowered:
                continue

            subject = self._extract_subject(line_text)

            if not subject:
                continue

            if self._is_bad_fragment(subject):
                continue

            line_left = min(word["x0"] for word in line)
            line_right = max(word["x1"] for word in line)
            line_width = line_right - line_left

            if line_right <= first_group_x:
                continue

            overlap_left = max(line_left, target_left)
            overlap_right = min(line_right, target_right)
            overlap_width = max(0, overlap_right - overlap_left)
            overlap_ratio = overlap_width / target_width

            has_stream_marker = "потік" in lowered
            is_wide_shared_lecture = line_width >= target_width * 1.8

            if not has_stream_marker and not is_wide_shared_lecture:
                continue

            if overlap_ratio <= 0 and not is_wide_shared_lecture:
                continue

            if line_text not in selected_lines:
                selected_lines.append(line_text)

        return self._clean_text(" ; ".join(selected_lines))

    def _active_vertical_lines_at_y(
        self,
        grid: dict[str, Any],
        y: float,
        page_width: float,
    ) -> list[float]:
        active = []

        for segment in grid["vertical_segments"]:
            if segment["y0"] - 2 <= y <= segment["y1"] + 2:
                active.append(segment["x"])

        active = self._merge_close_numbers(active, tolerance=3)

        if not active:
            active = grid.get("vertical", [])

        if not active:
            return [0, page_width]

        if min(active) > 5:
            active.insert(0, 0)

        if max(active) < page_width - 5:
            active.append(page_width)

        return sorted(active)

    def _find_interval_for_value(
        self,
        lines: list[float],
        value: float,
    ) -> tuple[float, float] | None:
        lines = sorted(lines)

        if len(lines) < 2:
            return None

        for index in range(len(lines) - 1):
            left = lines[index]
            right = lines[index + 1]

            if left <= value <= right:
                return left, right

        return None

    def _detect_day_labels(
        self,
        words: list[dict[str, Any]],
        layout: dict[str, Any],
    ) -> list[dict[str, Any]]:
        labels = []

        for word in words:
            if word["cx"] > layout["first_group_x"]:
                continue

            day = self._normalize_day(word["text"])

            if day:
                labels.append(
                    {
                        "day_code": day,
                        "cy": word["cy"],
                        "text": word["text"],
                    }
                )

        labels.sort(key=lambda item: item["cy"])

        filtered = []

        for label in labels:
            if not filtered:
                filtered.append(label)
                continue

            if label["day_code"] == filtered[-1]["day_code"] and abs(label["cy"] - filtered[-1]["cy"]) < 40:
                continue

            filtered.append(label)

        return filtered

    def _assign_days_to_rows(
        self,
        rows: list[dict[str, Any]],
        day_labels: list[dict[str, Any]],
    ) -> None:
        if not rows:
            return

        if day_labels:
            for row in rows:
                nearest = min(
                    day_labels,
                    key=lambda label: abs(label["cy"] - row["center_y"]),
                )
                row["day_of_week"] = nearest["day_code"]

            self._fix_days_by_pair_reset(rows)
            return

        current_day = "MO"
        previous_pair = None

        for row in rows:
            pair_number = row.get("pair_number")

            if previous_pair is not None and pair_number is not None and pair_number < previous_pair:
                current_day = self._next_day(current_day)

            row["day_of_week"] = current_day

            if pair_number is not None:
                previous_pair = pair_number

    def _fix_days_by_pair_reset(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return

        current_day = rows[0].get("day_of_week") or "MO"
        previous_pair = None

        for row in rows:
            pair_number = row.get("pair_number")

            if previous_pair is not None and pair_number is not None and pair_number < previous_pair:
                next_day = self._next_day(current_day)

                if row.get("day_of_week") == current_day:
                    row["day_of_week"] = next_day

                current_day = row.get("day_of_week") or next_day
            else:
                current_day = row.get("day_of_week") or current_day

            if pair_number is not None:
                previous_pair = pair_number

    def _next_day(self, current_day: str) -> str:
        if current_day not in self.DAY_SEQUENCE:
            return current_day

        index = self.DAY_SEQUENCE.index(current_day)

        if index + 1 >= len(self.DAY_SEQUENCE):
            return current_day

        return self.DAY_SEQUENCE[index + 1]

    def _events_from_cell(
        self,
        cell_text: str,
        group_name: str,
        subgroup: str,
        day_of_week: str,
        pair_number: int | None,
        start_time: str,
        end_time: str,
        page_index: int,
        row_y: float,
        cell_left: float,
        cell_right: float,
        is_merged_cell: bool,
        source_cell_type: str = "exact",
    ) -> list[dict[str, Any]]:
        text = self._clean_text(cell_text)

        if not text:
            return []

        segments = self._split_cell_into_segments(text)
        events = []

        for segment in segments:
            segment = self._clean_text(segment)

            if not segment:
                continue

            if self._is_non_study_text(segment):
                continue

            if self._is_bad_fragment(segment):
                continue

            segment_subgroup = self._extract_subgroup(segment)
            event_type = self._extract_event_type(segment)
            lowered_segment = self._clean_text(segment).lower()

            if source_cell_type == "shared_lecture":
                if event_type != "lecture":
                    continue

                if re.search(r"підгр\.?\s*\d|підгрупа\s*\d", lowered_segment, flags=re.IGNORECASE):
                    continue

                if "зб.груп" in lowered_segment or "зб. груп" in lowered_segment or "зб груп" in lowered_segment:
                    continue

                if "(прс" in lowered_segment or "прс)" in lowered_segment:
                    continue

                if "практ" in lowered_segment or "практи" in lowered_segment:
                    continue

                if "лаб" in lowered_segment or "лаборатор" in lowered_segment:
                    continue

            if subgroup:
                if segment_subgroup and segment_subgroup != subgroup:
                    continue

                if self._has_other_subgroup_only(segment, subgroup):
                    continue

                if (
                    source_cell_type != "exact"
                    and not segment_subgroup
                    and event_type in {"laboratory", "practice", "seminar"}
                ):
                    continue

            if is_merged_cell and source_cell_type != "shared_lecture":
                if event_type in {"laboratory", "practice", "seminar"} and not segment_subgroup:
                    continue

            subject = self._extract_subject(segment)

            if not subject:
                continue

            if self._is_bad_fragment(subject):
                continue

            event = {
                "subject": subject,
                "event_type": event_type,
                "day_of_week": day_of_week,
                "pair_number": pair_number,
                "start_time": start_time,
                "end_time": end_time,
                "teacher": self._extract_teacher(segment),
                "room": self._extract_room(segment),
                "group_name": group_name,
                "source_group_text": (
                    "shared_lecture"
                    if source_cell_type == "shared_lecture"
                    else group_name if not is_merged_cell else "merged_over_target_group"
                ),
                "source_cell_type": source_cell_type,
                "subgroup": segment_subgroup,
                "week_pattern": self._extract_week_pattern(segment),
                "scope": "subgroup" if segment_subgroup else "group",
                "source_text": (
                    f"PDF page {page_index}, y={round(row_y, 2)}, "
                    f"x={round(cell_left, 2)}-{round(cell_right, 2)}: {segment}"
                ),
                "confidence": 1.0 if source_cell_type == "exact" else 0.9,
                "needs_review": False if day_of_week and start_time and end_time else True,
            }

            events.append(event)

        return events

    def _split_cell_into_segments(self, text: str) -> list[str]:
        text = self._clean_text(text)

        if not text:
            return []

        parts = [
            part.strip()
            for part in re.split(r"\s*;\s*|\s*\n\s*", text)
            if part.strip()
        ]

        if not parts:
            parts = [text]

        result = []

        for part in parts:
            part = self._clean_text(part)

            if not part:
                continue

            lesson_parts = self._split_by_type_repetition(part)

            for lesson_part in lesson_parts:
                lesson_part = self._clean_text(lesson_part)

                if not lesson_part:
                    continue

                markers = list(
                    re.finditer(
                        r"(підгр\.?\s*\d|підгрупа\s*\d|чис\.?|знам\.?|н/пар\.?|пар\.?)",
                        lesson_part,
                        flags=re.IGNORECASE,
                    )
                )

                if len(markers) <= 1:
                    if not self._is_bad_fragment(lesson_part):
                        result.append(lesson_part)
                    continue

                prefix = lesson_part[: markers[0].start()].strip()

                for index, marker in enumerate(markers):
                    start = marker.start()
                    end = markers[index + 1].start() if index + 1 < len(markers) else len(lesson_part)
                    chunk = lesson_part[start:end].strip()

                    if prefix and not self._is_bad_fragment(prefix):
                        chunk = f"{prefix} {chunk}"

                    if chunk and not self._is_bad_fragment(chunk):
                        result.append(chunk)

        cleaned = []

        for item in result:
            item = self._clean_text(item)

            if item and not self._is_bad_fragment(item):
                cleaned.append(item)

        return cleaned

    def _split_by_type_repetition(self, text: str) -> list[str]:
        text = self._clean_text(text)

        if not text:
            return []

        matches = list(self.TYPE_MARKER_RE.finditer(text))

        if len(matches) <= 1:
            return [text]

        starts = [0]

        for index in range(len(matches) - 1):
            current = matches[index]
            next_match = matches[index + 1]

            possible_start = self._find_next_subject_start(
                text=text,
                start=current.end(),
                end=next_match.start(),
            )

            if possible_start is not None and possible_start > 0:
                starts.append(possible_start)

        starts = sorted(set(starts))

        if len(starts) <= 1:
            return [text]

        result = []

        for index, start in enumerate(starts):
            end = starts[index + 1] if index + 1 < len(starts) else len(text)
            chunk = text[start:end].strip()

            if chunk:
                result.append(chunk)

        return result or [text]

    def _find_next_subject_start(
        self,
        text: str,
        start: int,
        end: int,
    ) -> int | None:
        fragment = text[start:end]

        if not fragment.strip():
            return None

        room_matches = list(self.ROOM_RE.finditer(fragment))

        if room_matches:
            after_room = start + room_matches[-1].end()
            tail = text[after_room:end]

            next_word = re.search(
                r"[А-ЯІЇЄҐA-Z][А-Яа-яІіЇїЄєҐґA-Za-z0-9'’`-]{2,}",
                tail,
            )

            if next_word:
                return after_room + next_word.start()

        teacher_matches = list(self.TEACHER_RE.finditer(fragment))

        if teacher_matches:
            after_teacher = start + teacher_matches[-1].end()
            tail = text[after_teacher:end]

            next_word = re.search(
                r"[А-ЯІЇЄҐA-Z][А-Яа-яІіЇїЄєҐґA-Za-z0-9'’`-]{2,}",
                tail,
            )

            if next_word:
                return after_teacher + next_word.start()

        return None

    def _extract_subject(self, text: str) -> str:
        text = self._clean_text(text)

        text = re.sub(r"^підгр\.?\s*\d\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^підгрупа\s*\d\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^потік\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^зб\.?\s*група\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^(чис\.?|знам\.?|н/пар\.?|пар\.?)\s*", "", text, flags=re.IGNORECASE)

        cut_positions = []

        type_match = self.TYPE_MARKER_RE.search(text)
        teacher_match = self.TEACHER_RE.search(text)
        room_match = self.ROOM_RE.search(text)

        if type_match:
            cut_positions.append(type_match.start())

        if teacher_match:
            cut_positions.append(teacher_match.start())

        if room_match:
            cut_positions.append(room_match.start())

        if cut_positions:
            subject = text[: min(cut_positions)]
        else:
            subject = text

        subject = self._clean_text(subject)
        subject = subject.strip(" .,:;-")

        if len(subject) < 3:
            return ""

        if self._is_bad_fragment(subject):
            return ""

        if self._is_non_study_text(subject):
            return ""

        return subject

    def _extract_event_type(self, text: str) -> str:
        lowered = text.lower()

        for marker, event_type in self.EVENT_TYPES.items():
            if marker in lowered:
                return event_type

        return "class"

    def _extract_teacher(self, text: str) -> str:
        match = self.TEACHER_RE.search(text)

        if not match:
            return ""

        teacher = f"{match.group(1)} {match.group(2)}"
        teacher = self.ROOM_RE.sub("", teacher)
        teacher = re.split(
            r"\b(?:підгр|підгрупа|чис|знам|н/пар|пар|потік|зб\.?\s*група)\b",
            teacher,
            flags=re.IGNORECASE,
        )[0]

        teacher = self._clean_text(teacher)
        teacher = teacher.strip(" .,:;-")

        return teacher

    def _extract_room(self, text: str) -> str:
        matches = list(self.ROOM_RE.finditer(text))

        if not matches:
            return ""

        room = matches[-1].group(1)
        room = self._clean_text(room)

        return room

    def _extract_subgroup(self, text: str) -> str:
        patterns = [
            r"підгр\.?\s*(\d+)",
            r"підгрупа\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)

            if match:
                return match.group(1)

        return ""

    def _has_other_subgroup_only(self, text: str, target_subgroup: str) -> bool:
        numbers = []

        for pattern in [r"підгр\.?\s*(\d+)", r"підгрупа\s*(\d+)"]:
            numbers.extend(re.findall(pattern, text, flags=re.IGNORECASE))

        if not numbers:
            return False

        return target_subgroup not in numbers

    def _extract_week_pattern(self, text: str) -> str:
        lowered = self._clean_text(text).lower()

        if any(marker in lowered for marker in ["чис.", "чис ", "чисельник", "н/пар", "непар"]):
            return "odd"

        if any(marker in lowered for marker in ["знам", "знаменник", "пар.", "парн"]):
            return "even"

        return "weekly"

    def _is_stream_or_whole_group_event(self, text: str) -> bool:
        lowered = self._clean_text(text).lower()

        if "потік" in lowered:
            return True

        if "зб. груп" in lowered or "зб.груп" in lowered or "зб груп" in lowered:
            return True

        if self._extract_event_type(text) == "lecture":
            return True

        return False

    def _extract_pair_number(self, text: str) -> int | None:
        cleaned = self._clean_text(text)

        match = re.search(r"(^|\s)(\d{1,2})(\s|$)", cleaned)

        if not match:
            return None

        value = int(match.group(2))

        if 1 <= value <= 12:
            return value

        return None

    def _extract_time(self, text: str) -> tuple[str, str]:
        cleaned = self._clean_text(text)
        cleaned = cleaned.replace(".", ":")
        cleaned = cleaned.replace("–", "-")
        cleaned = cleaned.replace("—", "-")
        cleaned = re.sub(r"\s+", "", cleaned)

        match = re.search(r"(\d{1,2}:\d{2})-(\d{1,2}:\d{2})", cleaned)

        if match:
            return self._normalize_time(match.group(1)), self._normalize_time(match.group(2))

        times = re.findall(r"\d{1,2}:\d{2}", cleaned)

        if len(times) >= 2:
            return self._normalize_time(times[0]), self._normalize_time(times[1])

        return "", ""

    def _fix_alternating_same_time_events(
        self,
        events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}

        for event in events:
            key = "|".join(
                [
                    event.get("day_of_week", ""),
                    event.get("start_time", ""),
                    event.get("end_time", ""),
                ]
            )

            grouped.setdefault(key, []).append(event)

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
                    item.get("subject", ""),
                    item.get("teacher", ""),
                    item.get("room", ""),
                )
            )

            weekly_items[0]["week_pattern"] = "odd"
            weekly_items[0]["needs_review"] = True
            weekly_items[0]["confidence"] = min(float(weekly_items[0].get("confidence", 1)), 0.8)

            weekly_items[1]["week_pattern"] = "even"
            weekly_items[1]["needs_review"] = True
            weekly_items[1]["confidence"] = min(float(weekly_items[1].get("confidence", 1)), 0.8)

            for item in weekly_items[2:]:
                item["needs_review"] = True
                item["confidence"] = min(float(item.get("confidence", 1)), 0.7)

        return events

    def _deduplicate_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique = {}

        for event in events:
            key = "|".join(
                [
                    event.get("day_of_week", ""),
                    event.get("start_time", ""),
                    event.get("end_time", ""),
                    self._normalize_key(event.get("subject", "")),
                    event.get("event_type", ""),
                    event.get("subgroup", ""),
                    event.get("week_pattern", ""),
                    event.get("teacher", ""),
                    event.get("room", ""),
                ]
            )

            if key not in unique:
                unique[key] = event

        return list(unique.values())

    def _extract_words(self, page: fitz.Page) -> list[dict[str, Any]]:
        raw_words = page.get_text("words") or []
        words = []

        for item in raw_words:
            x0, y0, x1, y1, text = item[:5]
            clean = self._clean_text(text)

            if not clean:
                continue

            words.append(
                {
                    "x0": float(x0),
                    "y0": float(y0),
                    "x1": float(x1),
                    "y1": float(y1),
                    "cx": (float(x0) + float(x1)) / 2,
                    "cy": (float(y0) + float(y1)) / 2,
                    "text": clean,
                }
            )

        return words

    def _extract_text_in_rect(
        self,
        words: list[dict[str, Any]],
        left: float,
        right: float,
        top: float,
        bottom: float,
    ) -> str:
        selected = []

        for word in words:
            if left <= word["cx"] <= right and top <= word["cy"] <= bottom:
                selected.append(word)

        return self._join_words(selected)

    def _join_words(self, words: list[dict[str, Any]]) -> str:
        if not words:
            return ""

        lines = self._cluster_words_by_y(words, tolerance=4)
        result = []

        for line in lines:
            line.sort(key=lambda word: word["cx"])
            result.append(" ".join(word["text"] for word in line))

        return self._clean_text(" ".join(result))

    def _cluster_words_by_y(
        self,
        words: list[dict[str, Any]],
        tolerance: float = 4,
    ) -> list[list[dict[str, Any]]]:
        sorted_words = sorted(words, key=lambda word: (word["cy"], word["cx"]))
        rows: list[list[dict[str, Any]]] = []

        for word in sorted_words:
            added = False

            for row in rows:
                row_y = sum(item["cy"] for item in row) / len(row)

                if abs(word["cy"] - row_y) <= tolerance:
                    row.append(word)
                    added = True
                    break

            if not added:
                rows.append([word])

        for row in rows:
            row.sort(key=lambda word: word["cx"])

        return rows

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

    def _normalize_subgroup(self, value: Any) -> str:
        text = str(value or "").lower()
        text = text.replace("підгр.", "")
        text = text.replace("підгр", "")
        text = text.replace("підгрупа", "")
        text = text.replace(".", "")
        text = text.replace(" ", "")

        match = re.search(r"\d+", text)

        if match:
            return match.group(0)

        return ""

    def _normalize_day(self, value: Any) -> str:
        text = str(value or "").lower()
        text = text.replace(" ", "")
        text = text.replace("\n", "")
        text = text.replace("`", "'")
        text = text.replace("’", "'")
        text = text.replace("ʼ", "'")

        if "понед" in text:
            return "MO"

        if "вівт" in text or "вiвт" in text:
            return "TU"

        if "серед" in text:
            return "WE"

        if "четв" in text:
            return "TH"

        if "п'ят" in text or "пят" in text:
            return "FR"

        if "суб" in text:
            return "SA"

        if "нед" in text:
            return "SU"

        return ""

    def _normalize_time(self, value: Any) -> str:
        text = str(value or "").strip().replace(".", ":")

        match = re.fullmatch(r"(\d{1,2}):(\d{2})", text)

        if not match:
            return ""

        hours = int(match.group(1))
        minutes = int(match.group(2))

        if hours > 23 or minutes > 59:
            return ""

        return f"{hours:02d}:{minutes:02d}"

    def _normalize_key(self, value: Any) -> str:
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

    def _looks_like_group(self, value: Any) -> bool:
        text = str(value or "").strip()

        if not text:
            return False

        return bool(
            re.fullmatch(
                r"[A-Za-zА-Яа-яІіЇїЄєҐґ]{2,8}\s*[-–—]?\s*\d{1,4}\s*[A-Za-zА-Яа-яІіЇїЄєҐґ]?",
                text,
            )
        )

    def _clean_text(self, value: Any) -> str:
        text = str(value or "")
        text = text.replace("\r", " ")
        text = text.replace("\n", " ")
        text = text.replace("\u00a0", " ")
        text = text.replace("￾", "-")
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _remove_group_headers_from_text(self, text: str) -> str:
        parts = []

        for token in self._clean_text(text).split():
            if self._looks_like_group(token):
                continue

            parts.append(token)

        return self._clean_text(" ".join(parts))

    def _is_non_study_text(self, text: str) -> bool:
        lowered = self._clean_text(text).lower()

        if not lowered:
            return True

        ignored = [
            "затверджую",
            "проректор",
            "декан",
            "директор",
            "начальник",
            "розклад",
            "семестр",
            "міністерство",
            "львівський національний",
            "дисципліни загальної підготовки",
            "вибіркові дисципліни",
            "дввс",
            "примітки",
        ]

        return any(item in lowered for item in ignored)

    def _is_bad_fragment(self, text: str) -> bool:
        cleaned = self._clean_text(text).lower()
        cleaned = cleaned.strip(" .,:;-")

        if not cleaned:
            return True

        bad_values = {
            "під",
            "під.",
            "підгр",
            "підгр.",
            "підгрупа",
            "гр",
            "гр.",
            "група",
            "чис",
            "чис.",
            "знам",
            "знам.",
            "пар",
            "пар.",
            "н/пар",
            "н/пар.",
        }

        if cleaned in bad_values:
            return True

        if re.fullmatch(r"\d{1,2}", cleaned):
            return True

        if re.search(r"\d{1,2}\s*:\s*\d{2}", cleaned):
            return True

        letters_count = len(re.findall(r"[a-zа-яіїєґ]", cleaned, flags=re.IGNORECASE))
        digits_count = len(re.findall(r"\d", cleaned))

        if digits_count >= 3 and letters_count <= 3:
            return True

        return False