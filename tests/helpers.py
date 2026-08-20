"""Helpers for building real CSV/XLSX files in tests."""

from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from spending.models import SpendingData


def data_sheet(rows: int = 2, *, essential: list[object] | None = None) -> pd.DataFrame:
    """Build a valid expense sheet (real headers) with ``rows`` rows.

    Pass ``essential`` to include an ``Essential`` column of that length.
    """
    data: dict[str, list[object]] = {
        "Date": [f"2026-08-0{i + 1}" for i in range(rows)],
        "Price": [10.0 * (i + 1) for i in range(rows)],
        "Category": ["Food"] * rows,
        "Item": ["Thing"] * rows,
    }
    if essential is not None:
        data["Essential"] = essential
    return pd.DataFrame(data)


def spending_data(
    dates: list[str],
    prices: list[float],
    categories: list[str],
    *,
    essential: list[bool] | None = None,
) -> SpendingData:
    """Build a canonical ``SpendingData`` from parallel column lists.

    Dates are parsed to datetime and the columns given their canonical
    dtypes, matching what the ingest layer produces (including an all-NA
    ``item`` column). Pass ``essential`` to include a plain-``bool``
    ``essential`` column and set ``has_essential`` True.

    Args:
        dates: ISO date strings, one per row.
        prices: Row prices; may be negative for refunds.
        categories: Row categories.
        essential: Optional per-row essential flags. When given, the result
            has an ``essential`` column and ``has_essential`` is True.

    Returns:
        A ``SpendingData`` whose ``df`` uses the canonical column dtypes.
    """
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(dates),
            "price": pd.Series(prices, dtype="float64"),
            "category": pd.Series(categories, dtype="string"),
            "item": pd.Series([pd.NA] * len(dates), dtype="string"),
        }
    )
    if essential is not None:
        df["essential"] = pd.Series(essential, dtype="bool")
    return SpendingData(df=df, has_essential=essential is not None)


def write_csv(path: Path, df: pd.DataFrame) -> Path:
    """Write ``df`` to ``path`` as CSV and return the path."""
    df.to_csv(path, index=False)
    return path


def write_xlsx(path: Path, sheets: Mapping[str, pd.DataFrame]) -> Path:
    """Write ``sheets`` (name -> DataFrame) to ``path`` as XLSX and return it."""
    with pd.ExcelWriter(path) as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    return path
