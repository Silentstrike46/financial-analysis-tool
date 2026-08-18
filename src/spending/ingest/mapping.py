"""Column detection: match a sheet's headers to canonical columns.

Matching is case-insensitive and whitespace-insensitive, by normalized
*equality* against a small alias set per canonical column (so ``Essentials``
does not match ``essential``). Unrecognized columns - including ``notes`` -
are ignored.
"""

from dataclasses import dataclass

DATE = "date"
PRICE = "price"
CATEGORY = "category"
ITEM = "item"
ESSENTIAL = "essential"

REQUIRED: frozenset[str] = frozenset({DATE, PRICE, CATEGORY})

ALIASES: dict[str, set[str]] = {
    DATE: {"date"},
    PRICE: {"price"},
    CATEGORY: {"category"},
    ITEM: {"item"},
    ESSENTIAL: {"essential"},
}


@dataclass
class ColumnMatch:
    """Result of matching a sheet's headers to canonical columns."""

    mapping: dict[str, str]  # canonical -> actual header
    missing_required: set[str]
    duplicate_warnings: list[str]


def _normalize(name: str) -> str:
    return name.strip().lower()


def match_columns(columns: list[str]) -> ColumnMatch:
    """Match ``columns`` to canonical names; first match wins on duplicates."""
    alias_to_canonical = {
        alias: canonical for canonical, aliases in ALIASES.items() for alias in aliases
    }

    mapping: dict[str, str] = {}
    duplicate_warnings: list[str] = []
    for actual in columns:
        canonical = alias_to_canonical.get(_normalize(actual))
        if canonical is None:
            continue
        if canonical in mapping:
            duplicate_warnings.append(
                f"Multiple columns match '{canonical}': keeping "
                f"'{mapping[canonical]}', ignoring '{actual}'."
            )
            continue
        mapping[canonical] = actual

    missing_required = set(REQUIRED) - set(mapping)
    return ColumnMatch(mapping, missing_required, duplicate_warnings)
