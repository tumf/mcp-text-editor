# MCP Text Editor Server

A Model Context Protocol (MCP) server that provides text file editing capabilities through a standardized API.

## Features

- Get text file contents with line range specification
- Edit text file contents with conflict detection
- Support for multiple file operations
- Proper handling of concurrent edits with hash-based validation
- Line-based patch application with correct handling of line number shifts
- Robust error handling and validation
- Memory-efficient processing of large files

## Development Environment Setup

1. Install Python 3.11+

```bash
pyenv install 3.11.6
pyenv local 3.11.6
```

2. Install uv (recommended) or pip

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Create virtual environment and install dependencies

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

## Installation

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Usage

Start the server:

```bash
python -m mcp_text_editor
```

### API Endpoints

#### GetTextFileContents

Get the contents of a text file within a specified line range.

**Parameters:**
- `file_path`: (required) Path to the text file
- `line_start`: (optional, default: 1) Starting line number
- `line_end`: (optional, default: null) Ending line number

**Returns:**

```json
{
  "contents": "File contents",
  "line_start": 1,
  "line_end": 5,
  "hash": "sha256-hash-of-contents"
}
```

#### EditTextFileContents

Edit text file contents with conflict detection. Can handle multiple files and multiple patches per file.
Patches are always applied from bottom to top to handle line number shifts correctly.

**Parameters:**

```json
{
  "file_path": {
    "hash": "sha256-hash-of-original-contents",
    "patches": [
      {
        "line_start": 1,
        "line_end": null,
        "contents": "New content"
      }
    ]
  }
}
```

**Returns:**

```json
{
  "<file path>": {
    "result": "ok",
    "hash": "sha256-hash-of-new-contents"
  }
}
```

For error cases:

```json
{
  "<file path>": {
    "result": "error",
    "reason": "Error message",
    "hash": "current-hash",
    "content": "Current content (if hash mismatch)"
  }
}
```

### Error Handling

The server handles various error cases:
- File not found
- Permission errors
- Hash mismatches (concurrent edit detection)
- Invalid patch ranges
- Overlapping patches
- Line number out of bounds

## Development

### Setup

1. Clone the repository
2. Create and activate a Python virtual environment
3. Install development dependencies: `pip install -e ".[dev]"`
4. Run tests: `pytest`

### Code Quality Tools

- Ruff for linting
- Black for code formatting
- isort for import sorting
- mypy for type checking
- pytest-cov for test coverage

### Testing

Tests are located in the `tests` directory and can be run with pytest:

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=mcp_text_editor --cov-report=term-missing

# Run specific test file
pytest tests/test_text_editor.py -v
```

Current test coverage: 88%

### Project Structure

```
mcp-text-editor/
├── mcp_text_editor/
│   ├── __init__.py
│   ├── __main__.py      # Entry point
│   ├── models.py        # Data models
│   ├── server.py        # MCP Server implementation
│   ├── service.py       # Core service logic
│   └── text_editor.py   # Text editor functionality
├── tests/               # Test files
└── pyproject.toml       # Project configuration
```

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and code quality checks
5. Submit a pull request

### Type Hints

This project uses Python type hints throughout the codebase. Please ensure any contributions maintain this.

### Error Handling

All error cases should be handled appropriately and return meaningful error messages. The server should never crash due to invalid input or file operations.

### Testing

New features should include appropriate tests. Try to maintain or improve the current test coverage.

### Code Style

All code should be formatted with Black and pass Ruff linting. Import sorting should be handled by isort.
