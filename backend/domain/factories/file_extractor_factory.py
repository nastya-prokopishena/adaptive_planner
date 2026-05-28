import os

from backend.infrastructure.file_extractors.docx_extractor import DocxExtractor
from backend.infrastructure.file_extractors.excel_extractor import ExcelExtractor
from backend.infrastructure.file_extractors.image_extractor import ImageExtractor
from backend.infrastructure.file_extractors.pdf_extractor import PdfExtractor
from backend.infrastructure.file_extractors.text_extractor import TextExtractor


class FileExtractorFactory:
    PDF_EXTENSIONS = {"pdf"}
    IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    DOCX_EXTENSIONS = {"docx"}
    EXCEL_EXTENSIONS = {"xlsx", "xls"}
    TEXT_EXTENSIONS = {"txt", "csv"}

    @classmethod
    def create(cls, filename: str):
        extension = cls.get_extension(filename)

        if extension in cls.PDF_EXTENSIONS:
            return PdfExtractor()

        if extension in cls.IMAGE_EXTENSIONS:
            return ImageExtractor(extension)

        if extension in cls.DOCX_EXTENSIONS:
            return DocxExtractor()

        if extension in cls.EXCEL_EXTENSIONS:
            return ExcelExtractor(extension)

        if extension in cls.TEXT_EXTENSIONS:
            return TextExtractor(extension)

        raise ValueError(
            f"Формат .{extension} не підтримується. "
            "Підтримуються PDF, фото, Excel, DOCX, TXT, CSV."
        )

    @staticmethod
    def get_extension(filename: str) -> str:
        _, extension = os.path.splitext(filename or "")
        return extension.replace(".", "").lower().strip()
