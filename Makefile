.PHONY: help test lint typecheck check format run-app docker-build docker-run

.DEFAULT_GOAL := help

# Print the list of targets, generated from the "## ..." comment on each target
# so the list documents itself (add a target with a "## text" comment and it
# shows up here automatically). $(MAKEFILE_LIST) is make's built-in variable for
# this file's name. grep keeps only the "target: ... ## comment" lines; sed
# strips the "target:...## " middle down to a single tab, leaving
# "target<tab>comment"; sort orders them alphabetically.
help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | sort

test:  ## Run the test suite
	uv run pytest

lint:  ## Lint and check formatting (no changes made)
	uv run ruff check .
	uv run ruff format --check .

typecheck:  ## Type-check with mypy (strict)
	uv run mypy

check: lint typecheck test  ## Run the full quality gate (lint + types + tests)

format:  ## Auto-fix formatting and lint via prek
	prek run --all-files

run-app:  ## Run the Streamlit app locally
	uv run streamlit run streamlit_app.py

docker-build:  ## Build the Docker image via compose
	docker compose build

docker-run:  ## Run the app in Docker (mounts ./data, serves on :8501)
	docker compose up
