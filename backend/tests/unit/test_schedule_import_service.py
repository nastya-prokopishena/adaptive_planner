import pytest

from backend.application.schedule_import_service import ScheduleImportService


def make_service():
    return ScheduleImportService.__new__(ScheduleImportService)


class FakeFileExtractor:
    def extract(self, filename, file_bytes, group_name):
        return {
            "text": "schedule",
            "debug": {
                "filename": filename,
                "group_name": group_name,
                "size": len(file_bytes),
            },
        }

    def extract_text_input(self, raw_text):
        return {
            "text": raw_text,
            "debug": {
                "source": "manual_text",
            },
        }


class FakeAIReader:
    def read_schedule(self, extraction, group_name, subgroup):
        return {
            "warnings": ["AI warning"],
            "document_analysis": {
                "warnings": ["Document warning"],
                "quality": "ok",
            },
            "table_pages": [
                {
                    "page_number": 1,
                    "groups": [
                        {
                            "name": group_name,
                            "x1": 0.2,
                            "x2": 0.6,
                        }
                    ],
                    "rows": [
                        {
                            "row_id": "r1",
                            "day_of_week": "понеділок",
                            "pair_number": 1,
                            "start_time": "",
                            "end_time": "",
                        }
                    ],
                    "cells": [
                        {
                            "row_id": "r1",
                            "x1": 0.25,
                            "x2": 0.55,
                            "y1": 0.1,
                            "y2": 0.2,
                            "source_cell_type": "exact",
                            "text": "Фізика",
                            "parsed_events": [
                                {
                                    "subject": "Фізика",
                                    "event_type": "лекція",
                                    "teacher": "Іваненко",
                                    "room": "101",
                                    "subgroup": "",
                                    "subgroup_evidence": "none",
                                    "week_pattern": "",
                                    "scope": "group",
                                    "confidence": 0.95,
                                }
                            ],
                        }
                    ],
                }
            ],
        }


def test_build_preview_from_text_success():
    service = make_service()
    service.file_extractor = FakeFileExtractor()
    service.ai_reader = FakeAIReader()

    result = service.build_preview_from_text(
        raw_text="Розклад занять ФЕП-42",
        group_name="ФЕП-42",
        subgroup="",
    )

    assert result["total_found"] == 1
    assert result["events"][0]["subject"] == "Фізика"
    assert result["events"][0]["start_time"] == "08:30"
    assert result["events"][0]["end_time"] == "09:50"
    assert result["parser_mode"] == "ai_text_table_geometry_backend_group_intersection"
    assert "AI warning" in result["warnings"]
    assert "Document warning" in result["warnings"]


def test_build_preview_from_file_success():
    service = make_service()
    service.file_extractor = FakeFileExtractor()
    service.ai_reader = FakeAIReader()

    result = service.build_preview_from_file(
        filename="schedule.pdf",
        file_bytes=b"file-content",
        group_name="ФЕП-42",
        subgroup="",
    )

    assert result["total_found"] == 1
    assert result["events"][0]["group_name"] == "ФЕП-42"
    assert result["extraction_debug"]["filename"] == "schedule.pdf"
    assert result["parser_mode"] == "ai_table_geometry_backend_group_intersection"


def test_build_preview_requires_group_name():
    service = make_service()

    text_result = service.build_preview_from_text("some text", group_name="")
    file_result = service.build_preview_from_file("file.pdf", b"123", group_name="")

    assert text_result["total_found"] == 0
    assert "Вкажи групу" in text_result["error"]
    assert file_result["total_found"] == 0
    assert "Вкажи групу" in file_result["error"]


def test_build_preview_from_text_returns_error_response_on_exception():
    class BrokenExtractor:
        def extract_text_input(self, raw_text):
            raise RuntimeError("extract failed")

    service = make_service()
    service.file_extractor = BrokenExtractor()
    service.ai_reader = FakeAIReader()

    result = service.build_preview_from_text(
        raw_text="bad text",
        group_name="ФЕП-42",
    )

    assert result["total_found"] == 0
    assert result["error"] == "extract failed"


def test_events_from_ai_table_geometry_uses_previous_group_box():
    service = make_service()

    ai_result = {
        "table_pages": [
            {
                "page_number": 1,
                "groups": [
                    {
                        "name": "ФЕП-42",
                        "x1": 0.2,
                        "x2": 0.6,
                    }
                ],
                "rows": [],
                "cells": [],
            },
            {
                "page_number": 2,
                "groups": [],
                "rows": [
                    {
                        "row_id": "1",
                        "day_of_week": "вівторок",
                        "pair_number": 2,
                        "start_time": "",
                        "end_time": "",
                    }
                ],
                "cells": [
                    {
                        "row_id": "1",
                        "x1": 0.25,
                        "x2": 0.55,
                        "y1": 0.1,
                        "y2": 0.2,
                        "source_cell_type": "merged",
                        "text": "Математика",
                        "parsed_events": [
                            {
                                "subject": "Математика",
                                "event_type": "практ",
                                "teacher": "Петренко",
                                "room": "202",
                                "subgroup": "1",
                                "subgroup_evidence": "explicit",
                                "week_pattern": "парний",
                                "scope": "subgroup",
                                "confidence": 0.88,
                            }
                        ],
                    }
                ],
            },
        ]
    }

    events = service._events_from_ai_table_geometry(
        ai_result=ai_result,
        target_group="ФЕП-42",
        target_subgroup="1",
    )

    assert len(events) == 1
    assert events[0]["subject"] == "Математика"
    assert events[0]["day_of_week"] == "TU"
    assert events[0]["start_time"] == "10:10"
    assert events[0]["week_pattern"] == "even"


