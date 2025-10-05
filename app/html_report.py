from __future__ import annotations

import base64
import html
from typing import Dict, Iterable, List, Optional, Sequence

try:  # pragma: no cover - runtime import fallback
    from .models import ComparisonResult, PageContent, PageDiff, Span
except ImportError:  # pragma: no cover
    from models import ComparisonResult, PageContent, PageDiff, Span

DIFF_CLASS_MAP = {
    "missing": "diff-missing",
    "extra": "diff-extra",
    "modified": "diff-modified",
    "match": "diff-match",
}

COLOR_LEGEND = [
    ("Missing in target", "diff-missing"),
    ("Extra in target", "diff-extra"),
    ("Modified content", "diff-modified"),
]

STREAMLIT_STYLES = """
<style>
.pdf-compare-container {
    display: flex;
    gap: 1.25rem;
    margin-bottom: 1.5rem;
}
.pdf-compare-column {
    flex: 1;
    border: 1px solid #d0d7ff;
    border-radius: 12px;
    padding: 0.9rem 1rem;
    background: #f8faff;
    box-shadow: inset 0 0 0 1px rgba(88, 112, 255, 0.05);
    max-height: 600px;
    overflow-y: auto;
}
.pdf-compare-column h4 {
    margin-top: 0;
    font-weight: 600;
    color: #1d2a6b;
}
.pdf-page-text span {
    display: inline;
    line-height: 1.5;
}
.diff-missing {
    background: rgba(255, 105, 97, 0.32);
}
.diff-extra {
    background: rgba(91, 155, 255, 0.28);
}
.diff-modified {
    background: rgba(255, 212, 121, 0.42);
}
.pdf-page-empty {
    color: #6072a4;
    font-style: italic;
}
</style>
"""

