from backend.infrastructure.ml.dataset_builder.synthetic_task_generator import (
    SyntheticTaskGenerator,
)


def test_generate():
    generator = SyntheticTaskGenerator()

    rows = generator.generate(target_per_class=2)

    assert len(rows) > 0
    assert rows[0]["language"] == "uk"


def test_task_type_by_difficulty():
    generator = SyntheticTaskGenerator()

    assert generator._task_type_by_difficulty(1) in [
        "reading",
        "exam_preparation",
    ]

    assert generator._task_type_by_difficulty(5) in [
        "project",
        "laboratory",
    ]
