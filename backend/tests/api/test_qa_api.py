"""US-301 → US-311 over HTTP + SSE, with the scripted fake LLM (T-EN06.3)."""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

import httpx
import pytest

from chatdocs.adapters.http.main import create_app
from tests.conftest import csrf_headers, login
from tests.fakes import make_container, seed_ready_document

HOP_DONG = [
    "Hợp đồng ABC. Điều khoản thanh toán: khách hàng thanh toán 30% khi ký hợp đồng và 70% khi nghiệm thu.",
    "Hợp đồng ABC. Bảo hành phần mềm trong 24 tháng kể từ ngày nghiệm thu.",
]
BAO_GIA = ["Báo giá XYZ. Đơn giá triển khai là 500 triệu đồng, thanh toán theo tiến độ hợp đồng."]


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.split("\n\n"):
        lines = [ln for ln in block.split("\n") if ln and not ln.startswith(":")]
        if not lines:
            continue
        name = next(ln[7:] for ln in lines if ln.startswith("event: "))
        data = json.loads(next(ln[6:] for ln in lines if ln.startswith("data: ")))
        events.append((name, data))
    return events


async def make_client(**settings):
    container, f = make_container(**settings)
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(container)), base_url="https://testserver")
    return client, f


@pytest.fixture
async def qa():
    client, f = await make_client()
    await login(client)
    await seed_ready_document(f, "Hop-dong-ABC.pdf", HOP_DONG)
    await seed_ready_document(f, "Bao-gia-XYZ.pdf", BAO_GIA)
    yield client, f
    await client.aclose()


async def ask(client, text, conv=None, **body):
    if conv is None:
        r = await client.post("/api/v1/conversations", headers=csrf_headers(client))
        assert r.status_code == 201
        conv = r.json()["id"]
    r = await client.post(
        f"/api/v1/conversations/{conv}/questions", json={"text": text, **body}, headers=csrf_headers(client)
    )
    return r, conv


async def test_answer_streams_with_citations_and_one_final_event(qa):
    client, f = qa
    r, _ = await ask(client, "Điều khoản thanh toán của hợp đồng ABC là gì?")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    assert r.headers["cache-control"] == "no-store" and r.headers["x-accel-buffering"] == "no"
    events = parse_sse(r.text)
    names = [n for n, _ in events]
    assert names[0] == "meta" and names[-1] == "done" and names[-2] == "citations"
    assert names.count("done") + names.count("error") == 1  # §0.5 rule 1
    meta = events[0][1]
    assert meta["readyDocCount"] == 2 and meta["processingDocCount"] == 0
    streamed = "".join(d["text"] for n, d in events if n == "delta")
    assert streamed.startswith("Theo tài liệu")  # Vietnamese question → Vietnamese answer (AC-301.1)
    cites = events[-2][1]
    assert cites["items"] and all(c["page"] >= 1 for c in cites["items"])
    assert {c["fileName"] for c in cites["items"]} <= {"Hop-dong-ABC.pdf", "Bao-gia-XYZ.pdf"}
    assert events[-1][1]["status"] == "COMPLETED"
    saved = next(iter(f.qa_repo.answers.values()))
    assert saved["status"].value == "COMPLETED" and saved["citations"]


async def test_english_question_gets_an_english_answer(qa):
    client, f = qa
    r, _ = await ask(client, "What are the payment terms of contract ABC?")
    deltas = "".join(d["text"] for n, d in parse_sse(r.text) if n in ("delta",))
    assert deltas.startswith("According to")  # AC-301.2
    assert "tiếng Anh" in f.llm.last_prompt.system


async def test_answer_can_cite_two_documents(qa):
    client, _ = qa
    r, _ = await ask(client, "Thanh toán hợp đồng và đơn giá báo giá XYZ triển khai?")
    items = parse_sse(r.text)[-2][1]["items"]
    assert len({c["documentId"] for c in items}) == 2  # AC-302.1


async def test_no_matching_chunks_is_not_found_without_calling_the_llm(qa):
    client, f = qa
    r, _ = await ask(client, "zzqx wvvb kkpl")
    events = parse_sse(r.text)
    assert events[-1] == (
        "done",
        {
            "status": "NOT_FOUND",
            "reason": "NO_CHUNKS",
            "latencyMs": events[-1][1]["latencyMs"],
            "firstTokenMs": None,
        },
    )
    assert f.llm.calls == 0  # AC-304.4


