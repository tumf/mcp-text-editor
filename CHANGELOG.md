# Changelog

## [1.2.0] - 2026-01-05

### Fixed

- Fix hash calculation bug in `read_multiple_ranges` for multi-line ranges (#12)
  - The returned `end` value now correctly reflects the actual sliced range
  - This fixes "Content hash mismatch" errors when editing multi-line ranges

### Added

- Regression tests for hash consistency between read and edit operations

## [1.1.1] - 2026-01-05

### Fixed

- Add Gemini/Vertex AI schema compatibility for MCP tools (#11)
- Resolve lint and typecheck issues
- Path validation security improvements with secure hash compare and file locking

### Added

- Pre-commit hooks for code quality enforcement
- Docker support for running the tool

### Changed

- Improved codecov coverage targets

## [1.1.0] - 2024-12-23

### Added

- New text file manipulation operations:
  - `insert_text_file_contents`: Insert content at specific positions
  - `create_text_file`: Create new text files
  - `append_text_file_contents`: Append content to existing files
  - `delete_text_file_contents`: Delete specified ranges of text
  - `patch_text_file_contents`: Apply multiple patches to text files
- Enhanced error messages with useful suggestions for alternative editing methods

### Changed

- Unified parameter naming: renamed 'path' to 'file_path' across all APIs
- Improved handler organization by moving them to separate directory
- Made 'end' parameter required when not in append mode
- Enhanced validation for required parameters and file path checks
- Removed 'edit_text_file_contents' tool in favor of more specific operations
- Improved JSON serialization for handler responses

### Fixed

- Delete operation now uses dedicated deletion method instead of empty content replacement
- Improved range validation in delete operations
- Enhanced error handling across all operations
- Removed file hash from error responses for better clarity
- Fixed concurrency control with proper hash validation

## [1.0.2] - 2024-12-22

### Fixed

- Remove unexpected print logs

## [1.0.1] - 2024-12-17

### Added

- Support for custom file encoding options
- New file creation and line insertion capabilities
- Absolute path enforcement for file operations
- Append mode support for adding content at the end of files
- Range hash validation for content integrity

### Fixed

- Improved error messages and handling for file operations
- Enhanced file hash verification logic
- Better handling of empty file content
- Unified file_hash field naming across responses

### Changed

- Migrated to Pydantic models for better type validation
- Simplified server code and improved consistency
- Enhanced test coverage and code organization
- Updated documentation for clarity

## [1.0.0] - Initial Release

- Line-oriented text editor functionality
- Basic file operation support
- Hash-based conflict detection
