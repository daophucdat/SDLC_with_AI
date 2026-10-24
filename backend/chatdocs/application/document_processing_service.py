"""DocumentProcessingService — EN-04 pipeline, US-205 (no-text detection). Runs in the worker."""

from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from chatdocs.domain.documents.chunking import chunk_document
from chatdocs.domain.documents.document import DocumentStatus, ProcessingErrorCode
from chatdocs.domain.documents.text_cleanup import has_enough_text, nfc, remove_repeated_header_footer
from chatdocs.ports.chunk_index import ChunkIndex
from chatdocs.ports.embedding import EmbeddingProvider
from chatdocs.ports.pdf import PdfCorrupt, PdfPasswordProtected, PdfTextExtractor
from chatdocs.ports.qa import AnalyticsSink
from chatdocs.ports.repositories import DocumentRepository
from chatdocs.ports.storage import DocumentStorage


@dataclass(frozen=True)
class ProcessingConfig:
    chunk_tokens: int = 500
    chunk_overlap: int = 80
    no_text_chars_per_page: int = 20
    embed_batch: int = 32


class Outcome(str, Enum):
    READY = "ready"
    NO_TEXT = "no_text"
    ERROR = "error"
    SKIPPED = "skipped"  # removed or already processed — nothing to do


@dataclass(frozen=True)
class ProcessingResult:
    outcome: Outcome
    page_count: int = 0
    chunk_count: int = 0
    failure: str | None = None  # "password" | "corrupt" for the document_upload_failed event


class DocumentProcessingService:
    def __init__(
        self,
        *,
        documents: DocumentRepository,
        storage: DocumentStorage,
        extractor: PdfTextExtractor,
        embedder: EmbeddingProvider,
        index: ChunkIndex,
        config: ProcessingConfig,
        analytics: AnalyticsSink | None = None,
    ) -> None:
        self._docs, self._storage, self._extractor = documents, storage, extractor
        self._embedder, self._index, self._cfg = embedder, index, config
        self._analytics = analytics

    async def process(self, document_id: UUID) -> ProcessingResult:
        t0 = time.perf_counter()
        doc = await self._docs.get(document_id)
        result = await self._process(document_id)
        if self._analytics and doc is not None and result.outcome is not Outcome.SKIPPED:
            props = {
                "page_count": result.page_count,
                "duration_ms": int((time.perf_counter() - t0) * 1000),
                "status": result.outcome.value,
            }
            self._analytics.emit("document_processing_completed", props, user_id=doc.uploaded_by, session_id=None)
            if result.failure:
                self._analytics.emit(
                    "document_upload_failed", {"reason": result.failure}, user_id=doc.uploaded_by, session_id=None
                )
        return result

    async def _process(self, document_id: UUID) -> ProcessingResult:
        """Transient failures (storage, embedder, DB) propagate so the job runner retries.
        Permanent problems with the file itself are recorded on the document and are not retried."""
        doc = await self._docs.get(document_id)
        if doc is None or doc.removed_at is not None or doc.status is not DocumentStatus.PROCESSING:
            return ProcessingResult(Outcome.SKIPPED)

        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            await self._storage.download_to(doc.storage_key, path)
            try:
                raw_pages = self._extractor.extract_pages(path)
            except PdfPasswordProtected:
                await self._docs.mark_error(doc.id, ProcessingErrorCode.PASSWORD)
                return ProcessingResult(Outcome.ERROR, failure="password")
            except PdfCorrupt:
                await self._docs.mark_error(doc.id, ProcessingErrorCode.CORRUPT)
                return ProcessingResult(Outcome.ERROR, failure="corrupt")
        finally:
            os.unlink(path)

        pages = [nfc(p) for p in raw_pages]
        if not has_enough_text(pages, self._cfg.no_text_chars_per_page):
            await self._index.replace_document(doc.id, [], [], [])  # make sure nothing is searchable (AC-205.2)
            await self._docs.mark_no_text(doc.id, len(pages))
            return ProcessingResult(Outcome.NO_TEXT, page_count=len(pages))

        pages = remove_repeated_header_footer(pages)
        chunks = chunk_document(pages, self._cfg.chunk_tokens, self._cfg.chunk_overlap)
        vectors: list[list[float]] = []
        for i in range(0, len(chunks), self._cfg.embed_batch):
            batch = chunks[i : i + self._cfg.embed_batch]
            vectors.extend(await self._embedder.embed([c.content for c in batch]))
        if len(vectors) != len(chunks):
            raise RuntimeError(f"embedder returned {len(vectors)} vectors for {len(chunks)} chunks")

        await self._index.replace_document(doc.id, pages, chunks, vectors)  # idempotent (delete + insert)
        await self._docs.mark_ready(doc.id, len(pages))
        return ProcessingResult(Outcome.READY, page_count=len(pages), chunk_count=len(chunks))

    async def give_up(self, document_id: UUID) -> None:
        """Called by the job runner after the last retry failed."""
        await self._docs.mark_error(document_id, ProcessingErrorCode.INTERNAL)
