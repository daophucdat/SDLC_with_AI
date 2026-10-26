"""python -m pytest scripts"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from check_traceability import check_message, matrix_problems  # noqa: E402


def test_good_messages():
    assert check_message("feat(qa): stream answers over SSE [US-301, US-306]") == []
    assert check_message("fix: purge every object version\n\nSEC-06, US-204") == []
    assert check_message("ci(gates): coverage gate EN-01") == []
    assert check_message("Merge pull request #3 from x/y") == []


def test_missing_type_or_code():
    assert any("Conventional" in p for p in check_message("added upload [US-201]"))
    assert any("requirement code" in p for p in check_message("feat: add upload"))
    assert any("requirement code" in p for p in check_message("feat: add upload US-2"))  # code needs 3 digits


def test_matrix_needs_every_story_and_real_files():
    stories = "### US-101 · Đăng nhập\n### US-102 · Từ chối\n"
    mx = "| US-101 | `backend/a.py` | `backend/tests/t.py::test_x` |"
    problems = matrix_problems(stories, mx, exists=lambda p: p.endswith("a.py"))
    assert "US-102 is not in docs/traceability.md" in problems
    assert any("backend/tests/t.py" in p for p in problems)
    assert not any("backend/a.py" in p for p in problems)


def test_matrix_checks_named_tests_exist():
    mx = "| US-101 | `backend/t.py::test_real` | `backend/t.py::test_gone` |"
    problems = matrix_problems("### US-101", mx, exists=lambda p: True, read=lambda p: "async def test_real():")
    assert problems == ["docs/traceability.md points at a missing test: backend/t.py::test_gone"]


def test_mutation_score_counts_killed_and_survived():
    from mutation_score import score

    xml = (
        "<testsuites><testsuite>"
        "<testcase name='m1'/><testcase name='m2'/><testcase name='m3'><failure/></testcase>"
        "<testcase name='m4'><skipped/></testcase>"
        "</testsuite></testsuites>"
    )
    k, s, pct = score(xml)
    assert (k, s) == (2, 1) and abs(pct - 200 / 3) < 1e-9
