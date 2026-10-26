"""Day 7 — measure whether a skill triggers: 5 prompts that should, 5 that should not (Capture → Author → **Test**).

    python scripts/skill_triggers.py plan-tests        # reads .claude/skills/plan-tests/evals/triggers.json

Each prompt runs once in a fresh headless session (`claude -p`, stream-json) from the repo root, read-only
(Write / Edit / Bash disallowed, 2 turns), and counts as triggered when the session calls the Skill tool with this
skill. Writes reports/skill-triggers-<skill>.json and prints the markdown table for docs/skills.md.
Costs real tokens (~0.3 USD per prompt with the default model) — run when a description changes, not in CI.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def skills_called(stream: str) -> list[str]:
    """Names passed to the Skill tool in a stream-json transcript."""
    called = []
    for line in stream.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "assistant":
            continue
        for block in event["message"].get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == "Skill":
                called.append(block["input"].get("skill", ""))
    return called


def cost(stream: str) -> float:
    for line in reversed(stream.splitlines()):
        if '"type":"result"' in line.replace(" ", ""):
            return float(json.loads(line).get("total_cost_usd") or 0)
    return 0.0


def run(prompt: str) -> dict:
    claude = shutil.which("claude") or "claude"
    cmd = [claude, "-p", prompt, "--output-format", "stream-json", "--verbose", "--max-turns", "2"]
    cmd += ["--disallowedTools", "Write Edit Bash NotebookEdit"]
    out = subprocess.run(
        cmd, check=False, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    ).stdout
    return {"prompt": prompt, "skills": skills_called(out), "cost_usd": round(cost(out), 4)}


def summarize(skill: str, rows: list[dict]) -> dict:
    tp = sum(1 for r in rows if r["expected"] and skill in r["skills"])
    fp = sum(1 for r in rows if not r["expected"] and skill in r["skills"])
    pos = sum(1 for r in rows if r["expected"])
    neg = len(rows) - pos
    return {"skill": skill, "recall": f"{tp}/{pos}", "false_triggers": f"{fp}/{neg}", "correct": tp + neg - fp}


def table(rows: list[dict], skill: str) -> str:
    lines = ["| # | Prompt | Nên gọi | Skill được gọi | Đúng? |", "|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        hit = skill in r["skills"]
        ok = "✅" if hit == r["expected"] else "❌"
        called = ", ".join(r["skills"]) or "—"
        lines.append(f"| {i} | {r['prompt']} | {'có' if r['expected'] else 'không'} | {called} | {ok} |")
    return "\n".join(lines)


def main() -> int:
    skill = sys.argv[1] if len(sys.argv) > 1 else "plan-tests"
    spec = json.loads((ROOT / ".claude" / "skills" / skill / "evals" / "triggers.json").read_text(encoding="utf-8"))
    cases = [(p, True) for p in spec["should_trigger"]] + [(p, False) for p in spec["should_not_trigger"]]
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda c: run(c[0]), cases))
    rows = [{**r, "expected": exp} for r, (_, exp) in zip(results, cases)]
    summary = summarize(skill, rows)
    out = ROOT / "reports" / f"skill-triggers-{skill}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(table(rows, skill))
    print(
        f"\n{skill}: recall {summary['recall']}, false triggers {summary['false_triggers']}, "
        f"cost {sum(r['cost_usd'] for r in rows):.2f} USD → {out.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
