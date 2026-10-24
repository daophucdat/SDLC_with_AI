"""ALG-1 (Blueprint §3.9): split each page into overlapping windows. A chunk never crosses a page boundary,
so every citation can point at exactly one page."""

from __future__ import annotations

from dataclasses import dataclass

CHARS_PER_TOKEN = 4  # rough estimate; DQ-02 tracks replacing it with the embedder tokenizer


@dataclass(frozen=True)
class Chunk:
    page_number: int
    chunk_index: int
    char_start: int  # offsets into the cleaned page text, used later to highlight the excerpt
    char_end: int
    content: str


def _windows(text: str, size_tokens: int, overlap_tokens: int) -> list[tuple[int, int]]:
    size, overlap = size_tokens * CHARS_PER_TOKEN, overlap_tokens * CHARS_PER_TOKEN
    spans, start, n = [], 0, len(text)
    while start < n:
        end = min(n, start + size)
        if end < n:
            cut = max(text.rfind("\n\n", start, end), text.rfind(". ", start, end))
            if cut > start + size // 2:  # cut early only when the chunk stays reasonably long
                end = cut + 1
        spans.append((start, end))
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return spans


def chunk_page(page_number: int, text: str, size_tokens: int, overlap_tokens: int, first_index: int = 0) -> list[Chunk]:
    chunks: list[Chunk] = []
    for start, end in _windows(text, size_tokens, overlap_tokens):
        raw = text[start:end]
        stripped = raw.strip()
        if not stripped:
            continue
        lead = len(raw) - len(raw.lstrip())
        s = start + lead
        chunks.append(Chunk(page_number, first_index + len(chunks), s, s + len(stripped), stripped))
    return chunks


def chunk_document(pages: list[str], size_tokens: int, overlap_tokens: int) -> list[Chunk]:
    """pages[i] is the text of page i + 1. Empty pages produce no chunks but keep page numbering."""
    out: list[Chunk] = []
    for i, text in enumerate(pages):
        out.extend(chunk_page(i + 1, text, size_tokens, overlap_tokens, first_index=len(out)))
    return out
