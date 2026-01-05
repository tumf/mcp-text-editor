# AGENTS.md - MCP Text Editor Server

This document provides guidance for AI coding agents working on this codebase.

## Project Overview

MCP Text Editor Server is a Python MCP (Model Context Protocol) server providing line-oriented text file editing capabilities. It's optimized for LLM tools with efficient partial file access to minimize token usage.

## Build System

Package manager: `uv` with `hatchling` as build backend.

### Essential Commands

```bash
# Install dependencies
make install              # or: uv sync --all-extras

# Run all tests
make test                 # or: uv run pytest

# Run a single test file
uv run pytest tests/test_text_editor.py -v

# Run a single test function
uv run pytest tests/test_text_editor.py::test_calculate_hash -v

# Run tests matching a pattern
uv run pytest -k "test_edit" -v

# Run tests with coverage
make coverage

# Format code
make format

# Lint + typecheck
make check

# Format + typecheck + coverage (default)
make all
```

## Project Structure

```
src/mcp_text_editor/
├── server.py             # FastMCP server implementation
├── text_editor.py        # Core text editor functionality
├── service.py            # Core service logic
├── models.py             # Pydantic data models
├── utils.py              # Security utilities (path validation, file locking)
└── handlers/             # MCP tool handlers (inherit from base.py)
tests/                    # Test files (pytest)
```

## Code Style Guidelines

### Formatting & Linting

- **Line length**: 88 characters (Black)
- **Formatter**: Black (Python 3.13 target)
- **Import sorting**: isort with "black" profile
- **Linter**: Ruff (pycodestyle, pyflakes, isort, flake8-comprehensions, flake8-bugbear)

### Imports

```python
# 1. Standard library
from typing import Any, Dict, List, Optional, Sequence, Tuple

# 2. Third-party
from mcp.types import TextContent
from pydantic import BaseModel, Field, model_validator

# 3. Local (relative imports within package)
from ..text_editor import TextEditor
from .base import BaseHandler
```

### Type Hints

Use comprehensive type annotations:
- `Optional[T]` or `X | None` for nullable types
- `Sequence` for read-only collections, `List` for mutable

```python
async def read_file_contents(
    self, file_path: str, start: int = 1, end: Optional[int] = None,
) -> Tuple[str, int, int, str, int, int]:
```

### Docstrings (Google-style)

```python
def method(self, arg: str) -> Dict[str, Any]:
    """Short description.

    Args:
        arg: Description of argument

    Returns:
        Description of return value
    """
```

### Naming Conventions

- **Classes**: PascalCase (`TextEditor`, `EditPatch`)
- **Functions/Methods/Variables**: snake_case (`read_file_contents`, `file_path`)
- **Constants**: UPPER_SNAKE_CASE
- **Test functions**: `test_<description>`

### Pydantic Models

```python
class EditPatch(BaseModel):
    """Model for a single edit patch operation."""
    start: int = Field(1, description="Starting line for edit")
    end: Optional[int] = Field(None, description="Ending line for edit")

    @model_validator(mode="after")
    def validate_range_hash(self) -> "EditPatch":
        ...
        return self
```

### Error Handling

Use standardized error response patterns:
```python
return {
    "result": "error",
    "reason": error_message,
    "suggestion": suggestion,
    "hint": hint,
}
```

### Handler Pattern

```python
class MyHandler(BaseHandler):
    def __init__(self, editor: TextEditor | None = None):
        super().__init__(editor)

    async def run_tool(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Execute the tool with given arguments."""
```

## Testing

```python
import pytest
from mcp_text_editor.text_editor import TextEditor

@pytest.fixture
def editor():
    return TextEditor()

@pytest.mark.asyncio
async def test_something(editor, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content\n")
    result = await editor.some_method(str(test_file))
    assert result["result"] == "ok"
```

- Use `tmp_path` fixture for temporary files
- Use `mocker` from pytest-mock for mocking

## Security

- Use path validation utilities from `utils.py`
- Use `locked_file()` context manager for file operations
- Use `secure_compare_hash()` for hash comparisons
- Never expose sensitive information in error messages

## Pre-commit

Run `make all` before pushing. Pre-commit hooks run `make check test` and validate ASCII-only commit messages.
