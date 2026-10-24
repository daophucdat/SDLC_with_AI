"""ALG-2 (Blueprint §3.9): fuse vector and full-text rankings with Reciprocal Rank Fusion."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from uuid import UUID


@dataclass(frozen=True)
class Candidate:
    chunk_id: UUID
    document_id: UUID
    page_number: int
    content: str
    char_start: int = 0
    char_end: int = 0
    cosine: float | None = None  # similarity from the vector query
    fts_rank: float | None = None  # ts_rank_cd from the full-text query
    score: float = 0.0  # RRF score after fusion


def rrf_fuse(vector: list[Candidate], fts: list[Candidate], k: int = 60) -> list[Candidate]:
    """Each list must already be ordered best-first. Returns unique candidates ordered by RRF score."""
    scores: dict[UUID, float] = defaultdict(float)
    merged: dict[UUID, Candidate] = {}
    for ranking in (vector, fts):
        for rank, cand in enumerate(ranking, start=1):
            scores[cand.chunk_id] += 1.0 / (k + rank)
            prev = merged.get(cand.chunk_id)
            if prev is None:
                merged[cand.chunk_id] = cand
            else:
                merged[cand.chunk_id] = replace(
                    prev,
                    cosine=prev.cosine if prev.cosine is not None else cand.cosine,
                    fts_rank=prev.fts_rank if prev.fts_rank is not None else cand.fts_rank,
                )
    fused = [replace(c, score=scores[cid]) for cid, c in merged.items()]
    # Stable tie-break on cosine then id keeps results deterministic for tests and evaluation runs.
    fused.sort(key=lambda c: (-c.score, -(c.cosine or 0.0), str(c.chunk_id)))
    return fused


def select_top(fused: list[Candidate], top_n: int, max_per_document: int) -> list[Candidate]:
    """Keep at most `max_per_document` chunks per document so one long file cannot fill the whole context."""
    per_doc: dict[UUID, int] = defaultdict(int)
    out: list[Candidate] = []
    for c in fused:
        if per_doc[c.document_id] >= max_per_document:
            continue
        per_doc[c.document_id] += 1
        out.append(c)
        if len(out) == top_n:
            break
    return out


def is_empty(max_cosine: float | None, fts_hits: int, tau: float) -> bool:
    """No usable context: answer NOT_FOUND without calling the LLM (US-304 AC-304.4)."""
    return (max_cosine is None or max_cosine < tau) and fts_hits == 0
