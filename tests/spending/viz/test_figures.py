"""Tests for the visualization-layer figure builders.

The builders consume analysis-output DataFrames (tidy/long) and return
Plotly figures. Tests assert on the figure's data (trace count, types,
x/y arrays, trace names) and its axis titles, never on rendered pixels.
"""

from typing import Any

import pandas as pd

from spending.viz import (
    by_category_per_month_bar,
    by_category_per_month_line,
    essential_per_month_bar,
    essential_per_month_line,
    total_per_month_bar,
    total_per_month_line,
)


def _totals(months: list[str], totals: list[float]) -> pd.DataFrame:
    """Build a total-per-month frame: columns ``month``, ``total``."""
    return pd.DataFrame(
        {
            "month": pd.to_datetime(months),
            "total": pd.Series(totals, dtype="float64"),
        }
    )


def _by_category(
    months: list[str], categories: list[str], totals: list[float]
) -> pd.DataFrame:
    """Build a by-category frame: columns ``month``, ``category``, ``total``."""
    return pd.DataFrame(
        {
            "month": pd.to_datetime(months),
            "category": pd.Series(categories, dtype="string"),
            "total": pd.Series(totals, dtype="float64"),
        }
    )


def _essential(
    months: list[str], essential: list[bool], totals: list[float]
) -> pd.DataFrame:
    """Build an essential frame: columns ``month``, ``essential``, ``total``."""
    return pd.DataFrame(
        {
            "month": pd.to_datetime(months),
            "essential": pd.Series(essential, dtype="bool"),
            "total": pd.Series(totals, dtype="float64"),
        }
    )


def _months(trace_x: Any) -> list[pd.Timestamp]:
    """Coerce a trace's x array back to a list of Timestamps for comparison."""
    return [pd.Timestamp(x) for x in trace_x]


# --- total_per_month -------------------------------------------------------


def test_total_line_is_a_single_scatter_over_the_months():
    """Tests that the total line builder makes one line trace of the totals."""
    fig = total_per_month_line(_totals(["2026-08-01", "2026-09-01"], [30.0, 50.0]))
    assert len(fig.data) == 1
    (trace,) = fig.data
    assert trace.type == "scatter"
    assert trace.mode == "lines"
    assert _months(trace.x) == [pd.Timestamp("2026-08-01"), pd.Timestamp("2026-09-01")]
    assert list(trace.y) == [30.0, 50.0]


def test_total_bar_is_a_single_bar_over_the_months():
    """Tests that the total bar builder makes one bar trace of the totals."""
    fig = total_per_month_bar(_totals(["2026-08-01", "2026-09-01"], [30.0, 50.0]))
    assert len(fig.data) == 1
    (trace,) = fig.data
    assert trace.type == "bar"
    assert _months(trace.x) == [pd.Timestamp("2026-08-01"), pd.Timestamp("2026-09-01")]
    assert list(trace.y) == [30.0, 50.0]


def test_total_figures_label_both_axes():
    """Tests that the total builders set readable x and y axis titles."""
    frame = _totals(["2026-08-01"], [30.0])
    for fig in (total_per_month_line(frame), total_per_month_bar(frame)):
        assert fig.layout.xaxis.title.text == "Month"
        assert fig.layout.yaxis.title.text == "Total spend"


# --- by_category_per_month -------------------------------------------------


def test_by_category_line_has_one_line_per_category():
    """Tests that each category becomes its own named line trace."""
    frame = _by_category(
        ["2026-08-01", "2026-08-01", "2026-09-01"],
        ["Food", "Rent", "Food"],
        [10.0, 20.0, 30.0],
    )
    fig = by_category_per_month_line(frame)
    assert {t.name for t in fig.data} == {"Food", "Rent"}
    assert all(t.type == "scatter" for t in fig.data)


def test_by_category_line_pads_missing_months_with_zero():
    """Tests that a category's gap months are filled with zero by default."""
    frame = _by_category(
        ["2026-07-01", "2026-08-01", "2026-07-01"],
        ["Food", "Food", "Rent"],
        [10.0, 20.0, 5.0],
    )
    fig = by_category_per_month_line(frame)
    (rent,) = [t for t in fig.data if t.name == "Rent"]
    assert _months(rent.x) == [pd.Timestamp("2026-07-01"), pd.Timestamp("2026-08-01")]
    assert list(rent.y) == [5.0, 0.0]


def test_by_category_line_padding_can_be_disabled():
    """Tests that pad_values=False leaves a category's gaps unfilled."""
    frame = _by_category(
        ["2026-07-01", "2026-08-01", "2026-07-01"],
        ["Food", "Food", "Rent"],
        [10.0, 20.0, 5.0],
    )
    fig = by_category_per_month_line(frame, pad_values=False)
    (rent,) = [t for t in fig.data if t.name == "Rent"]
    assert _months(rent.x) == [pd.Timestamp("2026-07-01")]
    assert list(rent.y) == [5.0]


