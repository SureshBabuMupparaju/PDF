from __future__ import annotations

import io
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import fitz

try:  # pragma: no cover
    from .models import DiffType, PageDiff, Span
except ImportError:  # pragma: no cover
    from models import DiffType, PageDiff, Span

PDF_DIFF_COLORS = {
    DiffType.TEXT: (1.0, 0.0, 0.0),
    DiffType.LAYOUT: (1.0, 0.5, 0.0),
    DiffType.STRUCTURE: (0.6, 0.0, 0.6),
}

STATUS_COLORS_TARGET = {
    "extra": (0.2, 0.4, 1.0),
    "modified": (1.0, 0.95, 0.4),
    "missing": (1.0, 0.25, 0.25),
}

STATUS_COLORS_SOURCE = {
    "missing": (1.0, 0.25, 0.25),
    "modified": (1.0, 0.95, 0.4),
}

LAYOUT_COLOR = (1.0, 0.6, 0.2)
STRUCTURAL_COLOR = (0.6, 0.0, 0.6)


def _inflate_rect(rect: Tuple[float, float, float, float], amount: float = 1.0) -> Tuple[float, float, float, float]:
    x0, y0, x1, y1 = rect
    return (x0 - amount, y0 - amount, x1 + amount, y1 + amount)


def build_highlighted_pdf(
    pdf_bytes: bytes,
    page_diffs: Iterable[PageDiff],
    doc_type: str = "target",
) -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for page_diff in page_diffs:
        if page_diff.page_number >= doc.page_count:
            continue
        page = doc.load_page(page_diff.page_number)
        _annotate_page(page, page_diff, doc_type)
    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()


def render_dual_page_previews(
    source_pdf: Optional[bytes],
    target_pdf: Optional[bytes],
    page_diffs: Sequence[PageDiff],
    scale: float = 2.0,
) -> Tuple[Dict[int, bytes], Dict[int, bytes]]:
    previews_source: Dict[int, bytes] = {}
    previews_target: Dict[int, bytes] = {}

    source_doc = fitz.open(stream=source_pdf, filetype="pdf") if source_pdf else None
    target_doc = fitz.open(stream=target_pdf, filetype="pdf") if target_pdf else None

    try:
        for page_diff in page_diffs:
            if source_doc and page_diff.page_number < source_doc.page_count:
                page = source_doc.load_page(page_diff.page_number)
                _overlay_page_shapes(page, page_diff, doc_type="source")
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                previews_source[page_diff.page_number] = pix.tobytes("png")
            if target_doc and page_diff.page_number < target_doc.page_count:
                page = target_doc.load_page(page_diff.page_number)
                _overlay_page_shapes(page, page_diff, doc_type="target")
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                previews_target[page_diff.page_number] = pix.tobytes("png")
    finally:
        if source_doc:
            source_doc.close()
        if target_doc:
            target_doc.close()

    return previews_source, previews_target


def _annotate_page(page: fitz.Page, page_diff: PageDiff, doc_type: str) -> None:
    for rect, color, title, content in _iter_highlight_rects(page_diff, doc_type):
        fitz_rect = fitz.Rect(_inflate_rect(rect))
        annot = page.add_rect_annot(fitz_rect)
        annot.set_colors(stroke=color)
        annot.set_border(width=1)
        if content:
            annot.set_info(title=title, content=content)
        annot.update()


def _overlay_page_shapes(page: fitz.Page, page_diff: PageDiff, doc_type: str) -> None:
    for rect, color, _, _ in _iter_highlight_rects(page_diff, doc_type):
        shape = page.new_shape()
        shape.draw_rect(fitz.Rect(_inflate_rect(rect)))
        shape.finish(color=color, width=1.5)
        shape.commit(overlay=True)


def _iter_highlight_rects(
    page_diff: PageDiff,
    doc_type: str,
) -> Iterable[Tuple[Tuple[float, float, float, float], Tuple[float, float, float], str, str]]:
    if doc_type == "source":
        if page_diff.source_page:
            for span in page_diff.source_page.spans:
                color = STATUS_COLORS_SOURCE.get(span.diff_status or "")
                if color:
                    yield span.bbox, color, "Source difference", span.text.strip()
    else:
        if page_diff.target_page:
            for span in page_diff.target_page.spans:
                color = STATUS_COLORS_TARGET.get(span.diff_status or "")
                if color:
                    yield span.bbox, color, "Target difference", span.text.strip()
        for layout_diff in page_diff.layout_diffs:
            yield (
                layout_diff.bbox,
                LAYOUT_COLOR,
                "Layout difference",
                layout_diff.detail or "Layout change detected",
            )
        for structural_diff in page_diff.structural_diffs:
            if structural_diff.bbox:
                color = STATUS_COLORS_TARGET.get("missing", STRUCTURAL_COLOR)
                title = "Structural difference"
                if "Missing" in structural_diff.description:
                    title = "Missing content"
                yield (
                    structural_diff.bbox,
                    color,
                    title,
                    structural_diff.description,
                )


def build_annotated_pdf(target_pdf: bytes, page_diffs: Iterable[PageDiff]) -> bytes:
    return build_highlighted_pdf(target_pdf, page_diffs, doc_type="target")


def render_page_previews(target_pdf: bytes, page_diffs: Iterable[PageDiff], scale: float = 2.0) -> Dict[int, bytes]:
    _, previews_target = render_dual_page_previews(None, target_pdf, list(page_diffs), scale=scale)
    return previews_target


__all__ = [
    "build_highlighted_pdf",
    "render_dual_page_previews",
    "build_annotated_pdf",
    "render_page_previews",
]
