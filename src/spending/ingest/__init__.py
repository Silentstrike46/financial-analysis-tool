"""Ingestion layer.

Reads a CSV or Excel file, detects and maps columns, validates and cleans
rows, and produces a ``SpendingData`` plus an ``ImportReport`` via
``import_file``.
"""
