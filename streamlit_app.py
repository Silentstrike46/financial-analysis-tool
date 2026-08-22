"""Streamlit UI shell for the personal spending analysis tool.

Thin glue: it discovers data files, caches the import at the ingest boundary,
surfaces the import report, and lays out the figure builders. It holds no
analysis or chart-construction logic - it calls ``analysis`` and ``viz`` and
renders what they return.
"""

from pathlib import Path

import streamlit as st

from spending.analysis.metrics import (
    by_category_per_month,
    essential_per_month,
    total_per_month,
)
from spending.ingest import import_files
from spending.models import ImportReport, SheetStatus, SpendingData
from spending.viz import (
    by_category_per_month_bar,
    by_category_per_month_line,
    essential_per_month_bar,
    essential_per_month_line,
    total_per_month_bar,
    total_per_month_line,
)

DATA_DIR = Path("data")
# Mirrors the file types spending.ingest.reader can read (.csv + Excel).
_SUFFIXES = {".csv", ".xlsx", ".xlsm"}


@st.cache_data
def _load(
    file_keys: tuple[tuple[str, float], ...],
) -> tuple[SpendingData, ImportReport]:
    """Import the selected files once and cache the result.

    Keyed on ``(path, mtime)`` per file, so the import re-runs only when the
    selection changes or a selected file is modified on disk. ``import_files``
    itself stays cache-agnostic; this wrapper is the only UI-owned piece.
    """
    return import_files([Path(path) for path, _mtime in file_keys])


def _discover_files() -> list[Path]:
    """List importable files in ``data/``, sorted by name."""
    if not DATA_DIR.is_dir():
        return []
    return sorted(p for p in DATA_DIR.iterdir() if p.suffix.lower() in _SUFFIXES)


def _render_report(report: ImportReport) -> None:
    """Surface skipped sheets, dropped-row counts, and warnings."""
    with st.expander("Import summary"):
        for warning in report.warnings:
            st.warning(warning)
        for file_report in report.files:
            st.markdown(f"**{file_report.path}**")
            if file_report.error is not None:
                st.error(file_report.error)
                continue
            for sheet in file_report.sheets:
                if sheet.status is SheetStatus.IMPORTED:
                    st.write(
                        f"- {sheet.name}: imported {sheet.rows_imported} rows, "
                        f"dropped {sheet.rows_dropped}"
                    )
                else:
                    st.write(f"- {sheet.name}: skipped ({sheet.reason})")


def _section(title: str, bar_fig: object, line_fig: object) -> None:
    """Render one metric section: bar chart beside its line chart."""
    st.subheader(title)
    bar_col, line_col = st.columns(2)
    bar_col.plotly_chart(bar_fig, width="stretch")
    line_col.plotly_chart(line_fig, width="stretch")


def main() -> None:
    """Compose the layers and lay out the dashboard."""
    st.set_page_config(page_title="Spending Analysis", layout="wide")
    st.title("Personal Spending Analysis")

    files = _discover_files()
    if not files:
        st.info("No files available in data/.")
        return

    selected = st.sidebar.multiselect(
        "Data files",
        options=files,
        default=files,
        format_func=lambda path: path.name,
    )
    if not selected:
        st.info("Select one or more files to analyze.")
        return

    file_keys = tuple((str(path), path.stat().st_mtime) for path in selected)
    data, report = _load(file_keys)

    _render_report(report)

    if data.is_empty:
        st.info("No valid spending data found in the selected files.")
        return

    totals = total_per_month(data)
    _section(
        "Monthly spend",
        total_per_month_bar(totals),
        total_per_month_line(totals),
    )

    by_category = by_category_per_month(data)
    _section(
        "Spend by category",
        by_category_per_month_bar(by_category),
        by_category_per_month_line(by_category),
    )

    if data.has_essential:
        essential = essential_per_month(data)
        _section(
            "Essential vs non-essential",
            essential_per_month_bar(essential),
            essential_per_month_line(essential),
        )


main()
