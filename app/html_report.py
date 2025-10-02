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
    border-radius: 10px;
    padding: 0.9rem 1rem;
    background: #f8faff;
    box-shadow: inset 0 0 0 1px rgba(88, 112, 255, 0.04);
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
.pdf-page-text br {
    line-height: 1.25;
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
    --bg-gradient: radial-gradient(circle at top left, #f1f4ff 0%, #f8fbff 35%, #eef2ff 70%, #fdfcff 100%);
    --surface: #ffffff;
    --surface-muted: rgba(255, 255, 255, 0.78);
    --border-color: rgba(102, 126, 255, 0.15);
    --shadow-soft: 0 24px 60px rgba(20, 33, 83, 0.12);
    --shadow-card: 0 14px 38px rgba(54, 90, 200, 0.14);
    --text-primary: #12205c;
    --text-secondary: #4a5a88;
    --accent: #4f46e5;
    --accent-soft: rgba(79, 70, 229, 0.12);
    --badge-missing: #ff6b6b;
    --badge-extra: #4f8bff;
    --badge-modified: #f6b73c;
}

* {
    box-sizing: border-box;
}

body.report-body {
    margin: 0;
    background: var(--bg-gradient);
    font-family: "Segoe UI", "Inter", Arial, sans-serif;
    color: var(--text-primary);
}

.report-container {
    max-width: 1120px;
    margin: 0 auto;
    padding: 56px 38px 72px;
    position: relative;
}

.report-container::after {
    content: "";
    position: absolute;
    inset: 12% -12% auto;
    height: 420px;
    background: radial-gradient(circle, rgba(79, 70, 229, 0.18), rgba(79, 70, 229, 0));
    filter: blur(60px);
    z-index: -1;
}

.hero {
    background: linear-gradient(135deg, rgba(79, 70, 229, 0.08), rgba(59, 130, 246, 0.05));
    border: 1px solid rgba(79, 70, 229, 0.18);
    border-radius: 24px;
    padding: 36px 42px;
    margin-bottom: 36px;
    position: relative;
    overflow: hidden;
    box-shadow: var(--shadow-soft);
}

.hero::before {
    content: "";
    position: absolute;
    width: 320px;
    height: 320px;
    top: -120px;
    right: -120px;
    background: radial-gradient(circle, rgba(59, 130, 246, 0.22), rgba(59, 130, 246, 0));
    filter: blur(4px);
}

.hero::after {
    content: "";
    position: absolute;
    width: 220px;
    height: 220px;
    bottom: -100px;
    left: -80px;
    background: radial-gradient(circle, rgba(249, 115, 22, 0.25), rgba(249, 115, 22, 0));
    filter: blur(6px);
}

.hero-content {
    position: relative;
    z-index: 1;
}

.hero-title {
    font-size: 2.1rem;
    margin: 0 0 8px;
    font-weight: 700;
    color: #0f172a;
}

.hero-subtitle {
    margin: 0;
    font-size: 1rem;
    color: var(--text-secondary);
    max-width: 620px;
    line-height: 1.6;
}

.hero-badge {
    position: absolute;
    top: 28px;
    right: 32px;
    background: rgba(255, 255, 255, 0.85);
    color: #1e1b4b;
    font-weight: 600;
    padding: 8px 18px;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: 0.78rem;
    box-shadow: 0 10px 28px rgba(79, 70, 229, 0.18);
}

.summary-grid {
    display: grid;
    gap: 18px;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    margin-bottom: 32px;
}

.summary-card {
    position: relative;
    background: var(--surface);
    border-radius: 20px;
    padding: 26px 22px 24px 82px;
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-card);
    overflow: hidden;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.summary-card::before {
    content: "";
    position: absolute;
    width: 44px;
    height: 44px;
    top: 22px;
    left: 20px;
    border-radius: 14px;
    background: rgba(79, 70, 229, 0.12);
    backdrop-filter: blur(4px);
    border: 1px solid rgba(79, 70, 229, 0.25);
    box-shadow: 0 10px 18px rgba(79, 70, 229, 0.12);
}

.summary-card[data-icon="pages"]::after,
.summary-card[data-icon="alerts"]::after,
.summary-card[data-icon="diff"]::after,
.summary-card[data-icon="delta"]::after,
.summary-card[data-icon="extra"]::after {
    content: "";
    position: absolute;
    width: 24px;
    height: 24px;
    top: 32px;
    left: 30px;
    background-size: contain;
    background-repeat: no-repeat;
}

.summary-card[data-icon="pages"]::after {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48' fill='none'%3E%3Crect x='10' y='8' width='28' height='32' rx='6' stroke='%235f6bff' stroke-width='3'/%3E%3Cpath d='M16 18h16M16 26h16M16 34h12' stroke='%235f6bff' stroke-width='3' stroke-linecap='round'/%3E%3C/svg%3E");
}

.summary-card[data-icon="alerts"]::after {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48' fill='none'%3E%3Cpath d='M24 8l17 30H7l17-30z' stroke='%23ef4444' stroke-width='3' stroke-linejoin='round'/%3E%3Ccircle cx='24' cy='32' r='2.5' fill='%23ef4444'/%3E%3Cpath d='M24 20v8' stroke='%23ef4444' stroke-width='3' stroke-linecap='round'/%3E%3C/svg%3E");
}

.summary-card[data-icon="diff"]::after {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48' fill='none'%3E%3Ccircle cx='16' cy='24' r='8' stroke='%23f59e0b' stroke-width='3'/%3E%3Ccircle cx='32' cy='24' r='8' stroke='%235f6bff' stroke-width='3'/%3E%3C/svg%3E");
}

.summary-card[data-icon="delta"]::after {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48' fill='none'%3E%3Cpath d='M8 34l12-14 10 10 10-18' stroke='%234f46e5' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/%3E%3Cpath d='M34 14h8v8' stroke='%234f46e5' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
}

.summary-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 18px 40px rgba(79, 70, 229, 0.22);
}

