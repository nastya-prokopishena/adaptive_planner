import os
import re

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import LinearSVC

from backend.infrastructure.ml.model_registry import ModelRegistry

DATASET_CANDIDATES = [
    "backend/infrastructure/ml/datasets/processed/task_difficulty_dataset_relabelled.csv",
    "backend/infrastructure/ml/datasets/processed/task_difficulty_dataset_enriched.csv",
    "backend/infrastructure/ml/datasets/processed/task_difficulty_dataset_clean.csv",
    "backend/infrastructure/ml/datasets/processed/task_difficulty_dataset.csv",
]

MODEL_DIR = "backend/infrastructure/ml/models"
MODEL_PATH = os.path.join(MODEL_DIR, "task_difficulty_model.pkl")
REPORT_PATH = os.path.join(MODEL_DIR, "task_difficulty_report.txt")


class TextFeatureExtractor(BaseEstimator, TransformerMixin):
    ACTION_WORDS = [
        "прочитати",
        "ознайомитися",
        "описати",
        "пояснити",
        "виконати",
        "розв'язати",
        "розв’язати",
        "побудувати",
        "проаналізувати",
        "порівняти",
        "дослідити",
        "обґрунтувати",
        "розробити",
        "реалізувати",
        "створити",
        "спроєктувати",
        "оптимізувати",
        "інтегрувати",
    ]

    HARD_WORDS = [
        "реалізувати",
        "розробити",
        "дослідити",
        "порівняти",
        "проаналізувати",
        "обґрунтувати",
        "оптимізувати",
        "інтегрувати",
        "спроєктувати",
        "модель",
        "система",
        "проєкт",
        "проект",
        "api",
        "backend",
        "frontend",
        "база даних",
    ]

    def fit(self, x, y=None):
        return self

    def transform(self, x):
        features = []

        for text in x:
            text = str(text)
            lower = text.lower()

            length = len(text)
            word_count = len(re.findall(r"\w+", lower))
            action_count = sum(1 for word in self.ACTION_WORDS if word in lower)
            hard_count = sum(1 for word in self.HARD_WORDS if word in lower)
            step_count = len(re.findall(r"\b\d+[\).]\s+", text))
            bullet_count = len(re.findall(r"[-•●]\s+", text))
            question_count = text.count("?")

            features.append(
                [
                    length,
                    word_count,
                    action_count,
                    hard_count,
                    step_count,
                    bullet_count,
                    question_count,
                ]
            )

        return np.array(features)


def find_dataset_path():
    for path in DATASET_CANDIDATES:
        if os.path.exists(path):
            return path

    raise FileNotFoundError("Dataset file not found")


def load_dataset():
    dataset_path = find_dataset_path()
    print(f"Using dataset: {dataset_path}")

    df = pd.read_csv(dataset_path)
    df = df.dropna(subset=["text", "difficulty"])

    df["text"] = df["text"].astype(str)
    df["subject"] = df["subject"].fillna("Інше").astype(str)
    df["task_type"] = df["task_type"].fillna("other").astype(str)
    df["difficulty"] = df["difficulty"].astype(int)

    df = df[df["difficulty"].isin([1, 2, 3, 4, 5])]
    df = df[df["text"].str.len() >= 60]
    df = df[df["text"].str.len() <= 3500]

    df["combined_text"] = (
        "Предмет: "
        + df["subject"]
        + ". Тип задачі: "
        + df["task_type"]
        + ". Завдання: "
        + df["text"]
    )

    df["difficulty_group"] = df["difficulty"].apply(to_group)

    print("Dataset size:", len(df))
    print("Difficulty distribution:")
    print(df["difficulty"].value_counts().sort_index())
    print("Group distribution:")
    print(df["difficulty_group"].value_counts())

    return df


def to_group(difficulty):
    difficulty = int(difficulty)

    if difficulty in [1, 2]:
        return "easy"

    if difficulty == 3:
        return "medium"

    return "hard"


def build_preprocessor():
    return ColumnTransformer(
        transformers=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    max_features=14000,
                    min_df=2,
                    sublinear_tf=True,
                ),
                "combined_text",
            ),
            (
                "numeric",
                Pipeline(
                    [
                        ("features", TextFeatureExtractor()),
                        ("scaler", StandardScaler()),
                    ]
                ),
                "text",
            ),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                ["subject", "task_type"],
            ),
        ],
    )


def build_logistic_pipeline():
    return Pipeline(
        [
            ("features", build_preprocessor()),
            (
                "classifier",
                LogisticRegression(
                    max_iter=4000,
                    class_weight="balanced",
                    solver="lbfgs",
                ),
            ),
        ]
    )


def build_svc_pipeline():
    return Pipeline(
        [
            ("features", build_preprocessor()),
            (
                "classifier",
                LinearSVC(
                    class_weight="balanced",
                    max_iter=8000,
                ),
            ),
        ]
    )


