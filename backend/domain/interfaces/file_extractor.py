from abc import ABC, abstractmethod
from typing import Any


class FileExtractor(ABC):
    @abstractmethod
    def extract(self, filename: str, file_bytes: bytes) -> dict[str, Any]:
        pass