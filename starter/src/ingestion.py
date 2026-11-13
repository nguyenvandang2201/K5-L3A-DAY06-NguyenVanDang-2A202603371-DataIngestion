"""Read and normalize source data while preserving page traceability."""
from pathlib import Path
import re
import unicodedata
from pypdf import PdfReader
from .models import DocumentPage


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Extract physical PDF pages; mark image-only or empty pages explicitly."""
    pages = []
    for number, page in enumerate(PdfReader(path).pages, 1):
        text = normalize_text(page.extract_text() or "")
        pages.append(DocumentPage(document_id, source, number, text, {"empty": not bool(text)}))
    return pages


def normalize_text(text: str) -> str:
    """Apply NFC and normalize spacing without merging paragraphs."""
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t\f\v ]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
