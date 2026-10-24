"""Text clean-up applied to extracted PDF pages before chunking (SAD §2.2 steps 3–4)."""

from __future__ import annotations

import unicodedata
from collections import Counter


def nfc(text: str) -> str:
    # Vietnamese text extracted from PDFs often mixes NFC and NFD; search and highlight need one form.
    return unicodedata.normalize("NFC", text)


def has_enough_text(pages: list[str], min_chars_per_page: int) -> bool:
    """False for scanned / image-only PDFs (EC-10, BR-006)."""
    if not pages:
        return False
    chars = sum(len("".join(p.split())) for p in pages)
    return chars >= min_chars_per_page * len(pages)


def _edge_lines(page: str) -> tuple[str | None, str | None]:
    lines = [ln.strip() for ln in page.splitlines() if ln.strip()]
    if not lines:
        return None, None
    return lines[0], lines[-1]


def remove_repeated_header_footer(pages: list[str], threshold: float = 0.6, min_pages: int = 3) -> list[str]:
    """Drop the first / last line of a page when the same line appears there on >= threshold of all pages."""
    if len(pages) < min_pages:
        return pages
    heads, foots = Counter(), Counter()
    for p in pages:
        h, f = _edge_lines(p)
        if h:
            heads[h] += 1
        if f:
            foots[f] += 1
    need = threshold * len(pages)
    rep_heads = {line for line, n in heads.items() if n >= need}
    rep_foots = {line for line, n in foots.items() if n >= need}
    if not rep_heads and not rep_foots:
        return pages

    cleaned = []
    for p in pages:
        lines = p.splitlines()
        idx = [i for i, ln in enumerate(lines) if ln.strip()]
        drop = set()
        if idx and lines[idx[0]].strip() in rep_heads:
            drop.add(idx[0])
        if idx and lines[idx[-1]].strip() in rep_foots:
            drop.add(idx[-1])
        cleaned.append("\n".join(ln for i, ln in enumerate(lines) if i not in drop))
    return cleaned
