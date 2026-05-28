import re

import requests
from bs4 import BeautifulSoup


class HTMLTaskExtractor:
    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        }

    def extract_many(self, pages):
        extracted = []

        for index, item in enumerate(pages, start=1):
            url = item.get("url")

            print(f"[{index}/{len(pages)}] Extracting Moodle page: {url}")

            text = self.extract_text(url)

            if text and len(text) > 200:
                extracted.append(
                    {
                        **item,
                        "text": text,
                        "file_path": url,
                    }
                )

        return extracted

    def extract_text(self, url):
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=20,
                allow_redirects=True,
            )

            if response.status_code in [401, 403, 404, 500, 502, 503]:
                return ""

            content_type = response.headers.get("Content-Type", "").lower()

            if "text/html" not in content_type:
                return ""

            soup = BeautifulSoup(response.text, "lxml")

            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(" ")
            text = re.sub(r"\s+", " ", text)

            return text.strip()

        except Exception as error:
            print(f"HTML extract error: {error}")
            return ""
