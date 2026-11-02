"""MCP server of this repo: the project's sources of truth as read-only tools for any MCP client.

Claude Code starts it from ``.mcp.json`` (stdio). Standard library only — no ``mcp`` package, so any Python ≥ 3.10
runs it, the same way CI runs the other scripts. Tools (all read-only; running tests stays in /run-test-case):

- ``story``        US-xxx → story + AC (userStory.md), traceability row, its test cases;
- ``test_cases``   TC-xxx-yy / AC-xxx.y / US-xxx → rows of docs/test-cases.md with the PASS / FAIL expectations;
- ``test_results`` latest results per TC from reports/results-<run>.json + screenshot / GIF / video paths;
- ``defect``       BUG-n / TD-n / HD-n / OBS-n → its section in docs/bugs.md;
- ``find_code``    any requirement code (BR-001, SEC-06, NFR-03, ADR-…) → every line in docs/ that mentions it.

Protocol: JSON-RPC 2.0, one message per line on stdin / stdout (MCP stdio transport). Logs go to stderr only.

    python scripts/mcp_server.py            # normally started by the MCP client, not by hand
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
REPORTS = ROOT / "reports"
STORIES = DOCS / "implement" / "userStory.md"
TEST_CASES = DOCS / "test-cases.md"
TRACE = DOCS / "traceability.md"
BUGS = DOCS / "bugs.md"
MAX_LINES = 200  # keeps a tool answer well inside the client's context budget
SERVER = {"name": "chatdocs-sdlc", "version": "1.0.0"}

sys.path.insert(0, str(Path(__file__).parent))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _section(text: str, heading: re.Pattern[str]) -> str:
    """From the first heading line matching ``heading`` to the next heading of the same or higher level."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = heading.match(line)
        if not m:
            continue
        level = len(line) - len(line.lstrip("#"))
        end = next(
            (j for j in range(i + 1, len(lines)) if re.match(rf"^#{{1,{level}}} ", lines[j])),
            len(lines),
        )
        return "\n".join(lines[i:end]).strip()
    return ""


def _tc_rows(query: str) -> list[str]:
    """Table rows of docs/test-cases.md whose TC or AC column contains ``query`` (US-201 → every TC-201-…)."""
    q = query.strip().upper()
    if re.fullmatch(r"US-\d{3}", q):
        q = "TC-" + q[3:] + "-"
    return [ln for ln in _read(TEST_CASES).splitlines() if ln.startswith("| TC-") and q in ln.upper()[:40]]


TC_HEADER = "| TC | AC | H | Bước | PASS khi (ghi trước) | FAIL khi |\n|---|---|---|---|---|---|"


def story(us: str) -> str:
    us = us.strip().upper()
    body = _section(_read(STORIES), re.compile(rf"^#+ {re.escape(us)}\b"))
    if not body:
        return f"{us}: không có trong {STORIES.relative_to(ROOT).as_posix()}"
    trace = [ln for ln in _read(TRACE).splitlines() if ln.startswith(f"| {us} ")]
    rows = _tc_rows(us)
    parts = [body, "", "## Truy vết (docs/traceability.md)", *(trace or ["(chưa có dòng)"]), ""]
    parts += ["## Test case (docs/test-cases.md)", TC_HEADER, *rows] if rows else ["## Test case", "(chưa có TC)"]
    return "\n".join(parts)


def test_cases(query: str) -> str:
    rows = _tc_rows(query)
    return "\n".join([TC_HEADER, *rows]) if rows else f"không có test case khớp {query!r}"


def test_results(run: str = "") -> str:
    from test_report import evidence, load_run

    paths = sorted(REPORTS.glob("results-run*.json"))
    path = REPORTS / f"results-{run}.json" if run else (paths[-1] if paths else None)
    if path is None or not path.exists():
        return "chưa có reports/results-<run>.json — chạy /run-test-case trước"
    name = path.stem.removeprefix("results-")
    lines = [f"Lượt {name} ({path.relative_to(ROOT).as_posix()}); đường dẫn bằng chứng tính từ reports/", ""]
    results = load_run(path)
    for tc, r in sorted(results.items()):
        lines.append(f"- {tc}: {r['status']} · {r['seconds']:.1f} s · {' '.join(evidence(name, tc)) or '—'}")
    passed = sum(1 for r in results.values() if r["status"] == "passed")
    return "\n".join([*lines, "", f"Tổng: {passed}/{len(results)} PASS"])


