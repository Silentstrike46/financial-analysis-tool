"""End-to-end integration tests across the presentation pipeline.

Two layer-spans are exercised separately so a failure localizes:

* ``analysis -> viz``: hand-built ``SpendingData`` through the metric
  functions into the figure builders.
* ``ingest -> analysis -> viz``: a real multi-sheet workbook read from disk,
  then analyzed and charted.

Both use a combined realistic case (multiple months x multiple categories,
with a refund and an essential mix) that the analysis unit tests left out.
"""

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from spending.analysis.metrics import (
    by_category_per_month,
    essential_per_month,
    total_per_month,
)
from spending.ingest import import_file
from spending.models import SheetStatus, SpendingData
from spending.viz import (
    by_category_per_month_bar,
    by_category_per_month_line,
    essential_per_month_bar,
    total_per_month_bar,
)
from tests.helpers import spending_data, write_xlsx

_JUL = pd.Timestamp("2026-07-01")
_AUG = pd.Timestamp("2026-08-01")
_SEP = pd.Timestamp("2026-09-01")


def _multi_month_data() -> SpendingData:
    """Three months, three categories, a refund, and an essential mix."""
    return spending_data(
        dates=[
            "2026-07-05",
            "2026-07-20",
            "2026-08-03",
            "2026-08-15",
            "2026-08-28",
            "2026-09-10",
        ],
        prices=[100.0, 50.0, 120.0, 30.0, -20.0, 80.0],
        categories=["Rent", "Food", "Rent", "Food", "Food", "Transport"],
        essential=[True, True, True, True, True, False],
    )


def _trace_months(trace: Any) -> list[pd.Timestamp]:
    """Coerce a trace's x array back to a list of Timestamps."""
    return [pd.Timestamp(x) for x in trace.x]


# --- analysis -> viz -------------------------------------------------------


def test_analysis_to_viz_total_reflects_every_month():
    """Tests that per-month totals flow into a single ordered bar trace."""
    fig = total_per_month_bar(total_per_month(_multi_month_data()))
    (trace,) = fig.data
    assert _trace_months(trace) == [_JUL, _AUG, _SEP]
    assert list(trace.y) == pytest.approx([150.0, 130.0, 80.0])


def test_analysis_to_viz_by_category_reflects_every_category():
    """Tests that each category becomes its own line across the months."""
    fig = by_category_per_month_line(by_category_per_month(_multi_month_data()))
    assert {t.name for t in fig.data} == {"Rent", "Food", "Transport"}


def test_analysis_to_viz_essential_splits_into_two_stacked_series():
    """Tests that the essential split reaches viz as two stacked, named bars."""
    fig = essential_per_month_bar(essential_per_month(_multi_month_data()))
    assert {t.name for t in fig.data} == {"Essential", "Non-essential"}
    assert fig.layout.barmode == "relative"


# --- ingest -> analysis -> viz ---------------------------------------------


def _sheet(
    dates: list[str],
    prices: list[float],
    categories: list[str],
    essential: list[str],
) -> pd.DataFrame:
    """Build a real-header expense sheet with varied essential spellings."""
    return pd.DataFrame(
        {
            "Date": dates,
            "Price": prices,
            "Category": categories,
            "Item": ["x"] * len(dates),
            "Essential": essential,
        }
    )


def test_ingest_to_viz_full_pipeline(tmp_path: Path):
    """Tests a multi-sheet workbook flowing from disk through to figures."""
    path = write_xlsx(
        tmp_path / "book.xlsx",
        {
            "H1 2026": _sheet(
                ["2026-07-05", "2026-07-20", "2026-08-03"],
                [100.0, 50.0, 120.0],
                ["Rent", "Food", "Rent"],
                ["TRUE", "yes", "T"],
            ),
            "H2 2026": _sheet(
                ["2026-08-15", "2026-08-28", "2026-09-10"],
                [30.0, -20.0, 80.0],
                ["Food", "Food", "Transport"],
                ["yes", "1", "no"],
            ),
            "Summary": pd.DataFrame({"Month": ["Aug"], "Total": [30.0]}),
        },
    )

    data, report = import_file(path)

    assert data.has_essential is True
    skipped = {
        s.name
        for f in report.files
        for s in f.sheets
        if s.status is SheetStatus.SKIPPED
    }
    assert "Summary" in skipped

    total_fig = total_per_month_bar(total_per_month(data))
    (trace,) = total_fig.data
    assert _trace_months(trace) == [_JUL, _AUG, _SEP]
    assert list(trace.y) == pytest.approx([150.0, 130.0, 80.0])

    cat_fig = by_category_per_month_bar(by_category_per_month(data))
    assert {t.name for t in cat_fig.data} == {"Rent", "Food", "Transport"}

    ess_fig = essential_per_month_bar(essential_per_month(data))
    assert {t.name for t in ess_fig.data} == {"Essential", "Non-essential"}
