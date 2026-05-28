from backend.application.task_nlp_service import TaskNLPService


class FakeDifficultyService:
    def predict_difficulty(self, text, task_type, subject):
        return 3

    def get_model_info(self):
        return {"loaded": True}


def build_service():
    service = TaskNLPService()
    service.difficulty_ml_service = FakeDifficultyService()
    return service


def test_analyze_detects_laboratory_task_fields():
    service = build_service()

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


def test_analyze_uses_provided_subject_name():
    service = build_service()

    result = service.analyze(
        "Практична робота №2. Завдання: написати програму та оформити звіт.",
        subject_name="Python",
    )

    assert result["subject"] == "Python"


def test_analyze_many_splits_long_document_into_learning_blocks():
    service = build_service()

    text = """
    --- PAGE 1 ---
    Зміст
    Лабораторна робота №1 ................................ 2
    Лабораторна робота №2 ................................ 4
    --- PAGE 2 ---
    Лабораторна робота №1
    Мета роботи: навчитися працювати з файлами.
    Завдання: створити програму, виконати аналіз, оформити звіт.
    """ + (" Додатковий опис." * 40) + """
    --- PAGE 4 ---
    Лабораторна робота №2
    Мета роботи: навчитися працювати з базою даних.
    Завдання: розробити моделі, створити запити, проаналізувати результати.
    """ + (" Додатковий опис." * 40)

    results = service.analyze_many(text, subject_name="Software")

    assert len(results) >= 1
    assert all(item["subject"] == "Software" for item in results)


def test_private_helpers_extract_keywords_and_task_type():
    service = build_service()

    keywords = service._extract_keywords(
        "Розробити Python Flask застосунок, створити API, протестувати систему."
    )

    assert "python" in keywords or "flask" in keywords
    assert service._detect_task_type("Контрольна робота та іспит") == "exam_preparation"
    assert service._detect_task_type("Самостійна робота прочитати матеріал") == "reading"


def test_calibrate_difficulty_raises_project_complexity():
    service = build_service()

    difficulty = service._calibrate_difficulty(
        difficulty=2,
        text=(
            "створити систему машинне навчання "
            "архітектура ci/cd інтеграція"
        ),
        task_type="project",
    )

    assert difficulty >= 3


def test_estimate_duration_limits_reading_task():
    service = build_service()

    duration = service._estimate_duration_hours(
        text="прочитати матеріал",
        task_type="reading",
        difficulty=5,
    )

    assert duration <= 2.0
