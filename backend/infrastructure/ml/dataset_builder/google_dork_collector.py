import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()


class GoogleDorkCollector:
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY")
        self.search_url = "https://serpapi.com/search.json"

    def search(self, query, max_results=20):
        if not self.api_key:
            print("SERPAPI_KEY is not set")
            return []

        results = []
        start = 0

        while len(results) < max_results:
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.api_key,
                "num": 10,
                "start": start,
                "hl": "uk",
                "gl": "ua",
            }

            try:
                response = requests.get(
                    self.search_url,
                    params=params,
                    timeout=30,
                )

                response.raise_for_status()

            except Exception as error:
                print(f"Search error: {error}")
                break

            data = response.json()

            organic_results = data.get("organic_results", [])

            if not organic_results:
                break

            for item in organic_results:
                link = item.get("link", "")
                title = item.get("title", "")

                if not link.lower().endswith(".pdf"):
                    continue

                if self._is_valid_task_material(title, link):
                    results.append(
                        {
                            "query": query,
                            "title": title,
                            "url": link,
                        }
                    )

                if len(results) >= max_results:
                    break

            start += 10
            time.sleep(1)

        return results

    def _is_valid_task_material(self, title, url):
        text = f"{title} {url}".lower()

        positive_keywords = [
            "збірник задач",
            "збірник завдань",
            "лабораторна робота",
            "лабораторні роботи",
            "лабораторний практикум",
            "практична робота",
            "практичні роботи",
            "практичні завдання",
            "завдання для самостійної роботи",
            "самостійна робота",
            "семінарські заняття",
            "семінар",
            "методичні рекомендації",
            "контрольні питання",
            "задачі",
            "завдання",
            "кейси",
            "практикум",
        ]

        negative_keywords = [
            "лекція",
            "конспект",
            "презентація",
            "робоча програма",
            "syllabus",
            "силабус",
            "теоретичні відомості",
            "приклад виконання",
            "приклад розв'язку",
            "приклади розв'язання",
            "example",
            "solution",
            "lecture",
            "курс лекцій",
            "навчальна програма",
        ]

        has_positive = any(keyword in text for keyword in positive_keywords)

        has_negative = any(keyword in text for keyword in negative_keywords)

        return has_positive and not has_negative

    def collect_default_queries(self, max_results_per_query=10):
        queries = [
            'filetype:pdf site:.edu.ua "збірник задач"',
            'filetype:pdf site:.edu.ua "збірник завдань"',
            'filetype:pdf site:.edu.ua "лабораторний практикум"',
            'filetype:pdf site:.edu.ua "лабораторні роботи"',
            'filetype:pdf site:.edu.ua "лабораторна робота"',
            'filetype:pdf site:.edu.ua "практичні завдання"',
            'filetype:pdf site:.edu.ua "практичні роботи"',
            'filetype:pdf site:.edu.ua "семінарські заняття"',
            'filetype:pdf site:.edu.ua "завдання для самостійної роботи"',
            'filetype:pdf site:.edu.ua "контрольні питання"',
            'filetype:pdf site:.edu.ua "методичні рекомендації"',
            'filetype:pdf site:.edu.ua "практикум"',
            # предметні
            'filetype:pdf site:.edu.ua "лабораторні роботи" "програмування"',
            'filetype:pdf site:.edu.ua "практичні завдання" "економіка"',
            'filetype:pdf site:.edu.ua "семінарські заняття" "історія"',
            'filetype:pdf site:.edu.ua "збірник задач" "математика"',
            'filetype:pdf site:.edu.ua "лабораторний практикум" "біологія"',
            'filetype:pdf site:.edu.ua "практичні роботи" "хімія"',
            'filetype:pdf site:.edu.ua "семінарські завдання" "право"',
            'filetype:pdf site:.edu.ua "практичні завдання" "маркетинг"',
            'filetype:pdf site:.edu.ua "лабораторні роботи" "бази даних"',
            'filetype:pdf site:.edu.ua "лабораторні роботи" "python"',
            'filetype:pdf site:.edu.ua "лабораторні роботи" "javascript"',
            'filetype:pdf site:.edu.ua "практичні завдання" "психологія"',
            'filetype:pdf site:.edu.ua "практикум" "українська мова"',
        ]

        all_results = []

        for query in queries:
            print(f"Searching: {query}")

            query_results = self.search(
                query=query,
                max_results=max_results_per_query,
            )

            print(f"Found: {len(query_results)}")

            all_results.extend(query_results)

        unique = {}

        for item in all_results:
            unique[item["url"]] = item

        filtered_results = list(unique.values())

        print(f"Unique task PDFs: {len(filtered_results)}")

        return filtered_results
