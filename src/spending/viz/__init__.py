"""Visualization layer.

Framework-agnostic builders that turn analysis output into Plotly figures.
"""

from spending.viz.figures import (
    by_category_per_month_bar,
    by_category_per_month_line,
    essential_per_month_bar,
    essential_per_month_line,
    total_per_month_bar,
    total_per_month_line,
)

__all__ = [
    "by_category_per_month_bar",
    "by_category_per_month_line",
    "essential_per_month_bar",
    "essential_per_month_line",
    "total_per_month_bar",
    "total_per_month_line",
]
