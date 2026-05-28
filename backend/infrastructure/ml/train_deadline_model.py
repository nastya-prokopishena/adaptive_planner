import os

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

DATASET_PATH = "backend/infrastructure/ml/datasets/processed/" "deadline_recommendation_dataset.csv"

MODEL_PATH = "backend/infrastructure/ml/models/deadline_model.joblib"

FEATURE_COLUMNS = [
    "estimated_duration_hours",
    "difficulty_score",
    "priority_score",
    "task_type_score",
    "subject_has_events",
    "hours_until_next_subject_event",
    "day_load_score",
    "free_hours_today",
    "days_until_deadline",
]

TARGET_COLUMN = "recommended_deadline_hours"


def train_deadline_model():
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(
            "Dataset not found. Run: "
            "python -m backend.infrastructure.ml.dataset_builder.generate_deadline_dataset"
        )

    data = pd.read_csv(DATASET_PATH)

    data = data.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN])

    x = data[FEATURE_COLUMNS]
    y = data[TARGET_COLUMN]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
    )

    model = RandomForestRegressor(
        n_estimators=180,
        random_state=42,
        max_depth=12,
    )

    model.fit(x_train, y_train)

    predictions = model.predict(x_test)

    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    print("Deadline model trained successfully")
    print(f"Dataset path: {DATASET_PATH}")
    print(f"Model path: {MODEL_PATH}")
    print(f"Rows: {len(data)}")

    if "data_source" in data.columns:
        print("Data sources:")
        print(data["data_source"].value_counts().to_string())

    print(f"MAE: {round(mae, 2)} hours")
    print(f"R2: {round(r2, 3)}")


if __name__ == "__main__":
    train_deadline_model()
