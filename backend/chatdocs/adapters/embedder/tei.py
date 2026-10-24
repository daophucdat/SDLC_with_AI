"""Hugging Face Text Embeddings Inference adapter for BGE-M3 (EN-03, ADR-08). Internal network only."""

from __future__ import annotations

import asyncio
import math

import httpx

RETRY_DELAYS = (0.1, 0.4, 1.6)  # SAD §4.2: 3 retries, 100 ms → 400 ms → 1.6 s


class EmbedderError(Exception):
    pass


def l2_normalise(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    return vec if norm == 0 else [x / norm for x in vec]


class TeiEmbedder:
    def __init__(
        self,
        *,
        base_url: str,
        dimension: int,
        batch_size: int = 32,
        timeout_s: float = 2.0,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self.dimension = dimension
        self._url = base_url.rstrip("/")
        self._batch = batch_size
        # Indexing batches of 32 x 500 tokens take longer than one query on CPU; 2 s is the per-query budget.
        self._http = http or httpx.AsyncClient(timeout=httpx.Timeout(max(timeout_s, 30.0), connect=2.0))
        self._query_timeout = timeout_s

    async def _post(self, texts: list[str]) -> list[list[float]]:
        timeout = self._query_timeout if len(texts) == 1 else None
        last: Exception | None = None
        for attempt in range(len(RETRY_DELAYS) + 1):
            try:
                kwargs = {"timeout": timeout} if timeout else {}
                r = await self._http.post(
                    f"{self._url}/embed", json={"inputs": texts, "truncate": True, "normalize": True}, **kwargs
                )
                if r.status_code >= 500 or r.status_code == 429:
                    raise EmbedderError(f"embedder HTTP {r.status_code}")
                r.raise_for_status()
                data = r.json()
                if not isinstance(data, list) or len(data) != len(texts):
                    raise EmbedderError("unexpected embedder response shape")
                return data
            except (httpx.TransportError, EmbedderError) as e:
                last = e
                if attempt < len(RETRY_DELAYS):
                    await asyncio.sleep(RETRY_DELAYS[attempt])
            except httpx.HTTPStatusError as e:  # 4xx other than 429: not retryable
                raise EmbedderError(f"embedder rejected request: HTTP {e.response.status_code}") from e
        raise EmbedderError("embedder unavailable") from last

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self._batch):
            for vec in await self._post(texts[i : i + self._batch]):
                if len(vec) != self.dimension:
                    raise EmbedderError(f"expected {self.dimension}-d vectors, got {len(vec)}")
                out.append(l2_normalise([float(x) for x in vec]))
        return out

    async def health(self) -> bool:
        try:
            r = await self._http.get(f"{self._url}/health", timeout=2.0)
            return r.status_code == 200
        except httpx.HTTPError:
            return False
