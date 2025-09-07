# Code Style and Conventions

## Code Formatting
- **Black**: Line length 88 characters, Python 3.13 target
- **isort**: Black-compatible profile for import sorting
- **Ruff**: Linting with pycodestyle, pyflakes, flake8-comprehensions, flake8-bugbear

## Type Hints
- Full type annotations throughout codebase
- mypy for static type checking
- Python 3.13 compatibility

## Naming Conventions
- Classes: PascalCase (e.g., `TextEditor`, `BaseHandler`)
- Methods/Functions: snake_case (e.g., `read_file_contents`, `calculate_hash`)
- Private methods: Leading underscore (e.g., `_validate_file_path`)
- Constants: UPPER_SNAKE_CASE

## File Organization
- Source code in `src/mcp_text_editor/`
- Handlers in `src/mcp_text_editor/handlers/`
- Tests in `tests/` directory
- Async/await patterns throughout

## Error Handling
- Custom error types with meaningful messages
- Hash-based conflict detection
- Comprehensive input validation
- No sensitive information in error messages