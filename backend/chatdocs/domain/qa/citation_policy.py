"""ALG-3 CitationPolicy (US-303): every paragraph must cite, every [n] must point at a context chunk, and the
source location is always taken from the index — never from text the LLM wrote (AC-303.4)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from uuid import UUID

from chatdocs.domain.qa.question import NotFoundReason
from chatdocs.domain.retrieval.rrf import Candidate

REF = re.compile(r"\[(\d+)\]")
PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
NOT_FOUND_TOKEN = "NOT_FOUND"  # noqa: S105 — protocol token, not a secret
EXCERPT_CHARS = 200


@dataclass(frozen=True)
class Citation:
    index: int
    chunk_id: UUID | None
    document_id: UUID
    file_name: str
    page_number: int
    excerpt: str
    removed: bool = False


@dataclass(frozen=True)
class CitationResult:
    text: str = ""
    citations: list[Citation] = field(default_factory=list)
    not_found: NotFoundReason | None = None


def validate(text: str, chunks: list[Candidate], file_names: dict[UUID, str]) -> CitationResult:
    body = text.strip()
    if body.startswith(NOT_FOUND_TOKEN):
        return CitationResult(not_found=NotFoundReason.MODEL_NOT_FOUND)
    refs = [int(m) for m in REF.findall(body)]
    if not refs or any(n < 1 or n > len(chunks) for n in refs):
        return CitationResult(not_found=NotFoundReason.INVALID_CITATIONS)
    for para in (p for p in PARAGRAPH_SPLIT.split(body) if p.strip()):
        if not REF.search(para):
            return CitationResult(not_found=NotFoundReason.INVALID_CITATIONS)

    order = list(dict.fromkeys(refs))  # order of first appearance, duplicates dropped
    renumber = {n: i + 1 for i, n in enumerate(order)}
    text_out = REF.sub(lambda m: f"[{renumber[int(m.group(1))]}]", body)
    citations = []
    for i, n in enumerate(order):
        c = chunks[n - 1]
        citations.append(
            Citation(
                index=i + 1,
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                file_name=file_names.get(c.document_id, ""),
                page_number=c.page_number,
                excerpt=c.content[:EXCERPT_CHARS],
            )
        )
    return CitationResult(text=text_out, citations=citations)


def could_be_not_found(prefix: str) -> bool:
    """True while the streamed prefix might still turn out to be the NOT_FOUND token (§0.5 rule 3)."""
    p = prefix.strip()
    return NOT_FOUND_TOKEN.startswith(p[: len(NOT_FOUND_TOKEN)]) or p.startswith(NOT_FOUND_TOKEN)
