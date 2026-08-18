"""Tests for reading sheets out of CSV and Excel files."""

from pathlib import Path

import pandas as pd
import pytest

from spending.ingest.reader import read_sheets
from tests.helpers import write_csv, write_xlsx


def test_reads_csv_as_single_sheet(tmp_path: Path):
    """Tests that a CSV yields exactly one sheet named after the file."""
    df = pd.DataFrame({"Date": ["2026-08-01"], "Price": [10.0], "Category": ["Food"]})
    path = write_csv(tmp_path / "expenses.csv", df)

    sheets = list(read_sheets(path))

    assert len(sheets) == 1
    name, raw = sheets[0]
    assert name == "expenses"
    assert list(raw.columns) == ["Date", "Price", "Category"]


def test_reads_all_sheets_from_excel_in_order(tmp_path: Path):
    """Tests that every sheet in an Excel file is yielded in order."""
    data = pd.DataFrame({"Date": ["2026-08-01"], "Price": [10.0], "Category": ["Food"]})
    other = pd.DataFrame({"Category": ["Food"], "Essentials": [1]})
    path = write_xlsx(
        tmp_path / "book.xlsx", {"August 2026": data, "Categories": other}
    )

    names = [name for name, _ in read_sheets(path)]

    assert names == ["August 2026", "Categories"]


def test_missing_file_raises(tmp_path: Path):
    """Tests that reading a nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        list(read_sheets(tmp_path / "nope.xlsx"))


def test_unsupported_extension_raises(tmp_path: Path):
    """Tests that an unsupported file extension raises ValueError."""
    path = tmp_path / "data.txt"
    path.write_text("hello")
    with pytest.raises(ValueError):
        list(read_sheets(path))
