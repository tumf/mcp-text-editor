.PHONY: test format lint typecheck check coverage
.DEFAULT_GOAL := all

test:
	pytest

coverage:
	pytest --cov=mcp_text_editor --cov-report=term-missing

format:
	black src tests
	isort src tests
	ruff check --fix src tests


lint:
	black --check src tests
	isort --check src tests
	ruff check src tests

typecheck:
	mypy src tests

# Run all checks required before pushing
check:  lint typecheck
fix: format
all: format check coverage
