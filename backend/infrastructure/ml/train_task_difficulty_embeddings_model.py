import os
import joblib
import pandas as pd
import numpy as np

from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


DATASET_PATH = "backend/infrastructure/ml/datasets/processed/task_difficulty_dataset_enriched.csv"

MODEL_DIR = "backend/infrastructure/ml/models"
MODEL_PATH = os.path.join(MODEL_DIR, "task_difficulty_embeddings_model.pkl")
REPORT_PATH = os.path.join(MODEL_DIR, "task_difficulty_embeddings_report.txt")

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def train_model():
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    os.makedirs(MODEL_DIR, exist_ok=True)

    df = pd.read_csv(DATASET_PATH)

    df = df.dropna(subset=["text", "difficulty"])
    df["text"] = df["text"].astype(str)
    df["subject"] = df["subject"].fillna("").astype(str)
    df["task_type"] = df["task_type"].fillna("").astype(str)
    df["difficulty"] = df["difficulty"].astype(int)

    df = df[df["difficulty"].isin([1, 2, 3, 4, 5])]
    df = df[df["text"].str.len() >= 60]

    df["combined_text"] = (
        "Предмет: "
        + df["subject"]
        + ". Тип задачі: "
        + df["task_type"]
        + ". Завдання: "
        + df["text"]
    )

    x_train, x_test, y_train, y_test = train_test_split(
        df["combined_text"].tolist(),
        df["difficulty"].tolist(),
        test_size=0.2,
        random_state=42,
        stratify=df["difficulty"],
    )

    print("Loading embedding model...")
    embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    print("Encoding train texts...")
    x_train_embeddings = embedding_model.encode(
        x_train,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    print("Encoding test texts...")
    x_test_embeddings = embedding_model.encode(
        x_test,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    classifier = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        solver="lbfgs",
    )

    classifier.fit(x_train_embeddings, y_train)

    predictions = classifier.predict(x_test_embeddings)

    accuracy = accuracy_score(y_test, predictions)
    report = classification_report(y_test, predictions, digits=4)
    matrix = confusion_matrix(y_test, predictions)

    bundle = {
        "embedding_model_name": EMBEDDING_MODEL_NAME,
        "classifier": classifier,
        "accuracy": accuracy,
    }

    joblib.dump(bundle, MODEL_PATH)

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        file.write(f"Embedding model: {EMBEDDING_MODEL_NAME}\n")
        file.write(f"Accuracy: {accuracy}\n\n")
        file.write("Classification report:\n")
        file.write(report)
        file.write("\n\nConfusion matrix:\n")
        file.write(np.array2string(matrix))

    print(f"Model saved: {MODEL_PATH}")
    print(f"Report saved: {REPORT_PATH}")
    print(f"Accuracy: {accuracy}")


if __name__ == "__main__":
    train_model()