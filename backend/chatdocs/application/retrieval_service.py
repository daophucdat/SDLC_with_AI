"""RetrievalService — EN-05: hybrid search (vector + full text), RRF, per-document cap, empty decision (ALG-2)."""

from __future__ import annotations

import asyncio
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass
from uuid import UUID

from chatdocs.domain.retrieval.rrf import Candidate, is_empty, rrf_fuse, select_top
from chatdocs.ports.chunk_index import ChunkIndex
from chatdocs.ports.embedding import EmbeddingProvider


@dataclass(frozen=True)
class RetrievalConfig:
    topk_vector: int = 30
    topk_fts: int = 30
    top_n: int = 8
    max_per_document: int = 3
    tau: float = 0.35
    rrf_k: int = 60
    cache_size: int = 1000


@dataclass(frozen=True)
class SearchResult:
    chunks: list[Candidate]
    max_cosine: float | None
    fts_hits: int
    empty: bool


class _Lru:
    def __init__(self, size: int) -> None:
        self._size, self._data = size, OrderedDict()

    def get(self, key: str) -> list[float] | None:
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def put(self, key: str, value: list[float]) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        if len(self._data) > self._size:
            self._data.popitem(last=False)


def normalise_query(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).lower().split())


class RetrievalService:
    def __init__(self, *, embedder: EmbeddingProvider, index: ChunkIndex, config: RetrievalConfig) -> None:
        self._embedder, self._index, self._cfg = embedder, index, config
        self._cache = _Lru(config.cache_size)

    async def embed_query(self, query: str) -> list[float]:
        key = normalise_query(query)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        vec = (await self._embedder.embed([query]))[0]
        self._cache.put(key, vec)
        return vec

    async def search(self, query: str, document_ids: list[UUID]) -> SearchResult:
        """`document_ids` must come from DocumentLibrary.ready_documents() — never search unfiltered (RUL-003)."""
        if not document_ids or not query.strip():
            return SearchResult([], None, 0, True)
        vec = await self.embed_query(query)
        vector_hits, fts_hits = await asyncio.gather(
            self._index.vector_search(vec, document_ids, self._cfg.topk_vector),
            self._index.fts_search(query, document_ids, self._cfg.topk_fts),
        )
        allowed = set(document_ids)  # defence in depth: drop anything the adapter returned outside the filter
        vector_hits = [c for c in vector_hits if c.document_id in allowed]
        fts_hits = [c for c in fts_hits if c.document_id in allowed]
        max_cos = max((c.cosine for c in vector_hits if c.cosine is not None), default=None)
        if is_empty(max_cos, len(fts_hits), self._cfg.tau):
            return SearchResult([], max_cos, len(fts_hits), True)
        fused = rrf_fuse(vector_hits, fts_hits, k=self._cfg.rrf_k)
        top = select_top(fused, self._cfg.top_n, self._cfg.max_per_document)
        return SearchResult(top, max_cos, len(fts_hits), False)
