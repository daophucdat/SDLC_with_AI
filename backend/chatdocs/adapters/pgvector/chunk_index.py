"""ChunkIndex on PostgreSQL + pgvector (HNSW, cosine) + full-text search (GIN, 'simple' config + unaccent)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from chatdocs.domain.documents.chunking import Chunk
from chatdocs.domain.ids import uuid7
from chatdocs.domain.retrieval.rrf import Candidate


def vector_literal(vec: list[float]) -> str:
    # Sent as text and cast server-side: asyncpg has no codec for the `vector` type.
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


_COLS = "id, document_id, page_number, content, char_start, char_end"


class PgVectorChunkIndex:
    def __init__(self, engine: AsyncEngine, *, ef_search: int = 80) -> None:
        self._e = engine
        self._ef = int(ef_search)  # SET cannot take bind parameters; int() guards the f-string below

    async def replace_document(
        self, document_id: UUID, pages: list[str], chunks: list[Chunk], vectors: list[list[float]]
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        async with self._e.begin() as c:
            await c.execute(text("DELETE FROM documents.text_chunk WHERE document_id = :d"), {"d": document_id})
            await c.execute(text("DELETE FROM documents.document_page WHERE document_id = :d"), {"d": document_id})
            if pages:
                await c.execute(
                    text("INSERT INTO documents.document_page (document_id, page_number, text) VALUES (:d, :n, :t)"),
                    [{"d": document_id, "n": i + 1, "t": p} for i, p in enumerate(pages)],
                )
            if chunks:
                await c.execute(
                    text("""
                    INSERT INTO documents.text_chunk
                           (id, document_id, page_number, chunk_index, char_start, char_end, content, embedding)
                    VALUES (:id, :d, :p, :i, :s, :e, :c, CAST(CAST(:v AS text) AS vector))"""),
                    [
                        {
                            "id": uuid7(),
                            "d": document_id,
                            "p": ch.page_number,
                            "i": ch.chunk_index,
                            "s": ch.char_start,
                            "e": ch.char_end,
                            "c": ch.content,
                            "v": vector_literal(v),
                        }
                        for ch, v in zip(chunks, vectors, strict=True)
                    ],
                )

    async def vector_search(self, query_vector: list[float], document_ids: list[UUID], k: int) -> list[Candidate]:
        if not document_ids:
            return []
        async with self._e.begin() as c:
            await c.execute(text(f"SET LOCAL hnsw.ef_search = {self._ef}"))
            rows = (
                await c.execute(
                    text(f"""
                SELECT {_COLS}, 1 - (embedding <=> CAST(CAST(:q AS text) AS vector)) AS cos
                  FROM documents.text_chunk
                 WHERE document_id = ANY(:docs)
                 ORDER BY embedding <=> CAST(CAST(:q AS text) AS vector)
                 LIMIT :k"""),
                    {"q": vector_literal(query_vector), "docs": list(document_ids), "k": k},
                )
            ).all()
        return [
            Candidate(r.id, r.document_id, r.page_number, r.content, r.char_start, r.char_end, cosine=float(r.cos))
            for r in rows
        ]

    async def fts_search(self, query_text: str, document_ids: list[UUID], k: int) -> list[Candidate]:
        if not document_ids or not query_text.strip():
            return []
        async with self._e.connect() as c:
            rows = (
                await c.execute(
                    text(f"""
                SELECT {_COLS}, ts_rank_cd(tsv, q) AS r
                  FROM documents.text_chunk, websearch_to_tsquery('simple', platform.f_unaccent(:t)) AS q
                 WHERE document_id = ANY(:docs) AND tsv @@ q
                 ORDER BY r DESC
                 LIMIT :k"""),
                    {"t": query_text, "docs": list(document_ids), "k": k},
                )
            ).all()
        return [
            Candidate(r.id, r.document_id, r.page_number, r.content, r.char_start, r.char_end, fts_rank=float(r.r))
            for r in rows
        ]
