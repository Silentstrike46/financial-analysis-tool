"""Tests for column detection (alias matching)."""

from spending.ingest.mapping import match_columns


def test_matches_canonical_case_and_whitespace_insensitive():
    """Tests that headers match aliases ignoring case and surrounding space."""
    match = match_columns([" Date ", "PRICE", "category", "Item", "Essential"])
    assert match.mapping == {
        "date": " Date ",
        "price": "PRICE",
        "category": "category",
        "item": "Item",
        "essential": "Essential",
    }
    assert match.missing_required == set()


def test_required_columns_sufficient_without_optionals():
    """Tests that a sheet with only the required columns is fully matched."""
    match = match_columns(["Date", "Price", "Category"])
    assert set(match.mapping) == {"date", "price", "category"}
    assert match.missing_required == set()


def test_missing_required_column_is_reported():
    """Tests that an absent required column is flagged as missing."""
    match = match_columns(["Date", "Price"])  # no category
    assert "category" in match.missing_required
    assert "category" not in match.mapping


def test_notes_and_unknown_columns_are_ignored():
    """Tests that unrecognized columns (incl. notes) are left unmapped."""
    match = match_columns(["Date", "Price", "Category", "Notes", "Unnamed: 1"])
    assert set(match.mapping) == {"date", "price", "category"}


def test_price_aliases_amount_and_cost_match():
    """Tests that 'Amount' and 'Cost' are accepted as price aliases."""
    assert match_columns(["Date", "Amount", "Category"]).mapping["price"] == "Amount"
    assert match_columns(["Date", "Cost", "Category"]).mapping["price"] == "Cost"


def test_duplicate_match_keeps_first_and_warns():
    """Tests that two columns matching one canonical keep the first and warn."""
    match = match_columns(["Date", "Price", "price", "Category"])
    assert match.mapping["price"] == "Price"  # first occurrence wins
    assert match.duplicate_warnings


def test_essentials_plural_does_not_match_essential():
    """Tests that 'Essentials' does not match 'essential' (equality, not substring)."""
    match = match_columns(["Date", "Price", "Category", "Essentials"])
    assert "essential" not in match.mapping
    assert match.missing_required == set()  # still a valid data sheet
