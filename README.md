# MCP Text Editor Server

A Model Context Protocol (MCP) server that provides text file editing capabilities through a standardized API.

## Features

- Get text file contents with line range specification
- Read multiple ranges from multiple files in a single operation
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

### MCP Tools

The server provides two main tools:

#### get_text_file_contents

Get the contents of one or more text files with line range specification.

**Single Range Request:**

```json
{
  "file_path": "path/to/file.txt",
  "line_start": 1,
  "line_end": 10
}
```

**Multiple Ranges Request:**

```json
{
  "files": [
    {
      "file_path": "file1.txt",
      "ranges": [
        {"start": 1, "end": 10},
        {"start": 20, "end": 30}
      ]
    },
    {
      "file_path": "file2.txt",
      "ranges": [
        {"start": 5, "end": 15}
      ]
    }
  ]
}
```

Parameters:
- `file_path`: Path to the text file
- `line_start`/`start`: Line number to start from (1-based)
- `line_end`/`end`: Line number to end at (inclusive, null for end of file)

**Single Range Response:**

```json
{
  "contents": "File contents",
  "line_start": 1,
  "line_end": 10,
  "hash": "sha256-hash-of-contents",
  "file_lines": 50,
  "file_size": 1024
}
```

**Multiple Ranges Response:**

```json
{
  "file1.txt": [
    {
      "content": "Lines 1-10 content",
      "start_line": 1,
      "end_line": 10,
      "hash": "sha256-hash-1",
      "total_lines": 50,
      "content_size": 512
    },
    {
      "content": "Lines 20-30 content",
      "start_line": 20,
      "end_line": 30,
      "hash": "sha256-hash-2",
      "total_lines": 50,
      "content_size": 512
    }
  ],
  "file2.txt": [
    {
      "content": "Lines 5-15 content",
      "start_line": 5,
      "end_line": 15,
      "hash": "sha256-hash-3",
      "total_lines": 30,
      "content_size": 256
    }
  ]
}
```

#### edit_text_file_contents

Edit text file contents with conflict detection. Supports editing multiple files in a single operation.

**Request Format:**

```json
{
  "files": [
    {
      "path": "file1.txt",
      "hash": "sha256-hash-from-get-contents",
      "patches": [
        {
          "line_start": 5,
          "line_end": 8,
          "contents": "New content for lines 5-8\n"
        },
        {
          "line_start": 15,
          "line_end": 15,
          "contents": "Single line replacement\n"
        }
      ]
    },
    {
      "path": "file2.txt",
      "hash": "sha256-hash-from-get-contents",
      "patches": [
        {
          "line_start": 1,
          "line_end": 3,
          "contents": "Replace first three lines\n"
        }
      ]
    }
  ]
}
```

Important Notes:
1. Always get the current hash using get_text_file_contents before editing
2. Patches are applied from bottom to top to handle line number shifts correctly
3. Patches must not overlap within the same file
4. Line numbers are 1-based
5. If original content ends with newline, ensure patch content also ends with newline

**Success Response:**

```json
{
  "file1.txt": {
    "result": "ok",
    "hash": "sha256-hash-of-new-contents"
  },
  "file2.txt": {
    "result": "ok",
    "hash": "sha256-hash-of-new-contents"
  }
}
```

**Error Response:**

```json
{
  "file1.txt": {
    "result": "error",
    "reason": "File not found",
    "hash": null
  },
  "file2.txt": {
    "result": "error",
    "reason": "Content hash mismatch - file was modified",
    "hash": "current-hash",
    "content": "Current file content"
  }
}
```

### Common Usage Pattern

1. Get current content and hash:
```python
contents = await get_text_file_contents({
    "files": [
        {
            "file_path": "file.txt",
            "ranges": [{"start": 1, "end": null}]  # Read entire file
        }
    ]
})
```

2. Edit file content:
```python
result = await edit_text_file_contents({
    "files": [
        {
            "path": "file.txt",
            "hash": contents["file.txt"][0]["hash"],
            "patches": [
                {
                    "line_start": 5,
                    "line_end": 8,
                    "contents": "New content\n"
                }
            ]
        }
    ]
})
```

3. Handle conflicts:
```python
if result["file.txt"]["result"] == "error":
    if "hash mismatch" in result["file.txt"]["reason"]:
        # File was modified by another process
        # Get new content and retry
        pass
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

Current test coverage: 90%

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