"""US-201, US-202 (and the duplicate check of US-206) through the HTTP API."""

from __future__ import annotations

from dataclasses import replace

import httpx

from chatdocs.adapters.http.main import create_app
from chatdocs.domain.documents.document import DocumentStatus, ProcessingErrorCode
from chatdocs.domain.jobs import JobType
from tests.conftest import csrf_headers, login, pdf_bytes


async def upload(client, data: bytes, name="Hop_dong_X.pdf", **params) -> httpx.Response:
    return await client.post(
        "/api/v1/documents",
        params=params,
        headers=csrf_headers(client),
        files={"file": (name, data, "application/pdf")},
    )


async def test_upload_creates_processing_document_job_object_and_audit(client, stack):
    _, f = stack
    await login(client)
    r = await upload(client, pdf_bytes())
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "PROCESSING" and body["fileName"] == "Hop_dong_X.pdf"
    assert body["uploadedBy"]["displayName"] == "Trần Thu Hà" and body["canRemove"] is True
    doc = next(iter(f.documents.docs.values()))
    assert doc.storage_key in f.storage.objects  # original kept in object storage
    jobs = list(f.jobs.jobs.values())
    assert len(jobs) == 1 and jobs[0].type is JobType.PROCESS_DOCUMENT
    assert jobs[0].payload == {"document_id": str(doc.id)}
    assert f.jobs.notified == ["process_document"]  # workers are woken up
    assert f.audit.actions()[-1] == "upload"


async def test_non_pdf_is_rejected_even_with_pdf_extension(client, stack):
    _, f = stack
    await login(client)
    r = await upload(client, b"\x89PNG\r\n\x1a\nfake image", name="anh.pdf")
    assert r.status_code == 415 and r.json()["code"] == "FILE_NOT_PDF"  # AC-201.3, EC-07
    assert f.documents.docs == {} and f.storage.objects == {}


async def test_too_large_file_is_rejected(client, stack):
    _, f = stack  # test settings: MAX_UPLOAD_MB = 1
    await login(client)
    big = pdf_bytes() + b"0" * (1024 * 1024)
    r = await upload(client, big)
    assert r.status_code == 413 and r.json()["code"] == "FILE_TOO_LARGE" and r.json()["max_size_mb"] == 1
    assert f.storage.objects == {}


async def test_duplicate_needs_force(client, stack):
    _, f = stack
    await login(client)
    data = pdf_bytes("same content")
    first = await upload(client, data)
    r = await upload(client, data, name="ban_sao.pdf")
    assert r.status_code == 409
    body = r.json()
    assert body["code"] == "DUPLICATE_DOCUMENT" and body["existingId"] == first.json()["id"] and body["uploadedAt"]
    r = await upload(client, data, name="ban_sao.pdf", force="true")  # US-206 "Vẫn tải"
    assert r.status_code == 202
    assert len(f.documents.docs) == 2


async def test_file_name_is_sanitised(client):
    await login(client)
    r = await upload(client, pdf_bytes(), name="..\\..\\Báo giá Q3.pdf")
    assert r.json()["fileName"] == "Báo giá Q3.pdf"


async def test_list_filters_and_can_remove(stack):
    container, f = stack
    transport = httpx.ASGITransport(app=create_app(container))
    async with (
        httpx.AsyncClient(transport=transport, base_url="https://testserver") as member,
        httpx.AsyncClient(transport=transport, base_url="https://testserver") as lead,
    ):
        await login(member, "member")
        await login(lead, "lead")
        await upload(member, pdf_bytes("one"), name="Hop_dong_X.pdf")
        f.clock.advance(seconds=1)
        await upload(lead, pdf_bytes("two"), name="Bao_gia_Q3.pdf")

        items = (await member.get("/api/v1/documents")).json()["items"]
        assert [i["fileName"] for i in items] == ["Bao_gia_Q3.pdf", "Hop_dong_X.pdf"]  # newest first
        assert {i["fileName"]: i["canRemove"] for i in items} == {"Bao_gia_Q3.pdf": False, "Hop_dong_X.pdf": True}
        lead_items = (await lead.get("/api/v1/documents")).json()["items"]
        assert all(i["canRemove"] for i in lead_items)  # PD-02: the lead may remove any document

        assert [
            i["fileName"] for i in (await member.get("/api/v1/documents", params={"q": "bao"})).json()["items"]
        ] == ["Bao_gia_Q3.pdf"]
        assert len((await member.get("/api/v1/documents", params={"q": "b"})).json()["items"]) == 2  # < 2 chars

        doc = next(d for d in f.documents.docs.values() if d.file_name == "Hop_dong_X.pdf")
        f.documents.docs[doc.id] = replace(doc, status=DocumentStatus.READY, page_count=3)
        ready = (await member.get("/api/v1/documents", params={"status": "READY"})).json()["items"]
        assert [i["fileName"] for i in ready] == ["Hop_dong_X.pdf"] and ready[0]["pageCount"] == 3
        both = await member.get("/api/v1/documents", params=[("status", "READY"), ("status", "PROCESSING")])
        assert len(both.json()["items"]) == 2


async def test_list_pagination(client, stack):
    _, f = stack
    await login(client)
    for i in range(5):
        await upload(client, pdf_bytes(f"doc {i}"), name=f"d{i}.pdf")
        f.clock.advance(seconds=1)
    page1 = (await client.get("/api/v1/documents", params={"limit": 2})).json()
    page2 = (await client.get("/api/v1/documents", params={"limit": 2, "cursor": page1["nextCursor"]})).json()
    assert [i["fileName"] for i in page1["items"] + page2["items"]] == ["d4.pdf", "d3.pdf", "d2.pdf", "d1.pdf"]


async def test_retry_only_for_error_documents_and_owner(stack):
    container, f = stack
    transport = httpx.ASGITransport(app=create_app(container))
    async with (
        httpx.AsyncClient(transport=transport, base_url="https://testserver") as owner,
        httpx.AsyncClient(transport=transport, base_url="https://testserver") as other,
    ):
        await login(owner, "member")
        await login(other, "member2")
        doc_id = (await upload(owner, pdf_bytes())).json()["id"]
        url = f"/api/v1/documents/{doc_id}/retry"
        r = await owner.post(url, headers=csrf_headers(owner))
        assert r.status_code == 409 and r.json()["code"] == "INVALID_STATE"  # still PROCESSING

        doc = next(iter(f.documents.docs.values()))
        f.documents.docs[doc.id] = replace(doc, status=DocumentStatus.ERROR, error_code=ProcessingErrorCode.CORRUPT)
        assert (await other.post(url, headers=csrf_headers(other))).status_code == 403
        r = await owner.post(url, headers=csrf_headers(owner))
        assert r.status_code == 202 and r.json()["status"] == "PROCESSING"
        assert f.documents.docs[doc.id].status is DocumentStatus.PROCESSING
        assert len(f.jobs.jobs) == 2  # a new processing job was queued
        bad = await owner.post("/api/v1/documents/not-a-uuid/retry", headers=csrf_headers(owner))
        assert bad.status_code == 404
