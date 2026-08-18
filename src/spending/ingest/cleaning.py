"""Row cleaning: coerce a raw sheet into canonical, validated rows.

Produces the canonical columns (``date``, ``price``, ``category``, ``item``,
and ``essential`` when present), drops rows with an unparseable date or price
(counting them), trims text, and classifies the sheet's ``essential`` column
as ABSENT / COMPLETE / INCOMPLETE for the approach-A availability rule.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

import pandas as pd

from spending.ingest.mapping import ColumnMatch

_TRUE_STRINGS = {"true", "t", "yes", "y", "1"}
_FALSE_STRINGS = {"false", "f", "no", "n", "0"}


class EssentialState(Enum):
    """Availability of the essential column within a single cleaned sheet."""

    ABSENT = "absent"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


@dataclass
class CleanedSheet:
    """Canonical rows for one sheet plus cleaning diagnostics."""

    df: pd.DataFrame
    rows_dropped: int
    essential_state: EssentialState


def _to_bool(value: Any) -> bool | None:
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    text = str(value).strip().lower()
    if text in _TRUE_STRINGS:
        return True
    if text in _FALSE_STRINGS:
        return False
    return None


def parse_essential(series: pd.Series) -> pd.Series:
    """Convert an essential column to nullable booleans (NA when unknown)."""
    if pd.api.types.is_bool_dtype(series):
        return series.astype("boolean")
    return series.map(_to_bool).astype("boolean")


def clean_sheet(raw: pd.DataFrame, match: ColumnMatch) -> CleanedSheet:
    """Clean ``raw`` using ``match`` into canonical, validated rows.

    Dates are parsed permissively. Ambiguous non-ISO formats (e.g.
    ``01/02/2026``) follow pandas' month-first default and may misparse;
    ISO dates (``2026-08-01``) are unambiguous.
    """
    columns = match.mapping
    out = pd.DataFrame()
    out["date"] = pd.to_datetime(raw[columns["date"]], errors="coerce")
    out["price"] = pd.to_numeric(raw[columns["price"]], errors="coerce")
    out["category"] = raw[columns["category"]].astype("string").str.strip()

    if "item" in columns:
        out["item"] = raw[columns["item"]].astype("string").str.strip()
    else:
        out["item"] = pd.Series([pd.NA] * len(raw), dtype="string")

    essential_present = "essential" in columns
    if essential_present:
        out["essential"] = parse_essential(raw[columns["essential"]])

    valid = out["date"].notna() & out["price"].notna()
    rows_dropped = int((~valid).sum())
    out = out[valid].reset_index(drop=True)

    if not essential_present:
        state = EssentialState.ABSENT
    elif bool(out["essential"].isna().any()):
        state = EssentialState.INCOMPLETE
    else:
        state = EssentialState.COMPLETE

    return CleanedSheet(out, rows_dropped, state)