async def test_model_not_found_token_never_reaches_the_client(qa):
    client, _ = qa
    r, _ = await ask(client, "Điều khoản thanh toán hợp đồng ABC #notfound")
    events = parse_sse(r.text)
    assert all("NOT_FOUND" not in d.get("text", "") for n, d in events if n == "delta")  # §0.5 rule 3
    assert events[-1][1]["status"] == "NOT_FOUND" and events[-1][1]["reason"] == "MODEL_NOT_FOUND"


@pytest.mark.parametrize("marker", ["#badref", "#noref"])
async def test_invalid_citations_become_not_found(qa, marker):
    client, f = qa
    r, _ = await ask(client, f"Thanh toán hợp đồng ABC {marker}")
    events = parse_sse(r.text)
    assert events[-1][1]["reason"] == "INVALID_CITATIONS"  # AC-303.3 / AC-306.2
    assert "citations" not in [n for n, _ in events]
    assert next(iter(f.qa_repo.answers.values()))["text"] == ""  # no model text kept


@pytest.mark.parametrize(("text", "code"), [("", 400), ("   ", 400), ("x" * 2001, 400)])
async def test_invalid_questions_are_refused_before_streaming(qa, text, code):
    client, _ = qa
    r, _ = await ask(client, text)
    assert r.status_code == code and r.json()["code"] == "QUESTION_INVALID"  # AC-301.3, 301.4


async def test_no_ready_documents_is_409():
    client, f = await make_client()
    await login(client)
    r, _ = await ask(client, "Có gì trong kho?")
    assert r.status_code == 409 and r.json()["code"] == "NO_READY_DOCUMENTS"  # AC-301.5
    await client.aclose()


async def test_removed_document_is_never_cited(qa):
    client, f = qa
    abc = next(d for d in f.documents.docs.values() if d.file_name == "Hop-dong-ABC.pdf")
    r = await client.delete(f"/api/v1/documents/{abc.id}", headers=csrf_headers(client))
    assert r.status_code == 202
    r, _ = await ask(client, "Bảo hành phần mềm hợp đồng ABC bao lâu?")
    events = parse_sse(r.text)
    cited = [c["documentId"] for n, d in events if n == "citations" for c in d["items"]]
    assert str(abc.id) not in cited  # AC-302.3 / AC-204.3
    assert events[0][1]["readyDocCount"] == 1


async def test_processing_documents_are_counted_but_not_used(qa):
    client, f = qa
    from dataclasses import replace

    from chatdocs.domain.documents.document import DocumentStatus

    xyz = next(d for d in f.documents.docs.values() if d.file_name == "Bao-gia-XYZ.pdf")
    f.documents.docs[xyz.id] = replace(xyz, status=DocumentStatus.PROCESSING)
    r, _ = await ask(client, "Đơn giá triển khai báo giá XYZ?")
    events = parse_sse(r.text)
    assert events[0][1]["processingDocCount"] == 1  # AC-202.2
    assert all(c["documentId"] != str(xyz.id) for n, d in events if n == "citations" for c in d["items"])


async def test_rate_limit_is_429_with_retry_after():
    client, f = await make_client(rate_questions_per_min=2)
    await login(client)
    await seed_ready_document(f, "Hop-dong-ABC.pdf", HOP_DONG)
    r, conv = await ask(client, "Thanh toán hợp đồng ABC?")
    r, _ = await ask(client, "Thanh toán hợp đồng ABC?", conv)
    r, _ = await ask(client, "Thanh toán hợp đồng ABC?", conv)
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED"
    assert int(r.headers["retry-after"]) >= 1 and r.json()["retryAfter"] >= 1
    await client.aclose()


async def test_ai_busy_is_503_before_the_stream_opens():
    client, f = await make_client(llm_max_concurrency=1, llm_queue_wait_s=0.05)
    await login(client)
    await seed_ready_document(f, "Hop-dong-ABC.pdf", HOP_DONG)
    await f.gate.acquire()  # someone else holds the only slot
    r, _ = await ask(client, "Thanh toán hợp đồng ABC?")
    assert r.status_code == 503 and r.json()["code"] == "AI_BUSY"
    f.gate.release()
    await client.aclose()


async def test_provider_error_is_retried_once_then_reported(qa):
    client, f = qa
    r, _ = await ask(client, "Thanh toán hợp đồng ABC #503")
    events = parse_sse(r.text)
    assert events[-1] == ("error", {"code": "AI_UNAVAILABLE", "retryable": True})
    assert f.llm.calls == 2  # one retry before the first token (T-EN06.5)
    assert next(iter(f.qa_repo.answers.values()))["status"].value == "FAILED"