def test_events_from_ai_table_geometry_filters_wrong_group_and_noise():
    service = make_service()

    ai_result = {
        "table_pages": [
            {
                "page_number": 1,
                "groups": [
                    {
                        "name": "ФЕП-42",
                        "x1": 0.2,
                        "x2": 0.4,
                    }
                ],
                "rows": [
                    {
                        "row_id": "1",
                        "day_of_week": "середа",
                        "pair_number": 3,
                    }
                ],
                "cells": [
                    {
                        "row_id": "1",
                        "x1": 0.7,
                        "x2": 0.9,
                        "parsed_events": [
                            {
                                "subject": "Фізика",
                                "event_type": "лекція",
                            }
                        ],
                    },
                    {
                        "row_id": "1",
                        "x1": 0.21,
                        "x2": 0.39,
                        "parsed_events": [
                            {
                                "subject": "декан",
                                "event_type": "лекція",
                            }
                        ],
                    },
                ],
            }
        ]
    }

    events = service._events_from_ai_table_geometry(
        ai_result=ai_result,
        target_group="ФЕП-42",
        target_subgroup="",
    )

    assert events == []


def test_matches_subgroup_rejects_other_subgroup():
    service = make_service()

    event = {
        "subgroup": "2",
        "event_type": "practice",
        "scope": "subgroup",
        "subgroup_evidence": "explicit",
        "confidence": 0.9,
    }

    assert service._matches_subgroup(event, "1") is False


def test_matches_subgroup_marks_uncertain_group_event_for_review():
    service = make_service()

    event = {
        "subgroup": "",
        "event_type": "practice",
        "scope": "unknown",
        "subgroup_evidence": "none",
        "confidence": 0.95,
    }

    assert service._matches_subgroup(event, "1") is True
    assert event["needs_review"] is True
    assert event["confidence"] == 0.75


def test_resolve_same_slot_alternation_marks_odd_and_even():
    service = make_service()

    first = {
        "day_of_week": "MO",
        "start_time": "08:30",
        "end_time": "09:50",
        "pair_number": 1,
        "subgroup": "",
        "week_pattern": "weekly",
        "source_cell_type": "shared_lecture",
        "event_type": "lecture",
        "subject": "Фізика",
        "teacher": "A",
        "confidence": 0.9,
        "needs_review": False,
    }

    second = dict(first)
    second["subject"] = "Математика"

    result = service._resolve_same_slot_alternation([first, second])

    patterns = {item["week_pattern"] for item in result}

    assert patterns == {"odd", "even"}
    assert all(item["needs_review"] for item in result)


def test_mark_review_status_for_missing_day_time_and_unknown_week():
    service = make_service()

    event = {
        "day_of_week": "",
        "start_time": "",
        "end_time": "",
        "week_pattern": "unknown",
        "confidence": 0.9,
        "needs_review": False,
    }

    result = service._mark_review_status(event)

    assert result["needs_review"] is True
    assert result["confidence"] == 0.55


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("лек.", "lecture"),
        ("Л", "lecture"),
        ("лаб", "laboratory"),
        ("практ", "practice"),
        ("семінар", "seminar"),
        ("консультація", "consultation"),
        ("іспит", "exam"),
        ("залік", "credit"),
        ("невідомо", "class"),
    ],
)
def test_normalize_event_type_variants(value, expected):
    service = make_service()

    assert service._normalize_event_type(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("непарний", "odd"),
        ("н/пар", "odd"),
        ("чисельник", "odd"),
        ("парний", "even"),
        ("знаменник", "even"),
        ("custom", "custom"),
        ("unknown", "unknown"),
        ("", "weekly"),
    ],
)
def test_normalize_week_pattern_variants(value, expected):
    service = make_service()

    assert service._normalize_week_pattern(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("subgroup", "subgroup"),
        ("stream", "stream"),
        ("bad", "group"),
        ("", "group"),
    ],
)
def test_normalize_scope_variants(value, expected):
    service = make_service()

    assert service._normalize_scope(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("exact", "exact"),
        ("merged", "merged"),
        ("shared_lecture", "shared_lecture"),
        ("full_document", "full_document"),
        ("bad", "exact"),
    ],
)
def test_normalize_source_cell_type_variants(value, expected):
    service = make_service()

    assert service._normalize_source_cell_type(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("explicit", "explicit"),
        ("uncertain", "uncertain"),
        ("none", "none"),
        ("bad", "none"),
    ],
)
def test_normalize_subgroup_evidence_variants(value, expected):
    service = make_service()

    assert service._normalize_subgroup_evidence(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("MO", "MO"),
        ("понеділок", "MO"),
        ("вівторок", "TU"),
        ("середа", "WE"),
        ("четвер", "TH"),
        ("п'ятниця", "FR"),
        ("субота", "SA"),
        ("неділя", "SU"),
        ("unknown", ""),
    ],
)
def test_normalize_day_variants(value, expected):
    service = make_service()

    assert service._normalize_day(value) == expected


