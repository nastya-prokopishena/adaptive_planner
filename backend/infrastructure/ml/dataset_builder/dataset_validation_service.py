import os
import pandas as pd


class DatasetValidationService:
    def __init__(self):
        self.dataset_path = (
            "backend/infrastructure/ml/datasets/processed/task_difficulty_dataset.csv"
        )

    def get_tasks(self, status="pending", limit=30):
        df = self._load_dataset()

        if "id" not in df.columns:
            df = self._ensure_columns(df)

        if status != "all":
            df = df[df["validation_status"] == status]

        return df.head(limit).to_dict(orient="records")

    def update_task(self, task_id, data):
        df = self._load_dataset()
        df = self._ensure_columns(df)

        task_id = int(task_id)

        index_list = df.index[df["id"] == task_id].tolist()

        if not index_list:
            return None

        index = index_list[0]

        editable_fields = [
            "text",
            "subject",
            "task_type",
            "difficulty",
            "validation_status",
            "validation_note",
        ]

        for field in editable_fields:
            if field in data:
                df.at[index, field] = data[field]

        self._save_dataset(df)

        return df.loc[index].to_dict()

    def _load_dataset(self):
        if not os.path.exists(self.dataset_path):
            raise FileNotFoundError(self.dataset_path)

        return pd.read_csv(self.dataset_path)

    def _ensure_columns(self, df):
        df = df.copy()

        if "id" not in df.columns:
            df.insert(0, "id", range(1, len(df) + 1))

        if "validation_status" not in df.columns:
            df["validation_status"] = "pending"

        if "validation_note" not in df.columns:
            df["validation_note"] = ""

        self._save_dataset(df)

        return df

    def _save_dataset(self, df):
        df.to_csv(self.dataset_path, index=False, encoding="utf-8")