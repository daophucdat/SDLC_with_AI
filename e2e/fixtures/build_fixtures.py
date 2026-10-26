"""Test data of docs/test-plan.md §5, generated (never committed). Run with the backend venv (PyMuPDF):

    backend/.venv/Scripts/python e2e/fixtures/build_fixtures.py      # Windows
    backend/.venv/bin/python e2e/fixtures/build_fixtures.py          # Linux / macOS / CI

Deterministic content: every run produces the same text, so expected pages in docs/test-cases.md stay valid."""

from __future__ import annotations

import os
import random

import fitz

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LIMIT = 50 * 1024 * 1024  # MAX_UPLOAD_MB = 50 (US-201)
FONTS = [
    os.environ.get("EVAL_PDF_FONT", ""),
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
]
FONT = next((f for f in FONTS if f and os.path.exists(f)), None)

HOP_DONG = [
    "HỢP ĐỒNG CUNG CẤP PHẦN MỀM ABC. Điều 1. Phạm vi: triển khai phần mềm quản lý kho cho công ty ABC.",
    "Điều 5. Thanh toán: khách hàng thanh toán 30% giá trị hợp đồng khi ký và 70% khi nghiệm thu.",
    "Điều 7. Bảo hành: phần mềm được bảo hành 24 tháng kể từ ngày nghiệm thu.",
]
BAO_GIA = [
    "BÁO GIÁ XYZ quý 3. Đơn giá triển khai là 500 triệu đồng, thanh toán theo tiến độ dự án.",
    "Báo giá có hiệu lực 30 ngày. Thời gian triển khai dự kiến 10 tuần.",
]


def text_pdf(path: str, pages: list[str]) -> None:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        if FONT:
            page.insert_font(fontname="vn", fontfile=FONT)
        page.insert_textbox(fitz.Rect(56, 56, 540, 790), text, fontsize=12, fontname="vn" if FONT else "helv")
    doc.save(path)
    doc.close()


def big_pdf(path: str, target: int, seed: int) -> None:
    """A valid, readable PDF of ~target bytes: one text page + one incompressible noise image (≈ a scanned annex)."""
    rng = random.Random(seed)
    side = int(((target - 200_000) / 3) ** 0.5)
    doc = fitz.open()
    page = doc.new_page()
    if FONT:
        page.insert_font(fontname="vn", fontfile=FONT)
    page.insert_textbox(
        fitz.Rect(56, 56, 540, 300),
        f"Phụ lục kỹ thuật số {seed}. Hồ sơ dung lượng lớn dùng để kiểm thử giới hạn 50 MB.",
        fontsize=12,
        fontname="vn" if FONT else "helv",
    )
    samples = rng.randbytes(side * side * 3)
    pix = fitz.Pixmap(fitz.csRGB, side, side, samples, False)
    page.insert_image(fitz.Rect(56, 320, 540, 790), pixmap=pix)
    doc.save(path, deflate=False)
    doc.close()


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    p = lambda name: os.path.join(OUT, name)  # noqa: E731
    text_pdf(p("HopDong_ABC.pdf"), HOP_DONG)
    text_pdf(p("BaoGia_XYZ.pdf"), BAO_GIA)
    # Different topics from HopDong / BaoGia so they never compete in retrieval for the US-303 questions.
    text_pdf(p("Hợp đồng ABC – bản ký.pdf"), ["Biên bản ký kết giữa các bên vào ngày 05/09, có chữ ký và con dấu."])
    for i in range(1, 20):  # 01–10: TC-201-05, 11–19: TC-201-06 (distinct content → no duplicate prompt)
        text_pdf(p(f"TaiLieu_{i:02d}.pdf"), [f"Tài liệu số {i}. Ghi chú nội bộ số {i} về khách hàng số {i}."])
    for name, seed in (("Lon_49MB.pdf", 1), ("Lon_8MB_a.pdf", 2), ("Lon_8MB_b.pdf", 3)):
        want = int(49.5 * 1024 * 1024) if "49MB" in name else 8 * 1024 * 1024
        target = want
        for _ in range(4):  # image storage overhead is not exact: measure and correct
            if os.path.exists(p(name)) and abs(os.path.getsize(p(name)) - want) < want * 0.01:
                break
            big_pdf(p(name), target, seed)
            target = int(target * want / os.path.getsize(p(name)))
        assert 0 < os.path.getsize(p(name)) <= LIMIT, name
    with open(p("Qua_50MB.pdf"), "wb") as f:  # 50 MB + 1 KB: rejected on the client, never parsed
        f.write(b"%PDF-1.7\n")
        f.truncate(LIMIT + 1024)
    with open(p("Word_doi_duoi.pdf"), "wb") as f:  # a .doc (OLE header) renamed to .pdf
        f.write(bytes.fromhex("D0CF11E0A1B11AE1") + b"\x00" * 4096)
    open(p("Rong.pdf"), "wb").close()  # 0 bytes
    with open(p("anh.png"), "wb") as f:
        f.write(bytes.fromhex("89504E470D0A1A0A") + b"\x00" * 64)
    with open(p("Hong.pdf"), "wb") as f:  # PDF header, garbage body → processing ERROR / CORRUPT
        f.write(b"%PDF-1.7\n" + b"\x00garbage" * 512)
    for name in sorted(os.listdir(OUT)):
        print(f"{os.path.getsize(p(name)):>12,}  {name}")


if __name__ == "__main__":
    main()