REPORT_STYLES = """
<style>
:root {
    --bg-gradient: radial-gradient(circle at 10% -20%, #eef2ff 0%, #f9fbff 55%, #fdfdff 100%);
    --surface: #ffffff;
    --border: rgba(109, 127, 255, 0.18);
    --shadow-soft: 0 24px 52px rgba(64, 80, 181, 0.16);
    --shadow-card: 0 18px 44px rgba(37, 56, 130, 0.18);
    --text: #0f1f47;
    --text-subtle: #54608c;
    --accent: #4338ca;
    --accent-soft: rgba(67, 56, 202, 0.14);
}

* {
    box-sizing: border-box;
}

body.report-body {
    margin: 0;
    background: var(--bg-gradient);
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    color: var(--text);
}

.report-shell {
    max-width: 1180px;
    margin: 0 auto;
    padding: 60px 40px 80px;
    position: relative;
}

.hero {
    position: relative;
    overflow: hidden;
    border-radius: 28px;
    border: 1px solid var(--border);
    padding: 40px 48px;
    background: linear-gradient(140deg, rgba(67, 56, 202, 0.12), rgba(59, 130, 246, 0.06));
    box-shadow: var(--shadow-soft);
}

.hero::before,
.hero::after {
    content: "";
    position: absolute;
    border-radius: 50%;
    filter: blur(62px);
}

.hero::before {
    width: 360px;
    height: 360px;
    top: -140px;
    right: -120px;
    background: rgba(96, 165, 250, 0.25);
}

.hero::after {
    width: 320px;
    height: 320px;
    bottom: -180px;
    left: -120px;
    background: rgba(244, 114, 182, 0.24);
}

.hero-content {
    position: relative;
    z-index: 1;
}

.hero-title {
    margin: 0;
    font-size: 2.25rem;
    font-weight: 700;
    letter-spacing: -0.02em;
}

hero-subtitle {
    margin: 12px 0 0;
    max-width: 600px;
    line-height: 1.6;
    color: var(--text-subtle);
}

.hero-badge {
    position: absolute;
    top: 32px;
    right: 36px;
    padding: 9px 20px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.9);
    box-shadow: 0 12px 26px rgba(59, 130, 246, 0.22);
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-size: 0.78rem;
}

.summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 20px;
    margin: 42px 0;
}

.summary-card {
    position: relative;
    background: var(--surface);
    border-radius: 22px;
    padding: 26px 24px;
    border: 1px solid var(--border);
    box-shadow: var(--shadow-card);
    transition: transform 0.22s ease, box-shadow 0.22s ease;
}

.summary-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 26px 50px rgba(64, 80, 181, 0.26);
}

.summary-label {
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-subtle);
}

.summary-value {
    display: block;
    margin-top: 8px;
    font-size: 1.9rem;
    font-weight: 700;
}

.category-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 34px;
}

.category-chip {
    display: inline-flex;
    gap: 10px;
    align-items: center;
    padding: 10px 16px;
    border-radius: 14px;
    background: rgba(67, 56, 202, 0.08);
    border: 1px solid rgba(67, 56, 202, 0.18);
    font-weight: 600;
    font-size: 0.85rem;
    color: var(--accent);
}

.category-chip span {
    font-weight: 700;
    color: #1f2937;
}

.legend-cards {
    display: flex;
    flex-wrap: wrap;
    gap: 18px;
    margin-bottom: 36px;
}

.legend-card {
    flex: 1 1 220px;
    background: var(--surface);
    border-radius: 16px;
    border: 1px solid var(--border);
    padding: 16px 18px;
    display: flex;
    align-items: center;
    gap: 14px;
}

.legend-swatch {
    width: 22px;
    height: 22px;
    border-radius: 6px;
    border: 1px solid rgba(15, 23, 42, 0.08);
}

.legend-swatch.diff-missing { background: rgba(248, 113, 113, 0.28); }
.legend-swatch.diff-extra { background: rgba(96, 165, 250, 0.26); }
.legend-swatch.diff-modified { background: rgba(253, 224, 71, 0.38); }

.download-grid {
    display: grid;
    gap: 20px;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    margin-bottom: 40px;
}

.download-card {
    background: var(--surface);
    border-radius: 20px;
    border: 1px solid var(--border);
    padding: 22px 24px;
    box-shadow: var(--shadow-card);
}

.download-card h3 {
    margin: 0 0 14px;
    font-size: 1.05rem;
}

.download-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.download-chip {
    display: inline-flex;
    align-items: center;
    padding: 9px 18px;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 600;
    text-decoration: none;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.download-chip--source {
    background: rgba(59, 130, 246, 0.16);
    color: #1d4ed8;
}

.download-chip--target {
    background: rgba(236, 72, 153, 0.16);
    color: #9d174d;
}

.download-chip:hover {
    transform: translateY(-4px);
    box-shadow: 0 16px 24px rgba(59, 130, 246, 0.2);
}

.jump-nav {
    background: var(--surface);
    border-radius: 18px;
    border: 1px solid var(--border);
    padding: 20px 24px;
    margin-bottom: 36px;
}

.jump-nav h2 {
    margin-top: 0;
}

.nav-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
}

.nav-list a {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    border-radius: 12px;
    background: var(--accent-soft);
    color: var(--accent);
    text-decoration: none;
    font-weight: 600;
    font-size: 0.84rem;
}

.report-main {
    display: flex;
    flex-direction: column;
    gap: 30px;
}

.page-section {
    background: var(--surface);
    border-radius: 24px;
    border: 1px solid var(--border);
    padding: 28px 30px 32px;
    box-shadow: var(--shadow-card);
}

.page-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 18px;
}

.page-meta {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.diff-badge {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    padding: 6px 12px;
    border-radius: 999px;
    background: rgba(239, 246, 255, 0.9);
    font-weight: 600;
    font-size: 0.78rem;
}

.page-meta__clean {
    font-size: 0.9rem;
    color: var(--text-subtle);
    font-weight: 600;
}

.page-image-columns {
    display: flex;
    flex-wrap: wrap;
    gap: 18px;
    margin-bottom: 20px;
}

.page-image-column {
    flex: 1 1 320px;
    background: linear-gradient(180deg, rgba(248, 250, 255, 0.95), rgba(248, 250, 255, 0.99));
    border-radius: 18px;
    border: 1px solid rgba(191, 203, 255, 0.4);
    padding: 16px 16px 18px;
    box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.12);
}

.page-image-column h3 {
    margin: 0 0 12px;
    font-size: 0.95rem;
    color: #1f2a64;
}

.page-image-column img {
    width: 100%;
    border-radius: 12px;
    border: 1px solid rgba(148, 163, 255, 0.35);
    box-shadow: 0 20px 42px rgba(46, 64, 146, 0.28);
}

.diff-detail-card {
    background: rgba(247, 250, 255, 0.92);
    border-radius: 20px;
    border: 1px solid rgba(196, 203, 255, 0.6);
    padding: 20px 22px;
    margin-bottom: 18px;
}

.diff-detail-card h3 {
    margin: 0 0 12px;
}

.diff-detail-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.diff-detail-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
}

.diff-tag {
    flex-shrink: 0;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #1e1b4b;
    background: rgba(129, 140, 248, 0.22);
}

.diff-tag--mismatch { background: rgba(250, 204, 21, 0.28); color: #92400e; }
.diff-tag--spelling { background: rgba(96, 165, 250, 0.26); color: #1d4ed8; }
.diff-tag--extra { background: rgba(59, 130, 246, 0.18); color: #1e3a8a; }
.diff-tag--missing { background: rgba(248, 113, 113, 0.24); color: #7f1d1d; }
.diff-tag--layout { background: rgba(74, 222, 128, 0.24); color: #166534; }
.diff-tag--structure { background: rgba(251, 191, 36, 0.26); color: #92400e; }

.diff-detail-text {
    font-size: 0.9rem;
    color: #1e293b;
    line-height: 1.55;
}

.page-nav {
    display: flex;
    justify-content: space-between;
    margin-top: 24px;
}

.page-nav a {
    color: var(--accent);
    font-weight: 600;
    text-decoration: none;
}

.page-nav a:hover {
    text-decoration: underline;
}

@media (max-width: 768px) {
    .hero {
        padding: 32px;
    }
    .summary-grid {
        grid-template-columns: 1fr;
    }
    .page-header {
        flex-direction: column;
        align-items: flex-start;
    }
}
</style>
"""

