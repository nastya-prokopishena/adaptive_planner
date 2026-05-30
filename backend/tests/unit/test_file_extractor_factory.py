import pytest

from backend.domain.factories.file_extractor_factory import FileExtractorFactory
from backend.infrastructure.file_extractors.docx_extractor import DocxExtractor
from backend.infrastructure.file_extractors.excel_extractor import ExcelExtractor
from backend.infrastructure.file_extractors.image_extractor import ImageExtractor
from backend.infrastructure.file_extractors.pdf_extractor import PdfExtractor
from backend.infrastructure.file_extractors.text_extractor import TextExtractor


@pytest.mark.parametrize(
    ("filename", "expected_class"),
    [
        ("schedule.pdf", PdfExtractor),
        ("photo.png", ImageExtractor),
        ("schedule.docx", DocxExtractor),
        ("schedule.xlsx", ExcelExtractor),
        ("schedule.txt", TextExtractor),
    ],
)
def test_factory_returns_expected_extractor(filename, expected_class):
    assert isinstance(FileExtractorFactory.create(filename), expected_class)


def test_factory_rejects_unknown_format():
    with pytest.raises(ValueError):
        FileExtractorFactory.create("archive.zip")
