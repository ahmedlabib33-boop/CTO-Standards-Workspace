from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Any

try:
    import fitz
except Exception:
    fitz = None

@dataclass
class PageText:
    page: int
    text: str
    blocks: list[dict[str, Any]]
    tables: list[list[list[str]]]

@dataclass
class ExtractedPDF:
    pages: list[PageText]
    chars: int
    mode: str
    needs_ocr: bool


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_pdf(data: bytes) -> ExtractedPDF:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed")
    doc = fitz.open(stream=data, filetype="pdf")
    pages: list[PageText] = []
    total = 0
    for i, page in enumerate(doc):
        text = page.get_text("text") or ""
        blocks = page.get_text("dict").get("blocks", [])
        tables = []
        try:
            finder = page.find_tables()
            for table in getattr(finder, "tables", []):
                rows = table.extract() or []
                cleaned = [[str(c or "").strip() for c in row] for row in rows if row]
                if cleaned: tables.append(cleaned)
        except Exception:
            pass
        total += len(text)
        pages.append(PageText(page=i+1, text=text, blocks=blocks, tables=tables))
    # If essentially no native text exists, optional OCR may be needed.
    needs_ocr = total < max(80, len(doc) * 20)
    return ExtractedPDF(pages=pages, chars=total, mode="native_text" if not needs_ocr else "image_or_vector_low_text", needs_ocr=needs_ocr)


def try_ocr_pdf(data: bytes, dpi: int = 220) -> ExtractedPDF | None:
    """Last-resort OCR. Only runs when pytesseract and the Tesseract binary are available."""
    if fitz is None:
        return None
    try:
        import io
        import pytesseract
        from PIL import Image
        _ = pytesseract.get_tesseract_version()
    except Exception:
        return None
    doc = fitz.open(stream=data, filetype="pdf")
    pages: list[PageText] = []
    total = 0
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72.0, dpi/72.0), alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img) or ""
        total += len(text)
        pages.append(PageText(page=i+1, text=text, blocks=[], tables=[]))
    return ExtractedPDF(pages=pages, chars=total, mode="ocr", needs_ocr=False)
