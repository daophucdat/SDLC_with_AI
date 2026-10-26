"""Day 7 gate: skills are products — every skill is well-formed, bounded and owned; CLAUDE.md stays small.

    python scripts/check_skills.py

Checks for each .claude/skills/<name>/SKILL.md: frontmatter `name` = folder name, a description (with
when_to_use ≤ 1 536 characters — the part Claude sees every turn), SKILL.md < 500 lines, a `## KHÔNG ĐƯỢC`
section or `disallowed-tools`, every linked supporting file exists, and a row in docs/skills.md with owner,
version and review date. Also: CLAUDE.md plus the files it imports with @path < 200 lines.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
CATALOG = ROOT / "docs" / "skills.md"
MAX_ROUTER_CHARS = 1536
MAX_SKILL_LINES = 500
MAX_MEMORY_LINES = 200
LINK = re.compile(r"\]\(([^)#\s]+)\)")
VERSION = re.compile(r"\b\d+\.\d+\.\d+\b")
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def frontmatter(text: str) -> dict[str, str]:
    """`key: value` and folded `key: >-` blocks — enough for SKILL.md, no PyYAML needed in CI."""
    if not text.startswith("---\n"):
        return {}
    block = text[4:].split("\n---", 1)[0]
    out: dict[str, str] = {}
    key = None
    for line in block.splitlines():
        m = re.match(r"^([a-z][\w-]*):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            out[key] = "" if value in (">-", ">", "|", "|-") else value.strip("'\"")
        elif key and line.startswith(" "):
            out[key] = (out[key] + " " + line.strip()).strip()
    return out


def skill_problems(name: str, text: str, exists, catalog: str) -> list[str]:
    fm = frontmatter(text)
    problems = []
    if fm.get("name") != name:
        problems.append(f"{name}: frontmatter name {fm.get('name')!r} ≠ folder name")
    if not fm.get("description"):
        problems.append(f"{name}: no description — Claude cannot route to it")
    router = len(fm.get("description", "")) + len(fm.get("when_to_use", ""))
    if router > MAX_ROUTER_CHARS:
        problems.append(f"{name}: description + when_to_use is {router} chars (> {MAX_ROUTER_CHARS}, gets cut)")
    if text.count("\n") + 1 >= MAX_SKILL_LINES:
        problems.append(f"{name}: SKILL.md ≥ {MAX_SKILL_LINES} lines — move detail to supporting files")
    if "## KHÔNG ĐƯỢC" not in text and "disallowed-tools" not in fm:
        problems.append(f"{name}: no '## KHÔNG ĐƯỢC' section and no disallowed-tools")
    for link in LINK.findall(text):
        if not link.startswith("http") and not exists(link):
            problems.append(f"{name}: linked file {link} does not exist")
    row = next((ln for ln in catalog.splitlines() if ln.startswith(f"| `{name}`")), None)
    if row is None:
        problems.append(f"{name}: not listed in docs/skills.md")
    elif not (VERSION.search(row) and DATE.search(row)):
        problems.append(f"{name}: docs/skills.md row needs a version (x.y.z) and a review date (YYYY-MM-DD)")
    return problems


def memory_lines(path: Path) -> int:
    """Lines Claude loads for CLAUDE.md: the file plus every @path import (one level, as used here)."""
    text = path.read_text(encoding="utf-8")
    total = text.count("\n") + 1
    for imp in re.findall(r"^@(\S+)$", text, re.MULTILINE):
        target = path.parent / imp
        if target.exists():
            total += target.read_text(encoding="utf-8").count("\n") + 1
    return total


def main() -> int:
    catalog = CATALOG.read_text(encoding="utf-8") if CATALOG.exists() else ""
    problems = []
    names = sorted(p.parent.name for p in SKILLS.glob("*/SKILL.md"))
    for name in names:
        folder = SKILLS / name
        text = (folder / "SKILL.md").read_text(encoding="utf-8")
        problems += skill_problems(name, text, lambda link, f=folder: (f / link).exists(), catalog)
    lines = memory_lines(ROOT / "CLAUDE.md")
    if lines >= MAX_MEMORY_LINES:
        problems.append(f"CLAUDE.md + imports is {lines} lines (≥ {MAX_MEMORY_LINES}) — move processes to skills")
    for p in problems:
        print(p)
    print(f"skills: {'FAIL' if problems else 'OK'} ({len(names)} skills, CLAUDE.md + imports {lines} lines)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
