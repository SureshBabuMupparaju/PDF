from __future__ import annotations

import io
from typing import List, Union

import fitz

try:  # pragma: no cover - runtime import fallback
    from .models import PageContent, Span
except ImportError:  # pragma: no cover
    from models import PageContent, Span


def _open_pdf(source: Union[str, bytes, io.BytesIO, fitz.Document]) -> fitz.Document:
    if isinstance(source, fitz.Document):
        return source
    if isinstance(source, (bytes, bytearray)):
        return fitz.open(stream=source, filetype="pdf")
    if isinstance(source, io.BytesIO):
        return fitz.open(stream=source.read(), filetype="pdf")
    if isinstance(source, str):
        return fitz.open(source)
    raise TypeError(f"Unsupported PDF source type: {type(source)!r}")


def extract_pages(source: Union[str, bytes, io.BytesIO, fitz.Document]) -> List[PageContent]:
    doc = _open_pdf(source)
    pages: List[PageContent] = []

    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        raw_page = page.get_text("dict")
        page_content = PageContent(page_number=page_index)

        block_idx = 0
        for block in raw_page.get("blocks", []):
            if block.get("type") != 0:
                block_idx += 1
                continue
            for line_idx, line in enumerate(block.get("lines", [])):
                for span_idx, span in enumerate(line.get("spans", [])):
                    text = span.get("text", "")
                    if not text.strip():
                        continue
                    bbox = tuple(span.get("bbox", (0, 0, 0, 0)))
                    page_content.spans.append(
                        Span(
                            text=text,
                            bbox=bbox,  # type: ignore[arg-type]
                            page_number=page_index,
                            block_index=block_idx,
                            line_index=line_idx,
                            span_index=span_idx,
                            font=span.get("font"),
                            size=span.get("size"),
                        )
                    )
            block_idx += 1
        pages.append(page_content)
    return pages


def extract_text(source: Union[str, bytes, io.BytesIO, fitz.Document]) -> List[str]:
    doc = _open_pdf(source)
    return [doc.load_page(i).get_text() for i in range(doc.page_count)]


def close_document(doc: fitz.Document) -> None:
    try:
        doc.close()
    except Exception:
        pass


class PDFResource:
    """Context manager ensuring PyMuPDF documents are closed properly."""

    def __init__(self, source: Union[str, bytes, io.BytesIO, fitz.Document]):
        self._source = source
        self.document: fitz.Document | None = None

    def __enter__(self) -> fitz.Document:
        self.document = _open_pdf(self._source)
        return self.document

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.document is not None:
            close_document(self.document)


__all__ = ["extract_pages", "extract_text", "PDFResource"]
