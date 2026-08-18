"""Ingestion layer.

Reads a CSV or Excel file, detects and maps columns, validates and cleans
rows, and produces a ``SpendingData`` plus an ``ImportReport``.
"""

from spending.ingest.pipeline import import_file, import_files

__all__ = ["import_file", "import_files"]
