from backend.infrastructure.ml.dataset_builder.generate_deadline_dataset import (
    generate_dataset,
    OUTPUT_PATH,
)


class SyntheticDeadlineDatasetService:
    def save_csv(self):
        generate_dataset()
        return OUTPUT_PATH