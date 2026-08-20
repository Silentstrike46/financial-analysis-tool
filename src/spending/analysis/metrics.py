"""Analysis-layer metrics: pure aggregations over canonical spending data.

Each function takes a ``SpendingData`` and returns a tidy (long) DataFrame.
The ``month`` column is derived here from ``date`` as a month-start
``Timestamp`` (the first of the month), and ``total`` is the summed
``price``. Refunds are negative prices and net naturally within each sum.
"""

import pandas as pd

from spending.models import SpendingData


def _month(df: pd.DataFrame) -> pd.Series:
    """Derive a month-start timestamp from each row's date.

    Collapses every date to its year-month period and maps that period back
    to a concrete timestamp on the first of the month, so all dates in the
    same calendar month share one grouping key.

    Args:
        df: A DataFrame with a datetime ``date`` column.

    Returns:
        A datetime Series of month-start timestamps aligned to ``df``.
    """
    month: pd.Series = df["date"].dt.to_period("M").dt.to_timestamp()
    return month


def total_per_month(data: SpendingData) -> pd.DataFrame:
    """Sum spend per month.

    Args:
        data: The canonical spending data.

    Returns:
        A tidy DataFrame with columns ``month`` (month-start Timestamp) and
        ``total`` (summed price), one row per month, ordered by month.
    """
    df = data.df
    grouped = (
        df.assign(month=_month(df)).groupby("month", as_index=False)[["price"]].sum()
    )
    return grouped.rename(columns={"price": "total"})


def by_category_per_month(data: SpendingData) -> pd.DataFrame:
    """Sum spend per category per month.

    Args:
        data: The canonical spending data.

    Returns:
        A tidy DataFrame with columns ``month`` (month-start Timestamp),
        ``category``, and ``total`` (summed price), one row per
        month/category that occurs, ordered by month then category.
    """
    df = data.df
    grouped = (
        df.assign(month=_month(df))
        .groupby(["month", "category"], as_index=False)[["price"]]
        .sum()
    )
    return grouped.rename(columns={"price": "total"})


def essential_per_month(data: SpendingData) -> pd.DataFrame:
    """Sum essential vs non-essential spend per month.

    Only meaningful when the dataset carries a complete essential column.

    Args:
        data: The canonical spending data. Must have ``has_essential`` True.

    Returns:
        A tidy DataFrame with columns ``month`` (month-start Timestamp),
        ``essential`` (bool), and ``total`` (summed price), one row per
        month/essential value, ordered by month then essential.

    Raises:
        ValueError: If ``data.has_essential`` is False, so there is no
            essential column to group by.
    """
    if not data.has_essential:
        raise ValueError(
            "essential_per_month requires SpendingData with has_essential=True; "
            "this dataset has no essential column"
        )
    df = data.df
    grouped = (
        df.assign(month=_month(df))
        .groupby(["month", "essential"], as_index=False)[["price"]]
        .sum()
    )
    return grouped.rename(columns={"price": "total"})