CATEGORY_DISPLAY = {
    "mismatch": "Mismatched text",
    "spelling": "Spelling error",
    "extra": "Extra text",
    "missing": "Missing text",
}

DETAIL_TAG_CLASS = {
    "mismatch": "diff-tag diff-tag--mismatch",
    "spelling": "diff-tag diff-tag--spelling",
    "extra": "diff-tag diff-tag--extra",
    "missing": "diff-tag diff-tag--missing",
}


def _spans_to_html(spans: Sequence[Span]) -> str:
    parts: List[str] = []
    prev_block: Optional[int] = None
    prev_line: Optional[int] = None
    for span in spans:
        if prev_block is not None:
            if span.block_index != prev_block:
                parts.append("<br/><br/>")
            elif span.line_index != prev_line:
                parts.append("<br/>")
            else:
                parts.append(" ")
        css_class = DIFF_CLASS_MAP.get(span.diff_status or "")
        escaped = html.escape(span.text)
        if css_class:
            parts.append(f"<span class='{css_class}'>{escaped}</span>")
        else:
            parts.append(f"<span>{escaped}</span>")
        prev_block = span.block_index
        prev_line = span.line_index
    return "".join(parts) if parts else "<span></span>"


def _render_page_text(page: Optional[PageContent]) -> str:
    if page is None:
        return "<p class='page-empty'>No content available for this page.</p>"
    return f"<div class='page-text'>{_spans_to_html(page.spans)}</div>"


def _image_tag(image_b64: Optional[str]) -> str:
    if not image_b64:
        return "<p class='page-empty'>Preview unavailable.</p>"
    return f"<img src='data:image/png;base64,{image_b64}' alt='PDF page preview'/>"


def _safe_filename(name: str) -> str:
    sanitized = [ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in name.strip()]
    return "".join(sanitized) or "file"


def _category_chips(span_totals: Dict[str, int]) -> List[str]:
    chips: List[str] = []
    for key, label in CATEGORY_DISPLAY.items():
        count = span_totals.get(key)
        if count:
            chips.append(f"<div class='category-chip'>{label}: <span>{count}</span></div>")
    return chips


def _diff_detail_items(page: PageDiff) -> List[str]:
    items: List[str] = []
    for diff in page.span_diffs:
        category = diff.category or "mismatch"
        tag_class = DETAIL_TAG_CLASS.get(category, "diff-tag diff-tag--mismatch")
        label = CATEGORY_DISPLAY.get(category, "Text change")
        desc = diff.detail or (
            diff.target_span.text if diff.target_span else "Text change detected"
        )
        items.append(
            f"<li class='diff-detail-item'><span class='{tag_class}'>{label}</span><span class='diff-detail-text'>{html.escape(desc)}</span></li>"
        )
    for diff in page.layout_diffs:
        desc = diff.detail or "Layout change detected"
        items.append(
            "<li class='diff-detail-item'><span class='diff-tag diff-tag--layout'>Layout</span>"
            f"<span class='diff-detail-text'>{html.escape(desc)}</span></li>"
        )
    for diff in page.structural_diffs:
        desc = diff.description or "Structural change detected"
        items.append(
            "<li class='diff-detail-item'><span class='diff-tag diff-tag--structure'>Structure</span>"
            f"<span class='diff-detail-text'>{html.escape(desc)}</span></li>"
        )
    return items


