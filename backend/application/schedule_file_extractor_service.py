import base64
import io
import mimetypes
import re
from typing import Any

import pandas as pd


class ScheduleFileExtractorService:
    IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    PDF_EXTENSIONS = {"pdf"}
    EXCEL_EXTENSIONS = {"xlsx", "xls"}
    DOCX_EXTENSIONS = {"docx"}
    TEXT_EXTENSIONS = {"txt", "csv"}

    def extract(
        self,
        filename: str,
        file_bytes: bytes,
        group_name: str = "",
    ) -> dict[str, Any]:
        extension = self._get_extension(filename)

        result = {
            "filename": filename,
            "extension": extension,
            "text_context": "",
            "target_context": "",
            "images": [],
            "debug": {
                "detected_groups": [],
                "target_group_found_in_tables": False,
                "used_extractors": [],
                "is_complex_pdf": False,
            },
        }

        if extension in self.IMAGE_EXTENSIONS:
            result["images"] = [
                self._image_to_payload(filename, file_bytes, page_number=1)
            ]
            result["debug"]["used_extractors"].append("image")
            return result

        if extension in self.PDF_EXTENSIONS:
            return self._extract_pdf(filename, file_bytes, group_name)

        if extension in self.EXCEL_EXTENSIONS:
            return self._extract_excel(filename, file_bytes, group_name, extension)

        if extension in self.DOCX_EXTENSIONS:
            return self._extract_docx(filename, file_bytes, group_name)

        if extension in self.TEXT_EXTENSIONS:
            text = file_bytes.decode("utf-8", errors="ignore")
            result["text_context"] = text
            result["debug"]["used_extractors"].append("plain_text")
            return result

        raise ValueError(
            "Непідтримуваний формат файлу. "
            "Підтримуються PDF, Excel, DOCX, TXT, CSV, JPG, PNG, WEBP."
        )

    # --------------------------------------------------
    # PDF
    # --------------------------------------------------

    def _extract_pdf(
        self,
        filename: str,
        file_bytes: bytes,
        group_name: str,
    ) -> dict[str, Any]:
        result = {
            "filename": filename,
            "extension": "pdf",
            "text_context": "",
            "target_context": "",
            "images": [],
            "debug": {
                "detected_groups": [],
                "target_group_found_in_tables": False,
                "used_extractors": ["pdf_images", "pdf_text", "pdf_tables", "pdf_words"],
                "is_complex_pdf": False,
            },
        }

        result["images"] = self._render_pdf_pages_to_images(file_bytes)

        detected_groups = set()
        detected_groups.update(self._detect_groups_from_pdf_words(file_bytes))

        try:
            import pdfplumber
        except ImportError:
            result["text_context"] = (
                "pdfplumber не встановлено. "
                "Для PDF буде використано AI або координатний parser."
            )
            result["debug"]["detected_groups"] = sorted(detected_groups)
            result["debug"]["is_complex_pdf"] = len(detected_groups) >= 4
            return result

        text_parts = []
        target_parts = []

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""

                if page_text.strip():
                    text_parts.append(f"\n=== PDF PAGE {page_index} TEXT ===\n{page_text}")

                tables = page.extract_tables(
                    table_settings={
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "intersection_tolerance": 10,
                        "snap_tolerance": 6,
                        "join_tolerance": 6,
                        "edge_min_length": 15,
                        "min_words_vertical": 1,
                        "min_words_horizontal": 1,
                    }
                )

                for table_index, table in enumerate(tables, start=1):
                    if not table:
                        continue

                    table_text = self._table_to_text(
                        table=table,
                        title=f"PDF PAGE {page_index} TABLE {table_index}",
                    )

                    if table_text:
                        text_parts.append(table_text)

                    groups_in_table = self._detect_groups_in_table(table)
                    detected_groups.update(groups_in_table)

                    target_context = self._target_context_from_table(
                        table=table,
                        group_name=group_name,
                        title=f"PDF PAGE {page_index} TABLE {table_index}",
                    )

                    if target_context:
                        target_parts.append(target_context)
                        result["debug"]["target_group_found_in_tables"] = True

        result["text_context"] = "\n\n".join(text_parts).strip()
        result["target_context"] = "\n\n".join(target_parts).strip()
        result["debug"]["detected_groups"] = sorted(detected_groups)
        result["debug"]["is_complex_pdf"] = len(detected_groups) >= 4

        return result

    def _detect_groups_from_pdf_words(self, file_bytes: bytes) -> set[str]:
        try:
            import fitz
        except ImportError:
            return set()

        groups = set()

        document = fitz.open(stream=file_bytes, filetype="pdf")

        for page in document:
            words = page.get_text("words") or []

            for item in words:
                text = self._clean_cell(item[4])

                if self._looks_like_group(text):
                    groups.add(text)

        document.close()

        return groups

    def _render_pdf_pages_to_images(self, file_bytes: bytes) -> list[dict[str, Any]]:
        try:
            import fitz
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("Для PDF потрібно встановити: pip install pymupdf pillow") from exc

        document = fitz.open(stream=file_bytes, filetype="pdf")
        images = []

        for page_index, page in enumerate(document, start=1):
            matrix = fitz.Matrix(3, 3)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image_bytes = pixmap.tobytes("png")
            image = Image.open(io.BytesIO(image_bytes))

            images.append(
                {
                    "page_number": page_index,
                    "mime_type": "image/png",
                    "base64": base64.b64encode(image_bytes).decode("utf-8"),
                    "width": image.width,
                    "height": image.height,
                }
            )

        document.close()
        return images

    # --------------------------------------------------
    # EXCEL
    # --------------------------------------------------

    def _extract_excel(
        self,
        filename: str,
        file_bytes: bytes,
        group_name: str,
        extension: str,
    ) -> dict[str, Any]:
        result = {
            "filename": filename,
            "extension": extension,
            "text_context": "",
            "target_context": "",
            "images": [],
            "debug": {
                "detected_groups": [],
                "target_group_found_in_tables": False,
                "used_extractors": ["excel_cells"],
                "is_complex_pdf": False,
            },
        }

        if extension == "xlsx":
            return self._extract_xlsx(file_bytes, group_name, result)

        return self._extract_xls(file_bytes, group_name, result)

    def _extract_xlsx(
        self,
        file_bytes: bytes,
        group_name: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        from openpyxl import load_workbook
        from openpyxl.utils import get_column_letter

        workbook = load_workbook(io.BytesIO(file_bytes), data_only=True)

        text_parts = []
        target_parts = []
        detected_groups = set()

        for sheet in workbook.worksheets:
            text_parts.append(f"\n=== EXCEL SHEET: {sheet.title} ===")

            matrix = []

            for row_index in range(1, sheet.max_row + 1):
                row_values = []
                text_row_values = []

                for col_index in range(1, sheet.max_column + 1):
                    cell = sheet.cell(row=row_index, column=col_index)
                    cleaned = self._clean_cell(cell.value)
                    row_values.append(cleaned)

                    if cleaned:
                        coordinate = f"{get_column_letter(col_index)}{row_index}"
                        text_row_values.append(f"{coordinate}={cleaned}")

                matrix.append(row_values)

                if text_row_values:
                    text_parts.append(" | ".join(text_row_values))

            detected_groups.update(self._detect_groups_in_table(matrix))

            target_context = self._target_context_from_table(
                table=matrix,
                group_name=group_name,
                title=f"EXCEL SHEET {sheet.title}",
            )

            if target_context:
                target_parts.append(target_context)
                result["debug"]["target_group_found_in_tables"] = True

        result["text_context"] = "\n".join(text_parts).strip()
        result["target_context"] = "\n\n".join(target_parts).strip()
        result["debug"]["detected_groups"] = sorted(detected_groups)

        return result

    def _extract_xls(
        self,
        file_bytes: bytes,
        group_name: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        text_parts = []
        target_parts = []
        detected_groups = set()

        try:
            excel = pd.ExcelFile(io.BytesIO(file_bytes), engine="xlrd")
        except Exception:
            excel = pd.ExcelFile(io.BytesIO(file_bytes))

        for sheet_name in excel.sheet_names:
            df = pd.read_excel(
                io.BytesIO(file_bytes),
                sheet_name=sheet_name,
                header=None,
                dtype=str,
            )

            text_parts.append(f"\n=== EXCEL SHEET: {sheet_name} ===")
            matrix = []

            for row_index, row in df.iterrows():
                row_values = []
                text_row_values = []

                for col_index, value in enumerate(row.tolist()):
                    cleaned = self._clean_cell(value)
                    row_values.append(cleaned)

                    if cleaned:
                        text_row_values.append(f"R{row_index + 1}C{col_index + 1}={cleaned}")

                matrix.append(row_values)

                if text_row_values:
                    text_parts.append(" | ".join(text_row_values))

            detected_groups.update(self._detect_groups_in_table(matrix))

            target_context = self._target_context_from_table(
                table=matrix,
                group_name=group_name,
                title=f"EXCEL SHEET {sheet_name}",
            )

            if target_context:
                target_parts.append(target_context)
                result["debug"]["target_group_found_in_tables"] = True

        result["text_context"] = "\n".join(text_parts).strip()
        result["target_context"] = "\n\n".join(target_parts).strip()
        result["debug"]["detected_groups"] = sorted(detected_groups)

        return result

    # --------------------------------------------------
    # DOCX
    # --------------------------------------------------

    def _extract_docx(
        self,
        filename: str,
        file_bytes: bytes,
        group_name: str,
    ) -> dict[str, Any]:
        from docx import Document

        result = {
            "filename": filename,
            "extension": "docx",
            "text_context": "",
            "target_context": "",
            "images": [],
            "debug": {
                "detected_groups": [],
                "target_group_found_in_tables": False,
                "used_extractors": ["docx_text", "docx_tables"],
                "is_complex_pdf": False,
            },
        }

        document = Document(io.BytesIO(file_bytes))
        parts = []
        target_parts = []
        detected_groups = set()

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()

            if text:
                parts.append(text)

        for table_index, table in enumerate(document.tables, start=1):
            parts.append(f"\n=== DOCX TABLE {table_index} ===")
            matrix = []

            for row_index, row in enumerate(table.rows, start=1):
                row_values = []
                text_row_values = []

                for col_index, cell in enumerate(row.cells, start=1):
                    cleaned = self._clean_cell(cell.text)
                    row_values.append(cleaned)

                    if cleaned:
                        text_row_values.append(f"R{row_index}C{col_index}={cleaned}")

                matrix.append(row_values)

                if text_row_values:
                    parts.append(" | ".join(text_row_values))

            detected_groups.update(self._detect_groups_in_table(matrix))

            target_context = self._target_context_from_table(
                table=matrix,
                group_name=group_name,
                title=f"DOCX TABLE {table_index}",
            )

            if target_context:
                target_parts.append(target_context)
                result["debug"]["target_group_found_in_tables"] = True

        result["text_context"] = "\n".join(parts).strip()
        result["target_context"] = "\n\n".join(target_parts).strip()
        result["debug"]["detected_groups"] = sorted(detected_groups)

        return result

    # --------------------------------------------------
    # TABLE HELPERS
    # --------------------------------------------------

    def _target_context_from_table(
        self,
        table: list[list[Any]],
        group_name: str,
        title: str,
    ) -> str:
        if not group_name:
            return ""

        header_info = self._find_header_and_group_column(table, group_name)

        if not header_info:
            return ""

        header_row_index, group_col_index = header_info

        lines = [
            f"\n=== TARGET GROUP CONTEXT: {title} ===",
            f"TARGET_GROUP: {group_name}",
            "Format: ROW | DAY | PAIR | TIME | TARGET_GROUP_CELL",
        ]

        current_day = ""

        for row_index in range(header_row_index + 1, len(table)):
            row = table[row_index] or []

            day_cell = self._find_day_in_row(row)
            pair = self._find_pair_in_row(row)
            time = self._find_time_in_row(row)
            target_cell = self._safe_table_cell(row, group_col_index)

            normalized_day = self._normalize_day_label(day_cell)

            if normalized_day:
                current_day = normalized_day

            if not target_cell:
                continue

            lines.append(
                f"ROW {row_index + 1} | DAY={current_day or day_cell} | "
                f"PAIR={pair} | TIME={time} | CELL={target_cell}"
            )

        if len(lines) <= 3:
            return ""

        return "\n".join(lines)

    def _find_header_and_group_column(
        self,
        table: list[list[Any]],
        group_name: str,
    ) -> tuple[int, int] | None:
        normalized_target = self._normalize_group(group_name)

        for row_index, row in enumerate(table[:25]):
            if not row:
                continue

            for col_index, cell in enumerate(row):
                if self._normalize_group(cell) == normalized_target:
                    return row_index, col_index

        return None

    def _find_day_in_row(self, row: list[Any]) -> str:
        for index in range(min(5, len(row))):
            cell = self._safe_table_cell(row, index)

            if self._normalize_day_label(cell):
                return cell

        return self._safe_table_cell(row, 0)

    def _find_pair_in_row(self, row: list[Any]) -> str:
        for index in range(min(5, len(row))):
            cell = self._safe_table_cell(row, index)

            if re.fullmatch(r"\d{1,2}", cell):
                number = int(cell)

                if 1 <= number <= 12:
                    return cell

            if re.search(r"\b\d{1,2}\s*(?:пара|п\.)\b", cell.lower()):
                return cell

        return self._safe_table_cell(row, 1)

    def _find_time_in_row(self, row: list[Any]) -> str:
        for index in range(min(6, len(row))):
            cell = self._safe_table_cell(row, index)

            if self._looks_like_time_range(cell):
                return cell

        return self._safe_table_cell(row, 2)

    def _looks_like_time_range(self, value: str) -> bool:
        text = str(value or "").replace(".", ":")
        return bool(re.search(r"\d{1,2}:\d{2}\s*[-–—]\s*\d{1,2}:\d{2}", text))

    def _table_to_text(self, table: list[list[Any]], title: str) -> str:
        lines = [f"\n=== {title} ==="]

        for row_index, row in enumerate(table, start=1):
            row_values = []

            for col_index, cell in enumerate(row or [], start=1):
                cleaned = self._clean_cell(cell)

                if cleaned:
                    row_values.append(f"C{col_index}={cleaned}")

            if row_values:
                lines.append(f"R{row_index}: " + " | ".join(row_values))

        return "\n".join(lines) if len(lines) > 1 else ""

    def _detect_groups_in_table(self, table: list[list[Any]]) -> set[str]:
        groups = set()

        for row in table[:30]:
            if not row:
                continue

            for cell in row:
                cleaned = self._clean_cell(cell)

                if self._looks_like_group(cleaned):
                    groups.add(cleaned)

        return groups

    def _looks_like_group(self, value: str) -> bool:
        text = str(value or "").strip()

        if not text:
            return False

        return bool(
            re.fullmatch(
                r"[A-Za-zА-Яа-яІіЇїЄєҐґ]{2,8}\s*[-–—]?\s*\d{1,4}\s*[A-Za-zА-Яа-яІіЇїЄєҐґ]?",
                text,
            )
        )

    # --------------------------------------------------
    # GENERAL HELPERS
    # --------------------------------------------------

    def _image_to_payload(
        self,
        filename: str,
        file_bytes: bytes,
        page_number: int,
    ) -> dict[str, Any]:
        mime_type = mimetypes.guess_type(filename)[0] or "image/png"

        return {
            "page_number": page_number,
            "mime_type": mime_type,
            "base64": base64.b64encode(file_bytes).decode("utf-8"),
        }

    def _safe_table_cell(self, row: list[Any], index: int) -> str:
        if index >= len(row):
            return ""

        return self._clean_cell(row[index])

    def _clean_cell(self, value: Any) -> str:
        if value is None:
            return ""

        try:
            if pd.isna(value):
                return ""
        except Exception:
            pass

        text = str(value)
        text = text.replace("\r", " ")
        text = text.replace("\n", " ")
        text = text.replace("\u00a0", " ")
        text = text.replace("￾", "-")
        text = re.sub(r"\s+", " ", text)

        return text.strip()

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

        replacements = {
            "і": "i",
            "ї": "i",
            "є": "e",
            "ґ": "g",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text.strip()

    def _normalize_day_label(self, value: Any) -> str:
        text = str(value or "").lower()
        text = text.replace("\n", "")
        text = text.replace(" ", "")
        text = text.replace("’", "'")
        text = text.replace("`", "'")
        text = text.replace("ʼ", "'")

        day_map = {
            "понеділок": "Понеділок",
            "понедiлок": "Понеділок",
            "вівторок": "Вівторок",
            "вiвторок": "Вівторок",
            "середа": "Середа",
            "четвер": "Четвер",
            "п'ятниця": "П’ятниця",
            "пятниця": "П’ятниця",
            "субота": "Субота",
            "неділя": "Неділя",
            "недiля": "Неділя",
        }

        for raw, normalized in day_map.items():
            if raw.replace(" ", "") in text:
                return normalized

        if "понед" in text:
            return "Понеділок"

        if "вівт" in text or "вiвт" in text:
            return "Вівторок"

        if "серед" in text:
            return "Середа"

        if "четв" in text:
            return "Четвер"

        if "пятн" in text or "п'ятн" in text:
            return "П’ятниця"

        if "суб" in text:
            return "Субота"

        if "нед" in text:
            return "Неділя"

        return ""

    def _get_extension(self, filename: str) -> str:
        if "." not in filename:
            return ""

        return filename.rsplit(".", 1)[-1].lower().strip()