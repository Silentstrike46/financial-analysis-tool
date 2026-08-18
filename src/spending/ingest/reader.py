"""File reading: yield raw, unmapped sheets from a CSV or Excel file.

A CSV is treated as a single sheet named after the file; an Excel file
yields each of its sheets in order. Reading errors (missing file,
unsupported type) propagate to the caller, which records them per file.
"""

from collections.abc import Iterator
from pathlib import Path

import pandas as pd

_EXCEL_SUFFIXES = {".xlsx", ".xlsm"}


def read_sheets(path: str | Path) -> Iterator[tuple[str, pd.DataFrame]]:
    """Yield each raw sheet from a CSV or Excel file.

    A CSV is treated as a single sheet named after the file; an Excel file
    yields each of its sheets in order.

    Args:
        path: Path to a ``.csv``, ``.xlsx``, or ``.xlsm`` file.

    Yields:
        ``(sheet_name, raw_df)`` for each sheet, unmapped and uncleaned.

    Raises:
        ValueError: If the file extension is not supported.
    """
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        yield path.stem, pd.read_csv(path)
    elif suffix in _EXCEL_SUFFIXES:
        with pd.ExcelFile(path) as excel:
            for name in excel.sheet_names:
                yield str(name), excel.parse(name)
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")
