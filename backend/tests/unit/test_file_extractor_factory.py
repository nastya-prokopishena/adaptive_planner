import pytest

from backend.domain.factories.file_extractor_factory import FileExtractorFactory
from backend.infrastructure.file_extractors.docx_extractor import DocxExtractor
from backend.infrastructure.file_extractors.excel_extractor import ExcelExtractor
from backend.infrastructure.file_extractors.image_extractor import ImageExtractor
from backend.infrastructure.file_extractors.pdf_extractor import PdfExtractor
from backend.infrastructure.file_extractors.text_extractor import TextExtractor


def test_factory_returns_pdf_extractor():
    assert isinstance(FileExtractorFactory.create("schedule.pdf"), PdfExtractor)


def test_factory_returns_image_extractor():
    assert isinstance(FileExtractorFactory.create("photo.png"), ImageExtractor)


def test_factory_returns_docx_extractor():
    assert isinstance(FileExtractorFactory.create("schedule.docx"), DocxExtractor)


def test_factory_returns_excel_extractor():
    assert isinstance(FileExtractorFactory.create("schedule.xlsx"), ExcelExtractor)


def test_factory_returns_text_extractor():
    assert isinstance(FileExtractorFactory.create("schedule.txt"), TextExtractor)


def test_factory_rejects_unknown_format():
    with pytest.raises(ValueError):
        FileExtractorFactory.create("archive.zip")