def defect(defect_id: str) -> str:
    d = defect_id.strip().upper()
    body = _section(_read(BUGS), re.compile(rf"^#+ {re.escape(d)} "))
    return body or f"{d}: không có trong docs/bugs.md"


def find_code(code: str) -> str:
    code = code.strip()
    if len(code) < 3:
        return "mã quá ngắn — ví dụ BR-001, SEC-06, NFR-03, AC-201.2"
    hits = []
    for path in sorted(DOCS.rglob("*.md")):
        for n, line in enumerate(_read(path).splitlines(), 1):
            if code in line:
                hits.append(f"{path.relative_to(ROOT).as_posix()}:{n}: {line.strip()[:240]}")
    if not hits:
        return f"không thấy {code!r} trong docs/"
    more = f"\n… và {len(hits) - MAX_LINES} dòng nữa" if len(hits) > MAX_LINES else ""
    return "\n".join(hits[:MAX_LINES]) + more


def _schema(prop: str, description: str, required: bool = True) -> dict:
    return {
        "type": "object",
        "properties": {prop: {"type": "string", "description": description}},
        "required": [prop] if required else [],
    }


TOOLS = {
    "story": (
        story,
        "User story US-xxx: nội dung + AC, dòng truy vết US ↔ BR ↔ code ↔ test, các test case của nó.",
        _schema("us", "Mã story, ví dụ US-201"),
    ),
    "test_cases": (
        test_cases,
        "Test case trong docs/test-cases.md kèm kỳ vọng PASS / FAIL ghi trước khi chạy.",
        _schema("query", "TC-201-05, AC-201.2 hoặc US-201"),
    ),
    "test_results": (
        test_results,
        "Kết quả một lượt chạy Playwright theo TC (mặc định lượt cuối theo tên: run2 > run1),"
        " kèm link ảnh / GIF / video.",
        _schema("run", "Tên lượt, ví dụ run2; bỏ trống = lượt mới nhất", required=False),
    ),
    "defect": (
        defect,
        "Phiếu lỗi trong docs/bugs.md: BUG-n (sản phẩm), TD-n (dữ liệu / kỳ vọng TC), HD-n (bộ chạy), OBS-n.",
        _schema("defect_id", "Ví dụ HD-1, TD-2, OBS-1"),
    ),
    "find_code": (
        find_code,
        "Mọi dòng trong docs/ nhắc tới một mã yêu cầu (BR-001, SEC-06, NFR-03, AC-303.2, ADR-…), có file:dòng.",
        _schema("code", "Mã cần tìm"),
    ),
}


def handle(msg: dict) -> dict | None:
    """One JSON-RPC request → response (None for notifications)."""
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        return None  # notifications/initialized, notifications/cancelled …
    if method == "initialize":
        version = msg.get("params", {}).get("protocolVersion", "2025-06-18")
        result = {"protocolVersion": version, "capabilities": {"tools": {}}, "serverInfo": SERVER}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{"name": n, "description": d, "inputSchema": s} for n, (_, d, s) in TOOLS.items()]}
    elif method == "tools/call":
        result = call_tool(msg.get("params", {}))
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def call_tool(params: dict) -> dict:
    name, args = params.get("name"), params.get("arguments") or {}
    if name not in TOOLS:
        return {"content": [{"type": "text", "text": f"unknown tool {name}"}], "isError": True}
    try:
        text = TOOLS[name][0](**args)
    except Exception as exc:  # noqa: BLE001 — a tool error is reported to the client, never kills the server
        return {"content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}], "isError": True}
    return {"content": [{"type": "text", "text": text}], "isError": False}


def _reply(line: str) -> dict | None:
    try:
        return handle(json.loads(line))
    except json.JSONDecodeError as exc:
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}


def main() -> int:
    # UTF-8 both ways whatever the console code page (Windows defaults to cp1252)
    with (
        open(sys.stdin.fileno(), encoding="utf-8", closefd=False) as stdin,
        open(sys.stdout.fileno(), "w", encoding="utf-8", newline="\n", closefd=False) as stdout,
    ):
        for line in stdin:
            reply = _reply(line) if line.strip() else None
            if reply is not None:
                stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
                stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
