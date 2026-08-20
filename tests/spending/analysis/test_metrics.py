"""Tests for the analysis-layer metric functions."""

import pandas as pd
import pytest

from spending.analysis.metrics import (
    by_category_per_month,
    essential_per_month,
    total_per_month,
)
from tests.helpers import spending_data


def test_prices_in_one_month_sum_into_a_single_row():
    """Tests that same-month rows collapse into one total row."""
    data = spending_data(
        dates=["2026-08-01", "2026-08-20", "2026-08-31"],
        prices=[10.0, 20.0, 5.0],
        categories=["Food", "Rent", "Food"],
    )
    result = total_per_month(data)
    assert result["total"].tolist() == [35.0]


def test_separate_months_become_separate_rows_in_date_order():
    """Tests that each month gets its own row, ordered chronologically."""
    data = spending_data(
        dates=["2026-09-05", "2026-07-10", "2026-08-01"],
        prices=[30.0, 10.0, 20.0],
        categories=["Food", "Food", "Food"],
    )
    result = total_per_month(data)
    assert result["month"].tolist() == [
        pd.Timestamp("2026-07-01"),
        pd.Timestamp("2026-08-01"),
        pd.Timestamp("2026-09-01"),
    ]
    assert result["total"].tolist() == [10.0, 20.0, 30.0]


def test_refunds_net_within_a_months_total():
    """Tests that a negative price nets against spend in the same month."""
    data = spending_data(
        dates=["2026-08-01", "2026-08-15"],
        prices=[50.0, -20.0],
        categories=["Food", "Food"],
    )
    result = total_per_month(data)
    assert result["total"].tolist() == [30.0]


def test_decimal_prices_sum_to_the_expected_cent_total():
    """Tests that fractional cent prices sum correctly, not truncated."""
    data = spending_data(
        dates=["2026-08-01", "2026-08-02", "2026-08-03"],
        prices=[10.99, 5.00, 3.50],
        categories=["Food", "Food", "Food"],
    )
    result = total_per_month(data)
    assert result["total"].tolist() == pytest.approx([19.49])


def test_month_is_a_month_start_timestamp():
    """Tests that the month key is a Timestamp on the first of the month."""
    data = spending_data(
        dates=["2026-08-15"],
        prices=[10.0],
        categories=["Food"],
    )
    result = total_per_month(data)
    assert result["month"].tolist() == [pd.Timestamp("2026-08-01")]
    assert pd.api.types.is_datetime64_any_dtype(result["month"])


def test_empty_data_yields_an_empty_framed_result():
    """Tests that empty input returns an empty, correctly typed frame."""
    data = spending_data(dates=[], prices=[], categories=[])
    result = total_per_month(data)
    assert list(result.columns) == ["month", "total"]
    assert len(result) == 0
    assert pd.api.types.is_datetime64_any_dtype(result["month"])
    assert result["total"].dtype == "float64"


def test_a_month_splits_into_one_row_per_category():
    """Tests that categories in a month each get their own total row."""
    data = spending_data(
        dates=["2026-08-01", "2026-08-02"],
        prices=[10.0, 20.0],
        categories=["Food", "Rent"],
    )
    result = by_category_per_month(data)
    assert result["category"].tolist() == ["Food", "Rent"]
    assert result["total"].tolist() == [10.0, 20.0]


def test_same_category_in_one_month_sums_together():
    """Tests that repeated categories within a month collapse to one row."""
    data = spending_data(
        dates=["2026-08-01", "2026-08-20"],
        prices=[10.0, 5.0],
        categories=["Food", "Food"],
    )
    result = by_category_per_month(data)
    assert result["category"].tolist() == ["Food"]
    assert result["total"].tolist() == [15.0]


def test_same_category_across_months_stays_separate():
    """Tests that a category is summed per month, not across months."""
    data = spending_data(
        dates=["2026-08-01", "2026-09-01"],
        prices=[10.0, 20.0],
        categories=["Food", "Food"],
    )
    result = by_category_per_month(data)
    assert result["month"].tolist() == [
        pd.Timestamp("2026-08-01"),
        pd.Timestamp("2026-09-01"),
    ]
    assert result["total"].tolist() == [10.0, 20.0]


def test_category_total_can_go_negative_from_refunds():
    """Tests that refunds exceeding spend leave a negative category total."""
    data = spending_data(
        dates=["2026-08-01", "2026-08-02"],
        prices=[30.0, -50.0],
        categories=["Food", "Food"],
    )
    result = by_category_per_month(data)
    assert result["total"].tolist() == [-20.0]


def test_category_totals_sum_mixed_decimal_prices():
    """Tests that mixed decimal and whole prices sum within a category."""
    data = spending_data(
        dates=["2026-08-01", "2026-08-02", "2026-08-03"],
        prices=[10.99, 5.00, 3.50],
        categories=["Food", "Food", "Food"],
    )
    result = by_category_per_month(data)
    assert result["total"].tolist() == pytest.approx([19.49])


def test_by_category_empty_data_yields_an_empty_framed_result():
    """Tests that empty input returns an empty, correctly typed frame."""
    data = spending_data(dates=[], prices=[], categories=[])
    result = by_category_per_month(data)
    assert list(result.columns) == ["month", "category", "total"]
    assert len(result) == 0
    assert pd.api.types.is_datetime64_any_dtype(result["month"])
    assert result["total"].dtype == "float64"


def test_a_month_splits_into_essential_and_non_essential_rows():
    """Tests that a month splits by the essential flag into two rows."""
    data = spending_data(
        dates=["2026-08-01", "2026-08-02"],
        prices=[10.0, 20.0],
        categories=["Food", "Rent"],
        essential=[True, False],
    )
    result = essential_per_month(data)
    assert result["essential"].tolist() == [False, True]
    assert result["total"].tolist() == [20.0, 10.0]


def test_essential_groups_sum_within_a_month():
    """Tests that spend sums within each essential group of a month."""
    data = spending_data(
        dates=["2026-08-01", "2026-08-02", "2026-08-03"],
        prices=[10.0, 5.0, 20.0],
        categories=["Food", "Food", "Rent"],
        essential=[True, True, False],
    )
    result = essential_per_month(data)
    assert result["essential"].tolist() == [False, True]
    assert result["total"].tolist() == [20.0, 15.0]


def test_essential_per_month_raises_without_essential_data():
    """Tests that calling on data lacking essential raises ValueError."""
    data = spending_data(
        dates=["2026-08-01"],
        prices=[10.0],
        categories=["Food"],
    )
    with pytest.raises(ValueError):
        essential_per_month(data)


def test_essential_totals_sum_mixed_decimal_prices():
    """Tests that mixed decimal and whole prices sum within a group."""
    data = spending_data(
        dates=["2026-08-01", "2026-08-02", "2026-08-03"],
        prices=[10.99, 5.00, 3.50],
        categories=["Food", "Food", "Food"],
        essential=[True, True, True],
    )
    result = essential_per_month(data)
    assert result["total"].tolist() == pytest.approx([19.49])


def test_essential_empty_data_yields_an_empty_framed_result():
    """Tests that empty essential-enabled input returns an empty frame."""
    data = spending_data(dates=[], prices=[], categories=[], essential=[])
    result = essential_per_month(data)
    assert list(result.columns) == ["month", "essential", "total"]
    assert len(result) == 0
    assert pd.api.types.is_datetime64_any_dtype(result["month"])
    assert result["total"].dtype == "float64"
