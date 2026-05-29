from backend.infrastructure.ml.dataset_builder.llm_dataset_relabeler import LLMDatasetRelabeler
from backend.infrastructure.ml.dataset_builder.llm_difficulty5_generator import (
    LLMDifficulty5Generator,
)
from backend.infrastructure.ml.dataset_builder.llm_task_generator import LLMTaskGenerator


def test_clean_json_relabeler():
    service = LLMDatasetRelabeler()

    result = service._clean_json("```json\n[]\n```")

    assert result == "[]"


def test_clean_json_difficulty5():
    service = LLMDifficulty5Generator()

    result = service._clean_json("```json\n[]\n```")

    assert result == "[]"


def test_clean_json_llm_generator():
    service = LLMTaskGenerator()

    result = service._clean_json_response("```json\n[]\n```")

    assert result == "[]"
