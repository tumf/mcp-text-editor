# Changelog

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
