# Framework Selection

A record of the tech-stack decisions for the financial analysis tool, and the reasoning behind them, captured before planning the project structure.

## Summary of Decisions

- **Language:** Python. Chosen to align with the primary goal of upskilling on data analysis.
- **Data processing:** pandas. The mainstream, best-documented library; "learning data analysis in Python" effectively means learning pandas + numpy.
- **Storage:** Start with in-memory DataFrames (read file -> analyze -> done). Add DuckDB when persistence or data size warrants it. SQLite is the alternative if a general-purpose, more transferable SQL skill is preferred over DuckDB's analytical fit.
- **Dashboard / UI:** Streamlit, for the initial build.
- **Core architectural principle:** Keep analysis logic in plain, framework-agnostic Python modules, fully decoupled from the dashboard layer. The dashboard is a thin rendering shell that calls the analysis API. This makes every future framework change cheap.
- **Growth path (walked only when a real need forces it):** Streamlit -> NiceGUI or Dash -> Django/FastAPI + React.
  - **NiceGUI** if growth is app-like (parameterized tools, workflows) and/or we want to pre-empt an eventual React migration.
  - **Dash** if growth is dashboard-heavy and we want to maximize time in single-app Python.
  - **Django/FastAPI + React** if the tool is ever released publicly and needs auth, multi-user, and a real API.
- **Explicit decision:** Start with Streamlit rather than starting with Dash. Do not pre-commit to a heavier framework before we know how interactive the tool actually needs to be.

## Context and Requirements

The tool reads financial data from an external source (likely CSV or Excel), processes and analyzes it, and displays metrics as dashboards, graphs, etc. Additional analysis tools may be added later.

Key constraints that shaped the decisions:

- **Primary goal is learning data analysis** (Python side), not UI development. UI work should be minimized so focus stays on analysis.
- **Prefer a single Python app** for now, as long as the UI is sufficient. Willing to split into separate frontend/backend later.
- **Analysis scope is exploratory / not fixed.** Starts as personal spending visualization and forecasting; may grow to heavier analysis if the tool proves useful.
- **Interactivity needs are unknown yet.**
- **Deployment horizon is "eventual web app,"** but currently personal/local use.
- **No data-modification tooling needed.** Data is authored and maintained elsewhere; this tool only imports it temporarily for analysis. No permanent storage, no CRUD, no upload/edit/delete flows.

## Decision Detail and Reasoning

### Language: Python

The single most important driver is the learning goal: getting stronger on the data-analysis side. Python's data ecosystem (pandas, numpy, and the wider scientific stack) is where that skill lives, and the analysis work is where the interesting logic of this tool will be. JavaScript was a candidate for keeping upskilling broad, but it does not serve the analysis-learning goal nearly as well.

### Data processing: pandas

pandas is the standard and has the deepest pool of tutorials and community answers, so it is the right tool when the explicit aim is upskilling on the mainstream ecosystem. Polars is faster and more modern, but it is a poorer learning choice here: fewer resources and a more niche API. The plan is to start with pandas and consider Polars later, once there is enough fluency to appreciate what it improves on.

### Storage: in-memory first, DuckDB when needed

Because data is imported only temporarily for analysis and needs no permanent storage or modification tooling, the simplest sufficient option is to read files straight into DataFrames in memory and analyze them. That is legitimately enough for personal spending visualization.

Two upgrade paths when persistence or data size makes re-importing annoying:

- **DuckDB** - an embedded analytical (OLAP) database. It queries CSV/Parquet directly, integrates tightly with pandas, and is built for the aggregation/grouping queries financial analysis is full of. Same "just a local file, no server" convenience as SQLite, but optimized for analytics. Best analytical fit; the tradeoff is it is a less transferable skill than plain SQL.
- **SQLite** - familiar, general-purpose, gives SQL practice, persists between runs. A "known quantity" alternative; the tradeoff is it is row-oriented and not analytics-optimized.

### Core principle: decouple analysis from the dashboard

Analysis logic lives in plain Python modules that take a DataFrame in and return DataFrames / numbers / figures out. The dashboard layer only calls those functions and renders their output.

This is the decision that de-risks every framework choice:

- It keeps the interesting, learning-focused Python separate from UI plumbing.
- It makes the dashboard framework low-stakes and swappable. Changing frameworks becomes a bounded rewrite of a thin view layer, never a rewrite of the analysis.
- It provides the portability benefit of a frontend/backend "separation" without paying the cost of building a separate frontend now.

