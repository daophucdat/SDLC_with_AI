from __future__ import annotations

from typing import Protocol


class PdfPasswordProtected(Exception):
    pass


class PdfCorrupt(Exception):
    pass


class PdfTextExtractor(Protocol):
    def extract_pages(self, local_path: str) -> list[str]:
        """Text of each page, in order. Raises PdfPasswordProtected or PdfCorrupt."""
        ...
