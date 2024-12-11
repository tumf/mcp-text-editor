.PHONY: test format lint typecheck check

test:
	pytest

format:
	black .
	isort .
	ruff check --fix .


lint:
	black --check .
	isort --check .
	ruff check .

typecheck:
	mypy mcp_shell_server tests

# Run all checks required before pushing
check:  lint typecheck test
fix: check format
all: check