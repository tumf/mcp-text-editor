# Task Completion Checklist

When completing any development task:

## Code Quality
1. **Format code**: `make format`
2. **Lint check**: `make lint`
3. **Type check**: `make typecheck`
4. **All quality checks**: `make check`

## Testing
1. **Run all tests**: `make test`
2. **Check coverage**: `make coverage`
3. **Run specific tests** for changed modules

## Security (especially for PR #13 fixes)
1. **Path validation**: Verify no directory traversal vulnerabilities
2. **Hash comparison**: Use `hmac.compare_digest` for all hash comparisons
3. **File locking**: Implement proper file locking for concurrent access
4. **Input sanitization**: Validate all user inputs

## Final Validation
1. **All tests pass**: `uv run pytest`
2. **Static checks**: `grep` for security pattern usage
3. **No regressions**: Existing functionality intact
4. **New tests added**: For security fixes and new features

## Pre-commit
- Format, lint, type check, and test before any commits
- Use `make all` for comprehensive validation
