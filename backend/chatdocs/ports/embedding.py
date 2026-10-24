from __future__ import annotations

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Returns one L2-normalised vector per input text, in input order (ADR-08)."""

    dimension: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def health(self) -> bool: ...