def test_clean_subject_removes_event_type_prefix_and_suffix():
    service = make_service()

    assert service._clean_subject("лаб. Фізика") == "Фізика"
    assert service._clean_subject("Фізика лекція") == "Фізика"


def test_build_warnings_adds_empty_events_and_review_count():
    service = make_service()

    warnings = service._build_warnings(
        ai_result={
            "warnings": ["AI warning"],
            "document_analysis": {
                "warnings": ["Document warning"],
            },
        },
        events=[
            {
                "needs_review": True,
            },
            {
                "needs_review": False,
            },
        ],
    )

    assert "AI warning" in warnings
    assert "Document warning" in warnings
    assert "1 подій потребують перевірки перед імпортом." in warnings


def test_build_warnings_for_empty_events():
    service = make_service()

    warnings = service._build_warnings(
        ai_result={},
        events=[],
    )

    assert "Не знайдено подій, які перетинають колонку потрібної групи." in warnings


def test_build_response_and_error_response():
    service = make_service()

    response = service._build_response([{"subject": "Фізика"}])
    error = service._error_response("Помилка")

    assert response["total_found"] == 1
    assert response["events"][0]["subject"] == "Фізика"
    assert response["import_id"]

    assert error["total_found"] == 0
    assert error["events"] == []
    assert error["error"] == "Помилка"
    assert error["details"] == "Помилка"


def test_normalizers_and_safe_values():
    service = make_service()

    assert service._normalize_day("п'ятниця") == "FR"
    assert service._normalize_time("0830") == "08:30"
    assert service._normalize_time("25:00") == ""
    assert service._normalize_subgroup_value("підгр. 2") == "2"
    assert service._safe_pair_number("пара 4") == 4
    assert service._safe_pair_number("99") is None
    assert service._safe_coord(2) == 1.0
    assert service._safe_confidence(2) == 1.0


def test_cell_intersects_group_true_and_false():
    service = make_service()

    assert service._cell_intersects_group(
        {"x1": 0.30, "x2": 0.50},
        {"x1": 0.40, "x2": 0.60},
    )

    assert not service._cell_intersects_group(
        {"x1": 0.10, "x2": 0.20},
        {"x1": 0.40, "x2": 0.60},
    )


def test_find_target_group_box_normalizes_group_name():
    service = make_service()

    result = service._find_target_group_box(
        groups=[{"name": "ФЕП-42", "x1": 0.2, "x2": 0.4}],
        target_group="ФЕП 42",
    )

    assert result["name"] == "ФЕП-42"


def test_matches_subgroup_allows_lecture_for_whole_group():
    service = make_service()

    event = {
        "subgroup": "",
        "event_type": "lecture",
        "scope": "group",
        "subgroup_evidence": "none",
        "confidence": 0.9,
    }

    assert service._matches_subgroup(event, "1")


def test_fill_missing_time_uses_default_pair_time():
    service = make_service()

    event = {
        "pair_number": 2,
        "start_time": "",
        "end_time": "",
        "confidence": 0.9,
        "needs_review": False,
    }

    result = service._fill_missing_time(event)

    assert result["start_time"] == "10:10"
    assert result["end_time"] == "11:30"
    assert result["needs_review"] is True


def test_is_real_study_event_filters_service_text():
    service = make_service()

    assert service._is_real_study_event({"subject": "Фізика"}) is True
    assert service._is_real_study_event({"subject": "декан"}) is False


def test_deduplicate_keeps_higher_confidence():
    service = make_service()

    low = {
        "day_of_week": "MO",
        "start_time": "08:30",
        "end_time": "09:50",
        "pair_number": 1,
        "subject": "Фізика",
        "event_type": "lecture",
        "subgroup": "",
        "week_pattern": "weekly",
        "week_range": "",
        "teacher": "",
        "room": "",
        "confidence": 0.4,
    }

    high = dict(low)
    high["confidence"] = 0.9

    result = service._deduplicate_events([low, high])

    assert len(result) == 1
    assert result[0]["confidence"] == 0.9