def _build_download_cards(results: Sequence[ComparisonResult]) -> List[str]:
    cards: List[str] = []
    for result in results:
        chips: List[str] = []
        if result.source_annotated_pdf:
            b64 = base64.b64encode(result.source_annotated_pdf).decode()
            filename = _safe_filename(f"highlighted_{result.source_name}")
            chips.append(
                f"<a class='download-chip download-chip--source' href='data:application/pdf;base64,{b64}' download='{filename}'>Highlighted {html.escape(result.source_name)}</a>"
            )
        if result.annotated_pdf:
            b64 = base64.b64encode(result.annotated_pdf).decode()
            filename = _safe_filename(f"highlighted_{result.target_name}")
            chips.append(
                f"<a class='download-chip download-chip--target' href='data:application/pdf;base64,{b64}' download='{filename}'>Highlighted {html.escape(result.target_name)}</a>"
            )
        if chips:
            cards.append(
                "<div class='download-card'>"
                f"<h3>{html.escape(result.target_name)}</h3>"
                f"<div class='download-chip-row'>{''.join(chips)}</div>"
                "</div>"
            )
    return cards


def _build_page_section(
    pair_index: int,
    page: PageDiff,
    source_label: str,
    target_label: str,
    next_anchor: Optional[str],
    prev_anchor: Optional[str],
    source_image_b64: Optional[str],
    target_image_b64: Optional[str],
) -> str:
    anchor = f"pair{pair_index}-page{page.page_number + 1}"
    counts = page.diff_category_counts()

    badges: List[str] = []
    if counts.get("missing"):
        badges.append(f"<span class='diff-badge diff-badge--missing'>{counts['missing']} missing</span>")
    if counts.get("extra"):
        badges.append(f"<span class='diff-badge diff-badge--extra'>{counts['extra']} extra</span>")
    if counts.get("modified"):
        badges.append(f"<span class='diff-badge diff-badge--modified'>{counts['modified']} modified</span>")
    if not badges:
        badges.append("<span class='page-meta__clean'>No textual differences detected</span>")

    image_section = ""
    if source_image_b64 or target_image_b64:
        image_section = (
            "<div class='page-image-columns'>"
            f"<div class='page-image-column'><h3>{html.escape(source_label)}</h3>{_image_tag(source_image_b64)}</div>"
            f"<div class='page-image-column'><h3>{html.escape(target_label)}</h3>{_image_tag(target_image_b64)}</div>"
            "</div>"
        )

    detail_items = _diff_detail_items(page)
    detail_html = ""
    if detail_items:
        detail_html = (
            "<div class='diff-detail-card'>"
            "<h3>Key Differences</h3>"
            f"<ul class='diff-detail-list'>{''.join(detail_items)}</ul>"
            "</div>"
        )

    previous_link = f"<a href='#{prev_anchor}'>&larr; Previous page</a>" if prev_anchor else "<span></span>"
    next_link = f"<a href='#{next_anchor}'>Next page &rarr;</a>" if next_anchor else "<span></span>"

    return (
        f"<article id='{anchor}' class='page-section'>"
        "<div class='page-header'>"
        f"<h2>{html.escape(source_label)} &rarr; {html.escape(target_label)} â€” Page {page.page_number + 1}</h2>"
        f"<div class='page-meta'>{''.join(badges)}</div>"
        "</div>"
        f"{image_section}"
        f"{detail_html}"
        f"<div class='page-nav'><div>{previous_link}</div><div>{next_link}</div></div>"
        "</article>"
    )


def build_page_pair_html(page: PageDiff, source_label: str, target_label: str) -> str:
    source_html = _render_page_text(page.source_page)
    target_html = _render_page_text(page.target_page)
    return (
        "<div class='pdf-compare-container'>"
        f"<div class='pdf-compare-column'><h4>{html.escape(source_label)} - Page {page.page_number + 1}</h4>"
        f"<div class='pdf-page-text'>{source_html}</div></div>"
        f"<div class='pdf-compare-column'><h4>{html.escape(target_label)} - Page {page.page_number + 1}</h4>"
        f"<div class='pdf-page-text'>{target_html}</div></div>"
        "</div>"
    )