.summary-label {
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #5c6c9f;
    margin-bottom: 8px;
    display: block;
}

.summary-value {
    font-size: 1.9rem;
    font-weight: 700;
    color: #0b1a4a;
}

.legend-cards {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 34px;
}

.legend-card {
    flex: 1 1 220px;
    background: var(--surface);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 14px 18px;
    display: flex;
    align-items: center;
    gap: 14px;
    box-shadow: 0 10px 26px rgba(15, 23, 42, 0.08);
}

.legend-swatch {
    width: 22px;
    height: 22px;
    border-radius: 8px;
    border: 1px solid rgba(17, 25, 74, 0.08);
}

.legend-swatch.diff-missing {
    background: rgba(255, 106, 106, 0.42);
}

.legend-swatch.diff-extra {
    background: rgba(86, 149, 255, 0.4);
}

.legend-swatch.diff-modified {
    background: rgba(249, 187, 66, 0.46);
}

.download-grid {
    display: grid;
    gap: 18px;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    margin-bottom: 40px;
}

.download-card {
    background: var(--surface);
    border-radius: 18px;
    padding: 22px;
    border: 1px solid var(--border-color);
    box-shadow: 0 16px 40px rgba(79, 70, 229, 0.16);
}

.download-card h3 {
    margin: 0 0 14px;
    font-size: 1.1rem;
    color: #111c4e;
}

.download-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.download-chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 9px 18px;
    border-radius: 999px;
    text-decoration: none;
    font-size: 0.85rem;
    font-weight: 600;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.download-chip--source {
    background: rgba(59, 130, 246, 0.15);
    color: #1e3a8a;
}

.download-chip--target {
    background: rgba(236, 72, 153, 0.16);
    color: #831843;
}

.download-chip:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 22px rgba(20, 33, 83, 0.18);
}

.jump-nav {
    background: var(--surface);
    border-radius: 18px;
    border: 1px solid var(--border-color);
    padding: 18px 22px;
    margin-bottom: 32px;
    box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
}

.jump-nav h2 {
    margin-top: 0;
    margin-bottom: 12px;
}

.nav-list {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    padding: 0;
    margin: 0;
    list-style: none;
}

.nav-list a {
    display: inline-flex;
    align-items: center;
    padding: 8px 16px;
    border-radius: 12px;
    background: var(--accent-soft);
    color: var(--accent);
    text-decoration: none;
    font-weight: 600;
    font-size: 0.85rem;
}

