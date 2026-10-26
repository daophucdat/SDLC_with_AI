"""US-402: test-set template validation. Rows come from the .xlsx adapter as plain lists of cell values."""

from __future__ import annotations

from dataclasses import dataclass

from chatdocs.domain.errors import TestsetInvalid

MAX_CASES = 200
COLUMNS = ("stt", "cau_hoi", "dap_an_mong_doi", "khong_co_dap_an")  # template header row (row 1)
HEADER_LABELS = {
    "stt": "STT",
    "cau_hoi": "Câu hỏi",
    "dap_an_mong_doi": "Đáp án mong đợi",
    "khong_co_dap_an": "Không có đáp án (x)",
}
RESULT_HEADER = (
    "STT",
    "Câu hỏi",
    "Đáp án mong đợi",
    "Câu trả lời",
    "Trạng thái",
    "Trích dẫn",
    "Độ trễ (ms)",
    "Chấm: Đúng / Sai",
    "Ghi chú người chấm",
)


@dataclass(frozen=True)
class TestCase:
    __test__ = False  # not a pytest test class

    ordinal: int
    question: str
    expected_answer: str | None
    expects_not_found: bool


def _norm(v) -> str:
    return "" if v is None else str(v).strip()


YES = frozenset({"x", "có", "co", "yes", "1"})


def _check_header(row: list) -> None:
    header = [_norm(c).lower() for c in row]
    for i, key in enumerate(COLUMNS[:2]):  # STT and Câu hỏi are mandatory columns
        if i >= len(header) or header[i] != HEADER_LABELS[key].lower():
            raise TestsetInvalid(row=1, column=HEADER_LABELS[key])


def _parse_case(r: int, cells: list[str], default_ordinal: int) -> TestCase:
    if not cells[1]:
        raise TestsetInvalid(row=r, column=HEADER_LABELS["cau_hoi"])
    if len(cells[1]) > 2000:
        raise TestsetInvalid(row=r, column=HEADER_LABELS["cau_hoi"], reason="too_long")
    try:
        ordinal = int(float(cells[0])) if cells[0] else default_ordinal
    except ValueError:
        raise TestsetInvalid(row=r, column=HEADER_LABELS["stt"]) from None
    return TestCase(ordinal, cells[1], cells[2] or None, cells[3].lower() in YES)


def parse_rows(rows: list[list]) -> list[TestCase]:
    """Row numbers in errors are spreadsheet rows (header = row 1), so the user can find the cell (AC-402.2)."""
    if not rows:
        raise TestsetInvalid(row=1, column=HEADER_LABELS["cau_hoi"])
    _check_header(rows[0])
    cases: list[TestCase] = []
    for r, row in enumerate(rows[1:], start=2):
        cells = [_norm(c) for c in row] + [""] * 4
        if not any(cells[:4]):
            continue  # blank line
        cases.append(_parse_case(r, cells, len(cases) + 1))
        if len(cases) > MAX_CASES:
            raise TestsetInvalid(row=r, column=HEADER_LABELS["stt"], reason="too_many", max=MAX_CASES)
    if not cases:
        raise TestsetInvalid(row=2, column=HEADER_LABELS["cau_hoi"])
    return cases
