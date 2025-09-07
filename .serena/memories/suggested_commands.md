# Suggested Development Commands

## Essential Commands
```bash
# Install dependencies
uv sync --all-extras

# Run all tests
uv run pytest
make test

# Run tests with coverage
uv run pytest --cov=mcp_text_editor --cov-report=term-missing
make coverage

# Format code
uv run black src tests
uv run isort src tests
uv run ruff check --fix src tests
make format

# Lint code
uv run black --check src tests
uv run isort --check src tests
uv run ruff check src tests
make lint

# Type check
uv run mypy src tests
make typecheck

# Run all quality checks
make check

# Run complete validation (format + typecheck + coverage)
make all

# Start the server
python -m mcp_text_editor
```

## Testing Commands
```bash
# Run specific test file
uv run pytest tests/test_text_editor.py -v

# Run with verbose output
uv run pytest -v

# Run only failed tests
uv run pytest --lf
```

## System Commands (Linux)
- Standard Linux utilities: ls, cd, grep, find
- Git version control
- uv for Python package management
