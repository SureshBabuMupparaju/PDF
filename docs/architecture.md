# Automated PDF Form Validation and Comparison System

## High-Level Flow
1. **Input capture** via Streamlit UI gathers a golden PDF and one or more generated PDFs, along with comparison options (LLM filtering, thresholds, page range, etc.).
2. **Pre-processing** loads PDFs with PyMuPDF, extracting structured page content (spans with bounding boxes, font metadata, and reading order).
3. **Variable-field filtering** tags spans that likely contain user-specific data via heuristics and (optionally) LLM guidance, so they are ignored during diffs.
4. **Comparison engine** diff-checks the remaining spans, classifying differences as textual, layout, or structural, and records bounding boxes for later annotation.
5. **Annotation & visualization** draws colored overlays on the target PDF pages and renders PNG previews that highlight the detected issues.
6. **Reporting layer** aggregates page-level diffs into pass/fail verdicts, detail metrics, and row-wise descriptions for use in the UI and exports.
7. **HTML rendering & delivery** produces side-by-side page views with color-coded highlights and builds a downloadable HTML report with navigation and legend.
8. **Streamlit presentation** displays the left/right page view, diff summaries, and download links for annotated and HTML artifacts.

## Key Components
- `app/models.py` - Typed dataclasses for spans, diffs, comparison results, and report rows.
- `app/pdf_extractor.py` - Helpers built on PyMuPDF for loading PDFs and extracting structured text spans with geometric metadata.
- `app/llm_filter.py` - Variable-data filtering strategies (regex heuristics + optional LLM call via OpenAI-compatible client).
- `app/diff_engine.py` - Core comparison logic that aligns spans with `difflib`, marks missing/extra/modified spans, and produces `PageDiff` objects.
- `app/html_report.py` - Utilities for building side-by-side HTML snippets, global CSS, embedded page imagery, and the downloadable HTML report with navigation, legend, and inline download links.
- `app/visualization.py` - Annotation utilities that build annotated PDFs (golden + target) and paired PNG previews with colored bounding boxes.
- `app/reporter.py` - Aggregation helpers to create pass/fail status, per-page metrics, and row-wise detail tables for Streamlit.
- `app/streamlit_app.py` - Streamlit UI wiring everything together with upload widgets, option toggles, page-range inputs, and rendered outputs.

## External Dependencies
- **PyMuPDF (`pymupdf`)** for PDF parsing, text extraction, and bitmap rendering.
- **Pillow** for image post-processing (already included in the environment).
- **pandas** for report table generation.
- **streamlit** for the interactive UI.
- **openai** (or compatible SDK) only when LLM-based filtering is enabled; otherwise the logic falls back to heuristics.

## Extensibility Notes
- The `VariableFieldFilter` exposes a strategy interface, making it easy to plug in custom rules or different LLM providers.
- `PDFComparator` accepts tuning thresholds and page ranges, enabling calibration for different insurers/templates without touching the UI.
- The HTML report utilities centralize color palettes and layout so future branding/layout tweaks remain isolated.
- The reporting layer emits plain dictionaries/dataframes so additional exporters (CSV, JSON, email) can be added later.
- Visualization utilities centralize color and styling constants, simplifying future branding/layout tweaks.

