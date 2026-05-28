from backend.infrastructure.file_extractors.text_extractor import TextExtractor


def test_text_extractor_reads_utf8_text():
    extractor = TextExtractor("txt")

    result = extractor.extract("test.txt", "Привіт\nРозклад".encode("utf-8"))

    assert result["extension"] == "txt"
    assert "Привіт" in result["text_context"]
    assert result["debug"]["extractor"] == "txt_text_strategy"


def test_csv_extractor_converts_rows_to_pipe_text():
    extractor = TextExtractor("csv")

    result = extractor.extract("test.csv", "day,subject\nMO,Math".encode("utf-8"))

    assert "day | subject" in result["text_context"]
    assert "MO | Math" in result["text_context"]
