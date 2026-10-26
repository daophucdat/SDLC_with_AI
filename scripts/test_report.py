"""Day 6 test report: one row per test case (docs/test-cases.md) with its result in every run and its evidence.

Reads the Playwright JSON results ``reports/results-<run>.json`` and rewrites the table between the
``<!-- results:start -->`` / ``<!-- results:end -->`` markers of ``reports/test-report.md``; the rest of the report
(defects, notes) is written by hand.

    python scripts/test_report.py            # after: cd e2e && E2E_RUN=run1 npm run test:tc ; E2E_RUN=run2 ...
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
REPORT = REPORTS / "test-report.md"
START, END = "<!-- results:start -->", "<!-- results:end -->"
TC = re.compile(r"TC-\d{3}-\d{2}")
MEASURES = ("measured", "max uploads", "attempts", "stored citation")  # annotations shown in the report
ICON = {"passed": "PASS", "failed": "**FAIL**", "timedOut": "**FAIL**", "skipped": "skip", "interrupted": "**FAIL**"}


def load_run(path: Path) -> dict[str, dict]:
    """TC id → {status, seconds, notes} for one run. A test titled with two TC ids reports for both."""
    out: dict[str, dict] = {}

    def walk(suite: dict) -> None:
        for spec in suite.get("specs", []):
            for test in spec["tests"]:
                result = test["results"][-1] if test["results"] else {"status": "skipped", "duration": 0}
                notes = [f'{a["type"]}: {a.get("description", "")}' for a in test.get("annotations", [])]
                for tc in TC.findall(spec["title"]):
                    out[tc] = {"status": result["status"], "seconds": result["duration"] / 1000, "notes": notes}
        for child in suite.get("suites", []):
            walk(child)

    for suite in json.loads(path.read_text(encoding="utf-8"))["suites"]:
        walk(suite)
    return out


def evidence(run: str, tc: str) -> list[str]:
    shots = sorted((REPORTS / "screenshots" / run).glob(f"{tc}*.png"))
    return [f"[{p.stem}](screenshots/{run}/{p.name})" for p in shots]


def table(runs: dict[str, dict[str, dict]]) -> str:
    names = sorted(runs)
    tcs = sorted({tc for r in runs.values() for tc in r})
    head = "| TC | " + " | ".join(names) + " | Thời gian (s) | Đo được | Bằng chứng (" + names[-1] + ") |"
    rows = [head, "|" + "---|" * (len(names) + 4)]
    for tc in tcs:
        cells = [ICON.get(runs[n].get(tc, {}).get("status", "-"), "-") for n in names]
        last = runs[names[-1]].get(tc, {})
        secs = " / ".join(f'{runs[n][tc]["seconds"]:.1f}' for n in names if tc in runs[n])
        notes = "<br>".join(n.replace("|", "\\|") for n in last.get("notes", []) if any(k in n for k in MEASURES))
        rows.append(f"| {tc} | " + " | ".join(cells) + f" | {secs} | {notes} | {' '.join(evidence(names[-1], tc))} |")
    total = {n: sum(1 for v in runs[n].values() if v["status"] == "passed") for n in names}
    rows.append("")
    rows.append(
        "Tổng: " + " · ".join(f"{n}: {total[n]}/{len(runs[n])} PASS" for n in names) + f" — {len(tcs)} TC tự động."
    )
    return "\n".join(rows)


def main() -> int:
    runs = {p.stem.removeprefix("results-"): load_run(p) for p in sorted(REPORTS.glob("results-run*.json"))}
    if not runs:
        print("no reports/results-run*.json — run the suite first (see docs/test-plan.md §4)", file=sys.stderr)
        return 1
    text = REPORT.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print(f"{REPORT} has no {START} … {END} markers", file=sys.stderr)
        return 1
    before, rest = text.split(START, 1)
    after = rest.split(END, 1)[1]
    REPORT.write_text(f"{before}{START}\n{table(runs)}\n{END}{after}", encoding="utf-8")
    failed = [(n, tc) for n, r in runs.items() for tc, v in r.items() if v["status"] != "passed"]
    print(f"{REPORT.relative_to(ROOT)}: {len(runs)} runs, {len(failed)} non-passing results")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
