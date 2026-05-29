from backend.application.task_nlp_service import TaskNLPService


def make_service():
    service = TaskNLPService.__new__(TaskNLPService)

    class DummyDifficultyService:
        def predict_difficulty(self, text, task_type="other", subject="Інше"):
            return 3

    service.difficulty_ml_service = DummyDifficultyService()
    return service


def test_detect_task_type_variants():
    service = make_service()

    assert service._detect_task_type("Лабораторна робота №1") == "laboratory"
    assert service._detect_task_type("Самостійна робота") == "reading"
    assert service._detect_task_type("Контрольна робота") == "exam_preparation"
    assert service._detect_task_type("Проєкт з архітектури") == "project"


def test_extract_deadline_and_keywords():
    service = make_service()

    assert service._extract_deadline("Здати до 15.06.2026") == "15.06.2026"

    keywords = service._extract_keywords(
        "реалізувати систему планування задач та проаналізувати результати"
    )

    assert "реалізувати" in keywords or len(keywords) > 0


def test_calibrate_difficulty_raises_for_project_markers():
    service = make_service()

    result = service._calibrate_difficulty(
        difficulty=2,
        text="створити систему та розробити застосунок з ci/cd pipeline",
        task_type="project",
    )

    assert result >= 4


def test_estimate_duration_limits_reading_and_project():
    service = make_service()

    reading = service._estimate_duration_hours(
        text="прочитати матеріал",
        task_type="reading",
        difficulty=2,
    )

    project = service._estimate_duration_hours(
        text="реалізувати розробити створити систему",
        task_type="project",
        difficulty=5,
    )

    assert reading <= 2
    assert project >= 6


def test_analyze_returns_expected_task_fields():
    service = make_service()

    result = service.analyze(
        """
        Лабораторна робота №1
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
