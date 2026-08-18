"""Helpers for building real CSV/XLSX files in tests."""

from collections.abc import Mapping
from pathlib import Path

import pandas as pd


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
