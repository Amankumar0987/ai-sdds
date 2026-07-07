"""
pdf_engine.py
=============
Extracts text from PDFs entirely in memory. Handles two cases:
  1. Text-based PDF  -> pdfplumber pulls text directly (fast, accurate).
  2. Scanned PDF      -> falls back to rendering each page as an image
                         and running it through ocr_engine.

Page count is capped (security.MAX_PDF_PAGES) so a 10,000-page hostile
PDF cannot be used to exhaust CPU/memory (a denial-of-service vector).
"""

from __future__ import annotations
import io
import pdfplumber

from . import security
from . import ocr_engine


def extract_text(pdf_bytes: bytes) -> str:
    chunks: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = pdf.pages[: security.MAX_PDF_PAGES]
        for page in pages:
            text = page.extract_text() or ""
            if text.strip():
                chunks.append(text)
            else:
                # Likely a scanned page with no embedded text layer.
                pil_image = page.to_image(resolution=200).original
                chunks.append(ocr_engine.extract_text(pil_image))
    return "\n".join(chunks)
