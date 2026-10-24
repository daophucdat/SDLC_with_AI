"""US-402 .xlsx in / out (openpyxl). Formulas are never evaluated; only cell values of the first sheet are read."""

from __future__ import annotations

import io
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from chatdocs.domain.errors import TestsetInvalid
from chatdocs.domain.evaluation.test_set import COLUMNS, HEADER_LABELS, MAX_CASES, RESULT_HEADER
from chatdocs.ports.insights import EvaluationResult

HEADER_FILL = "1F5FBF"  # tokens.css --color-primary (spreadsheet styles cannot read CSS variables)


def read_rows(path: str) -> list[list[Any]]:
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception:  # noqa: BLE001 — not an .xlsx / damaged file
        raise TestsetInvalid(row=1, column="file") from None
    try:
        ws = wb.worksheets[0]
        rows = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i > MAX_CASES + 50:  # stop reading absurdly long sheets; parse_rows reports too_many
                break
            rows.append(list(row[:4]))
        return rows
    finally:
        wb.close()


def template() -> bytes:
    """Empty template users can download and fill in."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Bo cau hoi"
    ws.append([HEADER_LABELS[c] for c in COLUMNS])
    ws.append([1, "Điều khoản thanh toán của hợp đồng ABC là gì?", "Thanh toán 30% khi ký, 70% khi nghiệm thu", ""])
    ws.append([2, "Giá trị hợp đồng với công ty XYZ năm 2019?", "", "x"])
    _style_header(ws, len(COLUMNS))
    return _bytes(wb)


def build_results(results: list[EvaluationResult]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Ket qua"
    ws.append(list(RESULT_HEADER))
    for r in results:
        cites = "\n".join(f"[{c.get('index')}] {c.get('file')} — trang {c.get('page')}" for c in r.citations)
        ws.append(
            [
                r.case.ordinal,
                r.case.question,
                r.case.expected_answer or ("(không có đáp án)" if r.case.expects_not_found else ""),
                r.answer_text,
                r.status,
                cites,
                r.latency_ms,
                "",
                "",
            ]
        )
    _style_header(ws, len(RESULT_HEADER))
    for col, width in zip("ABCDEFGHI", (6, 45, 40, 60, 22, 40, 12, 16, 30), strict=True):
        ws.column_dimensions[col].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    return _bytes(wb)


def _style_header(ws, n: int) -> None:
    for cell in ws[1][:n]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=HEADER_FILL)


def _bytes(wb: Workbook) -> bytes:
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
