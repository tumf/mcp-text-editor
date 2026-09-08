# MCP Text Editor Server

[![codecov](https://codecov.io/gh/tumf/mcp-text-editor/branch/main/graph/badge.svg?token=52D51U0ZUR)](https://codecov.io/gh/tumf/mcp-text-editor)
[![smithery badge](https://smithery.ai/badge/mcp-text-editor)](https://smithery.ai/server/mcp-text-editor)
[![Glama MCP Server](https://glama.ai/mcp/servers/k44dnvso10/badge)](https://glama.ai/mcp/servers/k44dnvso10)

A Model Context Protocol (MCP) server that provides line-oriented text file editing capabilities through a standardized API. Optimized for LLM tools with efficient partial file access to minimize token usage.

## Quick Start for Claude.app Users

To use this editor with Claude.app, add the following configuration to your prompt:

```shell
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

```json
{
  "mcpServers": {
    "text-editor": {
      "command": "uvx",
      "args": [
        "mcp-text-editor"
      ]
    }
  }
}
```

## Overview

MCP Text Editor Server is designed to facilitate safe and efficient line-based text file operations in a client-server architecture. It implements the Model Context Protocol, ensuring reliable file editing with robust conflict detection and resolution. The line-oriented approach makes it ideal for applications requiring synchronized file access, such as collaborative editing tools, automated text processing systems, or any scenario where multiple processes need to modify text files safely. The partial file access capability is particularly valuable for LLM-based tools, as it helps reduce token consumption by loading only the necessary portions of files.

### Key Benefits

- Line-based editing operations
- Token-efficient partial file access with line-range specifications
- Optimized for LLM tool integration
- Safe concurrent editing with hash-based validation
- Atomic multi-file operations
- Robust error handling with custom error types
- Comprehensive encoding support (utf-8, shift_jis, latin1, etc.)

## Features

- Line-oriented text file editing and reading
- Smart partial file access to minimize token usage in LLM applications
- Get text file contents with line range specification
- Read multiple ranges from multiple files in a single operation
- Line-based patch application with correct handling of line number shifts
- Edit text file contents with conflict detection
- Flexible character encoding support (utf-8, shift_jis, latin1, etc.)
- Support for multiple file operations
- Proper handling of concurrent edits with hash-based validation
- Memory-efficient processing of large files

## Requirements

- Python 3.11 or higher
- POSIX-compliant operating system (Linux, macOS, etc.) or Windows
- Sufficient disk space for text file operations
- File system permissions for read/write operations

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

## Requirements

- Python 3.13+
- POSIX-compliant operating system (Linux, macOS, etc.) or Windows
- File system permissions for read/write operations

## Installation

### Run via uvx

```bash
uvx mcp-text-editor
```

### Installing via Smithery

To install Text Editor Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp-text-editor):

```bash
npx -y @smithery/cli install mcp-text-editor --client claude
```

### Manual Installation

1. Install Python 3.13+

```bash
pyenv install 3.13.0
pyenv local 3.13.0
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

## Usage

Start the server:

```bash
python -m mcp_text_editor
```

### MCP Tools

The server provides several tools for text file manipulation:

#### get_text_file_contents

Get the contents of one or more text files with line range specification.

**Request:**

The tool accepts a `files` array. Each file contains one or more line ranges using
`start` and `end`. File paths must be absolute.

```json
{
  "files": [
    {
      "file_path": "/absolute/path/to/file.txt",
      "ranges": [
        {"start": 1, "end": 10},
        {"start": 20, "end": null}
      ]
    }
  ],
  "encoding": "utf-8"
}
```

Parameters:

- `file_path`: Absolute path to the text file
- `start`: First line to read (1-based)
- `end`: Last line to read (inclusive); `null` reads through end of file
- `encoding`: File encoding for all requested files (default: `utf-8`)

**Response:**

The top-level object is keyed by absolute file path. `file_hash` protects the
whole-file state; each `range_hash` protects the corresponding range.

```json
{
  "/absolute/path/to/file.txt": {
    "file_hash": "sha256-hash-of-the-file",
    "ranges": [
      {
        "content": "Lines 1-10 content",
        "start": 1,
        "end": 10,
        "range_hash": "sha256-hash-of-this-range",
        "total_lines": 50,
        "content_size": 512
      }
    ]
  }
}
```

#### patch_text_file_contents

Apply one or more non-overlapping patches to one file. Read the target ranges
first and pass both the current `file_hash` and each matching `range_hash`.

**Request:**

```json
{
  "file_path": "/absolute/path/to/file.txt",
  "file_hash": "sha256-hash-from-get-response",
  "patches": [
    {
      "start": 5,
      "end": 8,
      "range_hash": "sha256-hash-of-lines-5-through-8",
      "contents": "New content for lines 5-8\n"
    }
  ],
  "encoding": "utf-8"
}
```

Important notes:

1. Obtain current hashes with `get_text_file_contents` immediately before editing.
2. Use `start` and `end`; `line_start` and `line_end` are not accepted.
3. Patches are applied from bottom to top and must not overlap.
4. Line numbers are 1-based.
5. Use `append_text_file_contents`, `insert_text_file_contents`, or
   `delete_text_file_contents` for those specialized operations.
6. Use the same encoding for the read and patch calls.

**Success response:**

```json
{
  "result": "ok",
  "file_hash": "sha256-hash-of-new-file-contents",
  "reason": null,
  "suggestion": null,
  "hint": null
}
```

**Error response:**

```json
{
  "result": "error",
  "reason": "Content range hash mismatch",
  "suggestion": "get",
  "hint": "Please run get_text_file_contents first to get current content and hashes"
}
```

### Common Usage Pattern

1. Call `get_text_file_contents` for the exact range to replace.
2. Read `file_hash` and the range's `range_hash` from the keyed response.
3. Call `patch_text_file_contents` with those hashes and the same range.
4. If the result is an error, read the file again before retrying.

```python
path = "/absolute/path/to/file.txt"
contents = await get_text_file_contents({
    "files": [{
        "file_path": path,
        "ranges": [{"start": 5, "end": 8}]
    }]
})
file_info = contents[path]
selected_range = file_info["ranges"][0]

result = await patch_text_file_contents({
    "file_path": path,
    "file_hash": file_info["file_hash"],
    "patches": [{
        "start": 5,
        "end": 8,
        "range_hash": selected_range["range_hash"],
        "contents": "New content\n"
    }]
})
```

### Error Handling

The server handles various error cases:
- File not found
- Permission errors
- Hash mismatches (concurrent edit detection)
- Invalid patch ranges
- Overlapping patches
- Encoding errors (when file cannot be decoded with specified encoding)
- Line number out of bounds

## Security Considerations

- File Path Validation: The server validates all file paths to prevent directory traversal attacks
- Access Control: Proper file system permissions should be set to restrict access to authorized directories
- Hash Validation: All file modifications are validated using SHA-256 hashes to prevent race conditions
- Input Sanitization: All user inputs are properly sanitized and validated
- Error Handling: Sensitive information is not exposed in error messages

## Troubleshooting

### Common Issues

1. Permission Denied
   - Check file and directory permissions
   - Ensure the server process has necessary read/write access

2. Hash Mismatch and Range Hash Errors
   - The file was modified by another process
   - Content being replaced has changed
   - Run get_text_file_contents to get fresh hashes

3. Encoding Issues
   - Verify file encoding matches the specified encoding
   - Use utf-8 for new files
   - Check for BOM markers in files

4. Connection Issues
   - Verify the server is running and accessible
   - Check network configuration and firewall settings

5. Performance Issues
   - Consider using smaller line ranges for large files
   - Monitor system resources (memory, disk space)
   - Use appropriate encoding for file type

## Development

### Setup

1. Clone the repository
2. Create and activate a Python virtual environment
3. Install development dependencies: `uv pip install -e ".[dev]"`
4. Run tests: `make all`

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