.nav-list a:hover {
    background: rgba(79, 70, 229, 0.22);
}

.report-main {
    display: flex;
    flex-direction: column;
    gap: 28px;
}

.page-section {
    background: var(--surface);
    border-radius: 22px;
    border: 1px solid var(--border-color);
    padding: 26px 28px 32px;
    box-shadow: 0 24px 54px rgba(79, 70, 229, 0.14);
}

.page-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 20px;
}

.page-header h2 {
    margin: 0;
    font-size: 1.25rem;
    color: #0f172a;
}

.page-meta {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.page-meta__clean {
    color: var(--text-secondary);
    font-size: 0.9rem;
    font-weight: 600;
}

.diff-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.78rem;
    background: rgba(240, 246, 255, 0.9);
}

.diff-badge--missing {
    color: var(--badge-missing);
    border: 1px solid rgba(255, 107, 107, 0.32);
    background: rgba(255, 107, 107, 0.14);
}

.diff-badge--extra {
    color: var(--badge-extra);
    border: 1px solid rgba(79, 139, 255, 0.35);
    background: rgba(79, 139, 255, 0.16);
}

.diff-badge--modified {
    color: var(--badge-modified);
    border: 1px solid rgba(246, 183, 60, 0.32);
    background: rgba(246, 183, 60, 0.18);
}

.page-image-columns {
    display: flex;
    flex-wrap: wrap;
    gap: 18px;
    margin-bottom: 18px;
}

.page-image-column {
    flex: 1 1 320px;
    background: #f6f8ff;
    border-radius: 18px;
    padding: 16px 16px 18px;
    border: 1px solid rgba(96, 109, 209, 0.12);
    box-shadow: inset 0 0 0 1px rgba(96, 109, 209, 0.07);
}

.page-image-column h3 {
    margin: 0 0 12px;
    font-size: 0.95rem;
    color: #1f2a64;
}

.page-image-column img {
    width: 100%;
    border-radius: 12px;
    border: 1px solid rgba(29, 78, 216, 0.22);
    box-shadow: 0 16px 40px rgba(15, 23, 42, 0.18);
}

.diff-detail-card {
    background: linear-gradient(160deg, rgba(238, 242, 255, 0.85), rgba(255, 255, 255, 0.94));
    border-radius: 18px;
    border: 1px solid rgba(165, 180, 252, 0.45);
    padding: 20px 22px;
    box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.12);
}

.diff-detail-card h3 {
    margin: 0 0 12px;
    font-size: 1rem;
    color: #1b2564;
}

