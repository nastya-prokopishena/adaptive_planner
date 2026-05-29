import json

import pytest

from backend.application.schedule_ai_reader_service import ScheduleAIReaderService


def make_service():
    service = ScheduleAIReaderService.__new__(ScheduleAIReaderService)
    service.model = "test-model"
    service.client = None
    return service


def make_page_result(page_number=1, warning="warn"):
    return {
        "page_number": page_number,
        "page_analysis": {
            "has_table": True,
            "target_group_found": True,
            "detected_group_headers": ["ФЕП-42"],
            "layout_description": "table",
        },
        "groups": [{"name": "ФЕП-42", "x1": 0.2, "x2": 0.4}],
        "rows": [],
        "cells": [],
        "warnings": [warning],
    }


def test_read_schedule_requires_group_name():
    service = make_service()

    result = service.read_schedule(
        extraction={"text_context": "розклад"},
        group_name="",
    )

    assert result["table_pages"] == []
    assert result["warnings"] == ["Не вказано групу."]


def test_read_schedule_uses_visual_pages(monkeypatch):
    service = make_service()

    calls = []

    def fake_analyze_visual_page(**kwargs):
        calls.append(kwargs)
        return make_page_result(page_number=kwargs["page_number"], warning="same")

    monkeypatch.setattr(service, "_analyze_visual_page", fake_analyze_visual_page)

    result = service.read_schedule(
        extraction={
            "pages": [
                {
                    "page": 1,
                    "page_text": "text",
                    "full_image": {"mime_type": "image/png", "base64": "abc"},
                },
                {
                    "page": 2,
                    "page_text": "without image",
                    "full_image": None,
                },
            ],
        },
        group_name=" ФЕП-42 ",
        subgroup=" 1 ",
    )

    assert len(calls) == 1
    assert result["table_pages"][0]["page_number"] == 1
    assert result["warnings"] == ["same"]
    assert result["document_analysis"]["target_group"] == "ФЕП-42"
    assert result["document_analysis"]["target_subgroup"] == "1"


def test_read_text_tables_returns_warning_for_empty_text():
    service = make_service()

    result = service._read_text_tables(
        extraction={"text_context": ""},
        group_name="ФЕП-42",
        subgroup="",
    )

    assert result["table_pages"] == []
    assert result["warnings"] == ["У файлі не знайдено тексту для аналізу."]
    assert result["document_analysis"]["schedule_kind"] == "text"


def test_read_text_tables_calls_schema_for_each_chunk(monkeypatch):
    service = make_service()
    monkeypatch.setattr(service, "TEXT_CHUNK_LIMIT", 5)

    calls = []

    def fake_call_json_schema(**kwargs):
        calls.append(kwargs)
        return make_page_result(warning=f"warn-{len(calls)}")

    monkeypatch.setattr(service, "_call_json_schema", fake_call_json_schema)

    result = service._read_text_tables(
        extraction={"text_context": "abcdefghijk"},
        group_name="ФЕП-42",
        subgroup="2",
    )

    assert len(calls) == 3
    assert [page["page_number"] for page in result["table_pages"]] == [1, 2, 3]
    assert result["warnings"] == ["warn-1", "warn-2", "warn-3"]
    assert result["document_analysis"]["target_subgroup"] == "2"


def test_split_text_returns_empty_for_blank_text():
    service = make_service()

    assert service._split_text("") == []
    assert service._split_text("   ") == []


def test_split_text_returns_single_chunk_when_under_limit():
    service = make_service()

    assert service._split_text("abc") == ["abc"]


def test_split_text_splits_long_text(monkeypatch):
    service = make_service()
    monkeypatch.setattr(service, "TEXT_CHUNK_LIMIT", 4)

    assert service._split_text("abcdefghij") == ["abcd", "efgh", "ij"]


def test_table_page_schema_contains_required_top_level_fields():
    service = make_service()

    schema = service._table_page_schema()

    assert schema["type"] == "object"
    assert "groups" in schema["required"]
    assert "cells" in schema["required"]
    assert schema["properties"]["cells"]["items"]["properties"]["parsed_events"]["items"]


def test_parsed_event_schema_contains_expected_enums():
    service = make_service()

    schema = service._parsed_event_schema()

    assert "lecture" in schema["properties"]["event_type"]["enum"]
    assert "subgroup" in schema["properties"]["scope"]["enum"]
    assert "needs_review" in schema["required"]


def test_call_json_schema_parses_client_output():
    service = make_service()

    class FakeResponses:
        def create(self, **kwargs):
            return type("Response", (), {"output_text": json.dumps({"ok": True})})()

    class FakeClient:
        responses = FakeResponses()

    service.client = FakeClient()

    result = service._call_json_schema(
        content=[{"type": "input_text", "text": "hello"}],
        schema_name="test_schema",
        schema={"type": "object"},
    )

    assert result == {"ok": True}


def test_init_requires_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        ScheduleAIReaderService()
