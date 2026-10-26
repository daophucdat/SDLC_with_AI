"""Run the local L0 gates on the staged tree and write reports/gate-<tree>.json.

    python .claude/skills/commit-gate/scripts/gate.py "feat(qa): summary [US-304]"

<tree> is `git write-tree` of the index — the exact tree the commit will have, so after committing
`git rev-parse HEAD^{tree}` names the gate file that proves it. Exit code 0 only when every gate passed.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
GATES = ["lint", "typecheck", "coverage", "traceability"]  # = scripts/dev.sh check


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def run_gate(name: str) -> dict:
    t0 = time.monotonic()
    proc = subprocess.run(
        ["bash", "scripts/dev.sh", name],
        check=False,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-15:]
    return {"gate": name, "ok": proc.returncode == 0, "seconds": round(time.monotonic() - t0, 1), "tail": tail}


def main() -> int:
    message = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.path.insert(0, str(ROOT / "scripts"))
    from check_traceability import check_message

    tree = git("write-tree")
    staged = git("diff", "--cached", "--name-only").splitlines()
    results = [run_gate(g) for g in GATES]
    msg_problems = check_message(message) if message else ["no commit message given"]
    results.append({"gate": "commit-message", "ok": not msg_problems, "seconds": 0, "tail": msg_problems})
    report = {
        "tree": tree,
        "head": git("rev-parse", "HEAD"),
        "message": message,
        "staged": staged,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ok": all(r["ok"] for r in results),
        "gates": results,
    }
    out = ROOT / "reports" / f"gate-{tree[:12]}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for r in results:
        print(f"{'OK  ' if r['ok'] else 'FAIL'} {r['gate']:<15} {r['seconds']:>6}s")
    print(f"{out.relative_to(ROOT)}: {'PASS' if report['ok'] else 'FAIL'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
