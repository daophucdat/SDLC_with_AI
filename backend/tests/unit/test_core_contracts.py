"""Assertions the mutation run (Day 5, ADR-19) showed were missing: coverage executed these lines, but no test would
have failed if they changed. Each test pins a contract from the docs, not the current implementation."""

from __future__ import annotations

import dataclasses
import os
import re

import pytest

from chatdocs.domain.errors import QuestionInvalid
from chatdocs.domain.ids import uuid7
from chatdocs.domain.qa import citation_policy
from chatdocs.domain.qa.citation_policy import Citation, CitationResult
from chatdocs.domain.qa.question import AnswerStatus, Language, NotFoundReason, Question, Turn
from chatdocs.domain.retrieval.rrf import Candidate, is_empty, rrf_fuse, select_top

MIGRATION = os.path.join(os.path.dirname(__file__), "..", "..", "migrations", "versions", "0001_init.py")


def _check_values(member: str) -> set[str]:
    """Values of the `CHECK (… IN (...))` list in migration 0001 that contains `member`."""
    with open(MIGRATION, encoding="utf-8") as f:
        sql = f.read()
    for m in re.finditer(r"CHECK \(\w+ IN \(([^)]*)\)\)", sql):
        values = {v.strip().strip("'") for v in m.group(1).split(",")}
        if member in values:
            return values
    raise AssertionError(f"no CHECK list contains {member}")


# ---------------------------------------------------------------- wire / storage values (dev_tasks.md §0.3, §0.5)
def test_answer_status_values_match_the_database_check():
    assert {s.value for s in AnswerStatus} == _check_values("STREAMING")


def test_language_values_match_the_database_check():
    assert {lang.value for lang in Language} == {"vi", "en"} == _check_values("vi")


def test_not_found_reasons_are_the_sse_contract():
    assert {r.value for r in NotFoundReason} == {"NO_CHUNKS", "MODEL_NOT_FOUND", "INVALID_CITATIONS"}


def test_question_invalid_says_why():
    with pytest.raises(QuestionInvalid) as empty:
        Question.create(uuid7(), "  ", follow_up=False, now=None)
    assert empty.value.details == {"reason": "empty"}
    with pytest.raises(QuestionInvalid) as long:
        Question.create(uuid7(), "x" * 2001, follow_up=False, now=None)
    assert long.value.details == {"reason": "too_long", "maxLength": 2000}


# ---------------------------------------------------------------- value objects are immutable, defaults are safe
@pytest.mark.parametrize(
    "obj",
    [
        Citation(1, None, uuid7(), "a.pdf", 1, "x"),
        CitationResult(),
        Candidate(uuid7(), uuid7(), 1, "x"),
        Turn(uuid7(), "q", uuid7(), "a", AnswerStatus.COMPLETED, []),
    ],
)
def test_value_objects_are_frozen(obj):
    field = dataclasses.fields(obj)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(obj, field, None)


def test_question_is_frozen():
    q = Question.create(uuid7(), "Giá?", follow_up=False, now=None)
    with pytest.raises(dataclasses.FrozenInstanceError):
        q.text = "khác"  # type: ignore[misc]


def test_defaults():
    assert Citation(1, None, uuid7(), "a.pdf", 1, "x").removed is False  # EC-15: a new citation is not crossed out
    r = CitationResult()
    assert (r.text, r.citations, r.not_found) == ("", [], None)
    c = Candidate(uuid7(), uuid7(), 1, "x")
    assert (c.char_start, c.char_end, c.cosine, c.fts_rank, c.score) == (0, 0, None, None, 0.0)
    assert Turn(uuid7(), "q", uuid7(), "a", AnswerStatus.COMPLETED, []).feedback is None


def test_unknown_document_name_is_empty_not_invented():
    """AC-303.4: the source shown comes from the index; nothing is made up when a name is missing."""
    chunk = Candidate(uuid7(), uuid7(), 4, "Bảo hành 24 tháng.")
    result = citation_policy.validate("Bảo hành 24 tháng [1].", [chunk], file_names={})
    assert result.citations[0].file_name == ""


# ---------------------------------------------------------------- ALG-2 exact numbers (SAD §3.2.1, RRF_K = 60)
def cand(cos=None, doc=None, cid=None):
    return Candidate(cid or uuid7(), doc or uuid7(), 1, "x", cosine=cos)


def test_rrf_score_is_one_over_k_plus_rank_starting_at_one():
    a, b = cand(0.9), cand(0.8)
    fused = rrf_fuse([a, b], [], k=60)
    assert [c.score for c in fused] == [pytest.approx(1 / 61), pytest.approx(1 / 62)]
    assert rrf_fuse([a], [])[0].score == pytest.approx(1 / 61)  # default k = 60


def test_rrf_sums_both_rankings():
    shared, only_fts = cand(0.5), cand(None)
    fused = rrf_fuse([shared], [only_fts, shared], k=60)
    assert fused[0].chunk_id == shared.chunk_id
    assert fused[0].score == pytest.approx(1 / 61 + 1 / 62)
    assert fused[1].score == pytest.approx(1 / 61)


def test_equal_scores_are_ordered_by_cosine_then_missing_cosine_counts_as_zero():
    high, none = cand(0.5), cand(None)
    # same rank in different lists → same RRF score; the tie is broken by cosine (descending), None = 0
    fused = rrf_fuse([high], [none], k=60)
    assert [c.chunk_id for c in fused] == [high.chunk_id, none.chunk_id]
    fused = rrf_fuse([none], [high], k=60)
    assert [c.chunk_id for c in fused] == [high.chunk_id, none.chunk_id]


def test_select_top_returns_exactly_top_n():
    fused = rrf_fuse([cand(0.9 - i / 10) for i in range(5)], [])
    assert len(select_top(fused, top_n=2, max_per_document=3)) == 2


def test_tau_boundary_is_inclusive_for_relevance():
    """ALG-2: NO_CHUNKS only when the best cosine is *below* τ (and full text found nothing)."""
    assert is_empty(0.35, 0, 0.35) is False
    assert is_empty(0.3499, 0, 0.35) is True
    assert is_empty(None, 0, 0.35) is True
    assert is_empty(0.1, 1, 0.35) is False
