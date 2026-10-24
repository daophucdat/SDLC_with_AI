from __future__ import annotations

from typing import Protocol
from uuid import UUID

from chatdocs.domain.documents.chunking import Chunk
from chatdocs.domain.retrieval.rrf import Candidate


class ChunkIndex(Protocol):
    """Vector + full-text index over TextChunk (EN-05, ADR-04, ADR-07)."""

    async def replace_document(
        self, document_id: UUID, pages: list[str], chunks: list[Chunk], vectors: list[list[float]]
    ) -> None:
        """Idempotent: removes any previous pages / chunks of the document, then writes the new ones atomically."""
        ...

    async def vector_search(self, query_vector: list[float], document_ids: list[UUID], k: int) -> list[Candidate]: ...

    async def fts_search(self, query_text: str, document_ids: list[UUID], k: int) -> list[Candidate]: ...
