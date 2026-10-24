from __future__ import annotations

import math

import httpx
import pytest

from chatdocs.adapters.embedder import tei
from chatdocs.adapters.embedder.tei import EmbedderError, TeiEmbedder


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def _sleep(_):
        return None

    monkeypatch.setattr(tei.asyncio, "sleep", _sleep)


def embedder(handler, dim=3, batch=2) -> TeiEmbedder:
    return TeiEmbedder(
        base_url="http://emb",
        dimension=dim,
        batch_size=batch,
        http=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


async def test_batches_and_normalises():
    sizes = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = __import__("json").loads(request.content)
        sizes.append(len(body["inputs"]))
        assert body["truncate"] is True
        return httpx.Response(200, json=[[3.0, 4.0, 0.0] for _ in body["inputs"]])

    vecs = await embedder(handler).embed(["a", "b", "c", "d", "e"])
    assert sizes == [2, 2, 1]
    assert len(vecs) == 5 and all(math.isclose(sum(x * x for x in v), 1.0) for v in vecs)


async def test_retries_transient_errors_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json=[[1.0, 0.0, 0.0]])

    assert await embedder(handler).embed(["q"]) == [[1.0, 0.0, 0.0]]
    assert calls["n"] == 3


async def test_gives_up_after_three_retries():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        raise httpx.ConnectError("refused")

    with pytest.raises(EmbedderError):
        await embedder(handler).embed(["q"])
    assert calls["n"] == 4  # 1 attempt + 3 retries


async def test_rejects_wrong_dimension_and_4xx():
    with pytest.raises(EmbedderError):
        await embedder(lambda r: httpx.Response(200, json=[[1.0, 2.0]])).embed(["q"])
    calls = {"n": 0}

    def bad(request):
        calls["n"] += 1
        return httpx.Response(413, json={"error": "too long"})

    with pytest.raises(EmbedderError):
        await embedder(bad).embed(["q"])
    assert calls["n"] == 1  # client errors are not retried
