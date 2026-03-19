from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import fitz  # PyMuPDF


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str


def extract_text_from_pdf(file_bytes: bytes) -> list[ExtractedPage]:
    doc = fitz.open(stream=BytesIO(file_bytes), filetype="pdf")
    pages: list[ExtractedPage] = []
    for i in range(len(doc)):
        page = doc.load_page(i)
        text = page.get_text("text") or ""
        pages.append(ExtractedPage(page_number=i + 1, text=text))
    return pages

