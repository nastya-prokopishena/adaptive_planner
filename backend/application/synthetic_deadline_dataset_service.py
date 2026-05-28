from backend.infrastructure.ml.dataset_builder.generate_deadline_dataset import (
    OUTPUT_PATH,
    generate_dataset,
)


class SyntheticDeadlineDatasetService:
    def save_csv(self):
        generate_dataset()
        return OUTPUT_PATH
