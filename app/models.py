from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class DiffType(str, Enum):
    TEXT = "textual"
    LAYOUT = "layout"
    STRUCTURE = "structural"


@dataclass
class Span:
    text: str
    bbox: Tuple[float, float, float, float]
    page_number: int
    block_index: int
    line_index: int
    span_index: int
    font: Optional[str] = None
    size: Optional[float] = None
    is_variable: bool = False
    diff_status: Optional[str] = None

    def normalized_text(self) -> str:
        return " ".join(self.text.split()).strip().lower()


@dataclass
class PageContent:
    page_number: int
    spans: List[Span] = field(default_factory=list)


@dataclass
class SpanDiff:
    source_span: Optional[Span]
    target_span: Optional[Span]
    diff_type: DiffType = DiffType.TEXT
    detail: str = ""
    category: Optional[str] = None

    @property
    def bbox(self) -> Optional[Tuple[float, float, float, float]]:
        if self.target_span:
            return self.target_span.bbox
        if self.source_span:
            return self.source_span.bbox
        return None


@dataclass
class LayoutDiff:
    target_span: Span
    source_span: Span
    delta_bbox: Tuple[float, float, float, float]
    delta_font: Optional[str] = None
    delta_size: Optional[float] = None
    detail: str = ""

    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        return self.target_span.bbox


@dataclass
class StructuralDiff:
    description: str
    bbox: Optional[Tuple[float, float, float, float]] = None
    related_spans: List[Span] = field(default_factory=list)


@dataclass
class PageDiff:
    page_number: int
    span_diffs: List[SpanDiff] = field(default_factory=list)
    layout_diffs: List[LayoutDiff] = field(default_factory=list)
    structural_diffs: List[StructuralDiff] = field(default_factory=list)
    source_page: Optional[PageContent] = None
    target_page: Optional[PageContent] = None

    def has_differences(self) -> bool:
        return any([self.span_diffs, self.layout_diffs, self.structural_diffs])

    def difference_summary(self) -> Dict[str, int]:
        return {
            "textual": len([d for d in self.span_diffs if d.diff_type == DiffType.TEXT]),
            "layout": len(self.layout_diffs),
            "structural": len(self.structural_diffs),
        }

    def diff_category_counts(self) -> Dict[str, int]:
        counts = {"missing": 0, "extra": 0, "modified": 0}
        if self.source_page:
            counts["missing"] += sum(1 for span in self.source_page.spans if span.diff_status == "missing")
        if self.target_page:
            counts["extra"] += sum(1 for span in self.target_page.spans if span.diff_status == "extra")
        counts["modified"] += sum(
            1
            for diff in self.span_diffs
            if diff.source_span is not None and diff.target_span is not None
        )
        return counts

    def span_category_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for diff in self.span_diffs:
            key = diff.category or "mismatch"
            counts[key] = counts.get(key, 0) + 1
        return counts

    def match_count(self) -> int:
        if not self.target_page:
            return 0
        return sum(1 for span in self.target_page.spans if span.diff_status == "match")


@dataclass
class ComparisonResult:
    source_name: str
    target_name: str
    pages: List[PageDiff] = field(default_factory=list)
    status: str = "pending"
    notes: List[str] = field(default_factory=list)
    annotated_pdf: Optional[bytes] = None
    source_annotated_pdf: Optional[bytes] = None
    page_previews_source: Dict[int, bytes] = field(default_factory=dict)
    page_previews_target: Dict[int, bytes] = field(default_factory=dict)

    def has_differences(self) -> bool:
        return any(page.has_differences() for page in self.pages)

    def summary_counts(self) -> Dict[str, int]:
        totals = {"textual": 0, "layout": 0, "structural": 0}
        for page in self.pages:
            summary = page.difference_summary()
            for key in totals:
                totals[key] += summary.get(key, 0)
        return totals

    def diff_category_totals(self) -> Dict[str, int]:
        totals = {"missing": 0, "extra": 0, "modified": 0}
        for page in self.pages:
            summary = page.diff_category_counts()
            for key in totals:
                totals[key] += summary.get(key, 0)
        return totals

    def span_category_totals(self) -> Dict[str, int]:
        totals: Dict[str, int] = {"mismatch": 0, "spelling": 0, "extra": 0, "missing": 0}
        for page in self.pages:
            counts = page.span_category_counts()
            for key, value in counts.items():
                totals[key] = totals.get(key, 0) + value
        return totals

    def match_total(self) -> int:
        return sum(page.match_count() for page in self.pages)

    def total_compared_tokens(self) -> int:
        span_totals = self.span_category_totals()
        return self.match_total() + sum(span_totals.values())


@dataclass
class ReportRow:
    pair_label: str
    page_number: int
    diff_type: DiffType
    description: str
    preview_ref: Optional[str] = None
    category: Optional[str] = None
