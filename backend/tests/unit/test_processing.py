"""EN-04 / US-205 with the real PyMuPDF extractor and in-memory storage, embedder and index."""

from __future__ import annotations

import os
from datetime import timezone

import fitz
import pytest

from chatdocs.adapters.pdf.pymupdf_extractor import PyMuPdfExtractor
from chatdocs.application.document_processing_service import (
    DocumentProcessingService,
    Outcome,
    ProcessingConfig,
)
from chatdocs.domain.documents.document import Document, DocumentStatus, ProcessingErrorCode
from chatdocs.domain.ids import uuid7
from chatdocs.ports.pdf import PdfCorrupt, PdfPasswordProtected
from tests.fakes import FakeEmbedder, MemChunkIndex, MemDocuments, MemJobQueue, MemStorage, MemUsers


def make_pdf(path, pages: list[str]) -> None:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_textbox(fitz.Rect(50, 50, 550, 800), text, fontsize=9)
    doc.save(path)
    doc.close()


def make_scanned_pdf(path, n_pages=3) -> None:
    doc = fitz.open()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 200, 200), False)
    pix.clear_with(180)
    for _ in range(n_pages):
        doc.new_page().insert_image(fitz.Rect(50, 50, 450, 450), pixmap=pix)
    doc.save(path)
    doc.close()


def make_locked_pdf(path) -> None:
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "secret contract")
    doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")
    doc.close()


@pytest.fixture
def pipeline(tmp_path):
    users, jobs = MemUsers(), MemJobQueue()
    docs, storage, index, embedder = MemDocuments(users, jobs), MemStorage(), MemChunkIndex(), FakeEmbedder()
    svc = DocumentProcessingService(
        documents=docs,
        storage=storage,
        extractor=PyMuPdfExtractor(),
        embedder=embedder,
        index=index,
        config=ProcessingConfig(chunk_tokens=100, chunk_overlap=20, embed_batch=4),
    )

    def add(path) -> Document:
        from datetime import datetime

        doc_id = uuid7()
        d = Document(
            doc_id,
            uuid7(),
            os.path.basename(path),
            os.path.getsize(path),
            b"h",
            DocumentStatus.PROCESSING,
            f"k/{doc_id}",
            uuid7(),
            datetime.now(timezone.utc),
        )
        docs.docs[doc_id] = d
        with open(path, "rb") as f:
            storage.objects[d.storage_key] = f.read()
        return d

    return svc, docs, index, embedder, add, tmp_path


async def test_text_pdf_becomes_ready_with_page_numbers(pipeline):
    svc, docs, index, embedder, add, tmp = pipeline
    path = tmp / "hop_dong.pdf"
    make_pdf(
        path,
        [
            "Điều 1. Thanh toán 30% trong vòng 07 ngày kể từ ngày ký hợp đồng. " * 15,
            "",
            "Điều 5. Bảo hành 12 tháng kể từ ngày nghiệm thu. " * 15,
        ],
    )
    d = add(path)
    result = await svc.process(d.id)
    assert result.outcome is Outcome.READY and result.page_count == 3
    assert docs.docs[d.id].status is DocumentStatus.READY and docs.docs[d.id].page_count == 3
    stored = index.chunks[d.id]
    assert {ch.page_number for _, ch, _ in stored} == {1, 3}  # the empty page 2 has no chunk, numbering kept
    assert "Thanh toán" in stored[0][1].content  # Vietnamese text survives extraction + NFC
    assert embedder.calls >= 2  # batched (embed_batch=4)


async def test_processing_twice_is_idempotent(pipeline):
    svc, docs, index, _, add, tmp = pipeline
    path = tmp / "a.pdf"
    make_pdf(path, ["Nội dung trang một khá dài để tạo nhiều đoạn văn bản. " * 30])
    d = add(path)
    await svc.process(d.id)
    first = len(index.chunks[d.id])
    docs.docs[d.id] = docs.docs[d.id].__class__(**{**docs.docs[d.id].__dict__, "status": DocumentStatus.PROCESSING})
    await svc.process(d.id)
    assert len(index.chunks[d.id]) == first


