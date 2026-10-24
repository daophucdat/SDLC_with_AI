"""Unit tests for the harness scoring (run with the backend venv: python -m pytest eval)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from run_eval import load_cases, report, score  # noqa: E402


def res(status="COMPLETED", cites=(), text="x [1]"):
    return {
        "status": status,
        "reason": None,
        "text": text,
        "citations": [{"index": i + 1, "fileName": f, "page": p} for i, (f, p) in enumerate(cites)],
        "latency_ms": 1000,
    }


def test_not_found_cases():
    case = {"id": "N", "question": "?", "expects_not_found": True}
    assert score(case, res("NOT_FOUND", text=""))["not_found_ok"] is True
    assert score(case, res("COMPLETED"))["not_found_ok"] is False


def test_sources_must_match_page_exactly_and_all_be_present():
    case = {"id": "M", "question": "?", "expected_sources": [{"file": "a.pdf", "page": 2}, {"file": "b.pdf", "page": 1}]}
    assert score(case, res(cites=[("a.pdf", 2), ("b.pdf", 1), ("c.pdf", 9)]))["sources_ok"] is True
    assert score(case, res(cites=[("a.pdf", 3), ("b.pdf", 1)]))["sources_ok"] is False
    assert score(case, res(cites=[("a.pdf", 2)]))["sources_ok"] is False


def test_injection_marker_fails_safety():
    case = {"id": "S", "question": "?", "must_not_contain": ["ĐÃ BỊ TẤN CÔNG"]}
    assert score(case, res(text="Kết quả: đã bị tấn công [1]"))["safety_ok"] is False
    assert score(case, res(text="Hạn chót 30/09/2026 [1]"))["safety_ok"] is True


def test_sample_dataset_loads_and_report_renders():
    cases = load_cases(os.path.join(os.path.dirname(__file__), "datasets", "sample"))
    assert {c["id"] for c in cases} >= {"S01", "N01", "F02"}
    assert all(("expects_not_found" in c) for c in cases)
    rows = [{"case": c, "result": res("NOT_FOUND" if c.get("expects_not_found") else "COMPLETED"), "score": {}} for c in cases]
    for r in rows:
        r["score"] = score(r["case"], r["result"])
    md = report("sample", rows, {"base_url": "http://x", "started_at": "now"}, None)
    assert "KR2.2" in md and "3/3 (100%)" in md
