.PHONY: test format run-app

test:
	uv run pytest

format:
	prek run --all-files

run-app:
	uv run streamlit run streamlit_app.py
