# Design Specification

The design and structure for the first iteration of the financial analysis tool. This document is the record of the structural decisions made before implementation; it builds on `framework_selection.md` (which records the tech-stack choices and reasoning).

## 1. Purpose and Scope

### Goal

A local, single-user prototype that reads personal spending data from a spreadsheet, analyzes it, and displays the results as a dashboard. The primary aim is to prove the concept and to build up the analysis layer, while keeping the door open for later expansion.

### In scope (this iteration)

- Import spending data from a CSV or Excel file (Excel may contain multiple sheets).
- Process and validate that data into a single canonical in-memory structure.
- Produce three analyses: total spend per month, spend per category per month, and essential vs. non-essential spend per month.
- Render those analyses as charts in a Streamlit dashboard.
- Report, at import time, which sheets were skipped and how many rows were dropped, so import problems are visible.

### Non-goals (deferred)

- No authentication and no concept of multiple users (assumed to run locally).
- No database or persistence layer yet (data is re-read from the file on refresh; see Section 10).
- No data modification tooling: no upload/edit/delete flows, no CRUD. Data is authored and maintained elsewhere; this tool only imports it for read-only analysis.
- No income/earning analysis (refunds are handled, but income is out of scope).
- No heavy normalization of free-text fields.

## 2. Architecture and Layering

The core principle from `framework_selection.md` is that analysis logic stays decoupled from the UI. This iteration expresses that as a four-layer split, each layer depending only on the one before it:

```
ingest  ->  analysis  ->  viz  ->  ui
```

- **ingest** - reads the file, detects and maps columns, validates and cleans rows, and produces the canonical data structure plus an import report. Knows about files and spreadsheets; knows nothing about analysis or charts.
- **analysis** - takes the canonical structure and returns aggregated data (DataFrames and numbers). Pure data-in / data-out. Knows nothing about charting or the UI.
- **viz** - turns aggregated analysis output into Plotly figures. Framework-agnostic: a figure does not care whether Streamlit, Dash, or NiceGUI renders it.
- **ui** - the Streamlit shell. Wires the layers together, handles caching, and lays out the page.

### Why this split (reuse and migration)

- **analysis** is pure and carries no presentation or framework dependency, so it survives every future migration untouched. If the tool later becomes a backend API, the analysis layer is lifted out and reused as-is.
- **viz** is the only layer discarded in a future two-app split (a React frontend would build its own charts from the analysis data). Keeping it separate from both analysis and ui means it can be dropped cleanly without disturbing either.
- **ui** is deliberately thin. Swapping Streamlit for another framework is a rewrite of this layer only.

Dependencies point in one direction only. `ui` may import `viz`, `analysis`, and the shared models; `viz` may import `analysis` output and the models; `analysis` imports the models; `ingest` imports the models. No layer imports a layer above it.

## 3. Canonical Data Model

Two shared types form the contract between `ingest` and the rest of the application. They live at the package level (`spending/models.py`) because they are shared, not owned by any single layer.

### `SpendingData` (the wrapper)

A lightweight object (dataclass) that holds the cleaned data plus the metadata the rest of the app needs:

- `df: DataFrame` - the canonical, validated spending data.
- `has_essential: bool` - whether the essential analysis can be run (see Section 4, approach A).
- Minimal metadata as needed (e.g. the set of source sheets imported). Kept small; extended only when a real need appears.

The wrapper exists so that the DataFrame is available for efficient pandas work while the extra facts about the dataset (chiefly `has_essential`) live in one place rather than being re-derived by sniffing columns throughout the app.

**Canonical schema of `df`:**

| Column      | Type            | Required | Notes                                              |
|-------------|-----------------|----------|----------------------------------------------------|
| `date`      | datetime        | yes      | Full parseable date; month is derived from this.   |
| `price`     | float           | yes      | May be negative (refunds). No income tracked.      |
| `category`  | str             | yes      | Lightly normalized (whitespace trimmed).           |
| `item`      | str or null     | no       | Imported if present; parked, unused in this iteration. |
| `essential` | bool or null    | no       | Present only if available across all imported data.|

`notes` is dropped at import. `month` is not stored; it is derived in the analysis layer from `date`.

### `ImportReport` (the diagnostics)

Returned alongside `SpendingData` so import problems are visible. It records, per sheet, what happened:

