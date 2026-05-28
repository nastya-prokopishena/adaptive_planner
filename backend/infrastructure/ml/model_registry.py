import json
import os
from datetime import datetime

import joblib


class ModelRegistry:
    def __init__(self, model_dir="backend/infrastructure/ml/models"):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)

        self.latest_model_path = os.path.join(
            self.model_dir,
            "task_difficulty_model.pkl",
        )

        self.metadata_path = os.path.join(
            self.model_dir,
            "task_difficulty_model_metadata.json",
        )

    def save_model(self, model_bundle, metadata):
        version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        versioned_model_path = os.path.join(
            self.model_dir,
            f"task_difficulty_model_{version}.pkl",
        )

        joblib.dump(model_bundle, versioned_model_path)
        joblib.dump(model_bundle, self.latest_model_path)

        metadata = {
            **metadata,
            "version": version,
            "saved_at": datetime.utcnow().isoformat(),
            "latest_model_path": self.latest_model_path,
            "versioned_model_path": versioned_model_path,
        }

        with open(self.metadata_path, "w", encoding="utf-8") as file:
            json.dump(metadata, file, ensure_ascii=False, indent=2)

        return {
            "latest_model_path": self.latest_model_path,
            "versioned_model_path": versioned_model_path,
            "metadata_path": self.metadata_path,
            "metadata": metadata,
        }

    def load_latest_model(self):
        if not os.path.exists(self.latest_model_path):
            return None

        return joblib.load(self.latest_model_path)

    def load_metadata(self):
        if not os.path.exists(self.metadata_path):
            return None

        with open(self.metadata_path, "r", encoding="utf-8") as file:
            return json.load(file)


_cached_model = None


def get_model():
    global _cached_model

    registry = ModelRegistry()

    if _cached_model is None:
        _cached_model = registry.load_latest_model()

    return _cached_model


def get_model_metadata():
    registry = ModelRegistry()

    metadata = registry.load_metadata()

    if metadata:
        return {
            "loaded": os.path.exists(registry.latest_model_path),
            **metadata,
        }

    return {
        "loaded": os.path.exists(registry.latest_model_path),
        "model_path": registry.latest_model_path,
        "metadata_path": registry.metadata_path,
        "message": "Metadata file not found",
    }
