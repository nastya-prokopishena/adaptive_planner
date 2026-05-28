import csv
import json
import os
from collections import Counter

from backend.infrastructure.ml.dataset_builder.google_dork_collector import GoogleDorkCollector
from backend.infrastructure.ml.dataset_builder.html_task_extractor import HTMLTaskExtractor
from backend.infrastructure.ml.dataset_builder.llm_task_generator import LLMTaskGenerator
from backend.infrastructure.ml.dataset_builder.moodle_collector import MoodleCollector
from backend.infrastructure.ml.dataset_builder.pdf_downloader import PDFDownloader
from backend.infrastructure.ml.dataset_builder.pdf_text_extractor import PDFTextExtractor
from backend.infrastructure.ml.dataset_builder.synthetic_task_generator import (
    SyntheticTaskGenerator,
)
from backend.infrastructure.ml.dataset_builder.ukrainian_text_filter import UkrainianTextFilter
from backend.infrastructure.ml.dataset_builder.weak_labeler import WeakTaskLabeler


class TaskDatasetBuilder:
    def __init__(self):
        self.pdf_collector = GoogleDorkCollector()
        self.moodle_collector = MoodleCollector()

        self.downloader = PDFDownloader()
        self.pdf_extractor = PDFTextExtractor()
        self.html_extractor = HTMLTaskExtractor()

        self.labeler = WeakTaskLabeler()
        self.ukrainian_filter = UkrainianTextFilter()

        self.synthetic_generator = SyntheticTaskGenerator()
        self.llm_generator = LLMTaskGenerator()

        self.raw_dir = "backend/infrastructure/ml/datasets/raw"
        self.processed_dir = "backend/infrastructure/ml/datasets/processed"

        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)

    def build_hybrid_dataset(
        self,
        use_existing_raw=True,
        use_pdf_google=True,
        use_moodle=True,
        use_llm=True,
        use_synthetic=True,
        max_results_per_query=6,
        llm_per_difficulty=60,
        synthetic_per_class=80,
    ):
        dataset = []

        if use_existing_raw:
            print("Building from existing raw PDF files...")
            dataset.extend(self._build_from_existing_raw_files())

        if use_pdf_google:
            print("Building from Google PDF dorks...")
            dataset.extend(
                self._build_from_google_pdf_dorks(
                    max_results_per_query=max_results_per_query,
                )
            )

        if use_moodle:
            print("Building from public Moodle pages...")
            dataset.extend(
                self._build_from_public_moodle(
                    max_results_per_query=max_results_per_query,
                )
            )

        dataset = self._remove_duplicates(dataset)

        print("Real dataset distribution:")
        self._print_distribution(dataset)

        if use_llm:
            print("Generating LLM Ukrainian tasks...")
            llm_rows = self.llm_generator.generate_dataset_rows(
                total_per_difficulty=llm_per_difficulty,
            )
            dataset.extend(llm_rows)

        if use_synthetic:
            print("Generating template synthetic tasks...")
            synthetic_rows = self.synthetic_generator.generate(
                target_per_class=synthetic_per_class,
            )
            dataset.extend(synthetic_rows)

        dataset = self._remove_duplicates(dataset)
        dataset = self._filter_valid_rows(dataset)
        dataset = self._balance_dataset(dataset, max_per_class=220)

        print("Final dataset distribution:")
        self._print_distribution(dataset)

        csv_path = os.path.join(
            self.processed_dir,
            "task_difficulty_dataset.csv",
        )

        self._save_csv(csv_path, dataset)

        print(f"Dataset saved: {csv_path}")
        print(f"Samples: {len(dataset)}")

        return csv_path

    def _build_from_google_pdf_dorks(self, max_results_per_query=6):
        search_results = self.pdf_collector.collect_default_queries(
            max_results_per_query=max_results_per_query,
        )

        self._save_json("search_results_pdf.json", search_results)

        print(f"PDF links found: {len(search_results)}")

        downloaded = self.downloader.download_many(search_results)

        self._save_json("downloaded_files_pdf.json", downloaded)

        extracted = self.pdf_extractor.extract_many(downloaded)

        return self._extract_labeled_tasks_from_documents(extracted)

    def _build_from_existing_raw_files(self):
        files = []

        for filename in os.listdir(self.raw_dir):
            if filename.lower().endswith(".pdf"):
                files.append(
                    {
                        "file_path": os.path.join(self.raw_dir, filename),
                        "url": "local_raw_file",
                        "title": filename,
                        "source_type": "local_pdf",
                    }
                )

        print(f"Found raw PDFs: {len(files)}")

        extracted = self.pdf_extractor.extract_many(files)

        return self._extract_labeled_tasks_from_documents(extracted)

    def _build_from_public_moodle(self, max_results_per_query=6):
        moodle_pages = self.moodle_collector.search_public_moodle_tasks(
            max_results_per_query=max_results_per_query,
        )

        self._save_json("search_results_moodle.json", moodle_pages)

        print(f"Moodle pages found: {len(moodle_pages)}")

        extracted = self.html_extractor.extract_many(moodle_pages)

        return self._extract_labeled_tasks_from_documents(extracted)

    def _extract_labeled_tasks_from_documents(self, documents):
        dataset = []

        for index, item in enumerate(documents, start=1):
            text = item.get("text", "")

            print(f"[{index}/{len(documents)}] Processing document")

            if not self.ukrainian_filter.is_ukrainian(text):
                print("Skipped non-Ukrainian document")
                continue

            if not self._looks_like_task_collection(text):
                print("Skipped non-task material")
                continue

            task_candidates = self.labeler.split_into_task_candidates(text)

            print(f"Task candidates found: {len(task_candidates)}")

            for task_text in task_candidates:
                task_text = self.labeler.clean_text(task_text)

                if not self.ukrainian_filter.is_ukrainian(
                    task_text,
                    min_cyrillic_ratio=0.5,
                    min_ukrainian_markers=1,
                    min_stopwords=2,
                ):
                    continue

                if not self._looks_like_single_task(task_text):
                    continue

                labeled = self.labeler.label_task(task_text)

                labeled["source_url"] = item.get("url")
                labeled["source_title"] = item.get("title")
                labeled["source_file"] = item.get("file_path")
                labeled["language"] = "uk"

                dataset.append(labeled)

        return dataset

    def _looks_like_task_collection(self, text):
        lower_text = text.lower()

        positive_patterns = [
            "завдання",
            "задача",
            "задачі",
            "вправа",
            "лабораторна робота",
            "лабораторні роботи",
            "лабораторний практикум",
            "практична робота",
            "практичні роботи",
            "практичні завдання",
            "семінарське заняття",
            "семінарські заняття",
            "самостійна робота",
            "завдання для самостійної роботи",
            "контрольні питання",
            "питання для самоконтролю",
            "хід роботи",
            "порядок виконання",
            "мета роботи",
            "виконати",
            "розв'язати",
            "розв’язати",
            "проаналізувати",
            "побудувати",
            "порівняти",
            "дослідити",
            "описати",
            "обґрунтувати",
        ]

        negative_patterns = [
            "лекція",
            "курс лекцій",
            "конспект лекцій",
            "презентація",
            "силабус",
            "syllabus",
            "робоча програма",
            "навчальна програма",
            "анотація дисципліни",
            "опис дисципліни",
            "теоретичні відомості",
            "приклад виконання",
            "приклад розв'язку",
            "приклад розв’язку",
            "приклади розв'язання",
            "приклади розв’язання",
            "відповіді",
            "готові відповіді",
        ]

        positive_score = sum(1 for pattern in positive_patterns if pattern in lower_text)

        negative_score = sum(1 for pattern in negative_patterns if pattern in lower_text)

        return positive_score >= 2 and negative_score <= 1

    def _looks_like_single_task(self, text):
        lower_text = text.lower()

        if len(text.strip()) < 80:
            return False

        if len(text.strip()) > 3500:
            return False

        task_markers = [
            "завдання",
            "задача",
            "вправа",
            "лабораторна робота",
            "практична робота",
            "семінарське заняття",
            "самостійна робота",
            "виконати",
            "розв'язати",
            "розв’язати",
            "побудувати",
            "проаналізувати",
            "порівняти",
            "дослідити",
            "описати",
            "обґрунтувати",
            "підготувати",
            "скласти",
            "розробити",
            "створити",
            "визначити",
            "обчислити",
        ]

        non_task_markers = [
            "список літератури",
            "рекомендована література",
            "зміст",
            "вступ",
            "передмова",
            "навчальна дисципліна",
            "кількість годин",
            "форма контролю",
            "критерії оцінювання",
            "isbn",
            "удк",
        ]

        has_task_marker = any(marker in lower_text for marker in task_markers)
        has_bad_marker = any(marker in lower_text for marker in non_task_markers)

        return has_task_marker and not has_bad_marker

    def _filter_valid_rows(self, dataset):
        filtered = []

        allowed_task_types = {
            "laboratory",
            "homework",
            "project",
            "reading",
            "exam_preparation",
            "other",
        }

        for item in dataset:
            text = item.get("text", "").strip()
            difficulty = int(item.get("difficulty", 0))
            task_type = item.get("task_type", "other")

            if not text:
                continue

            if difficulty not in [1, 2, 3, 4, 5]:
                continue

            if task_type not in allowed_task_types:
                item["task_type"] = "other"

            if item.get("language") != "uk":
                continue

            filtered.append(item)

        return filtered

    def _balance_dataset(self, dataset, max_per_class=220):
        grouped = {}

        for item in dataset:
            difficulty = int(item["difficulty"])
            grouped.setdefault(difficulty, []).append(item)

        balanced = []

        for difficulty in [1, 2, 3, 4, 5]:
            rows = grouped.get(difficulty, [])
            balanced.extend(rows[:max_per_class])

        return balanced

    def _remove_duplicates(self, dataset):
        unique = {}

        for item in dataset:
            text = item.get("text", "").strip().lower()

            if not text:
                continue

            key = text[:350]
            unique[key] = item

        return list(unique.values())

    def _print_distribution(self, dataset):
        difficulty_counter = Counter(int(item["difficulty"]) for item in dataset)

        type_counter = Counter(item.get("task_type", "other") for item in dataset)

        subject_counter = Counter(item.get("subject", "Інше") for item in dataset)

        print("Difficulty:", dict(difficulty_counter))
        print("Task type:", dict(type_counter))
        print("Subjects:", dict(subject_counter))

    def _save_csv(self, file_path, dataset):
        fields = [
            "text",
            "subject",
            "task_type",
            "difficulty",
            "language",
            "source_url",
            "source_title",
            "source_file",
        ]

        with open(file_path, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()

            for item in dataset:
                writer.writerow(item)

    def _save_json(self, filename, data):
        path = os.path.join(self.processed_dir, filename)

        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    builder = TaskDatasetBuilder()

    builder.build_hybrid_dataset(
        use_existing_raw=True,
        use_pdf_google=True,
        use_moodle=True,
        use_llm=True,
        use_synthetic=True,
        max_results_per_query=6,
        llm_per_difficulty=60,
        synthetic_per_class=80,
    )
