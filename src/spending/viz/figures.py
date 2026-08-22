"""Plotly figure builders, one line and one bar variant per metric.

Each builder takes an analysis-output DataFrame (tidy/long) and returns a
Plotly ``Figure``. The builders are framework-agnostic: they never import a
UI framework, and the ``has_essential`` gate lives in the caller, which
simply does not invoke the essential builders when the flag is False.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

_LABELS = {
    "month": "Month",
    "total": "Total spend",
    "category": "Category",
    "essential": "Essential",
}


def total_per_month_line(totals: pd.DataFrame) -> go.Figure:
    """Build a line chart of total spend per month.

    Args:
        totals: A frame with columns ``month`` and ``total``.

    Returns:
        A single-line Plotly figure over the months, with a y-axis that
        always includes zero so a low month does not read as no spend.
    """
    fig = px.line(totals, x="month", y="total", labels=_LABELS)
    fig.update_yaxes(rangemode="tozero")
    return fig


def total_per_month_bar(totals: pd.DataFrame) -> go.Figure:
    """Build a bar chart of total spend per month.

    Args:
        totals: A frame with columns ``month`` and ``total``.

    Returns:
        A single-series bar Plotly figure over the months.
    """
    return px.bar(totals, x="month", y="total", labels=_LABELS)


def by_category_per_month_line(
    by_category: pd.DataFrame, *, pad_values: bool = True
) -> go.Figure:
    """Build a line chart of spend per month, one line per category.

    Args:
        by_category: A frame with columns ``month``, ``category``, ``total``.
        pad_values: When True (default), months in which a category has no
            entry are filled with a zero total, so each line spans the full
            timeline instead of ending when that category's spend does. When
            False, only the observed points are plotted (lines stop at a
            category's last month).

    Returns:
        A Plotly figure with one line trace per category, with a y-axis that
        always includes zero so a low month does not read as no spend.
    """
    frame = _pad_missing_months(by_category, "category") if pad_values else by_category
    fig = px.line(frame, x="month", y="total", color="category", labels=_LABELS)
    fig.update_yaxes(rangemode="tozero")
    return fig


def by_category_per_month_bar(by_category: pd.DataFrame) -> go.Figure:
    """Build a stacked bar chart of spend per month, split by category.

    Args:
        by_category: A frame with columns ``month``, ``category``, ``total``.

    Returns:
        A stacked (relative) Plotly bar figure, one bar trace per category.
    """
    return px.bar(by_category, x="month", y="total", color="category", labels=_LABELS)


def essential_per_month_line(
    essential: pd.DataFrame, *, pad_values: bool = True
) -> go.Figure:
    """Build a line chart of essential vs non-essential spend per month.

    Args:
        essential: A frame with columns ``month``, ``essential`` (bool),
            ``total``.
        pad_values: When True (default), a month in which one group has no
            entry is filled with a zero total, so both lines span the full
            timeline instead of gapping. When False, only the observed points
            are plotted.

    Returns:
        A Plotly figure with an "Essential" and a "Non-essential" line, with
        a y-axis that always includes zero so a low month does not read as no
        spend.
    """
    labeled = _with_essential_labels(essential)
    frame = _pad_missing_months(labeled, "essential") if pad_values else labeled
    fig = px.line(frame, x="month", y="total", color="essential", labels=_LABELS)
    fig.update_yaxes(rangemode="tozero")
    return fig


def essential_per_month_bar(essential: pd.DataFrame) -> go.Figure:
    """Build a stacked bar chart of essential vs non-essential spend per month.

    Args:
        essential: A frame with columns ``month``, ``essential`` (bool),
            ``total``.

    Returns:
        A stacked (relative) Plotly bar figure with an "Essential" and a
        "Non-essential" trace.
    """
    return px.bar(
        _with_essential_labels(essential),
        x="month",
        y="total",
        color="essential",
        labels=_LABELS,
    )


def _with_essential_labels(essential: pd.DataFrame) -> pd.DataFrame:
    """Map the boolean ``essential`` column to readable trace labels."""
    labels = essential["essential"].map({True: "Essential", False: "Non-essential"})
    return essential.assign(essential=labels)


def _pad_missing_months(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Fill a zero total for every month a group has no entry.

    A line chart otherwise skips the months where a series has no row, making
    that category or group look like it stops mid-timeline instead of dropping
    to zero spend. Pivoting to a full month-by-group grid, filling the gaps
    with zero, and melting back to long makes each line span the whole range.

    ``pivot`` sorts the group columns alphabetically; reindexing them back to
    their first-appearance order keeps the padded line's trace order matching
    the unpadded bar chart's.
    """
    order = df[group_col].drop_duplicates().tolist()
    return (
        df.pivot(index="month", columns=group_col, values="total")
        .reindex(columns=order)
        .fillna(0.0)
        .reset_index()
        .melt(id_vars="month", var_name=group_col, value_name="total")
    )
