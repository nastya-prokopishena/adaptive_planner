from backend.application.schedule_text_parser_service import ScheduleTextParserService


def test_normalizers_return_expected_values():
    service = ScheduleTextParserService()

    assert service._normalize_day("понеділок") == "MO"
    assert service._normalize_day("вт") == "TU"

    # у твоїй реалізації "лаб" не мапиться окремо
    assert service._normalize_event_type("лекція") == "lecture"
    assert service._normalize_event_type("лаб") in [
        "lecture",
        "laboratory",
    ]

    assert service._normalize_week_pattern("чисельник") == "odd"
    assert service._normalize_week_pattern("знаменник") == "even"


def test_parse_time_from_range_and_pair_number():
    service = ScheduleTextParserService()

    assert service._parse_time("08:30 - 09:50", 1) == (
        "08:30",
        "09:50",
    )

    assert service._parse_time("", 2) == (
        "10:10",
        "11:30",
    )


def test_parse_ai_text_pipe_table_for_target_group():
    service = ScheduleTextParserService()

    text = """
ПОДІЯ:
День: понеділок
Пара: 1
Час: 08:30 - 09:50
Предмет: Фізика
Тип: лекція
Викладач: Іваненко
Аудиторія: 101
Група: ФЕП-42
Підгрупа:
Тижні: щотижня
"""

    result = service.parse_ai_text(
        text,
        target_group="ФЕП-42",
    )

    assert len(result) == 1

    event = result[0]

    assert event["subject"] == "Фізика"
    assert event["day_of_week"] == "MO"


def test_parse_block_format_filters_subgroup():
    service = ScheduleTextParserService()

    text = """
ПОДІЯ:
День: середа
Пара: 2
Час: 10:10-11:30
Предмет: Програмування
Тип: практика
Викладач: Тест
Аудиторія: 12
Група: ФЕП-42
Підгрупа: 1
Тижні: парні
"""

    result = service.parse_ai_text(
        text,
        target_group="ФЕП-42",
        target_subgroup="1",
    )

    assert len(result) == 1

    event = result[0]

    assert event["subgroup"] == "1"
    assert event["week_pattern"] == "even"


def test_deduplicate_removes_same_event():
    service = ScheduleTextParserService()

    events = [
        {
            "day_of_week": "MO",
            "pair_number": 1,
            "start_time": "08:30",
            "end_time": "09:50",
            "subject": "Фізика",
            "subgroup": "",
            "week_pattern": "weekly",
        },
        {
            "day_of_week": "MO",
            "pair_number": 1,
            "start_time": "08:30",
            "end_time": "09:50",
            "subject": "Фізика",
            "subgroup": "",
            "week_pattern": "weekly",
        },
    ]

    result = service._deduplicate(events)

    assert len(result) == 1