async def test_scanned_pdf_is_no_text_and_not_searchable(pipeline):
    svc, docs, index, _, add, tmp = pipeline
    path = tmp / "scan.pdf"
    make_scanned_pdf(path)
    d = add(path)
    result = await svc.process(d.id)
    assert result.outcome is Outcome.NO_TEXT
    assert docs.docs[d.id].status is DocumentStatus.NO_TEXT and docs.docs[d.id].page_count == 3
    assert index.chunks[d.id] == []  # AC-205.2: never cited


async def test_password_and_corrupt_files_are_permanent_errors(pipeline):
    svc, docs, _, _, add, tmp = pipeline
    locked, broken = tmp / "locked.pdf", tmp / "broken.pdf"
    make_locked_pdf(locked)
    broken.write_bytes(b"%PDF-1.4\n this is not really a pdf")
    d1, d2 = add(locked), add(broken)
    assert (await svc.process(d1.id)).outcome is Outcome.ERROR
    assert docs.docs[d1.id].error_code is ProcessingErrorCode.PASSWORD
    assert (await svc.process(d2.id)).outcome is Outcome.ERROR
    assert docs.docs[d2.id].error_code is ProcessingErrorCode.CORRUPT


async def test_removed_or_finished_documents_are_skipped(pipeline):
    svc, docs, index, _, add, tmp = pipeline
    path = tmp / "a.pdf"
    make_pdf(path, ["text " * 50])
    d = add(path)
    docs.docs[d.id] = docs.docs[d.id].__class__(**{**docs.docs[d.id].__dict__, "status": DocumentStatus.READY})
    assert (await svc.process(d.id)).outcome is Outcome.SKIPPED
    assert d.id not in index.chunks


async def test_transient_embedder_failure_propagates_for_retry(pipeline):
    svc, docs, _, embedder, add, tmp = pipeline
    path = tmp / "a.pdf"
    make_pdf(path, ["text " * 50])
    d = add(path)
    embedder.fail_times = 1
    with pytest.raises(RuntimeError):
        await svc.process(d.id)
    assert docs.docs[d.id].status is DocumentStatus.PROCESSING  # left for the job runner to retry
    await svc.give_up(d.id)
    assert docs.docs[d.id].error_code is ProcessingErrorCode.INTERNAL


def test_extractor_raises_typed_errors(tmp_path):
    locked = tmp_path / "l.pdf"
    make_locked_pdf(locked)
    with pytest.raises(PdfPasswordProtected):
        PyMuPdfExtractor().extract_pages(str(locked))
    junk = tmp_path / "j.pdf"
    junk.write_bytes(b"\x89PNG not a pdf at all")
    with pytest.raises(PdfCorrupt):
        PyMuPdfExtractor().extract_pages(str(junk))


def make_scan_variant(path, i: int) -> None:
    """Scanned-looking PDFs: 1–10 pages of images, some with a stamped page number or a short header (as real scans
    often have), always well under NO_TEXT_CHARS_PER_PAGE characters per page."""
    doc = fitz.open()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 120 + 20 * i, 160), False)
    pix.clear_with(150 + i * 8)
    for p in range(1 + i % 10):
        page = doc.new_page(width=595, height=842)
        page.insert_image(fitz.Rect(30, 30, 565, 812), pixmap=pix)
        if i % 3 == 1:
            page.insert_text((290, 830), str(p + 1), fontsize=8)  # page number only
        if i % 3 == 2:
            page.insert_text((40, 20), "Bản scan", fontsize=7)
    doc.save(path)
    doc.close()


async def test_ten_scanned_pdfs_are_all_no_text(pipeline):
    """T205.3 / AC-205.1 (AC-006): 10/10 scanned files → NO_TEXT, none of them searchable."""
    svc, docs, index, _, add, tmp = pipeline
    outcomes = []
    for i in range(10):
        path = tmp / f"scanned_{i:02d}.pdf"
        make_scan_variant(path, i)
        d = add(path)
        outcomes.append((await svc.process(d.id)).outcome)
        assert index.chunks[d.id] == []
    assert outcomes == [Outcome.NO_TEXT] * 10
