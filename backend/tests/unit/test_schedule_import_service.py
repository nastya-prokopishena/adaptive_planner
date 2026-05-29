from backend.application.schedule_import_service import ScheduleImportService


def make_service():
    return ScheduleImportService.__new__(ScheduleImportService)


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
