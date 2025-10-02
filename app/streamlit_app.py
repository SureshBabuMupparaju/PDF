from __future__ import annotations

import base64
from typing import List, Optional

import fitz
import pandas as pd
import streamlit as st

try:  # pragma: no cover
    from .diff_engine import ComparatorSettings, PDFComparator
    from .html_report import STREAMLIT_STYLES, build_page_pair_html, generate_html_report
    from .llm_filter import VariableFieldFilter
    from .models import ComparisonResult
    from .reporter import build_detail_rows, build_page_table, build_summary_table
except ImportError:  # pragma: no cover
    from diff_engine import ComparatorSettings, PDFComparator
    from html_report import STREAMLIT_STYLES, build_page_pair_html, generate_html_report
    from llm_filter import VariableFieldFilter
    from models import ComparisonResult
    from reporter import build_detail_rows, build_page_table, build_summary_table


def _bytes_to_download_link(data: bytes, filename: str, label: str) -> None:
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">{label}</a>'
    st.markdown(href, unsafe_allow_html=True)


def _get_page_count(pdf_bytes: Optional[bytes]) -> Optional[int]:
    if not pdf_bytes:
        return None
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            return doc.page_count
    except Exception:
        return None


def _render_image_columns(result: ComparisonResult) -> None:
    if not result.pages:
        st.info("No pages compared within the selected range.")
        return

    if not (result.page_previews_source or result.page_previews_target):
        st.info("Image previews are unavailable for this comparison.")
        return

    st.markdown("**Page Comparisons (Images)**")
    for page in result.pages:
        cols = st.columns(2)
        source_img = result.page_previews_source.get(page.page_number)
        target_img = result.page_previews_target.get(page.page_number)
        cols[0].markdown(f"*{result.source_name} – Page {page.page_number + 1}*")
        if source_img:
            cols[0].image(source_img, use_column_width=True)
        else:
            cols[0].info("Preview unavailable.")
        cols[1].markdown(f"*{result.target_name} – Page {page.page_number + 1}*")
        if target_img:
            cols[1].image(target_img, use_column_width=True)
        else:
            cols[1].info("Preview unavailable.")

    st.caption(
        "Red = missing content, Blue = extra content, Yellow = modified content."
    )


def run_app() -> None:
    st.set_page_config(page_title="Automated PDF Comparator", layout="wide")
    st.title("Automated PDF Form Validation & Comparison")
    st.write(
        "Upload a golden source PDF and one or more generated PDFs to automatically identify "
        "textual, layout, and structural differences. Optionally ignore variable user fields "
        "with heuristic or LLM-driven filtering."
    )

    source_file = st.file_uploader("Upload Golden Source PDF", type=["pdf"])
    target_files = st.file_uploader(
        "Upload Target PDF(s)", type=["pdf"], accept_multiple_files=True
    )

    source_bytes_preview: Optional[bytes] = source_file.getvalue() if source_file else None
    page_count = _get_page_count(source_bytes_preview)

    with st.sidebar:
        st.header("Comparison Options")
        layout_tol = st.slider("Layout tolerance (points)", 1.0, 20.0, 6.0, 0.5)
        size_tol = st.slider("Font size tolerance", 0.1, 3.0, 0.75, 0.05)
        enable_visuals = st.checkbox("Generate annotated previews", value=True)
        enable_llm = st.checkbox("Use LLM for variable fields", value=False)
        llm_model = st.text_input("LLM model", value="gpt-4o-mini")
        llm_api_key = st.text_input("LLM API key", type="password")

        max_pages = page_count or 999
        default_end = page_count or 1
        start_page = st.number_input(
            "Start page",
            min_value=1,
            max_value=max_pages,
            value=1,
            step=1,
            format="%d",
        )
        end_page = st.number_input(
            "End page",
            min_value=1,
            max_value=max_pages,
            value=default_end,
            step=1,
            format="%d",
        )
        if page_count:
            st.caption(f"Detected {page_count} page(s) in the golden PDF.")

    if not source_file or not target_files:
        st.info("Provide a source PDF and at least one target PDF to begin.")
        return

    if start_page > end_page:
        st.warning("Start page is greater than end page; the values will be swapped for comparison.")

    if st.button("Run comparison"):
        with st.spinner("Analyzing PDFs..."):
            source_bytes = source_file.getvalue()
            variable_filter = VariableFieldFilter(
                enable_llm=enable_llm,
                model=llm_model,
                api_key=llm_api_key or None,
            )
            comparator = PDFComparator(
                settings=ComparatorSettings(
                    layout_tolerance=layout_tol,
                    size_tolerance=size_tol,
                    enable_visuals=enable_visuals,
                    start_page=int(min(start_page, end_page)),
                    end_page=int(max(start_page, end_page)),
                ),
                variable_filter=variable_filter,
            )
            results: List[ComparisonResult] = []
            for target_file in target_files:
                target_bytes = target_file.getvalue()
                result = comparator.compare(
                    source=source_bytes,
                    target=target_bytes,
                    source_name=source_file.name,
                    target_name=target_file.name,
                )
                results.append(result)

        if not results:
            st.warning("No target PDFs were processed.")
            return

        summary_df = build_summary_table(results)
        st.subheader("Summary Report")
        st.dataframe(summary_df, use_container_width=True)

        html_report = generate_html_report(results)
        _bytes_to_download_link(
            html_report.encode("utf-8"),
            filename="pdf_comparison_report.html",
            label="Download HTML report",
        )

        st.markdown(STREAMLIT_STYLES, unsafe_allow_html=True)

        for result in results:
            st.markdown("---")
            header = f"Results for {result.target_name} (Status: {result.status.upper()})"
            st.subheader(header)

            page_df = build_page_table(result)
            if not page_df.empty:
                st.dataframe(page_df, use_container_width=True)

            detail_rows = build_detail_rows(result)
            if detail_rows:
                detail_df = pd.DataFrame(
                    [
                        {
                            "Pair": row.pair_label,
                            "Page": row.page_number,
                            "Type": row.diff_type.value,
                            "Description": row.description,
                            "Preview Ref": row.preview_ref,
                        }
                        for row in detail_rows
                    ]
                )
                st.markdown("**Row-wise Differences**")
                st.dataframe(detail_df, use_container_width=True)
            else:
                st.success("No differences detected on any page.")

            if result.source_annotated_pdf:
                _bytes_to_download_link(
                    result.source_annotated_pdf,
                    filename=f"highlighted_{result.source_name}",
                    label="Download highlighted golden PDF",
                )

            if result.annotated_pdf:
                _bytes_to_download_link(
                    result.annotated_pdf,
                    filename=f"highlighted_{result.target_name}",
                    label="Download highlighted target PDF",
                )

            _render_image_columns(result)

            if result.pages:
                st.markdown("**Page Comparisons (Text)**")
                for page in result.pages:
                    html_snippet = build_page_pair_html(page, result.source_name, result.target_name)
                    st.markdown(html_snippet, unsafe_allow_html=True)
            if result.notes:
                st.info("\n".join(result.notes))


if __name__ == "__main__":
    run_app()
