"""EN-03 / TQ-02: benchmark the BGE-M3 embedder against NFR-03 and the query budget.

Usage (dev compose running):  python eval/bench_embedder.py --url http://localhost:8081
Writes docs/implement/reports/embedder_benchmark.md.

(a) Indexing: 1,500 chunks of ~500 tokens in batches of 32 — a 300-page / 50 MB PDF (NFR-03: READY ≤ 5 min).
(b) Queries: 200 single short questions — p95 must be ≤ 200 ms (SAD §3.2.3).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import platform
import random
import statistics
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from chatdocs.adapters.embedder.tei import TeiEmbedder  # noqa: E402

WORDS = ("hợp đồng thanh toán bảo hành nghiệm thu báo giá khách hàng điều khoản phụ lục giá trị ngày ký bên A bên B "
         "phạt chậm trả hiệu lực bản quyền phần mềm triển khai đào tạo vận hành hỗ trợ").split()
NFR03_SECONDS = 300
QUERY_P95_MS = 200


def fake_chunk(rng: random.Random, tokens: int = 500) -> str:
    return " ".join(rng.choice(WORDS) for _ in range(int(tokens * 0.75)))


def p95(values: list[float]) -> float:
    return statistics.quantiles(values, n=100)[94]


async def run(url: str, chunks: int, batch: int, queries: int, out: str) -> int:
    rng = random.Random(42)
    emb = TeiEmbedder(base_url=url, dimension=1024, batch_size=batch)
    if not await emb.health():
        print(f"embedder at {url} is not healthy", file=sys.stderr)
        return 2
    await emb.embed(["khởi động"])  # warm-up

    texts = [fake_chunk(rng) for _ in range(chunks)]
    t0 = time.perf_counter()
    await emb.embed(texts)
    index_s = time.perf_counter() - t0

    lat = []
    for _ in range(queries):
        q = " ".join(rng.choice(WORDS) for _ in range(rng.randint(5, 15)))
        t = time.perf_counter()
        await emb.embed([q])
        lat.append((time.perf_counter() - t) * 1000)
    q95 = p95(lat)

    rate = chunks / index_s
    ok_index, ok_query = index_s <= NFR03_SECONDS * 0.6, q95 <= QUERY_P95_MS  # keep 40% of NFR-03 for extraction + DB
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"""# Embedder benchmark (EN-03, TQ-02)

| Thuộc tính | Giá trị |
|---|---|
| Ngày | {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC |
| Embedder | {url} (BGE-M3, 1024 chiều) |
| Máy chạy script | {platform.platform()} |
| Lô | {batch} |

| Phép đo | Kết quả | Ngưỡng | Đạt |
|---|---|---|---|
| Lập chỉ mục {chunks} đoạn × ~500 token (≈ file 300 trang) | {index_s:.1f} s ({rate:.1f} đoạn/s) | ≤ {NFR03_SECONDS * 0.6:.0f} s (60% của NFR-03) | {"✅" if ok_index else "❌"} |
| Truy vấn đơn, p95 trên {queries} câu | {q95:.0f} ms (trung vị {statistics.median(lat):.0f} ms) | ≤ {QUERY_P95_MS} ms | {"✅" if ok_query else "❌"} |

**Quyết định (điền sau khi review):** CPU đủ / thêm bản sao embedder / cần GPU — đóng TQ-02.
""")
    print(f"index {index_s:.1f}s ({rate:.1f}/s)  query p95 {q95:.0f}ms  -> {out}")
    return 0 if ok_index and ok_query else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8081")
    ap.add_argument("--chunks", type=int, default=1500)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--queries", type=int, default=200)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "docs", "implement", "reports",
                                                 "embedder_benchmark.md"))
    a = ap.parse_args()
    sys.exit(asyncio.run(run(a.url, a.chunks, a.batch, a.queries, a.out)))
