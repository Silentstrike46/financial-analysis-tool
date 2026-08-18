"""Smoke test: the package and its subpackages import cleanly."""

import spending
import spending.analysis
import spending.ingest
import spending.models
import spending.viz


def test_spending_package_imports() -> None:
    assert spending.__doc__ is not None
    assert spending.analysis is not None
    assert spending.ingest is not None
    assert spending.models is not None
    assert spending.viz is not None
