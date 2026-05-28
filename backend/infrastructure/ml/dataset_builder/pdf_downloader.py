import hashlib
import os
import time

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PDFDownloader:
    def __init__(self, output_dir="backend/infrastructure/ml/datasets/raw"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def download_many(self, items):
        downloaded = []

        for index, item in enumerate(items, start=1):
            url = item.get("url")

            if not url:
                continue

            print(f"[{index}/{len(items)}] Downloading: {url}")

            file_path = self.download(url, index=index)

            if file_path:
                downloaded.append(
                    {
                        **item,
                        "file_path": file_path,
                    }
                )

            time.sleep(0.2)

        return downloaded

    def download(self, url, index):
        file_path = self._make_file_path(url, index)

        if os.path.exists(file_path) and os.path.getsize(file_path) > 1000:
            print(f"Already downloaded: {file_path}")
            return file_path

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/pdf,text/html,*/*",
            "Connection": "close",
        }

        response = self._safe_get(url, headers)

        if response is None:
            return None

        if response.status_code in [401, 403, 404, 408, 429, 500, 502, 503, 504]:
            print(f"Skipped HTTP {response.status_code}: {url}")
            return None

        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as error:
            print(f"Skipped request error: {error}")
            return None

        content = response.content

        if not content or len(content) < 1000:
            print(f"Skipped empty/small file: {url}")
            return None

        if not self._looks_like_pdf(content, response.headers, url):
            print(f"Skipped non-PDF response: {url}")
            return None

        with open(file_path, "wb") as file:
            file.write(content)

        print(f"Saved: {file_path}")
        return file_path

    def _safe_get(self, url, headers):
        try:
            return requests.get(
                url,
                headers=headers,
                timeout=(5, 20),
                allow_redirects=True,
                verify=True,
            )
        except requests.exceptions.SSLError:
            print(f"SSL error, retry without verification: {url}")

            try:
                return requests.get(
                    url,
                    headers=headers,
                    timeout=(5, 20),
                    allow_redirects=True,
                    verify=False,
                )
            except requests.exceptions.RequestException as error:
                print(f"Skipped after SSL retry: {error}")
                return None

        except requests.exceptions.Timeout:
            print(f"Skipped timeout: {url}")
            return None

        except requests.exceptions.RequestException as error:
            print(f"Skipped request exception: {error}")
            return None

    def _make_file_path(self, url, index):
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
        file_name = f"{index}_{url_hash}.pdf"

        return os.path.join(self.output_dir, file_name)

    def _looks_like_pdf(self, content, headers, url):
        content_type = headers.get("Content-Type", "").lower()

        if content[:4] == b"%PDF":
            return True

        if "pdf" in content_type:
            return True

        if url.lower().endswith(".pdf"):
            return True

        return False
