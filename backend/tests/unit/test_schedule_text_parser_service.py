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
