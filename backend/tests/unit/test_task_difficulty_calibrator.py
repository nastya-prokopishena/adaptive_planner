from backend.infrastructure.ml.dataset_builder.task_difficulty_calibrator import (
    TaskDifficultyCalibrator,
)


def test_calibrate_project():
    calibrator = TaskDifficultyCalibrator()

    result = calibrator.calibrate(
        prediction=2,
        text="реалізувати backend api та документація",
        task_type="project",
    )

    assert result >= 4


def test_calibrate_easy():
    calibrator = TaskDifficultyCalibrator()

    result = calibrator.calibrate(
        prediction=5,
        text="прочитати короткий текст",
        task_type="reading",
    )

    assert result <= 2


def test_count_steps():
    calibrator = TaskDifficultyCalibrator()

    text = "1. виконати\n2. створити\n- описати"

    assert calibrator._count_steps(text) >= 3