- **Skipped sheets** - name and reason (e.g. "missing required column: category"). This is how a user notices that, say, `May 2026` was skipped because of a header mismatch, while an expected skip like `Summary` makes sense at a glance. The importer does not try to guess which skips are intentional; it reports all of them uniformly and lets the user judge.
- **Imported sheets** - name, rows imported, and rows dropped (with the reason, e.g. unparseable date or non-numeric price).
- **Warnings** - dataset-level notes, such as `essential` being disabled because it was absent from some sheets, or a duplicate column match resolved by first-match-wins.

The import entry point returns both:

```
import_file(filepath) -> (SpendingData, ImportReport)
```

## 4. Ingestion Design

### Sheet iteration

A single file may be a CSV (one implicit sheet) or an Excel file with an arbitrary number of sheets, some of which are not data (e.g. `Summary`, `Categories`). Ingestion iterates over every available sheet, checks whether it contains the required columns, and imports the ones that do. Sheets without the required columns are skipped and recorded in the report. Data is identified by its columns and rows, never by sheet names.

### Column matching

Columns are matched case-insensitively against a small alias set per canonical column (e.g. `price` may also match `amount` or `cost`). Adding support for another person's header naming is then just adding an alias, not changing processing logic.

- **Required columns** (a sheet must have all of these to count as data): `date`, `price`, `category`.
- **Optional columns** (imported if present): `item`, `essential`.
- **Dropped:** `notes`.
- **Duplicate match** (two columns in one sheet both match the same alias set): first match wins, with a warning in the report.
- **Unrecognized columns** are ignored.

### The `essential` parser

`essential` is a boolean but arrives in varied spreadsheet forms. A dedicated, forgiving parser converts common representations to a real bool: `TRUE`/`FALSE` (any case), `T`/`F`, `yes`/`no`, `1`/`0`. Values it cannot interpret are treated as missing.

### `essential` availability (approach A - all-or-nothing)

`essential` is treated as available only if it is present and populated across every imported sheet that contains data. If any data sheet lacks it, the whole dataset is treated as not having essential data: `has_essential` is `False`, the essential analysis and its chart are omitted, and a warning is logged in the report explaining why. This keeps the essential analysis from ever being partial or misleading. (Approach B - analyzing only the rows where essential is known - is a possible future upgrade if mixed sheets become common.)

### Row cleaning

Rows are validated and coerced to the canonical types:

- `date` parsed to datetime; unparseable -> row dropped.
- `price` coerced to float; non-numeric -> row dropped.
- `category` / `item` whitespace trimmed (light normalization only).

Dropped rows are counted per sheet and recorded in the report (drop-and-report, never silent, never a hard failure on bad rows).

### Empty result

If no sheet contains the required columns, ingestion does not raise. It returns an empty `SpendingData` and an `ImportReport` listing every sheet as skipped with its reason; the UI surfaces a "no valid data found" message.

## 5. Analysis Layer

Pure functions that take a `SpendingData` and return aggregated data (tidy DataFrames or numbers). No charting, no framework dependency, no side effects. Month is derived here from the `date` column (grouped by year-month).

Three analyses for this iteration:

1. **Total spend per month** - sum of `price` grouped by month.
2. **Spend per category per month** - sum of `price` grouped by month and `category`.
3. **Essential vs. non-essential spend per month** - sum of `price` grouped by month and `essential`. Only meaningful when `has_essential` is `True`; callers check the flag before invoking it.

Refunds (negative `price`) net naturally within each sum, so no special handling is required. The set of analyses is expected to grow; new metrics are added as new pure functions here.

## 6. Visualization Layer

Functions that take analysis output and return Plotly figures. Framework-agnostic: they build figures without referencing any UI framework, so the same figure can be rendered by Streamlit now or another framework later. One builder per analysis for this iteration (total, by-category, essential-vs-non-essential). A future backend that serves JSON to a separate frontend would bypass this layer entirely.

## 7. UI Shell (Streamlit)

A thin Streamlit app that composes the layers and lays out the page. Its responsibilities:

- **Caching at the ingest boundary.** The import + process step is cached (via `st.cache_data`, keyed on file identity such as path and modification time) so the file is read and processed once, not per chart. All charts operate on the single cached `SpendingData`. The pure `import_file` function itself stays caching-agnostic; the cache wrapper lives in the UI layer.
- **Consuming the report.** Skipped sheets, dropped-row counts, and warnings from the `ImportReport` are surfaced to the user (e.g. an expandable import summary), so import problems are visible.
- **Conditional rendering.** The essential-vs-non-essential chart is shown only when `has_essential` is `True`.
- **Layout.** Arranging the charts and any filters on the page.

