import os
import time
import requests
from dotenv import load_dotenv


load_dotenv()


class MoodleCollector:
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY")
        self.search_url = "https://serpapi.com/search.json"

    def search_public_moodle_tasks(self, max_results_per_query=10):
        queries = [
            'site:.edu.ua inurl:moodle "лабораторна робота"',
            'site:.edu.ua inurl:moodle "практичне завдання"',
            'site:.edu.ua inurl:moodle "практична робота"',
            'site:.edu.ua inurl:moodle "завдання для самостійної роботи"',
            'site:.edu.ua inurl:moodle "семінарське заняття"',
            'site:.edu.ua inurl:moodle "контрольні питання"',
            'site:.edu.ua inurl:moodle "виконати завдання"',
            'site:.edu.ua inurl:moodle "розв’язати задачі"',
            'site:.edu.ua inurl:moodle "лабораторні роботи"',
            'site:.edu.ua inurl:moodle "самостійна робота"',
        ]

        all_results = []

        for query in queries:
            print(f"Searching Moodle: {query}")

            results = self._search(query, max_results=max_results_per_query)
            all_results.extend(results)

        unique = {}

        for item in all_results:
            unique[item["url"]] = item

        return list(unique.values())

    def _search(self, query, max_results=10):
        if not self.api_key:
            print("SERPAPI_KEY is not set. Moodle search skipped.")
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
                print(f"Moodle search error: {error}")
                break

            data = response.json()
            organic_results = data.get("organic_results", [])

            if not organic_results:
                break

            for item in organic_results:
                link = item.get("link", "")
                title = item.get("title", "")

                if not link:
                    continue

                if self._looks_like_public_task_page(title, link):
                    results.append({
                        "title": title,
                        "url": link,
                        "query": query,
                        "source_type": "moodle",
                    })

                if len(results) >= max_results:
                    break

            start += 10
            time.sleep(1)

        return results

    def _looks_like_public_task_page(self, title, url):
        text = f"{title} {url}".lower()

        positive = [
            "moodle",
            "лабораторна",
            "практична",
            "завдання",
            "самостійна",
            "семінар",
            "контрольні питання",
        ]

        negative = [
            "login",
            "signin",
            "auth",
            "calendar",
            "forum",
            "user",
            "profile",
        ]

        return any(word in text for word in positive) and not any(
            word in text for word in negative
        )