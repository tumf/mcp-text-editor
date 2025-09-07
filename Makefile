.PHONY: test format lint typecheck check coverage
.DEFAULT_GOAL := all

test:
	uv run pytest

install:
	uv sync --all-extras 

coverage:
	uv run pytest --cov=mcp_text_editor --cov-report=term-missing

format:
	uv run black src tests
	uv run isort src tests
	uv run ruff check --fix src tests


lint:
	uv run black --check src tests
	uv run isort --check src tests
	uv run ruff check src tests

typecheck:
	uv run mypy src tests

# Run all checks required before pushing
check:  lint typecheck
fix: format
all: format typecheck coverage