def generate_html_report(
    results: Sequence[ComparisonResult],
    title: str = "Automated PDF Comparison Report",
) -> str:
    sections: List[str] = []
    nav_items: List[str] = []
    total_pages = 0
    pages_with_diffs = 0
    aggregate_counts: Dict[str, int] = {"missing": 0, "extra": 0, "modified": 0}
    span_category_totals: Dict[str, int] = {"mismatch": 0, "spelling": 0, "extra": 0, "missing": 0}

    for pair_index, result in enumerate(results):
        pair_prefix = f"pair{pair_index}"
        span_counts = result.span_category_totals()
        for key in span_category_totals:
            span_category_totals[key] += span_counts.get(key, 0)

        for page in result.pages:
            total_pages += 1
            if page.has_differences():
                pages_with_diffs += 1
            counts = page.diff_category_counts()
            for key, value in counts.items():
                aggregate_counts[key] += value
            anchor = f"{pair_prefix}-page{page.page_number + 1}"
            nav_items.append(
                f"<li><a href='#{anchor}'>{html.escape(result.target_name)} &mdash; Page {page.page_number + 1}</a></li>"
            )

        for idx, page in enumerate(result.pages):
            next_anchor = None
            prev_anchor = None
            if idx + 1 < len(result.pages):
                next_anchor = f"{pair_prefix}-page{result.pages[idx + 1].page_number + 1}"
            if idx - 1 >= 0:
                prev_anchor = f"{pair_prefix}-page{result.pages[idx - 1].page_number + 1}"
            source_img = result.page_previews_source.get(page.page_number)
            target_img = result.page_previews_target.get(page.page_number)
            sections.append(
                _build_page_section(
                    pair_index,
                    page,
                    result.source_name,
                    result.target_name,
                    next_anchor,
                    prev_anchor,
                    base64.b64encode(source_img).decode() if source_img else None,
                    base64.b64encode(target_img).decode() if target_img else None,
                )
            )

    span_chips = _category_chips(span_category_totals)

    summary_cards = [
        f"<div class='summary-card'><span class='summary-label'>Total pages compared</span><span class='summary-value'>{total_pages}</span></div>",
        f"<div class='summary-card'><span class='summary-label'>Pages with differences</span><span class='summary-value'>{pages_with_diffs}</span></div>",
        f"<div class='summary-card'><span class='summary-label'>Missing elements</span><span class='summary-value'>{aggregate_counts['missing']}</span></div>",
        f"<div class='summary-card'><span class='summary-label'>Extra elements</span><span class='summary-value'>{aggregate_counts['extra']}</span></div>",
        f"<div class='summary-card'><span class='summary-label'>Modified elements</span><span class='summary-value'>{aggregate_counts['modified']}</span></div>",
    ]

    legend_cards = [
        f"<div class='legend-card'><span class='legend-swatch {css}'></span><span>{label}</span></div>"
        for label, css in COLOR_LEGEND
    ]

    download_cards = _build_download_cards(results)

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='utf-8'/>",
        f"<title>{html.escape(title)}</title>",
        REPORT_STYLES,
        "</head>",
        "<body class='report-body'>",
        "<div class='report-shell'>",
        "<section class='hero'>",
        "<div class='hero-content'>",
        f"<p class='hero-title'>{html.escape(title)}</p>",
        "<p class='hero-subtitle'>Automated visual and textual analysis that highlights missing, extra, modified, and misspelled content across insurance PDF deliverables.</p>",
        "</div>",
        "<div class='hero-badge'>Automated QA</div>",
        "</section>",
        "<section>",
        "<div class='summary-grid'>",
        *summary_cards,
        "</div>",
        "</section>",
    ]

    if span_chips:
        html_parts.extend([
            "<section>",
            "<div class='category-chips'>",
            *span_chips,
            "</div>",
            "</section>",
        ])

    html_parts.extend([
        "<section>",
        "<div class='legend-cards'>",
        *legend_cards,
        "</div>",
        "</section>",
    ])

    if download_cards:
        html_parts.extend([
            "<section>",
            "<div class='download-grid'>",
            *download_cards,
            "</div>",
            "</section>",
        ])

    if nav_items:
        html_parts.extend([
            "<section class='jump-nav'>",
            "<h2>Jump to page</h2>",
            "<ul class='nav-list'>",
            *nav_items,
            "</ul>",
            "</section>",
        ])

    html_parts.append("<main class='report-main'>")
    html_parts.extend(sections)
    html_parts.append("</main>")
    html_parts.append("</div>")
    html_parts.append("</body>")
    html_parts.append("</html>")

    return "".join(html_parts)


__all__ = [
    "build_page_pair_html",
    "generate_html_report",
    "STREAMLIT_STYLES",
]

