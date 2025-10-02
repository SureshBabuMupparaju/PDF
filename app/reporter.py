from __future__ import annotations

from typing import Dict, Iterable, List

import pandas as pd

try:  # pragma: no cover
    from .models import ComparisonResult, DiffType, ReportRow
except ImportError:  # pragma: no cover
    from models import ComparisonResult, DiffType, ReportRow


def build_summary_table(results: Iterable[ComparisonResult]) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for result in results:
        counts = result.summary_counts()
        categories = result.diff_category_totals()
        rows.append(
            {
                "Golden": result.source_name,
                "Target": result.target_name,
                "Status": result.status.upper(),
                "Textual": counts.get("textual", 0),
                "Layout": counts.get("layout", 0),
                "Structural": counts.get("structural", 0),
                "Missing": categories.get("missing", 0),
                "Extra": categories.get("extra", 0),
                "Modified": categories.get("modified", 0),
            }
        )
    return pd.DataFrame(rows)


def build_page_table(result: ComparisonResult) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for page in result.pages:
        summary = page.difference_summary()
        categories = page.diff_category_counts()
        rows.append(
            {
                "Target": result.target_name,
                "Page": page.page_number + 1,
                "Textual": summary.get("textual", 0),
                "Layout": summary.get("layout", 0),
                "Structural": summary.get("structural", 0),
                "Missing": categories.get("missing", 0),
                "Extra": categories.get("extra", 0),
                "Modified": categories.get("modified", 0),
                "Status": "FAIL" if page.has_differences() else "PASS",
            }
        )
    return pd.DataFrame(rows)


def build_detail_rows(result: ComparisonResult) -> List[ReportRow]:
    rows: List[ReportRow] = []
    pair_label = f"{result.source_name} ➜ {result.target_name}"
    for page in result.pages:
        for diff in page.span_diffs:
            rows.append(
                ReportRow(
                    pair_label=pair_label,
                    page_number=page.page_number + 1,
                    diff_type=diff.diff_type,
                    description=diff.detail or (diff.target_span.text if diff.target_span else "Text changed"),
                    preview_ref=f"page-{page.page_number}",
                )
            )
        for diff in page.layout_diffs:
            rows.append(
                ReportRow(
                    pair_label=pair_label,
                    page_number=page.page_number + 1,
                    diff_type=DiffType.LAYOUT,
                    description=diff.detail or "Layout difference",
                    preview_ref=f"page-{page.page_number}",
                )
            )
        for diff in page.structural_diffs:
            rows.append(
                ReportRow(
                    pair_label=pair_label,
                    page_number=page.page_number + 1,
                    diff_type=DiffType.STRUCTURE,
                    description=diff.description,
                    preview_ref=f"page-{page.page_number}",
                )
            )
    return rows


__all__ = [
    "build_summary_table",
    "build_page_table",
    "build_detail_rows",
]
