from __future__ import annotations

from uuid import UUID, uuid4

from chatdocs.application.retrieval_service import RetrievalConfig, RetrievalService
from chatdocs.domain.documents.chunking import chunk_document
from chatdocs.domain.retrieval.rrf import Candidate, is_empty, rrf_fuse, select_top
from tests.fakes import FakeEmbedder, MemChunkIndex


def cand(doc: UUID, n: int, cos=None, fts=None) -> Candidate:
    return Candidate(UUID(int=n), doc, 1, f"c{n}", cosine=cos, fts_rank=fts)


def test_rrf_rewards_chunks_found_by_both_queries():
    d = uuid4()
    vector = [cand(d, 1, cos=0.9), cand(d, 2, cos=0.8), cand(d, 3, cos=0.7)]
    fts = [cand(d, 3, fts=5.0), cand(d, 4, fts=4.0)]
    fused = rrf_fuse(vector, fts, k=60)
    assert fused[0].chunk_id == UUID(int=3)  # 1/63 + 1/61 beats 1/61 alone
    assert {c.chunk_id for c in fused} == {UUID(int=i) for i in (1, 2, 3, 4)}
    merged = next(c for c in fused if c.chunk_id == UUID(int=3))
    assert merged.cosine == 0.7 and merged.fts_rank == 5.0


def test_select_top_caps_chunks_per_document():
    a, b = uuid4(), uuid4()
    fused = [cand(a, i) for i in range(1, 6)] + [cand(b, i) for i in range(6, 9)]
    top = select_top(fused, top_n=8, max_per_document=3)
    assert sum(1 for c in top if c.document_id == a) == 3
    assert sum(1 for c in top if c.document_id == b) == 3


def test_is_empty_rule():
    assert is_empty(None, 0, 0.35)
    assert is_empty(0.2, 0, 0.35)
    assert not is_empty(0.2, 1, 0.35)  # a keyword hit (contract number, name) is enough
    assert not is_empty(0.5, 0, 0.35)


async def _service_with_docs():
    index, embedder = MemChunkIndex(), FakeEmbedder()
    docs = {
        "hop_dong": ["Điều khoản thanh toán: thanh toán 30% khi ký hợp đồng", "Phụ lục bảo hành 12 tháng"],
        "bao_gia": ["Báo giá quý 3 gồm bản quyền phần mềm", "Hiệu lực báo giá đến 31/12"],
    }
    ids = {}
    for name, pages in docs.items():
        did = uuid4()
        chunks = chunk_document(pages, 500, 80)
        await index.replace_document(did, pages, chunks, await embedder.embed([c.content for c in chunks]))
        ids[name] = did
    svc = RetrievalService(embedder=embedder, index=index, config=RetrievalConfig(tau=0.3))
    return svc, ids, embedder


async def test_search_returns_relevant_chunks_with_pages():
    svc, ids, _ = await _service_with_docs()
    res = await svc.search("điều khoản thanh toán", list(ids.values()))
    assert not res.empty
    assert res.chunks[0].document_id == ids["hop_dong"] and res.chunks[0].page_number == 1


async def test_search_only_inside_given_documents():
    svc, ids, _ = await _service_with_docs()
    res = await svc.search("thanh toán hợp đồng", [ids["bao_gia"]])  # removed / not-ready docs are not passed in
    assert all(c.document_id == ids["bao_gia"] for c in res.chunks)


async def test_search_empty_when_nothing_matches():
    svc, ids, _ = await _service_with_docs()
    res = await svc.search("zzz qqq", list(ids.values()))
    assert res.empty and res.chunks == []
    assert (await svc.search("thanh toán", [])).empty


async def test_query_embedding_is_cached():
    svc, ids, embedder = await _service_with_docs()
    before = embedder.calls
    await svc.search("Thanh  toán", list(ids.values()))
    await svc.search("thanh toán", list(ids.values()))  # same after NFC + lowercase + whitespace normalisation
    assert embedder.calls == before + 1
