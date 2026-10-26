"""Mutation score gate (Day 5: ≥ 60 % on core modules). Reads `mutmut junitxml` output.

    cd backend && mutmut run && mutmut junitxml > mutmut.xml && python ../scripts/mutation_score.py mutmut.xml 60

Score = killed / (killed + survived). Mutants that timed out count as killed (the tests noticed); skipped ones are
ignored. Each surviving mutant is a missing assertion: write the test that kills it, or record why it is equivalent."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET  # noqa: S405 — parses our own CI artifact


def score(xml_text: str) -> tuple[int, int, float]:
    root = ET.fromstring(xml_text)  # noqa: S314 — trusted input (generated in the same job)
    killed = survived = 0
    for case in root.iter("testcase"):
        if case.find("skipped") is not None:
            continue
        if case.find("failure") is not None:
            survived += 1
        else:
            killed += 1
    total = killed + survived
    return killed, survived, (100.0 * killed / total if total else 100.0)


if __name__ == "__main__":
    path, threshold = sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    with open(path, encoding="utf-8") as f:
        k, s, pct = score(f.read())
    print(f"mutation score: {pct:.1f}% ({k} killed, {s} survived) — threshold {threshold:.0f}%")
    sys.exit(0 if pct >= threshold else 1)
