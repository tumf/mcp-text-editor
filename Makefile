.PHONY: test format lint typecheck check
.DEFAULT_GOAL := all

test:
	pytest

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
check:  lint typecheck test
fix: check format
all: format check