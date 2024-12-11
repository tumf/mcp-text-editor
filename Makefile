.PHONY: test format lint typecheck check

test:
	pytest

format:
	black .
	isort .

lint:
	ruff check .

typecheck:
	mypy mcp_shell_server tests

# Run all checks required before pushing
check: format lint typecheck test