The UI holds no analysis logic and no chart construction; it calls `analysis` and `viz` and renders what they return.

## 8. Package Structure

A `src/` layout with the `spending` package installed editable via the build
system (see Section 9 for why):

```
financial-analysis-tool/
  streamlit_app.py          # UI entry point: caching, layout, report display
  src/
    spending/               # the reusable core (installed editable)
      __init__.py
      models.py             # SpendingData, ImportReport  (shared contract)
      ingest/
        __init__.py         # import_file(path) -> (SpendingData, ImportReport)  (orchestrator)
        reader.py           # open CSV/Excel, yield (sheet_name, raw_df)
        mapping.py          # alias sets + case-insensitive column detection
        cleaning.py         # dtype parsing, essential parser, row validation, drop + count
      analysis/
        __init__.py         # the three metric functions (pure)
      viz/
        __init__.py         # Plotly figure builders
  tests/
  pyproject.toml            # managed by uv; build-system + tool config
  design_docs/
    design_spec.md
    framework_selection.md
```

`streamlit_app.py` stays at the repo root (it is the app entry point, not part
of the importable package) and imports `spending`.

- `ingest` is split into reader / mapping / cleaning because they are genuinely different jobs (I/O vs. header-matching vs. row-cleaning) and each is unit-testable in isolation, which matters for the reuse goal.
- `models.py` sits at the package level because both `ingest` (produces) and `analysis` / `ui` (consume) depend on it.
- `ImportReport` is produced only by `ingest` and consumed by `ui`; it can live in `models.py` alongside `SpendingData` for a single shared contract location.

## 9. Tooling and Setup

- **Dependency and project management:** `uv`. Runtime dependencies (pandas, streamlit, plotly, an Excel engine such as openpyxl) and dev dependencies (pytest, pytest-cov, ruff, mypy, pandas-stubs) declared in `pyproject.toml`. `uv.lock` is committed for reproducibility.
- **Source control:** `git`, with a `.gitignore` covering the virtual environment, caches, and any local data files.
- **Layout:** `src/` layout with a build system (`uv_build`). The `spending` package is installed editable into the venv, so `import spending` works everywhere (tests, REPL, the Streamlit app) with no `sys.path` or `pythonpath` configuration, and tests exercise the package as installed rather than the raw working-directory folder. The distribution name is `financial-analysis-tool` while the import name is `spending` (set via `[tool.uv.build-backend] module-name`).
- **Quality tooling:** `ruff` for linting and formatting (88-character line length); `mypy` in strict mode (with `pandas-stubs`) for type checking, relaxed for `tests/`. `prek` (a drop-in, `pre-commit`-compatible runner) enforces format + lint at pre-commit and the test suite at pre-push. A `Makefile` provides `make test` (`uv run pytest`) and `make format` (`prek run`).

## 10. Deferred and Future Work

Recorded so the prototype is built with these directions in mind, without building for them now:

- **Persistence / database.** Currently data is re-read from the file on each refresh. The natural next step is a static local DB: `import -> DB`, then `DB -> SpendingData`, leaving `analysis`, `viz`, and `ui` unchanged. DuckDB is the preferred target when heavier analytics justify it; the choice is deferred until then. This is the reason the canonical `SpendingData` wrapper is the seam between ingest and analysis - only the producer of the wrapper changes.
- **Framework growth path.** Streamlit for this iteration; then NiceGUI or Dash, then Django/FastAPI + React, walked only when a concrete wall forces it (see `framework_selection.md`).
- **Shared / utils extraction.** The low-level ingest machinery (file reading, sheet iteration, alias matching, row cleaning) is domain-agnostic. If the tool ever grows beyond spending (e.g. an `earning` analysis, which would differ in ingest, analysis, and viz), those generics can be extracted into a shared `utils/` package with `spending/` and `earning/` as sibling domain packages. Not built now.
- **Analysis expansion.** More metrics and charts are added as new pure functions in `analysis` and builders in `viz`.
- **Normalization.** Heavier normalization of free-text fields (`category`, `item`) is deferred; `item` is imported but parked, `notes` is dropped, and both can be revisited if a feature needs them.
