"""Ingestion pipeline: orchestrate reading, mapping, and cleaning.

``import_files`` imports one or more CSV/Excel files into a single
``SpendingData`` plus a nested ``ImportReport``. ``import_file`` is a
convenience wrapper for a single path. Files are assumed disjoint (no
row deduplication).
"""

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from spending.ingest.cleaning import CleanedSheet, EssentialState, clean_sheet
from spending.ingest.mapping import match_columns
from spending.ingest.reader import read_sheets
from spending.models import (
    FileReport,
    ImportReport,
    SheetReport,
    SheetStatus,
    SpendingData,
)

_CANONICAL_COLUMNS = ["date", "price", "category", "item"]

_ImportedSheet = tuple[str, CleanedSheet]


def import_files(
    paths: Sequence[str | Path],
) -> tuple[SpendingData, ImportReport]:
    """Import one or more files into a single SpendingData and report.

    Each file's sheets are read, matched, cleaned, and concatenated. Files
    are assumed disjoint (no row deduplication). ``has_essential`` is
    resolved all-or-nothing across every imported sheet and file. Per-file
    read errors are recorded on the report and do not abort the batch.

    Args:
        paths: Paths to the CSV/Excel files to import.

    Returns:
        The combined SpendingData and a nested ImportReport.
    """
    file_reports: list[FileReport] = []
    warnings: list[str] = []
    imported: list[_ImportedSheet] = []

    for path in paths:
        file_report, sheets, file_warnings = _import_single_file(path)
        file_reports.append(file_report)
        imported.extend(sheets)
        warnings.extend(file_warnings)

    has_essential, essential_warning = _resolve_essential(imported)
    if essential_warning is not None:
        warnings.append(essential_warning)

    df = _combine(imported, has_essential=has_essential)
    report = ImportReport(files=file_reports, warnings=warnings)
    return SpendingData(df=df, has_essential=has_essential), report


def import_file(path: str | Path) -> tuple[SpendingData, ImportReport]:
    """Import a single file (convenience wrapper over ``import_files``).

    Args:
        path: Path to the CSV/Excel file to import.

    Returns:
        The combined SpendingData and a nested ImportReport.
    """
    return import_files([path])


def _import_single_file(
    path: str | Path,
) -> tuple[FileReport, list[_ImportedSheet], list[str]]:
    """Read and clean one file into its report, sheets, and warnings."""
    try:
        sheets = list(read_sheets(path))
    except Exception as exc:
        # Broad by design: record any read failure and let the batch continue.
        return FileReport(path=str(path), sheets=[], error=str(exc)), [], []

    reports: list[SheetReport] = []
    imported: list[_ImportedSheet] = []
    warnings: list[str] = []
    for name, raw in sheets:
        match = match_columns([str(col) for col in raw.columns])
        if match.missing_required:
            missing = ", ".join(sorted(match.missing_required))
            reports.append(
                SheetReport(
                    name,
                    SheetStatus.SKIPPED,
                    reason=f"missing required column(s): {missing}",
                )
            )
            continue
        cleaned = clean_sheet(raw, match)
        reports.append(
            SheetReport(
                name,
                SheetStatus.IMPORTED,
                rows_imported=len(cleaned.df),
                rows_dropped=cleaned.rows_dropped,
            )
        )
        imported.append((name, cleaned))
        warnings.extend(f"[{path} / {name}] {w}" for w in match.duplicate_warnings)

    return FileReport(path=str(path), sheets=reports), imported, warnings


def _resolve_essential(imported: list[_ImportedSheet]) -> tuple[bool, str | None]:
    """Decide has_essential across sheets, with a warning when disabled.

    Returns ``(True, None)`` only when every sheet's essential column is
    COMPLETE; ``(False, None)`` when all are ABSENT; otherwise
    ``(False, warning)`` naming the offending sheets.
    """
    states = [cleaned.essential_state for _, cleaned in imported]
    if not states:
        return False, None
    if all(state is EssentialState.COMPLETE for state in states):
        return True, None
    if all(state is EssentialState.ABSENT for state in states):
        return False, None

    offenders = [
        name
        for name, cleaned in imported
        if cleaned.essential_state is not EssentialState.COMPLETE
    ]
    warning = (
        "Essential analysis disabled: not all sheets have a complete "
        f"essential column. Offending sheets: {', '.join(offenders)}."
    )
    return False, warning


def _combine(imported: list[_ImportedSheet], *, has_essential: bool) -> pd.DataFrame:
    """Concatenate cleaned sheets into the canonical DataFrame.

    Includes the ``essential`` column only when ``has_essential`` is True.
    """
    columns = (
        [*_CANONICAL_COLUMNS, "essential"] if has_essential else _CANONICAL_COLUMNS
    )
    if not imported:
        return pd.DataFrame(columns=columns)
    df = pd.concat([cleaned.df for _, cleaned in imported], ignore_index=True)
    if has_essential:
        df["essential"] = df["essential"].astype(bool)
    return df[columns]
