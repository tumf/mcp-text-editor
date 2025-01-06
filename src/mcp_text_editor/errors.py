"""Custom error types for MCP Text Editor."""

from enum import Enum, auto


class ErrorCode(Enum):
    """Error codes for MCP Text Editor."""

    # Validation errors
    INVALID_REQUEST = auto()
    INVALID_RANGE = auto()

    # File operation errors
    FILE_NOT_FOUND = auto()
    FILE_ACCESS_DENIED = auto()
    FILE_CREATE_FAILED = auto()
    FILE_WRITE_FAILED = auto()

    # Content operation errors
    CONTENT_HASH_MISMATCH = auto()
    CONTENT_ENCODING_ERROR = auto()
    CONTENT_VALIDATION_ERROR = auto()


class MTextEditorError(Exception):
    """Base error class for MCP Text Editor."""

    def __init__(
        self, message: str, code: ErrorCode, details: dict | None = None
    ) -> None:
        """Initialize the error.

        Args:
            message (str): Error message
            code (ErrorCode): Error code
            details (dict | None, optional): Additional error details. Defaults to None.
        """
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ValidationError(MTextEditorError):
    """Raised when input validation fails."""


class FileOperationError(MTextEditorError):
    """Raised when file operations fail."""


class ContentOperationError(MTextEditorError):
    """Raised when content operations fail."""
