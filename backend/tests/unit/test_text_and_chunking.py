from __future__ import annotations

import unicodedata

from chatdocs.domain.documents.chunking import chunk_document, chunk_page
from chatdocs.domain.documents.text_cleanup import has_enough_text, nfc, remove_repeated_header_footer


def test_nfc_unifies_vietnamese():
    decomposed = unicodedata.normalize("NFD", "Hợp đồng")
    assert decomposed != "Hợp đồng"
    assert nfc(decomposed) == "Hợp đồng"


def test_has_enough_text_detects_scans():
    assert not has_enough_text(["", " \n ", "abc"], min_chars_per_page=20)
    assert has_enough_text(["x" * 30, "y" * 30], min_chars_per_page=20)
    assert not has_enough_text([], 20)


def test_repeated_header_footer_removed_but_body_kept():
    pages = [f"CÔNG TY ABC — BẢO MẬT\nNội dung trang {i}\nTrang {i}/5\nCông ty ABC" for i in range(1, 6)]
    cleaned = remove_repeated_header_footer(pages)
    for i, p in enumerate(cleaned, start=1):
        assert "BẢO MẬT" not in p and "Công ty ABC" not in p
        assert f"Nội dung trang {i}" in p and f"Trang {i}/5" in p  # varying lines stay


def test_header_footer_untouched_for_short_documents():
    pages = ["H\nbody 1\nF", "H\nbody 2\nF"]
    assert remove_repeated_header_footer(pages) == pages


def test_chunks_stay_within_page_and_offsets_match():
    text = ("Điều 1. Thanh toán 30% khi ký hợp đồng. " * 120).strip()
    chunks = chunk_page(4, text, size_tokens=100, overlap_tokens=20)
    assert len(chunks) > 3
    for c in chunks:
        assert c.page_number == 4
        assert 0 <= c.char_start < c.char_end <= len(text)
        assert text[c.char_start : c.char_end] == c.content  # offsets point at the exact excerpt
        assert len(c.content) <= 100 * 4
    # consecutive windows overlap, so no sentence is lost at a boundary
    assert all(b.char_start < a.char_end for a, b in zip(chunks, chunks[1:], strict=False))
    assert chunks[-1].char_end == len(text)


def test_chunk_prefers_sentence_boundary():
    text = "A" * 300 + ". " + "B" * 300
    first = chunk_page(1, text, size_tokens=100, overlap_tokens=10)[0]
    assert first.content.endswith(".")


def test_chunk_document_numbers_pages_and_skips_empty():
    chunks = chunk_document(["page one text", "", "  ", "page four text"], size_tokens=50, overlap_tokens=5)
    assert [c.page_number for c in chunks] == [1, 4]
    assert [c.chunk_index for c in chunks] == [0, 1]


def test_chunking_terminates_on_text_without_breaks():
    chunks = chunk_page(1, "x" * 10_000, size_tokens=500, overlap_tokens=80)
    assert chunks and chunks[-1].char_end == 10_000