def test_by_category_bar_is_stacked_with_one_trace_per_category():
    """Tests that categories stack (relative barmode) as one bar per category."""
    frame = _by_category(
        ["2026-08-01", "2026-08-01", "2026-09-01"],
        ["Food", "Rent", "Food"],
        [10.0, 20.0, 30.0],
    )
    fig = by_category_per_month_bar(frame)
    assert {t.name for t in fig.data} == {"Food", "Rent"}
    assert all(t.type == "bar" for t in fig.data)
    assert fig.layout.barmode == "relative"


def test_by_category_trace_carries_only_its_category_values():
    """Tests that a category's trace holds that category's months and totals."""
    frame = _by_category(
        ["2026-08-01", "2026-09-01"],
        ["Food", "Food"],
        [10.0, 30.0],
    )
    fig = by_category_per_month_bar(frame)
    (food,) = [t for t in fig.data if t.name == "Food"]
    assert _months(food.x) == [pd.Timestamp("2026-08-01"), pd.Timestamp("2026-09-01")]
    assert list(food.y) == [10.0, 30.0]


def test_by_category_figures_label_axes_and_legend():
    """Tests readable axis titles and a Category legend title."""
    frame = _by_category(["2026-08-01"], ["Food"], [10.0])
    for fig in (by_category_per_month_line(frame), by_category_per_month_bar(frame)):
        assert fig.layout.xaxis.title.text == "Month"
        assert fig.layout.yaxis.title.text == "Total spend"
        assert fig.layout.legend.title.text == "Category"


# --- essential_per_month ---------------------------------------------------


def test_essential_line_names_traces_essential_and_non_essential():
    """Tests that the essential flag maps to readable line names."""
    frame = _essential(
        ["2026-08-01", "2026-08-01"],
        [False, True],
        [20.0, 10.0],
    )
    fig = essential_per_month_line(frame)
    assert [t.name for t in fig.data] == ["Non-essential", "Essential"]
    assert all(t.type == "scatter" for t in fig.data)


def test_essential_line_pads_missing_months_with_zero():
    """Tests that a group's gap months are filled with zero by default."""
    frame = _essential(
        ["2026-07-01", "2026-08-01", "2026-07-01"],
        [True, True, False],
        [10.0, 20.0, 5.0],
    )
    fig = essential_per_month_line(frame)
    (non_essential,) = [t for t in fig.data if t.name == "Non-essential"]
    assert _months(non_essential.x) == [
        pd.Timestamp("2026-07-01"),
        pd.Timestamp("2026-08-01"),
    ]
    assert list(non_essential.y) == [5.0, 0.0]


def test_essential_line_padding_can_be_disabled():
    """Tests that pad_values=False leaves a group's gaps unfilled."""
    frame = _essential(
        ["2026-07-01", "2026-08-01", "2026-07-01"],
        [True, True, False],
        [10.0, 20.0, 5.0],
    )
    fig = essential_per_month_line(frame, pad_values=False)
    (non_essential,) = [t for t in fig.data if t.name == "Non-essential"]
    assert _months(non_essential.x) == [pd.Timestamp("2026-07-01")]
    assert list(non_essential.y) == [5.0]


def test_essential_bar_is_stacked_and_named_readably():
    """Tests that essential bars stack and carry readable names."""
    frame = _essential(
        ["2026-08-01", "2026-08-01"],
        [False, True],
        [20.0, 10.0],
    )
    fig = essential_per_month_bar(frame)
    assert [t.name for t in fig.data] == ["Non-essential", "Essential"]
    assert all(t.type == "bar" for t in fig.data)
    assert fig.layout.barmode == "relative"


def test_essential_figures_label_axes_and_legend():
    """Tests readable axis titles and an Essential legend title."""
    frame = _essential(["2026-08-01"], [True], [10.0])
    for fig in (essential_per_month_line(frame), essential_per_month_bar(frame)):
        assert fig.layout.xaxis.title.text == "Month"
        assert fig.layout.yaxis.title.text == "Total spend"
        assert fig.layout.legend.title.text == "Essential"


# --- y-axis baseline -------------------------------------------------------


def test_line_builders_pin_the_y_axis_to_include_zero():
    """Tests that every line builder forces the y-axis range to include zero."""
    totals = _totals(["2026-08-01"], [400.0])
    by_category = _by_category(["2026-08-01"], ["Food"], [400.0])
    essential = _essential(["2026-08-01"], [True], [400.0])
    for fig in (
        total_per_month_line(totals),
        by_category_per_month_line(by_category),
        essential_per_month_line(essential),
    ):
        assert fig.layout.yaxis.rangemode == "tozero"


# --- empty data ------------------------------------------------------------


def test_single_series_builders_handle_empty_data():
    """Tests that total builders return a valid empty figure, no exception."""
    empty = _totals([], [])
    for fig in (total_per_month_line(empty), total_per_month_bar(empty)):
        (trace,) = fig.data
        assert list(trace.x) == []
        assert list(trace.y) == []


def test_multi_series_builders_handle_empty_data():
    """Tests that grouped builders return an empty, traceless figure."""
    empty_cat = _by_category([], [], [])
    empty_ess = _essential([], [], [])
    assert by_category_per_month_line(empty_cat).data == ()
    assert by_category_per_month_bar(empty_cat).data == ()
    assert essential_per_month_line(empty_ess).data == ()
    assert essential_per_month_bar(empty_ess).data == ()
