from backend.infrastructure.ml.dataset_builder.html_task_extractor import HTMLTaskExtractor
from backend.infrastructure.ml.dataset_builder.pdf_downloader import PDFDownloader
from backend.infrastructure.ml.dataset_builder.pdf_text_extractor import PDFTextExtractor


def test_pdf_downloader_helpers():
    downloader = PDFDownloader()

    assert downloader._looks_like_pdf(
        b"%PDF-test",
        {"Content-Type": "application/pdf"},
        "file.pdf",
    )
    assert downloader._make_file_path("https://test.pdf", 1).endswith(".pdf")


def test_html_and_pdf_text_extractors_basic_behavior():
    assert HTMLTaskExtractor().extract_many([]) == []
    assert PDFTextExtractor(max_pages=5).max_pages == 5