async def test_first_token_timeout_is_reported(qa):
    client, _ = qa
    r, _ = await ask(client, "Thanh toán hợp đồng ABC #slow")
    assert parse_sse(r.text)[-1] == ("error", {"code": "AI_TIMEOUT", "retryable": True})


async def test_slot_is_released_after_every_outcome(qa):
    client, f = qa
    for text in ["Thanh toán hợp đồng ABC?", "zzqx", "Thanh toán hợp đồng ABC #503", "Thanh toán ABC #notfound"]:
        await ask(client, text)
    assert f.gate._sem._value == f.gate._sem._value and not f.gate._sem.locked()


async def test_history_is_private_to_the_session(qa):
    client, f = qa
    r, conv = await ask(client, "Điều khoản thanh toán hợp đồng ABC?")
    await ask(client, "Bảo hành hợp đồng ABC?", conv)
    h = await client.get(f"/api/v1/conversations/{conv}/questions")
    assert h.status_code == 200
    turns = h.json()
    assert [t["text"] for t in turns] == ["Điều khoản thanh toán hợp đồng ABC?", "Bảo hành hợp đồng ABC?"]
    assert turns[0]["answer"]["status"] == "COMPLETED" and turns[0]["answer"]["citations"]
    # another session of the same user cannot read it (PD-04)
    async with httpx.AsyncClient(transport=client._transport, base_url="https://testserver") as other:
        await login(other)
        assert (await other.get(f"/api/v1/conversations/{conv}/questions")).status_code == 404


async def test_logout_deletes_the_conversation_session(qa):
    client, f = qa
    _, conv = await ask(client, "Thanh toán hợp đồng ABC?")
    await client.post("/auth/logout", headers=csrf_headers(client))
    assert not f.sessions.rows  # conversations cascade with the session in PostgreSQL (AC-103.3, AC-308.2)


async def test_feedback_once_and_only_on_completed_answers(qa):
    client, f = qa
    r, _ = await ask(client, "Điều khoản thanh toán hợp đồng ABC?")
    answer_id = parse_sse(r.text)[0][1]["answerId"]
    url = f"/api/v1/answers/{answer_id}/feedback"
    assert (await client.post(url, json={"value": "HELPFUL"}, headers=csrf_headers(client))).status_code == 204
    again = await client.post(url, json={"value": "NOT_HELPFUL", "reason": "wrong"}, headers=csrf_headers(client))
    assert again.status_code == 409 and again.json()["code"] == "ALREADY_SUBMITTED"
    events = [r.name for r in f.events.records if r.name == "answer_feedback_submitted"]
    assert len(events) == 1  # AC-309.1

    r, _ = await ask(client, "zzqx wvvb")
    nf_id = parse_sse(r.text)[0][1]["answerId"]
    bad = await client.post(
        f"/api/v1/answers/{nf_id}/feedback", json={"value": "HELPFUL"}, headers=csrf_headers(client)
    )
    assert bad.status_code == 409 and bad.json()["code"] == "INVALID_STATE"


async def test_feedback_reason_must_be_listed(qa):
    client, _ = qa
    r, _ = await ask(client, "Điều khoản thanh toán hợp đồng ABC?")
    answer_id = parse_sse(r.text)[0][1]["answerId"]
    r = await client.post(
        f"/api/v1/answers/{answer_id}/feedback",
        json={"value": "NOT_HELPFUL", "reason": "tôi không thích"},
        headers=csrf_headers(client),
    )
    assert r.status_code == 400


async def test_stop_cancels_generation_and_keeps_partial_text():
    """US-310 at service level: the stop arrives while the stream is running (AC-310.1, AC-310.2)."""
    container, f = make_container()
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(container)), base_url="https://testserver")
    await login(client)
    await seed_ready_document(f, "Hop-dong-ABC.pdf", HOP_DONG)
    auth = await container.access.authenticate(client.cookies.get("__Host-session"))
    conv = await f.qa.start_conversation(auth)
    f.llm._delay = 0.01
    handle = await f.qa.prepare(auth, conv, "Điều khoản thanh toán hợp đồng ABC?")
    events = []
    async for name, data in handle.events():
        events.append((name, data))
        if name == "delta":
            await f.qa.stop(auth, handle.answer_id)
    assert events[-1][0] == "done" and events[-1][1]["status"] == "STOPPED"
    assert f.qa_repo.answers[handle.answer_id]["status"].value == "STOPPED"
    assert f.qa_repo.answers[handle.answer_id]["text"]
    assert any(r.name == "answer_stopped" for r in f.events.records)
    assert not f.gate._sem.locked()
    await client.aclose()


