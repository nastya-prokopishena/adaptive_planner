import pytest

from backend.infrastructure.ml.dataset_builder.llm_dataset_relabeler import LLMDatasetRelabeler
from backend.infrastructure.ml.dataset_builder.llm_difficulty5_generator import (
    LLMDifficulty5Generator,
)
from backend.infrastructure.ml.dataset_builder.llm_task_generator import LLMTaskGenerator


@pytest.mark.parametrize(
    ("service_factory", "method_name"),
    [
        (LLMDatasetRelabeler, "_clean_json"),
        (LLMDifficulty5Generator, "_clean_json"),
        (LLMTaskGenerator, "_clean_json_response"),
    ],
)
def test_clean_json_blocks(service_factory, method_name):
    service = service_factory()
    clean_method = getattr(service, method_name)

    assert clean_method("```json\n[]\n```") == "[]"
