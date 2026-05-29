from backend.application.schedule_text_parser_service import ScheduleTextParserService


def test_schedule_text_parser_parses_pipe_table_for_target_group():
    service = ScheduleTextParserService()

    ai_text = """
    день | пара | час | предмет | тип | викладач | аудиторія | група | підгрупа | тижні
    Понеділок | 1 | 08:30-09:50 | Архітектура ПЗ | лекція | Іваненко | 101 | ФеП-42 | | щотижня
    Понеділок | 2 | 10:10-11:30 | Інша пара | лекція | Іваненко | 102 | ФеП-41 | | щотижня
    """

    events = service.parse_ai_text(
        ai_text=ai_text,
        target_group="ФеП-42",
        target_subgroup="",
    )

    assert len(events) == 1
    assert events[0]["subject"] == "Архітектура ПЗ"
    assert events[0]["day_of_week"] == "MO"
    assert events[0]["event_type"] == "lecture"
    assert events[0]["start_time"] == "08:30"


def test_schedule_text_parser_filters_subgroup():
    service = ScheduleTextParserService()

    ai_text = """
    день | пара | час | предмет | тип | викладач | аудиторія | група | підгрупа | тижні
    Вівторок | 1 | 08:30-09:50 | Бази даних | лаб | Петренко | 201 | ФеП-42 | 1 | щотижня
    Вівторок | 1 | 08:30-09:50 | Web | лаб | Петренко | 202 | ФеП-42 | 2 | щотижня
    """

    events = service.parse_ai_text(
        ai_text=ai_text,
        target_group="ФеП-42",
        target_subgroup="1",
    )

    assert len(events) == 1
    assert events[0]["subject"] == "Бази даних"
    assert events[0]["subgroup"] == "1"


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
