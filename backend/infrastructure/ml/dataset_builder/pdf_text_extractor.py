import os

import PyPDF2


class PDFTextExtractor:
    def __init__(self, max_pages=25):
        self.max_pages = max_pages

    def extract_from_file(self, file_path):
        text = ""

        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file, strict=False)
            total_pages = len(reader.pages)

            pages_to_read = min(total_pages, self.max_pages)

            for page_index in range(pages_to_read):
                try:
                    page = reader.pages[page_index]
                    page_text = page.extract_text()

                    if page_text:
                        text += page_text + "\n"

                except Exception as error:
                    print(f"Skipped page {page_index + 1} in {file_path}: {error}")
                    continue

        return text.strip()

    def extract_many(self, downloaded_items):
        extracted = []

        for index, item in enumerate(downloaded_items, start=1):
            file_path = item.get("file_path")

            if not file_path or not os.path.exists(file_path):
                continue

            print(f"[{index}/{len(downloaded_items)}] Extracting text: {file_path}")

            try:
                text = self.extract_from_file(file_path)

                if len(text) > 300:
                    extracted.append(
                        {
                            **item,
                            "text": text,
                        }
                    )
                else:
                    print(f"Skipped low-text PDF: {file_path}")

            except Exception as error:
                print(f"Extract error: {file_path}")
                print(error)

        return extracted