.diff-detail-list {
    list-style: none;
    padding: 0;
    margin: 0;
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

.diff-tag--text {
    background: rgba(250, 204, 21, 0.28);
    color: #92400e;
}

.diff-tag--layout {
    background: rgba(74, 222, 128, 0.24);
    color: #166534;
}

.diff-tag--structure {
    background: rgba(248, 113, 113, 0.24);
    color: #7f1d1d;
}

.diff-detail-text {
    font-size: 0.9rem;
    color: #1e293b;
    line-height: 1.5;
}

.page-nav {
    display: flex;
    justify-content: space-between;
    margin-top: 22px;
}

.page-nav a {
    color: var(--accent);
    text-decoration: none;
    font-weight: 600;
    font-size: 0.9rem;
}

.page-nav a:hover {
    text-decoration: underline;
}

@media (max-width: 768px) {
    .hero {
        padding: 28px;
    }
    .page-header {
        flex-direction: column;
        align-items: flex-start;
    }
    .summary-card {
        padding: 24px 18px 22px 72px;
    }
}
</style>
"""


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
    allowed = []
    for ch in name:
        if ch.isalnum() or ch in ("_", "-", "."):
            allowed.append(ch)
        elif ch.isspace():
            allowed.append("_")
    return ''.join(allowed) or 'file'


def _diff_detail_items(page: PageDiff) -> List[str]:
    details: List[str] = []
    for diff in page.span_diffs:
        label = "Text"
        tag_class = "diff-tag diff-tag--text"
        desc = diff.detail or (diff.target_span.text if diff.target_span else "Text change detected")
        details.append(
            f"<li class='diff-detail-item'><span class='{tag_class}'>{label}</span><span class='diff-detail-text'>{html.escape(desc)}</span></li>"
        )
    for diff in page.layout_diffs:
        desc = diff.detail or "Layout change detected"
        details.append(
            f"<li class='diff-detail-item'><span class='diff-tag diff-tag--layout'>Layout</span><span class='diff-detail-text'>{html.escape(desc)}</span></li>"
        )
    for diff in page.structural_diffs:
        desc = diff.description or "Structural change detected"
        details.append(
            f"<li class='diff-detail-item'><span class='diff-tag diff-tag--structure'>Structure</span><span class='diff-detail-text'>{html.escape(desc)}</span></li>"
        )
    return details


def _build_download_sections(results: Sequence[ComparisonResult]) -> List[str]:
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

    nav_html = []
    if prev_anchor:
        nav_html.append(f"<a href='#{prev_anchor}'>&larr; Previous page</a>")
    else:
        nav_html.append("<span></span>")
    if next_anchor:
        nav_html.append(f"<a href='#{next_anchor}'>Next page &rarr;</a>")
    else:
        nav_html.append("<span></span>")

    return (
        f"<article id='{anchor}' class='page-section'>"
        "<div class='page-header'>"
        f"<h2>{html.escape(source_label)} &rarr; {html.escape(target_label)} &mdash; Page {page.page_number + 1}</h2>"
        f"<div class='page-meta'>{''.join(badges)}</div>"
        "</div>"
        f"{image_section}"
        f"{detail_html}"
        f"<div class='page-nav'><div>{nav_html[0]}</div><div>{nav_html[1]}</div></div>"
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

    for pair_index, result in enumerate(results):
        pair_prefix = f"pair{pair_index}"
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

    summary_cards = [
        f"<div class='summary-card' data-icon='pages'><span class='summary-label'>Total pages compared</span><span class='summary-value'>{total_pages}</span></div>",
        f"<div class='summary-card' data-icon='alerts'><span class='summary-label'>Pages with differences</span><span class='summary-value'>{pages_with_diffs}</span></div>",
        f"<div class='summary-card' data-icon='diff'><span class='summary-label'>Missing elements</span><span class='summary-value'>{aggregate_counts['missing']}</span></div>",
        f"<div class='summary-card' data-icon='delta'><span class='summary-label'>Extra elements</span><span class='summary-value'>{aggregate_counts['extra']}</span></div>",
        f"<div class='summary-card' data-icon='extra'><span class='summary-label'>Modified elements</span><span class='summary-value'>{aggregate_counts['modified']}</span></div>",
    ]

    legend_items = [
        f"<div class='legend-card'><span class='legend-swatch {css}'></span><span>{label}</span></div>"
        for label, css in COLOR_LEGEND
    ]

    download_cards = _build_download_sections(results)

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='utf-8'/>",
        f"<title>{html.escape(title)}</title>",
        REPORT_STYLES,
        "</head>",
        "<body class='report-body'>",
        "<div class='report-container'>",
        "<header class='hero'>",
        "<div class='hero-content'>",
        f"<p class='hero-title'>{html.escape(title)}</p>",
        "<p class='hero-subtitle'>High-fidelity side-by-side comparison across every page, with automated highlighting for missing, extra, and modified content so review teams can approve PDFs with confidence.</p>",
        "</div>",
        "<div class='hero-badge'>Automated QA</div>",
        "</header>",
        "<section>",
        "<div class='summary-grid'>",
        *summary_cards,
        "</div>",
        "</section>",
        "<section>",
        "<div class='legend-cards'>",
        *legend_items,
        "</div>",
        "</section>",
    ]

    if download_cards:
        html_parts.extend(
            [
                "<section>",
                "<div class='download-grid'>",
                *download_cards,
                "</div>",
                "</section>",
            ]
        )

    if nav_items:
        html_parts.extend(
            [
                "<section class='jump-nav'>",
                "<h2>Jump to page</h2>",
                "<ul class='nav-list'>",
                *nav_items,
                "</ul>",
                "</section>",
            ]
        )

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
