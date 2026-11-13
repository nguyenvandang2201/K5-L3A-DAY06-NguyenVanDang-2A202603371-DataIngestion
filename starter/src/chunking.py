"""Deterministic, page-bounded chunking strategies."""
import hashlib
from .models import Chunk, DocumentPage


def _chunk(page: DocumentPage, method: str, index: int, text: str) -> Chunk:
    key = f"{method}:{page.document_id}:{page.page}:{index}:{text}"
    chunk_id = hashlib.sha256(key.encode()).hexdigest()[:24]
    return Chunk(chunk_id, page.document_id, page.source, page.page, text, dict(page.metadata))


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Require size > overlap >= 0")
    text = page.text
    step = size - overlap
    return [_chunk(page, "fixed", i, text[start:start + size])
            for i, start in enumerate(range(0, len(text), step)) if text[start:start + size].strip()]


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    if max_size <= 0:
        raise ValueError("max_size must be positive")
    pieces = []
    for paragraph in page.text.split("\n\n"):
        paragraph = paragraph.strip()
        while len(paragraph) > max_size:
            cut = paragraph.rfind(" ", 0, max_size + 1)
            cut = cut if cut > max_size // 2 else max_size
            pieces.append(paragraph[:cut].strip())
            paragraph = paragraph[cut:].strip()
        if paragraph:
            pieces.append(paragraph)
    groups, current = [], ""
    for piece in pieces:
        candidate = f"{current}\n\n{piece}" if current else piece
        if current and len(candidate) > max_size:
            groups.append(current)
            current = piece
        else:
            current = candidate
    if current:
        groups.append(current)
    return [_chunk(page, "paragraph", i, text) for i, text in enumerate(groups)]
