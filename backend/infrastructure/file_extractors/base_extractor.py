import re
from typing import Any


class BaseExtractor:
    MAX_TEXT_CHARS = 160_000

    def _truncate_text(self, text: str) -> str:
        text = str(text or "")

        if len(text) <= self.MAX_TEXT_CHARS:
            return text

        return text[: self.MAX_TEXT_CHARS] + "\n\n--- TEXT TRUNCATED ---"

    def _clean_text(self, value: Any) -> str:
        if value is None:
            return ""

        text = str(value)
        text = text.replace("\r", " ")
        text = text.replace("\u00a0", " ")
        text = text.replace("￾", "-")
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _text_result(
        self,
        filename: str,
        extension: str,
        text: str,
        extractor_name: str,
        tables=None,
    ) -> dict[str, Any]:
        text = self._truncate_text(text)

        return {
            "filename": filename,
            "extension": extension,
            "text_context": text,
            "pages": [],
            "tables": tables or [],
            "debug": {
                "extractor": extractor_name,
                "text_chars": len(text),
            },
        }
