import base64
import io

import fitz
from PIL import Image

from backend.domain.interfaces.file_extractor import FileExtractor
from backend.infrastructure.file_extractors.base_extractor import BaseExtractor


class PdfExtractor(BaseExtractor, FileExtractor):
    PDF_ZOOM = 3
    MAX_IMAGE_SIDE = 2800
    MAX_PDF_PAGES = 20

    def extract(self, filename: str, file_bytes: bytes):
        document = fitz.open(stream=file_bytes, filetype="pdf")

        pages = []
        text_parts = []

        try:
            page_count = min(len(document), self.MAX_PDF_PAGES)

            for page_index in range(page_count):
                page = document[page_index]
                page_number = page_index + 1

                page_text = self._clean_text(page.get_text("text") or "")
                text_parts.append(
                    f"\n\n--- PDF PAGE {page_number} TEXT ---\n{page_text}"
                )

                pixmap = page.get_pixmap(
                    matrix=fitz.Matrix(self.PDF_ZOOM, self.PDF_ZOOM),
                    alpha=False,
                )

                image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
                image.thumbnail((self.MAX_IMAGE_SIDE, self.MAX_IMAGE_SIDE))

                output = io.BytesIO()
                image.save(output, format="PNG")

                pages.append(
                    {
                        "page": page_number,
                        "page_text": page_text,
                        "full_image": {
                            "filename": f"{filename}_page_{page_number}.png",
                            "mime_type": "image/png",
                            "base64": base64.b64encode(
                                output.getvalue()
                            ).decode("utf-8"),
                        },
                    }
                )

        finally:
            document.close()

        text_context = self._truncate_text("\n".join(text_parts))

        return {
            "filename": filename,
            "extension": "pdf",
            "text_context": text_context,
            "pages": pages,
            "tables": [],
            "debug": {
                "extractor": "pdf_visual_and_text_strategy",
                "pages": len(pages),
                "text_chars": len(text_context),
                "size_bytes": len(file_bytes),
            },
        }
