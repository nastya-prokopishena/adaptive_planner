import pytest

from backend.application.schedule_text_parser_service import ScheduleTextParserService
from backend.application.task_nlp_service import TaskNLPService


@pytest.mark.performance
def test_task_nlp_analyze_many_performance(benchmark):
    service = TaskNLPService()

    text = (
        """
    Лабораторна робота №1.
    Мета: навчитись працювати з алгоритмами.
    Завдання: реалізувати програму, проаналізувати результати,
    оформити звіт та здати до 15.06.2026.
    """
        * 10
    )

    result = benchmark(service.analyze_many, text=text, subject_name="Програмування")

    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.performance
def test_schedule_text_parser_performance(benchmark):
    service = ScheduleTextParserService()

    text = (
        """
ПОДІЯ:
День: понеділок
Пара: 1
Час: 08:30 - 09:50
Предмет: Програмування
Тип: лекція
Викладач: Іваненко
Аудиторія: 101
Група: ФЕП-42
Підгрупа:
Тижні: щотижня
"""
        * 20
    )

    result = benchmark(
        service.parse_ai_text,
        text,
        target_group="ФЕП-42",
        target_subgroup="",
    )

    assert isinstance(result, list)
