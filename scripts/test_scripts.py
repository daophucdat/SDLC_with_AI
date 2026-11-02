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


def test_gif_pacing_drops_close_frames_and_shortens_idle_waits():
    from test_media import LAST_HOLD_MS, MAX_HOLD_MS, pace

    # 0 → 50 ms is closer than 8 fps (dropped); 200 → 10 200 ms is an idle wait (capped); the last frame is held
    assert pace([0, 50, 200, 10_200]) == [(0, 200), (2, MAX_HOLD_MS), (3, LAST_HOLD_MS)]
    assert pace([]) == []


def test_media_gallery_names_a_shared_test_after_every_test_case(tmp_path, monkeypatch):
    import test_media

    monkeypatch.setattr(test_media, "REPORTS", tmp_path)
    t = {"title": "TC-303-01 + TC-303-10 hỏi", "ids": ["TC-303-01", "TC-303-10"], "status": "failed"}
    t["gif"] = tmp_path / "gifs" / "run2" / "TC-303-01+TC-303-10.gif"
    t["video"] = None
    md = test_media.gallery("run2", [t])
    assert "## TC-303-01 + TC-303-10 hỏi — FAIL" in md
    assert "![TC-303-01+TC-303-10](gifs/run2/TC-303-01+TC-303-10.gif)" in md
    assert "không có video" in md


def test_mcp_server_lists_and_calls_tools():
    import mcp_server

    init = mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "x"}})
    assert init["result"]["protocolVersion"] == "x" and "tools" in init["result"]["capabilities"]
    assert mcp_server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    names = {
        t["name"] for t in mcp_server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
    }
    assert names == {"story", "test_cases", "test_results", "defect", "find_code"}
    call = {"name": "test_cases", "arguments": {"query": "US-201"}}
    text = mcp_server.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": call})["result"]
    assert not text["isError"] and "| TC-201-01 |" in text["content"][0]["text"]


def test_mcp_server_reports_errors_without_dying():
    import mcp_server

    bad = mcp_server.call_tool({"name": "story", "arguments": {"wrong": "US-201"}})
    assert bad["isError"] and "TypeError" in bad["content"][0]["text"]
    assert mcp_server.call_tool({"name": "nope"})["isError"]
    assert mcp_server.handle({"jsonrpc": "2.0", "id": 9, "method": "nope"})["error"]["code"] == -32601


def test_html_report_renders_markdown_tables_and_keeps_a_header_row_heading():
    from test_report_html import inline_md, md_cells, md_table, table_after

    text = "intro\n| Mã | TC |\n|---|---|\n| HD-1 | TC-201-05 |\n\nafter\n"
    text += "## Ma trận\n\n| AC | TC |\n|---|---|\n| A | B |\n"
    assert table_after(text, "| Mã") == ["| Mã | TC |", "|---|---|", "| HD-1 | TC-201-05 |"]
    assert table_after(text, "## Ma trận") == ["| AC | TC |", "|---|---|", "| A | B |"]
    assert "<th>Mã</th>" in md_table(table_after(text, "| Mã")) and "<td>HD-1</td>" in md_table(
        table_after(text, "| Mã")
    )
    assert md_cells(r"| a \| b | c |") == [r"a \| b", "c"]
    assert inline_md("**3** `POST` <x> [d](docs/bugs.md)") == (
        '<b>3</b> <code>POST</code> &lt;x&gt; <a href="docs/bugs.md">d</a>'
    )


def test_an_agent_needs_name_description_tools_rules_and_a_catalog_row():
    from check_skills import agent_problems

    good = "---\nname: code-reviewer\ndescription: Review L1.\ntools: Read, Grep\n---\n\n## KHÔNG ĐƯỢC\n- Không sửa.\n"
    assert agent_problems("code-reviewer", good, "| `code-reviewer` | x |") == []
    bare = "---\nname: other\n---\n"
    problems = "\n".join(agent_problems("code-reviewer", bare, ""))
    for expected in ("≠ file name", "no description", "no tools", "KHÔNG ĐƯỢC", "not listed"):
        assert expected in problems
