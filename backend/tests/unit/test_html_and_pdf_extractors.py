from backend.infrastructure.ml.dataset_builder.html_task_extractor import HTMLTaskExtractor
from backend.infrastructure.ml.dataset_builder.pdf_downloader import PDFDownloader
from backend.infrastructure.ml.dataset_builder.pdf_text_extractor import PDFTextExtractor


def test_pdf_looks_like_pdf():
    downloader = PDFDownloader()

    assert downloader._looks_like_pdf(
        b"%PDF-test",
        {"Content-Type": "application/pdf"},
        "file.pdf",
    )


def test_make_file_path():
    downloader = PDFDownloader()

    path = downloader._make_file_path("https://test.pdf", 1)

    assert path.endswith(".pdf")


def test_html_extract_empty():
    extractor = HTMLTaskExtractor()

    result = extractor.extract_many([])

    assert result == []


def test_pdf_text_extractor_init():
    extractor = PDFTextExtractor(max_pages=5)

    assert extractor.max_pages == 5
