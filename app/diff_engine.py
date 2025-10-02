from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Optional

try:  # pragma: no cover - runtime import fallback
    from .llm_filter import VariableFieldFilter
    from .models import (
        ComparisonResult,
        DiffType,
        LayoutDiff,
        PageContent,
        PageDiff,
        Span,
        SpanDiff,
        StructuralDiff,
    )
    from .pdf_extractor import extract_pages
    from .visualization import build_highlighted_pdf, render_dual_page_previews
except ImportError:  # pragma: no cover
    from llm_filter import VariableFieldFilter
    from models import (
        ComparisonResult,
        DiffType,
        LayoutDiff,
        PageContent,
        PageDiff,
        Span,
        SpanDiff,
        StructuralDiff,
    )
    from pdf_extractor import extract_pages
    from visualization import build_highlighted_pdf, render_dual_page_previews


@dataclass
class ComparatorSettings:
    layout_tolerance: float = 6.0
    font_tolerance: float = 0.5
    size_tolerance: float = 0.75
    enable_visuals: bool = True
    start_page: Optional[int] = None  # 1-based inclusive
    end_page: Optional[int] = None  # 1-based inclusive


class PDFComparator:
    def __init__(
        self,
        settings: ComparatorSettings | None = None,
        variable_filter: VariableFieldFilter | None = None,
    ) -> None:
        self.settings = settings or ComparatorSettings()
        self.variable_filter = variable_filter or VariableFieldFilter(enable_llm=False)

    def compare(
        self,
        source: bytes,
        target: bytes,
        source_name: str = "source.pdf",
        target_name: str = "target.pdf",
    ) -> ComparisonResult:
        source_pages = extract_pages(source)
        target_pages = extract_pages(target)

        self.variable_filter.tag_variable_fields(source_pages)
        self.variable_filter.tag_variable_fields(target_pages)

        total_pages = max(len(source_pages), len(target_pages))
        result = ComparisonResult(source_name=source_name, target_name=target_name)

        if total_pages == 0:
            result.status = "pass"
            return result

        start_idx = 0
        if self.settings.start_page is not None:
            start_idx = max(0, self.settings.start_page - 1)
        start_idx = min(start_idx, total_pages - 1)

        end_idx = total_pages - 1
        if self.settings.end_page is not None:
            end_idx = max(0, self.settings.end_page - 1)
        end_idx = min(end_idx, total_pages - 1)

        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx

        for page_index in range(start_idx, end_idx + 1):
            src_page = source_pages[page_index] if page_index < len(source_pages) else None
            tgt_page = target_pages[page_index] if page_index < len(target_pages) else None
            page_diff = self._compare_page(page_index, src_page, tgt_page)
            result.pages.append(page_diff)

        result.status = "fail" if result.has_differences() else "pass"

        if self.settings.enable_visuals and result.pages:
            try:
                if target:
                    result.annotated_pdf = build_highlighted_pdf(target, result.pages, doc_type="target")
                if source:
                    result.source_annotated_pdf = build_highlighted_pdf(source, result.pages, doc_type="source")
                previews_source, previews_target = render_dual_page_previews(source, target, result.pages)
                result.page_previews_source = previews_source
                result.page_previews_target = previews_target
            except Exception as exc:  # pragma: no cover
                result.notes.append(f"Visualization failed: {exc}")
        return result

    def _compare_page(
        self,
        page_number: int,
        source_page: Optional[PageContent],
        target_page: Optional[PageContent],
    ) -> PageDiff:
        page_diff = PageDiff(
            page_number=page_number,
            source_page=source_page,
            target_page=target_page,
        )

        if source_page is None and target_page is not None:
            for span in target_page.spans:
                span.diff_status = "extra"
            page_diff.structural_diffs.append(
                StructuralDiff(
                    description="Extra page present in target document",
                    bbox=None,
                    related_spans=target_page.spans,
                )
            )
            return page_diff
        if target_page is None and source_page is not None:
            for span in source_page.spans:
                span.diff_status = "missing"
            page_diff.structural_diffs.append(
                StructuralDiff(
                    description="Missing page in target document",
                    bbox=None,
                    related_spans=source_page.spans,
                )
            )
            return page_diff
        if source_page is None or target_page is None:
            return page_diff

        src_spans = [span for span in source_page.spans if not span.is_variable]
        tgt_spans = [span for span in target_page.spans if not span.is_variable]

        src_tokens = [span.normalized_text() for span in src_spans]
        tgt_tokens = [span.normalized_text() for span in tgt_spans]

        matcher = difflib.SequenceMatcher(None, src_tokens, tgt_tokens, autojunk=False)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for offset in range(i2 - i1):
                    src_span = src_spans[i1 + offset]
                    tgt_span = tgt_spans[j1 + offset]
                    self._check_layout_difference(page_diff, src_span, tgt_span)
            elif tag == "replace":
                span_count = max(i2 - i1, j2 - j1)
                for offset in range(span_count):
                    src_span = src_spans[i1 + offset] if (i1 + offset) < i2 else None
                    tgt_span = tgt_spans[j1 + offset] if (j1 + offset) < j2 else None
                    detail = self._describe_text_change(src_span, tgt_span)
                    if src_span and tgt_span:
                        src_span.diff_status = "modified"
                        tgt_span.diff_status = "modified"
                    elif src_span and not tgt_span:
                        src_span.diff_status = "missing"
                    elif tgt_span and not src_span:
                        tgt_span.diff_status = "extra"
                    page_diff.span_diffs.append(
                        SpanDiff(
                            source_span=src_span,
                            target_span=tgt_span,
                            diff_type=DiffType.TEXT,
                            detail=detail,
                        )
                    )
            elif tag == "delete":
                for src_index in range(i1, i2):
                    src_span = src_spans[src_index]
                    src_span.diff_status = "missing"
                    detail = f"Missing in target: '{src_span.text.strip()}'"
                    page_diff.structural_diffs.append(
                        StructuralDiff(description=detail, bbox=src_span.bbox, related_spans=[src_span])
                    )
            elif tag == "insert":
                for tgt_index in range(j1, j2):
                    tgt_span = tgt_spans[tgt_index]
                    tgt_span.diff_status = "extra"
                    detail = f"Unexpected text in target: '{tgt_span.text.strip()}'"
                    page_diff.span_diffs.append(
                        SpanDiff(source_span=None, target_span=tgt_span, diff_type=DiffType.TEXT, detail=detail)
                    )
        return page_diff

    def _check_layout_difference(self, page_diff: PageDiff, source_span: Span, target_span: Span) -> None:
        sx0, sy0, sx1, sy1 = source_span.bbox
        tx0, ty0, tx1, ty1 = target_span.bbox
        deltas = (tx0 - sx0, ty0 - sy0, tx1 - sx1, ty1 - sy1)
        significant_shift = any(abs(delta) > self.settings.layout_tolerance for delta in deltas)
        font_changed = False
        size_changed = False
        if source_span.font and target_span.font:
            font_changed = source_span.font != target_span.font
        if source_span.size and target_span.size:
            size_changed = abs(source_span.size - target_span.size) > self.settings.size_tolerance

        if significant_shift or font_changed or size_changed:
            detail_parts: list[str] = []
            if significant_shift:
                detail_parts.append(
                    f"Position delta: ({deltas[0]:.1f}, {deltas[1]:.1f}, {deltas[2]:.1f}, {deltas[3]:.1f})"
                )
            if font_changed:
                detail_parts.append(f"Font changed {source_span.font} -> {target_span.font}")
            if size_changed and source_span.size and target_span.size:
                detail_parts.append(f"Size changed {source_span.size:.1f} -> {target_span.size:.1f}")
            page_diff.layout_diffs.append(
                LayoutDiff(
                    target_span=target_span,
                    source_span=source_span,
                    delta_bbox=deltas,
                    delta_font=target_span.font if font_changed else None,
                    delta_size=(target_span.size - source_span.size) if size_changed and source_span.size else None,
                    detail="; ".join(detail_parts),
                )
            )

    def _describe_text_change(self, source_span: Optional[Span], target_span: Optional[Span]) -> str:
        if source_span and target_span:
            return f"'{source_span.text.strip()}' -> '{target_span.text.strip()}'"
        if source_span and not target_span:
            return f"Removed: '{source_span.text.strip()}'"
        if target_span and not source_span:
            return f"Added: '{target_span.text.strip()}'"
        return "Text changed"


__all__ = ["PDFComparator", "ComparatorSettings"]