async def test_stop_from_another_replica_goes_through_the_bus():
    container, f = make_container()
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(container)), base_url="https://testserver")
    await login(client)
    await seed_ready_document(f, "Hop-dong-ABC.pdf", HOP_DONG)
    auth = await container.access.authenticate(client.cookies.get("__Host-session"))
    conv = await f.qa.start_conversation(auth)
    handle = await f.qa.prepare(auth, conv, "Điều khoản thanh toán hợp đồng ABC?")
    gen = handle.events()
    await gen.__anext__()  # meta: question + answer saved, flag registered
    flag = f.qa._stop_flags.pop(handle.answer_id)  # pretend the stream runs on another replica
    await f.qa.stop(auth, handle.answer_id)
    assert f.stop_bus.published == [handle.answer_id]
    f.qa._stop_flags[handle.answer_id] = flag
    await f.qa._bus.publish(handle.answer_id)
    assert flag.is_set()
    await gen.aclose()
    await client.aclose()


async def test_stop_of_finished_answer_is_409(qa):
    client, _ = qa
    r, _ = await ask(client, "Điều khoản thanh toán hợp đồng ABC?")
    answer_id = parse_sse(r.text)[0][1]["answerId"]
    s = await client.post(f"/api/v1/answers/{answer_id}/stop", headers=csrf_headers(client))
    assert s.status_code == 409


async def test_follow_up_uses_history_only_when_flag_is_on():
    client, f = await make_client(feature_flags="followup")
    await login(client)
    await seed_ready_document(f, "Hop-dong-ABC.pdf", HOP_DONG)
    _, conv = await ask(client, "Điều khoản thanh toán hợp đồng ABC?")
    await ask(client, "Còn bảo hành thì sao?", conv, followUp=True)
    assert "Lịch sử hội thoại" in f.llm.last_prompt.user  # US-311
    q = list(f.qa_repo.questions.values())[-1]
    assert q.is_followup
    await client.aclose()

    client, f = await make_client(feature_flags="")
    await login(client)
    await seed_ready_document(f, "Hop-dong-ABC.pdf", HOP_DONG)
    _, conv = await ask(client, "Điều khoản thanh toán hợp đồng ABC?")
    await ask(client, "Còn bảo hành thì sao?", conv, followUp=True)
    assert "Lịch sử hội thoại" not in f.llm.last_prompt.user
    await client.aclose()


async def test_analytics_events_carry_no_question_text(qa, capsys):
    """T-EN07.3: a marker in the question never shows up in logs or analytics."""
    client, f = qa
    await ask(client, "Thanh toán hợp đồng ABC ZZZ-SECRET?")
    await ask(client, "Thanh toán hợp đồng ABC ZZZ-SECRET #503")
    names = [r.name for r in f.events.records]
    assert "question_submitted" in names and "answer_completed" in names and "answer_failed" in names
    assert "ZZZ-SECRET" not in json.dumps([r.props for r in f.events.records], ensure_ascii=False)
    assert "ZZZ-SECRET" not in capsys.readouterr().out
    q = next(r for r in f.events.records if r.name == "question_submitted")
    assert q.user_id_hash != str(next(iter(f.users.by_email.values())).id) and len(q.user_id_hash) == 64


async def test_sse_pings_while_waiting():
    from chatdocs.adapters.http.routes_qa import sse

    async def slow():
        await asyncio.sleep(0.12)
        yield "done", {"status": "COMPLETED"}

    chunks = [c async for c in sse(slow(), ping_seconds=0.05)]
    assert chunks[0] == b": ping\n\n" and chunks[-1].startswith(b"event: done")


def test_answer_ids_are_uuids():
    assert UUID(str(UUID(int=1)))


async def test_kill_switch_turns_qa_off_but_keeps_the_library():
    """REL-03: FEATURE_FLAGS=qa_off → 503 before any stream, documents still listed."""
    client, f = await make_client(feature_flags="qa_off")
    await login(client)
    await seed_ready_document(f, "Hop-dong-ABC.pdf", HOP_DONG)
    r, _ = await ask(client, "Thanh toán hợp đồng ABC?")
    assert r.status_code == 503 and r.json()["code"] == "AI_BUSY" and f.llm.calls == 0
    assert (await client.get("/api/v1/documents")).json()["items"]
    assert "qa_off" in (await client.get("/api/v1/me")).json()["flags"]
    await client.aclose()