def evaluate_model(name, model, x_train, x_test, y_train, y_test):
    print(f"Training {name}...")

    model.fit(x_train, y_train)
    predictions = model.predict(x_test)

    accuracy = accuracy_score(y_test, predictions)

    return {
        "name": name,
        "model": model,
        "accuracy": accuracy,
        "report": classification_report(y_test, predictions, digits=4),
        "matrix": confusion_matrix(y_test, predictions),
    }


def train_model():
    df = load_dataset()

    x = df[["combined_text", "text", "subject", "task_type"]]
    y_fine = df["difficulty"]
    y_group = df["difficulty_group"]

    x_train, x_test, y_fine_train, y_fine_test, y_group_train, y_group_test = train_test_split(
        x,
        y_fine,
        y_group,
        test_size=0.2,
        random_state=42,
        stratify=y_fine,
    )

    fine_candidates = [
        ("Fine LogisticRegression", build_logistic_pipeline()),
        ("Fine LinearSVC", build_svc_pipeline()),
    ]

    fine_results = []

    for name, model in fine_candidates:
        result = evaluate_model(
            name=name,
            model=model,
            x_train=x_train,
            x_test=x_test,
            y_train=y_fine_train,
            y_test=y_fine_test,
        )

        print(f"{name} accuracy: {result['accuracy']}")
        fine_results.append(result)

    best_fine = max(fine_results, key=lambda item: item["accuracy"])

    group_candidates = [
        ("Group LogisticRegression", build_logistic_pipeline()),
        ("Group LinearSVC", build_svc_pipeline()),
    ]

    group_results = []

    for name, model in group_candidates:
        result = evaluate_model(
            name=name,
            model=model,
            x_train=x_train,
            x_test=x_test,
            y_train=y_group_train,
            y_test=y_group_test,
        )

        print(f"{name} accuracy: {result['accuracy']}")
        group_results.append(result)

    best_group = max(group_results, key=lambda item: item["accuracy"])

    bundle = {
        "model_type": "hybrid_hierarchical",
        "fine_model": best_fine["model"],
        "group_model": best_group["model"],
        "fine_accuracy": best_fine["accuracy"],
        "group_accuracy": best_group["accuracy"],
        "fine_model_name": best_fine["name"],
        "group_model_name": best_group["name"],
    }

    registry = ModelRegistry(model_dir=MODEL_DIR)

    save_result = registry.save_model(
        model_bundle=bundle,
        metadata={
            "model_name": "task_difficulty_model",
            "model_type": "hybrid_hierarchical",
            "fine_model_name": best_fine["name"],
            "group_model_name": best_group["name"],
            "fine_accuracy": best_fine["accuracy"],
            "group_accuracy": best_group["accuracy"],
            "dataset_size": len(df),
            "difficulty_distribution": {
                str(key): int(value)
                for key, value in df["difficulty"].value_counts().sort_index().items()
            },
            "group_distribution": {
                str(key): int(value) for key, value in df["difficulty_group"].value_counts().items()
            },
        },
    )

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        file.write("Hybrid hierarchical difficulty model\n\n")
        file.write(f"Best fine model: {best_fine['name']}\n")
        file.write(f"Fine accuracy: {best_fine['accuracy']}\n\n")
        file.write(f"Best group model: {best_group['name']}\n")
        file.write(f"Group accuracy: {best_group['accuracy']}\n\n")

        file.write("=" * 80 + "\n")
        file.write("Fine models:\n\n")

        for result in fine_results:
            file.write(f"Model: {result['name']}\n")
            file.write(f"Accuracy: {result['accuracy']}\n")
            file.write(result["report"])
            file.write("\nConfusion matrix:\n")
            file.write(np.array2string(result["matrix"]))
            file.write("\n\n")

        file.write("=" * 80 + "\n")
        file.write("Group models:\n\n")

        for result in group_results:
            file.write(f"Model: {result['name']}\n")
            file.write(f"Accuracy: {result['accuracy']}\n")
            file.write(result["report"])
            file.write("\nConfusion matrix:\n")
            file.write(np.array2string(result["matrix"]))
            file.write("\n\n")

    print(f"Best fine model: {best_fine['name']}")
    print(f"Fine accuracy: {best_fine['accuracy']}")
    print(f"Best group model: {best_group['name']}")
    print(f"Group accuracy: {best_group['accuracy']}")
    print(f"Latest model saved: {save_result['latest_model_path']}")
    print(f"Versioned model saved: {save_result['versioned_model_path']}")
    print(f"Metadata saved: {save_result['metadata_path']}")
    print(f"Report saved: {REPORT_PATH}")


if __name__ == "__main__":
    train_model()
