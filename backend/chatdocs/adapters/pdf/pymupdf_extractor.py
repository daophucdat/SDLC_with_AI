"""PyMuPDF text extraction (EN-04). Runs only inside the worker, which has no outbound internet access."""

from __future__ import annotations

import fitz  # PyMuPDF

from chatdocs.ports.pdf import PdfCorrupt, PdfPasswordProtected


class PyMuPdfExtractor:
    def extract_pages(self, local_path: str) -> list[str]:
        try:
            doc = fitz.open(local_path, filetype="pdf")
        except Exception as e:  # PyMuPDF raises several exception types for unreadable files
            raise PdfCorrupt(str(e)) from e
        try:
            if doc.needs_pass:
                raise PdfPasswordProtected()
            pages = []
            for page in doc:
                try:
                    pages.append(page.get_text("text") or "")
                except Exception as e:
                    raise PdfCorrupt(f"page {page.number + 1}: {e}") from e
            if not pages:
                raise PdfCorrupt("no pages")
            return pages
        finally:
            doc.close()
