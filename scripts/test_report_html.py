"""Day 6 test report as one page to read or send: reports/test-report.html (screenshots, GIFs, video players) and
reports/test-report.pdf (the same page printed by Playwright's Chromium — screenshots instead of video).

Built from what the runs left behind, nothing typed by hand: reports/results-<run>.json (Playwright JSON reporter),
the expectations of docs/test-cases.md (written before the runs), the defect table of docs/bugs.md and the media of
scripts/test_media.py. Run after test_media.py:

    python scripts/test_report_html.py          # HTML + PDF (PDF needs: cd e2e && npm ci && npx playwright install)
    python scripts/test_report_html.py --no-pdf
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_report import load_run  # noqa: E402 — sibling script, path set on the line above

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
HTML_OUT = REPORTS / "test-report.html"
PDF_OUT = REPORTS / "test-report.pdf"
TEST_CASES = ROOT / "docs" / "test-cases.md"
BUGS = ROOT / "docs" / "bugs.md"
TC = re.compile(r"TC-\d{3}-\d{2}")
LABEL = {"passed": "PASS", "failed": "FAIL", "timedOut": "FAIL", "interrupted": "FAIL", "skipped": "SKIP"}

CSS = """
:root { --fg:#1d2433; --muted:#5b6475; --line:#d9dee7; --pass:#17723a; --fail:#b42318; --bg:#ffffff; --soft:#f4f6fa; }
* { box-sizing: border-box; }
body { margin: 0 auto; max-width: 1100px; padding: 24px 16px; font: 14px/1.5 system-ui, "Segoe UI", sans-serif;
       color: var(--fg); background: var(--bg); }
h1 { font-size: 24px; margin: 0 0 4px; }
h2 { font-size: 18px; margin: 28px 0 8px; border-bottom: 2px solid var(--line); }
h3 { font-size: 15px; margin: 0 0 6px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 13px; }
th, td { border: 1px solid var(--line); padding: 4px 6px; text-align: left; vertical-align: top; }
th { background: var(--soft); }
code { background: var(--soft); padding: 0 3px; border-radius: 3px; font-size: 12px; }
.muted { color: var(--muted); }
.badge { display: inline-block; padding: 0 8px; border-radius: 10px; font-weight: 600; font-size: 12px; color: #fff; }
.PASS { background: var(--pass); } .FAIL { background: var(--fail); } .SKIP, .none { background: var(--muted); }
.kpis { display: flex; flex-wrap: wrap; gap: 12px; margin: 12px 0; }
.kpi { border: 1px solid var(--line); border-radius: 8px; padding: 8px 14px; min-width: 150px; }
.kpi b { display: block; font-size: 22px; }
.tc { border: 1px solid var(--line); border-radius: 8px; padding: 12px; margin: 14px 0; break-inside: avoid; }
.media { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 8px; margin-top: 8px; }
.media img, .media video { width: 100%; border: 1px solid var(--line); border-radius: 4px; }
.media figcaption { font-size: 12px; color: var(--muted); }
.screen-only { display: block; }
@media print {
  body { max-width: none; padding: 0; font-size: 11px; }
  .screen-only { display: none !important; }
  .tc { page-break-inside: avoid; }
  a { color: inherit; }
}
@page { size: A4; margin: 12mm; }
"""


def inline_md(text: str) -> str:
    """The little markdown used inside test-case cells: `code`, **bold**, [text](link)."""
    out = html.escape(text.replace("\\|", "|"), quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)


def md_cells(line: str) -> list[str]:
    """Cells of one markdown table row; an escaped \\| stays inside its cell."""
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def md_table(lines: list[str]) -> str:
    """Markdown table lines (header, separator, rows) → HTML table."""
    head, *rows = [md_cells(ln) for ln in lines if not re.fullmatch(r"\|[\s|:-]+\|", ln.strip())]
    th = "".join(f"<th>{inline_md(c)}</th>" for c in head)
    body = "".join("<tr>" + "".join(f"<td>{inline_md(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def table_after(text: str, heading: str) -> list[str]:
    """The first markdown table below ``heading`` (or below the first line starting with it)."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.startswith(heading)), None)
    if start is None:
        return []
    # the heading may be the table's own header row ("| Mã | Loại |…") — keep it
    rows: list[str] = [lines[start]] if lines[start].startswith("|") else []
    for ln in lines[start + 1 :]:
        if ln.startswith("|"):
            rows.append(ln)
        elif rows:
            break
    return rows


def expectations() -> dict[str, dict[str, str]]:
    """TC id → AC, steps, PASS-when, FAIL-when from docs/test-cases.md."""
    out = {}
    for line in TEST_CASES.read_text(encoding="utf-8").splitlines():
        if line.startswith("| TC-"):
            c = md_cells(line)
            if len(c) >= 6:
                out[c[0]] = {"ac": c[1], "kind": c[2], "steps": c[3], "pass": c[4], "fail": c[5]}
    return out


def media(run: str, tc: str) -> dict[str, list[str]]:
    """Paths (relative to reports/) of the screenshots, GIF and video of one TC in one run."""

    def find(folder: str, pattern: str) -> list[str]:
        return [p.relative_to(REPORTS).as_posix() for p in sorted((REPORTS / folder / run).glob(pattern))]

    return {
        "shots": find("screenshots", f"{tc}*.png"),
        "gif": find("gifs", f"*{tc}*"),
        "video": find("videos", f"*{tc}*"),
    }


def badge(status: str | None) -> str:
    label = LABEL.get(status or "", "—")
    return f'<span class="badge {label if status else "none"}">{label}</span>'


def summary(runs: dict[str, dict], tcs: list[str], exp: dict) -> str:
    names = sorted(runs)
    head = "<tr><th>TC</th><th>AC</th>" + "".join(f"<th>{n}</th>" for n in names) + "<th>Thời gian (s)</th></tr>"
    rows = []
    for tc in tcs:
        cells = "".join(f"<td>{badge(runs[n].get(tc, {}).get('status'))}</td>" for n in names)
        secs = " / ".join(f"{runs[n][tc]['seconds']:.1f}" for n in names if tc in runs[n])
        ac = inline_md(exp.get(tc, {}).get("ac", ""))
        rows.append(f'<tr><td><a href="#{tc}">{tc}</a></td><td>{ac}</td>{cells}<td>{secs}</td></tr>')
    return f"<table><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>"


def media_html(m: dict[str, list[str]]) -> str:
    figs = [
        f'<figure><img src="{s}" alt="{Path(s).stem}"><figcaption>Ảnh: {Path(s).name}</figcaption></figure>'
        for s in m["shots"]
    ]
    figs += [
        f'<figure class="screen-only"><img src="{g}" alt="GIF"><figcaption>GIF diễn biến</figcaption></figure>'
        for g in m["gif"]
    ]
    poster = f' poster="{m["shots"][-1]}"' if m["shots"] else ""
    figs += [
        f'<figure class="screen-only"><video controls preload="none" src="{v}"{poster}></video>'
        f"<figcaption>Video đủ thời lượng</figcaption></figure>"
        for v in m["video"]
    ]
    links = " · ".join(f'<a href="{p}">{Path(p).name}</a>' for p in m["gif"] + m["video"])
    return f'<div class="media">{"".join(figs)}</div><p class="muted">Tệp: {links or "—"}</p>'


def tc_section(tc: str, runs: dict[str, dict], exp: dict, last: str) -> str:
    e = exp.get(tc, {})
    r = runs[last].get(tc, {})
    notes = "".join(f"<li>{html.escape(n)}</li>" for n in r.get("notes", []))
    statuses = " ".join(f"{n}: {badge(runs[n].get(tc, {}).get('status'))}" for n in sorted(runs))
    return f"""<section class="tc" id="{tc}">
<h3>{tc} · {inline_md(e.get('ac', ''))} [{inline_md(e.get('kind', ''))}] {statuses}</h3>
<table><tr><th style="width:14%">Bước</th><td>{inline_md(e.get('steps', '—'))}</td></tr>
<tr><th>PASS khi</th><td>{inline_md(e.get('pass', '—'))}</td></tr>
<tr><th>FAIL khi</th><td>{inline_md(e.get('fail', '—'))}</td></tr></table>
{f'<ul class="muted">{notes}</ul>' if notes else ''}
{media_html(media(last, tc))}
</section>"""


def commit() -> str:
    git = shutil.which("git") or "git"
    out = subprocess.run(  # noqa: S603 — fixed argv, no shell
        [git, "log", "-1", "--format=%h"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return out.stdout.strip() or "?"


def page(runs: dict[str, dict]) -> str:
    exp = expectations()
    names, last = sorted(runs), max(runs)
    tcs = sorted({tc for r in runs.values() for tc in r})
    passed = {n: sum(1 for v in runs[n].values() if v["status"] == "passed") for n in names}
    kpis = "".join(f'<div class="kpi">{n}<b>{passed[n]}/{len(runs[n])} PASS</b></div>' for n in names)
    bugs = BUGS.read_text(encoding="utf-8")
    matrix = table_after(TEST_CASES.read_text(encoding="utf-8"), "## Ma trận AC")
    manual = sorted(set(exp) - set(tcs))
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Báo cáo kiểm thử</title>
<style>{CSS}</style></head><body>
<h1>Báo cáo kiểm thử — US-201, US-303</h1>
<p class="muted">Sinh lúc {datetime.now():%Y-%m-%d %H:%M} từ <code>reports/results-*.json</code> · mã nguồn
<code>{commit()}</code> · Playwright, Chromium, retries 0 · app test cục bộ (<code>backend/tests/e2e_server.py</code>
+ Vite). Kỳ vọng lấy nguyên văn từ <code>docs/test-cases.md</code> (ghi trước khi chạy).</p>
<div class="kpis">{kpis}<div class="kpi">Test case tự động<b>{len(tcs)}</b></div>
<div class="kpi">Lỗi sản phẩm (BUG)<b>{sum(1 for ln in table_after(bugs, '| Mã') if '| BUG |' in ln)}</b></div></div>
<p class="screen-only muted">Bản in: <a href="test-report.pdf">test-report.pdf</a> · bảng markdown:
<a href="test-report.md">test-report.md</a> · thư viện GIF: <a href="test-media.md">test-media.md</a></p>
<h2>Tổng hợp</h2>{summary(runs, tcs, exp)}
<p class="muted">Chưa chạy tự động (thủ công): {", ".join(manual) or "—"}.</p>
<h2>Phiếu lỗi (docs/bugs.md)</h2>{md_table(table_after(bugs, "| Mã")) if table_after(bugs, "| Mã") else "—"}
<h2>Ma trận AC ↔ TC</h2>{md_table(matrix) if matrix else "—"}
<h2>Chi tiết từng test case — bằng chứng lượt {last}</h2>
{"".join(tc_section(tc, runs, exp, last) for tc in tcs)}
</body></html>"""


def print_pdf() -> int:
    node = shutil.which("node")
    if node is None:
        print("node not found — PDF skipped", file=sys.stderr)
        return 1
    return subprocess.run(  # noqa: S603 — fixed argv, no shell
        [node, "report-pdf.mjs", str(HTML_OUT), str(PDF_OUT)], cwd=ROOT / "e2e", check=False
    ).returncode


def main(argv: list[str]) -> int:
    runs = {p.stem.removeprefix("results-"): load_run(p) for p in sorted(REPORTS.glob("results-run*.json"))}
    if not runs:
        print("no reports/results-run*.json — run the suite first (see docs/test-plan.md §4)", file=sys.stderr)
        return 1
    HTML_OUT.write_text(page(runs), encoding="utf-8")
    print(f"{HTML_OUT.relative_to(ROOT)}: {len(runs)} runs")
    if "--no-pdf" in argv:
        return 0
    code = print_pdf()
    if code == 0:
        print(f"{PDF_OUT.relative_to(ROOT)}: {PDF_OUT.stat().st_size // 1024} KB")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
