"""Tests for row cleaning and the essential parser."""

import pandas as pd

from spending.ingest.cleaning import EssentialState, clean_sheet, parse_essential
from spending.ingest.mapping import match_columns


def _clean(raw: pd.DataFrame):
    return clean_sheet(raw, match_columns(list(raw.columns)))


def test_unparseable_dates_are_dropped_and_counted():
    """Tests that rows with an invalid date are dropped and counted."""
    raw = pd.DataFrame(
        {
            "Date": ["2026-08-01", "not-a-date", "2026-08-03"],
            "Price": [10.0, 20.0, 30.0],
            "Category": ["Food", "Food", "Food"],
        }
    )
    cleaned = _clean(raw)
    assert cleaned.rows_dropped == 1
    assert len(cleaned.df) == 2


def test_non_numeric_prices_are_dropped_and_counted():
    """Tests that rows with a non-numeric price are dropped and counted."""
    raw = pd.DataFrame(
        {
            "Date": ["2026-08-01", "2026-08-02"],
            "Price": ["oops", 30.0],
            "Category": ["Food", "Food"],
        }
    )
    cleaned = _clean(raw)
    assert cleaned.rows_dropped == 1
    assert cleaned.df["price"].tolist() == [30.0]


def test_price_is_always_float_even_when_integral():
    """Tests that all-integer prices are still coerced to float dtype."""
    raw = pd.DataFrame(
        {
            "Date": ["2026-08-01", "2026-08-02"],
            "Price": [10, 20],  # integer values
            "Category": ["Food", "Food"],
        }
    )
    cleaned = _clean(raw)
    assert cleaned.df["price"].dtype == "float64"


def test_negative_prices_are_kept():
    """Tests that negative prices (refunds) survive cleaning."""
    raw = pd.DataFrame(
        {
            "Date": ["2026-08-01", "2026-08-02"],
            "Price": [-50.0, 30.0],
            "Category": ["Food", "Food"],
        }
    )
    cleaned = _clean(raw)
    assert -50.0 in cleaned.df["price"].tolist()


def test_category_and_item_whitespace_is_trimmed():
    """Tests that surrounding whitespace is stripped from category and item."""
    raw = pd.DataFrame(
        {
            "Date": ["2026-08-01"],
            "Price": [10.0],
            "Category": ["  Food  "],
            "Item": ["  Bread  "],
        }
    )
    cleaned = _clean(raw)
    assert cleaned.df["category"].tolist() == ["Food"]
    assert cleaned.df["item"].tolist() == ["Bread"]


def test_notes_column_is_not_carried_into_output():
    """Tests that a notes column never appears in the cleaned output."""
    raw = pd.DataFrame(
        {
            "Date": ["2026-08-01"],
            "Price": [10.0],
            "Category": ["Food"],
            "Notes": ["ignore me"],
        }
    )
    cleaned = _clean(raw)
    assert "notes" not in cleaned.df.columns


def test_native_bool_essential_is_complete():
    """Tests that a fully populated native-bool essential column is COMPLETE."""
    raw = pd.DataFrame(
        {
            "Date": ["2026-08-01", "2026-08-02"],
            "Price": [10.0, 20.0],
            "Category": ["Food", "Food"],
            "Essential": [True, False],
        }
    )
    cleaned = _clean(raw)
    assert cleaned.essential_state is EssentialState.COMPLETE
    assert cleaned.df["essential"].tolist() == [True, False]


def test_missing_essential_column_is_absent():
    """Tests that a sheet without an essential column is classified ABSENT."""
    raw = pd.DataFrame(
        {
            "Date": ["2026-08-01"],
            "Price": [10.0],
            "Category": ["Food"],
        }
    )
    cleaned = _clean(raw)
    assert cleaned.essential_state is EssentialState.ABSENT
    assert "essential" not in cleaned.df.columns


def test_blank_essential_value_makes_sheet_incomplete():
    """Tests that any blank essential value classifies the sheet INCOMPLETE."""
    raw = pd.DataFrame(
        {
            "Date": ["2026-08-01", "2026-08-02"],
            "Price": [10.0, 20.0],
            "Category": ["Food", "Food"],
            "Essential": [True, None],
        }
    )
    cleaned = _clean(raw)
    assert cleaned.essential_state is EssentialState.INCOMPLETE


def test_parse_essential_handles_string_variants():
    """Tests that common textual truthy/falsey values parse to booleans."""
    series = pd.Series(["TRUE", "false", "Yes", "no", "T", "f", "1", "0"])
    parsed = parse_essential(series)
    assert parsed.tolist() == [True, False, True, False, True, False, True, False]


def test_parse_essential_marks_unknown_values_missing():
    """Tests that unrecognized essential values become missing (NA)."""
    series = pd.Series(["true", "maybe", ""])
    parsed = parse_essential(series)
    assert bool(parsed.isna().tolist() == [False, True, True])


def test_parse_essential_handles_numeric_values():
    """Tests that numeric 1/0 parse to booleans and other numbers are NA."""
    series = pd.Series([1, 0, 5])
    parsed = parse_essential(series)
    assert parsed.tolist()[:2] == [True, False]
    assert bool(parsed.isna().tolist() == [False, False, True])
