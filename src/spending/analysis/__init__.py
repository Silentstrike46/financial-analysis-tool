"""Analysis layer.

Pure functions that take a ``SpendingData`` and return aggregated data
(DataFrames / numbers). No charting, no framework dependency.
"""

from spending.analysis.metrics import (
    by_category_per_month,
    essential_per_month,
    total_per_month,
)

__all__ = ["by_category_per_month", "essential_per_month", "total_per_month"]
