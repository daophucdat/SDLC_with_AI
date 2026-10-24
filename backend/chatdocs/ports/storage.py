from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol


class DocumentStorage(Protocol):
    """IF-03. Object storage for original PDFs (S3 / MinIO, encrypted at rest — SEC-03)."""

    async def put_file(self, key: str, local_path: str, size_bytes: int) -> None: ...

    async def download_to(self, key: str, local_path: str) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def size(self, key: str) -> int | None:
        """Object size in bytes, or None if it does not exist."""
        ...

    def read_range(self, key: str, start: int, end: int) -> AsyncIterator[bytes]:
        """Bytes [start, end] inclusive, streamed (US-305: the PDF viewer only fetches the pages it shows)."""
        ...

    async def health(self) -> bool: ...
