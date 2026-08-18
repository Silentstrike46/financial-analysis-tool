"""Integration tests for the ingestion pipeline (import_files)."""

from pathlib import Path

import pandas as pd
import pytest

from spending.ingest import import_file, import_files
from spending.models import ImportReport, SheetStatus
from tests.helpers import data_sheet, write_csv, write_xlsx


def _status(report: ImportReport, sheet_name: str) -> SheetStatus:
    for file_report in report.files:
        for sheet in file_report.sheets:
            if sheet.name == sheet_name:
                return sheet.status
    raise AssertionError(f"no sheet report for {sheet_name!r}")


def test_data_sheets_imported_non_data_sheets_skipped(tmp_path: Path):
    """Tests that valid sheets import and non-data sheets are skipped."""
    path = write_xlsx(
        tmp_path / "book.xlsx",
        {
            "August 2026": data_sheet(essential=[True, False]),
            "Summary": pd.DataFrame({"Month": ["Aug"], "Total": [30.0]}),
            "Categories": pd.DataFrame({"Category": ["Food"], "Essentials": [1]}),
        },
    )

    data, report = import_file(path)

    assert _status(report, "August 2026") is SheetStatus.IMPORTED
    assert _status(report, "Summary") is SheetStatus.SKIPPED
    assert _status(report, "Categories") is SheetStatus.SKIPPED
    assert len(data.df) == 2
    assert data.has_essential is True
    assert "essential" in data.df.columns


def test_essential_disabled_when_a_file_lacks_it(tmp_path: Path):
    """Tests that has_essential is False (with a warning) if any file omits it."""
    with_essential = write_xlsx(
        tmp_path / "a.xlsx", {"August 2026": data_sheet(essential=[True, False])}
    )
    without_essential = write_xlsx(tmp_path / "b.xlsx", {"July 2026": data_sheet()})

    data, report = import_files([with_essential, without_essential])

    assert len(data.df) == 4
    assert data.has_essential is False
    assert "essential" not in data.df.columns
    assert report.warnings


def test_incomplete_essential_disables_with_warning(tmp_path: Path):
    """Tests that a blank essential value disables the feature and warns."""
    path = write_xlsx(
        tmp_path / "book.xlsx",
        {"August 2026": data_sheet(essential=[True, None])},
    )

    data, report = import_file(path)

    assert data.has_essential is False
    assert any("August 2026" in w for w in report.warnings)


def test_all_sheets_absent_essential_has_no_warning(tmp_path: Path):
    """Tests that a wholly absent essential column disables it silently."""
    path = write_xlsx(tmp_path / "book.xlsx", {"August 2026": data_sheet()})

    data, report = import_file(path)

    assert data.has_essential is False
    assert report.warnings == []


def test_no_valid_sheet_yields_empty_data(tmp_path: Path):
    """Tests that a file with no data sheets yields empty SpendingData."""
    path = write_xlsx(
        tmp_path / "book.xlsx",
        {"Summary": pd.DataFrame({"Month": ["Aug"], "Total": [30.0]})},
    )

    data, report = import_file(path)

    assert data.is_empty
    assert _status(report, "Summary") is SheetStatus.SKIPPED


def test_empty_result_has_typed_canonical_columns(tmp_path: Path):
    """Tests that empty SpendingData keeps canonical dtypes, not object."""
    path = write_xlsx(
        tmp_path / "book.xlsx",
        {"Summary": pd.DataFrame({"Month": ["Aug"], "Total": [30.0]})},
    )

    data, _ = import_file(path)

    assert data.is_empty
    assert data.df["date"].dtype == "datetime64[ns]"
    assert data.df["price"].dtype == "float64"


def test_import_files_rejects_a_bare_string_path():
    """Tests that a single string path is rejected instead of iterated."""
    with pytest.raises(TypeError):
        import_files("expenses.csv")


def test_essential_warning_identifies_the_offending_file(tmp_path: Path):
    """Tests that the essential warning is qualified by file, not just sheet."""
    good = write_xlsx(
        tmp_path / "good.xlsx", {"August 2026": data_sheet(essential=[True, False])}
    )
    bad = write_xlsx(tmp_path / "bad.xlsx", {"August 2026": data_sheet()})

    _data, report = import_files([good, bad])

    assert any("bad.xlsx" in w for w in report.warnings)


def test_bad_rows_are_counted_in_the_sheet_report(tmp_path: Path):
    """Tests that dropped rows are counted in the sheet report."""
    sheet = pd.DataFrame(
        {
            "Date": ["2026-08-01", "bad-date"],
            "Price": [10.0, 20.0],
            "Category": ["Food", "Food"],
        }
    )
    path = write_xlsx(tmp_path / "book.xlsx", {"August 2026": sheet})

    _data, report = import_file(path)

    august = report.files[0].sheets[0]
    assert august.rows_imported == 1
    assert august.rows_dropped == 1


def test_unreadable_file_is_recorded_and_batch_continues(tmp_path: Path):
    """Tests that an unreadable file is reported while other files import."""
    good = write_xlsx(tmp_path / "good.xlsx", {"August 2026": data_sheet()})
    missing = tmp_path / "missing.xlsx"

    data, report = import_files([missing, good])

    assert len(data.df) == 2  # good file still imported
    missing_report = next(f for f in report.files if f.path == str(missing))
    assert missing_report.error is not None


def test_corrupt_file_is_recorded_and_batch_continues(tmp_path: Path):
    """Tests that a corrupt file is reported (not raised) and others import."""
    corrupt = tmp_path / "corrupt.xlsx"
    corrupt.write_bytes(b"not a real xlsx")
    good = write_xlsx(tmp_path / "good.xlsx", {"August 2026": data_sheet()})

    data, report = import_files([corrupt, good])

    assert len(data.df) == 2
    corrupt_report = next(f for f in report.files if f.path == str(corrupt))
    assert corrupt_report.error is not None


def test_csv_file_is_imported_end_to_end(tmp_path: Path):
    """Tests that a CSV file imports through the full pipeline."""
    path = write_csv(tmp_path / "expenses.csv", data_sheet(rows=3))

    data, report = import_files([path])

    assert len(data.df) == 3
    assert report.files[0].sheets[0].status is SheetStatus.IMPORTED


def test_essential_enabled_when_all_files_complete(tmp_path: Path):
    """Tests that has_essential is True when every file has complete essential."""
    a = write_xlsx(
        tmp_path / "a.xlsx", {"August 2026": data_sheet(essential=[True, False])}
    )
    b = write_xlsx(
        tmp_path / "b.xlsx", {"July 2026": data_sheet(essential=[False, True])}
    )

    data, report = import_files([a, b])

    assert data.has_essential is True
    assert "essential" in data.df.columns
    assert len(data.df) == 4
    assert report.warnings == []


def test_duplicate_column_warning_is_surfaced(tmp_path: Path):
    """Tests that a duplicate column match appears in the report warnings."""
    sheet = pd.DataFrame(
        {
            "Date": ["2026-08-01"],
            "Price": [10.0],
            "price": [99.0],
            "Category": ["Food"],
        }
    )
    path = write_xlsx(tmp_path / "book.xlsx", {"August 2026": sheet})

    _data, report = import_files([path])

    assert any("match" in w.lower() for w in report.warnings)
