import base64
import io

from PIL import Image

from backend.domain.interfaces.file_extractor import FileExtractor
from backend.infrastructure.file_extractors.base_extractor import BaseExtractor


class ImageExtractor(BaseExtractor, FileExtractor):
    MAX_IMAGE_SIDE = 2800

    def __init__(self, extension: str):
        self.extension = extension

    def extract(self, filename: str, file_bytes: bytes):
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        image.thumbnail((self.MAX_IMAGE_SIDE, self.MAX_IMAGE_SIDE))

        output = io.BytesIO()
        image.save(output, format="PNG")

        return {
            "filename": filename,
            "extension": self.extension,
            "text_context": "",
            "pages": [
                {
                    "page": 1,
                    "page_text": "",
                    "full_image": {
                        "filename": filename,
                        "mime_type": "image/png",
                        "base64": base64.b64encode(
                            output.getvalue()
                        ).decode("utf-8"),
                    },
                }
            ],
            "tables": [],
            "debug": {
                "extractor": "image_visual_strategy",
                "size_bytes": len(file_bytes),
            },
        }
