import csv
import io

from backend.domain.interfaces.file_extractor import FileExtractor
from backend.infrastructure.file_extractors.base_extractor import BaseExtractor


class TextExtractor(BaseExtractor, FileExtractor):
    def __init__(self, extension: str):
        self.extension = extension

    def extract(self, filename: str, file_bytes: bytes):
        decoded = self._decode_bytes(file_bytes)

        if self.extension == "csv":
            reader = csv.reader(io.StringIO(decoded))
            lines = []

            for row in reader:
                lines.append(" | ".join(self._clean_text(cell) for cell in row))

            text = "\n".join(lines)
        else:
            text = decoded

        return self._text_result(
            filename=filename,
            extension=self.extension,
            text=text,
            extractor_name=f"{self.extension}_text_strategy",
            tables=[],
        )

    def _decode_bytes(self, file_bytes: bytes) -> str:
        for encoding in ["utf-8-sig", "utf-8", "cp1251", "latin-1"]:
            try:
                return file_bytes.decode(encoding)
            except Exception:
                continue

        return file_bytes.decode("utf-8", errors="ignore")
