from typing import Any

from backend.domain.factories.file_extractor_factory import FileExtractorFactory


class ScheduleFileExtractorService:
    def extract(
        self,
        filename: str,
        file_bytes: bytes,
        group_name: str = "",
    ) -> dict[str, Any]:
        extractor = FileExtractorFactory.create(filename)

        result = extractor.extract(
            filename=filename,
            file_bytes=file_bytes,
        )

        result.setdefault("debug", {})
        result["debug"]["target_group"] = group_name or ""

        return result

    def extract_text_input(self, raw_text: str) -> dict[str, Any]:
        text = str(raw_text or "")

        if len(text) > 160_000:
            text = text[:160_000] + "\n\n--- TEXT TRUNCATED ---"

        return {
            "filename": "manual_text",
            "extension": "txt",
            "text_context": text,
            "pages": [],
            "tables": [],
            "debug": {
                "extractor": "manual_text",
                "text_chars": len(text),
            },
        }
