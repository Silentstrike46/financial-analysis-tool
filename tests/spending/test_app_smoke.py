"""Headless smoke tests for the Streamlit shell via ``AppTest``.

These confirm the app script runs top to bottom without raising - they do
not assert on rendered pixels.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tests.helpers import data_sheet, write_xlsx

APP_PATH = Path(__file__).parents[2] / "streamlit_app.py"


def test_app_renders_all_sections_with_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Tests that a workbook in data/ renders every section without error."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    write_xlsx(
        data_dir / "book.xlsx",
        {"August 2026": data_sheet(essential=[True, False])},
    )
    monkeypatch.chdir(tmp_path)

    app = AppTest.from_file(str(APP_PATH)).run()

    assert not app.exception
    titles = [block.value for block in app.subheader]
    assert titles == [
        "Monthly spend",
        "Spend by category",
        "Essential vs non-essential",
    ]


def test_app_reports_when_data_dir_is_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Tests that an absent data/ folder shows a message, not an error."""
    monkeypatch.chdir(tmp_path)

    app = AppTest.from_file(str(APP_PATH)).run()

    assert not app.exception
    assert any("No files available" in block.value for block in app.info)
