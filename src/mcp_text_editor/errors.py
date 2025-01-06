"""Error handling for MCP Text Editor."""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
    """Error codes for MCP Text Editor."""

    # Protocol level errors (1000-1999)
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    INVALID_FIELD = "INVALID_FIELD"

    # File operation errors (2000-2999)
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_ALREADY_EXISTS = "FILE_ALREADY_EXISTS"
    FILE_ACCESS_DENIED = "FILE_ACCESS_DENIED"
    FILE_HASH_MISMATCH = "FILE_HASH_MISMATCH"

    # Content operation errors (3000-3999)
    CONTENT_HASH_MISMATCH = "CONTENT_HASH_MISMATCH"
    INVALID_LINE_RANGE = "INVALID_LINE_RANGE"
    CONTENT_TOO_LARGE = "CONTENT_TOO_LARGE"

    # Internal errors (9000-9999)
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class MCPError(Exception):
    """Base exception class for MCP Text Editor."""

    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format for JSON response."""
        error_dict = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details:
            error_dict["error"]["details"] = self.details
        return error_dict


class ValidationError(MCPError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        code: ErrorCode = ErrorCode.INVALID_SCHEMA,
    ):
        super().__init__(code=code, message=message, details=details)


class FileOperationError(MCPError):
    """Raised when file operations fail."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        code: ErrorCode = ErrorCode.FILE_NOT_FOUND,
    ):
        super().__init__(code=code, message=message, details=details)


class ContentOperationError(MCPError):
    """Raised when content operations fail."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        code: ErrorCode = ErrorCode.CONTENT_HASH_MISMATCH,
    ):
        super().__init__(code=code, message=message, details=details)


class InternalError(MCPError):
    """Raised when internal errors occur."""

    def __init__(
        self,
        message: str = "An internal error occurred",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=ErrorCode.INTERNAL_ERROR,
            message=message,
            details=details,
        )
