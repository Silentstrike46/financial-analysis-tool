.PHONY: test format

test:
	uv run pytest

format:
	prek run --all-files
