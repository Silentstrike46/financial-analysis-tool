# syntax=docker/dockerfile:1

# Stage 1: build the virtual environment with uv from the committed lockfile.
FROM astral/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install runtime dependencies first, in their own cached layer. This layer is
# rebuilt only when pyproject.toml or uv.lock change, not on every code edit.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Install the project itself (non-editable, so the package is copied into the
# venv and the runtime stage needs no src/ tree).
COPY src ./src
COPY README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-editable

# Stage 2: minimal runtime image with just the built venv and the entry point.
FROM python:3.13-slim-bookworm AS runtime

# Run as a non-root user.
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# The built virtual environment carries the app and all runtime dependencies.
COPY --from=builder /app/.venv /app/.venv
COPY streamlit_app.py ./

ENV PATH="/app/.venv/bin:$PATH"

USER appuser

EXPOSE 8501

# Data is mounted at runtime (see docker-compose.yml); it is never baked in.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "streamlit_app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
