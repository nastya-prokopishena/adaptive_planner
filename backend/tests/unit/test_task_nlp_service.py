from backend.application.task_nlp_service import TaskNLPService


class FakeDifficultyService:
    def predict_difficulty(self, text, task_type="other", subject="Інше"):
        return 3

    def get_model_info(self):
        return {"loaded": True}


def make_service(use_real_init=False):
    if use_real_init:
        service = TaskNLPService()
        service.difficulty_ml_service = FakeDifficultyService()
        return service

    service = TaskNLPService.__new__(TaskNLPService)
    service.difficulty_ml_service = FakeDifficultyService()
    return service


def test_task_type_deadline_keywords_and_helper_rules():
    service = make_service()

    task_type_cases = [
        ("Лабораторна робота №1", "laboratory"),
        ("Самостійна робота", "reading"),
        ("Контрольна робота", "exam_preparation"),
        ("Іспит з дисципліни", "exam_preparation"),
        ("Проєкт з архітектури", "project"),
        ("Практична робота №2", "homework"),
    ]

    for text, expected in task_type_cases:
        assert service._detect_task_type(text) == expected

    assert service._extract_deadline("Здати до 15.06.2026") == "15.06.2026"
    assert service._extract_deadline("без дедлайну") is None

    keywords = service._extract_keywords(
        "Розробити Python Flask застосунок, створити API, протестувати систему."
    )

    assert "python" in keywords or "flask" in keywords or len(keywords) > 0


def test_difficulty_and_duration_rules():
    service = make_service(use_real_init=True)

    difficulty_cases = [
        (
            2,
            "створити систему та розробити застосунок з ci/cd pipeline",
            "project",
            4,
            5,
        ),
        (5, "прочитати короткий текст", "reading", 1, 2),
        (2, "оформити звіт та проаналізувати результати", "laboratory", 3, 5),
    ]

    for difficulty, text, task_type, min_score, max_score in difficulty_cases:
        result = service._calibrate_difficulty(
            difficulty=difficulty,
            text=text,
            task_type=task_type,
        )
        assert min_score <= result <= max_score

    duration_cases = [
        ("прочитати матеріал", "reading", 5, 0.5, 2.0),
        ("реалізувати розробити створити систему", "project", 5, 6.0, 24.0),
        ("оформити звіт", "laboratory", 3, 2.5, 8.0),
    ]

    for text, task_type, difficulty, min_hours, max_hours in duration_cases:
        duration = service._estimate_duration_hours(
            text=text,
            task_type=task_type,
            difficulty=difficulty,
        )
        assert min_hours <= duration <= max_hours


def test_analyze_returns_expected_task_fields():
    service = make_service(use_real_init=True)

    result = service.analyze(
        """
        Лабораторна робота №1
        з дисципліни Програмування
        Мета: навчитись працювати з системою.
        Завдання: реалізувати програмний продукт, проаналізувати результати,
        оформити звіт та здати до 15.06.2026.
        """,
        subject_name="Програмування",
    )

    assert result["subject"] == "Програмування"
    assert result["task_type"] == "laboratory"
    assert result["difficulty_score"] >= 1
    assert result["estimated_duration_hours"] >= 0.5
    assert result["deadline"] is not None


def test_analyze_detects_laboratory_subject_title_and_many_blocks():
    service = make_service(use_real_init=True)

    text = """
    Лабораторна робота №4 «Побудова вебзастосунку»
    з дисципліни Архітектура програмного забезпечення
    Мета роботи: ознайомитися з архітектурними підходами.
    Завдання: створити вебзастосунок, розробити API, проаналізувати результати,
    оформити звіт та продемонструвати роботу системи до 28.05.2026.
    """

    result = service.analyze(text)

    assert "Лабораторна робота" in result["title"]
    assert result["subject"] == "Архітектура програмного забезпечення"
    assert result["task_type"] == "laboratory"
    assert result["difficulty_score"] >= 3
    assert result["estimated_duration_hours"] >= 2.5
    assert result["deadline"] is not None

    long_text = (
        """
    --- PAGE 1 ---
    Зміст
    Лабораторна робота №1 ................................ 2
    Лабораторна робота №2 ................................ 4
    --- PAGE 2 ---
    Лабораторна робота №1
    Мета роботи: навчитися працювати з файлами.
    Завдання: створити програму, виконати аналіз, оформити звіт.
    """
        + (" Додатковий опис." * 40)
        + """
    --- PAGE 4 ---
    Лабораторна робота №2
    Мета роботи: навчитися працювати з базою даних.
    Завдання: розробити моделі, створити запити, проаналізувати результати.
    """
        + (" Додатковий опис." * 40)
    )

    results = service.analyze_many(long_text, subject_name="Software")

    assert len(results) >= 1
    assert all(item["subject"] == "Software" for item in results)
