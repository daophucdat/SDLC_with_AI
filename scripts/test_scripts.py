"""python -m pytest scripts"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from check_traceability import check_message, matrix_problems, message_file  # noqa: E402


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


def test_commit_msg_hook_ignores_git_comment_lines(tmp_path):
    good = tmp_path / "good"
    good.write_text("feat(e2e): test cases [US-201]\n# Please enter the commit message\n", encoding="utf-8")
    bad = tmp_path / "bad"
    bad.write_text("feat(e2e): test cases\n# US-201 only in a comment does not count\n", encoding="utf-8")
    assert message_file(str(good)) == 0
    assert message_file(str(bad)) == 1


def test_report_table_has_one_row_per_test_case_and_marks_failures():
    import test_report

    runs = {
        "run1": {"TC-201-01": {"status": "passed", "seconds": 1.0, "notes": []}},
        "run2": {"TC-201-01": {"status": "failed", "seconds": 2.0, "notes": ["max uploads in flight: 4"]}},
    }
    table = test_report.table(runs)
    assert "| TC-201-01 | PASS | **FAIL** | 1.0 / 2.0 | max uploads in flight: 4 |" in table
    assert "run1: 1/1 PASS · run2: 0/1 PASS" in table


GOOD_SKILL = """---
name: plan-tests
description: >-
  Rút test case từ AC. Dùng khi lập test case,
  test plan, hỏi AC này test thế nào.
allowed-tools: Read Grep
---

Đọc [heuristics.md](heuristics.md).

## KHÔNG ĐƯỢC
- Không sửa AC.
"""
CATALOG = "| `plan-tests` | tự động | daophucdat | 1.0.0 | 2026-11-26 |"


def test_skill_frontmatter_folds_the_description():
    from check_skills import frontmatter

    fm = frontmatter(GOOD_SKILL)
    assert fm["name"] == "plan-tests"
    assert fm["description"] == "Rút test case từ AC. Dùng khi lập test case, test plan, hỏi AC này test thế nào."
    assert fm["allowed-tools"] == "Read Grep"


def test_a_well_formed_skill_passes():
    from check_skills import skill_problems

    assert skill_problems("plan-tests", GOOD_SKILL, lambda link: True, CATALOG) == []


def test_skill_problems_name_each_missing_part():
    from check_skills import skill_problems

    bare = "---\nname: other\n---\nSee [x](missing.md).\n"
    problems = "\n".join(skill_problems("plan-tests", bare, lambda link: False, ""))
    for expected in ("≠ folder name", "no description", "KHÔNG ĐƯỢC", "missing.md", "not listed"):
        assert expected in problems
    no_version = skill_problems("plan-tests", GOOD_SKILL, lambda link: True, "| `plan-tests` | x | y |")
    assert any("version" in p for p in no_version)
    long = GOOD_SKILL.replace("Rút test case từ AC.", "x" * 1600)
    assert any("1536" in p for p in skill_problems("plan-tests", long, lambda link: True, CATALOG))
