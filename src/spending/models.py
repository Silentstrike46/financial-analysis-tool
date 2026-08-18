"""Shared data contracts between ingest and the rest of the app.

``SpendingData`` is the canonical DataFrame wrapper consumed by the analysis
layer; ``ImportReport`` (and its nested ``FileReport`` / ``SheetReport``)
carries import diagnostics for the UI to surface.
"""

from dataclasses import dataclass
from enum import Enum

import pandas as pd


class SheetStatus(Enum):
    """Outcome of attempting to import a single sheet."""

    IMPORTED = "imported"
    SKIPPED = "skipped"


@dataclass
class SheetReport:
    """What happened to one sheet within a file."""

    name: str
    status: SheetStatus
    rows_imported: int = 0
    rows_dropped: int = 0
    reason: str | None = None


@dataclass
class FileReport:
    """Per-file collection of sheet outcomes.

    ``error`` is set when the file itself could not be read (missing,
    unsupported type); in that case ``sheets`` is empty.
    """

    path: str
    sheets: list[SheetReport]
    error: str | None = None


@dataclass
class ImportReport:
    """Diagnostics for a whole import run across one or more files."""

    files: list[FileReport]
    warnings: list[str]


@dataclass
class SpendingData:
    """Canonical spending data plus the metadata the app needs.

    ``df`` columns: ``date`` (datetime), ``price`` (float), ``category``
    (str), ``item`` (str/NaN), and ``essential`` (bool) only when
    ``has_essential`` is True.
    """

    df: pd.DataFrame
    has_essential: bool

    @property
    def is_empty(self) -> bool:
        """Whether the canonical DataFrame has no rows."""
        return bool(self.df.empty)
