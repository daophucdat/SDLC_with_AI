"""UploadPolicy (US-201, CON-002, BR-001)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from chatdocs.domain.errors import FileNotPdf, FileTooLarge

PDF_MAGIC = b"%PDF-"
MAX_FILE_NAME = 255


@dataclass(frozen=True)
class UploadPolicy:
    max_size_mb: int = 50

    @property
    def max_bytes(self) -> int:
        return self.max_size_mb * 1024 * 1024

    def check_size(self, size_bytes: int) -> None:
        if size_bytes > self.max_bytes:
            raise FileTooLarge(max_size_mb=self.max_size_mb)
        if size_bytes <= 0:
            raise FileNotPdf("empty file")

    @staticmethod
    def check_head(head: bytes) -> None:
        # Real PDFs may have a few junk bytes before the header; the spec allows the header within the first 1 KB.
        if PDF_MAGIC not in head[:1024]:
            raise FileNotPdf()

    @staticmethod
    def clean_file_name(raw: str | None) -> str:
        name = unicodedata.normalize("NFC", raw or "")
        name = re.split(r"[\\/]", name)[-1]  # drop any client-side path
        name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
        if not name:
            name = "tai-lieu.pdf"
        if len(name) > MAX_FILE_NAME:
            stem, dot, ext = name.rpartition(".")
            name = (stem[: MAX_FILE_NAME - len(ext) - 1] + dot + ext) if dot else name[:MAX_FILE_NAME]
        return name
