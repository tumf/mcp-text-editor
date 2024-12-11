# MCP Text Editor Server

A Model Context Protocol (MCP) server that provides text file editing capabilities through a standardized API.

## Features

- Get text file contents with line range specification
- Edit text file contents with conflict detection
- Support for multiple file operations

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
- `contents`: File contents
- `line_start`: Starting line number
- `line_end`: Ending line number
- `hash`: Hash of the contents

#### EditTextFileContents
Edit text file contents with conflict detection.

**Parameters:**
- `file_path`: Path to file with edit operations:
  - `hash`: Hash of original contents
  - `patches`: Array of edit operations:
    - `line_start`: (default: 1) Starting line for edit
    - `line_end`: (default: null) Ending line for edit
    - `contents`: New content to insert

**Returns:**
- `file_path`: Path with operation results:
  - `result`: "ok" or "error"
  - `reason`: Error message if applicable
  - `hash`: Current content hash
  - `content`: Current content (if hash conflict)

## Development

### Setup
1. Clone the repository
2. Install development dependencies: `pip install -e ".[dev]"`
3. Run tests: `pytest`

### Code Quality
- Ruff for linting
- Black for code formatting
- isort for import sorting
- mypy for type checking

### Testing
Tests are located in the `tests` directory and can be run with pytest:
```bash
pytest
```

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and code quality checks
5. Submit a pull request