### Dashboard / UI: Streamlit for the initial build

Streamlit was chosen over the alternatives for the initial build because it best serves the current priorities.

**Pros:**

- Fastest framework to learn by a wide margin; write a top-to-bottom Python script and widgets/charts appear.
- Keeps energy on analysis, not UI plumbing - directly serving the primary goal.
- Large community, strong pandas/Plotly support, ideal for personal dashboards and exploratory work.
- Squarely fits the stage-one prototype (spending visualization + forecasting with filters), so there is low risk it fails to carry the prototype.

**Cons (accepted, and deferred):**

- Its execution model reruns the whole script on every interaction. Simple at first, but awkward for complex interactivity and state management later.
- Layout customization is limited (though improving).
- It is a dashboard tool, not a general web-app framework - no built-in auth/multi-user story.

These costs are real but land later, and the decoupling principle makes them recoverable.

### The growth path

The plan is a lazy path, walked only when a concrete wall forces it - not pre-planned migrations. Choose the next rung based on which wall is hit:

- **Hit "I need richer or more dashboards" -> Dash.** Dash (Flask + Plotly/React under the hood, callback-based) is the most purpose-built, mature tool for complex analytical dashboards, and stretches the single-app Python paradigm the furthest. Its downside as a stepping stone is that its callback-graph paradigm is fairly Dash-specific and does not transfer cleanly to React.
- **Hit "I need app-like interaction / I want to start moving toward React" -> NiceGUI.** NiceGUI (FastAPI + Vue/Quasar, event-driven over websockets) builds genuine apps, not just dashboards. Its component/event/state model is the same mental model React uses, and its FastAPI foundation matches a modern API backend - so it transfers well toward the eventual split. Its downsides are a steeper learning curve, more UI code, and a smaller community than Streamlit.
- **Hit "I need to release publicly with auth and multi-user" -> Django (or FastAPI) + React.** This is the endpoint: a real two-app split with a JSON API backend and a separate SPA frontend. At this point the analysis modules lift out untouched and get wrapped in the backend.

Note on the migration reality: neither Dash nor NiceGUI yields reusable React frontend code (Dash's "React" is Plotly's internal components; NiceGUI's frontend is Vue). In any split, the frontend is rewritten. What a middle rung actually buys is mental-model transfer and backend footing, which is why NiceGUI is the more coherent bridge toward a React endpoint and Dash is the stronger place to settle if staying single-app.

If a single pre-planned path had to be named given the React/Django endpoint, it would be **Streamlit -> NiceGUI -> React/Django**, because every rung is a waypoint rather than a detour. But the path is deliberately not pre-committed.

## Alternatives Considered and Rejected (for now)

### NiceGUI as the starting point - rejected

More UI flexibility and a cleaner state model than Streamlit, but overkill for a dashboard and it pulls focus toward UI code - the opposite of the current priority. It is the natural next rung, not the starting one.

### Django as the starting point - rejected

Django ships zero data-viz/dashboard tooling, so its templating would force building every chart and interaction by hand in JavaScript - more UI work than a dashboard framework, not less. Its actual value (ORM, migrations, admin, auth, forms, API) is exactly the CRUD/persistence/multi-user machinery this tool does not need yet. The "clean separation" it offers is the same portability already gained for free via decoupled analysis modules, except paid for by building the whole frontend. Django is the right tool at the public-release endpoint, not now.

### Starting with Dash instead of Streamlit - rejected

The trade was: pay a certain, ongoing UI cost now (and forever) to avoid an uncertain, one-time migration later. That trade is poor:

- The migration it avoids is cheap - decoupling makes it a bounded view-layer swap, and Streamlit's UI layer is tiny, so little is thrown away.
- Dash is more verbose than Streamlit for the same dashboard at every stage, so the cost is per-feature and ongoing, not just upfront.
- It does not even avoid the big migration; a public release still lands at Django + React regardless.
- Interactivity needs are still unknown. Streamlit-first is the option-preserving move: build the analysis cheaply, learn how interactive the tool really needs to be, then upgrade with real knowledge instead of a guess.

Starting with Dash to avoid a future migration optimizes for a future that may not arrive, at a definite present cost charged in the currency (UI focus) least affordable right now. It would only be correct if we already knew Streamlit could not carry near-term needs - and the stage-one prototype sits squarely in Streamlit's sweet spot.
