"""Data models for the MCP Text Editor Server."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class GetTextFileContentsRequest(BaseModel):
    """Request model for getting text file contents."""

    file_path: str = Field(..., description="Path to the text file")
    start: int = Field(1, description="Starting line number (1-based)")
    end: Optional[int] = Field(None, description="Ending line number (inclusive)")


class GetTextFileContentsResponse(BaseModel):
    """Response model for getting text file contents."""

    contents: str = Field(..., description="File contents")
    start: int = Field(..., description="Starting line number")
    end: int = Field(..., description="Ending line number")
    hash: str = Field(..., description="Hash of the contents")


class EditPatch(BaseModel):
    """Model for a single edit patch operation."""

    start: int = Field(1, description="Starting line for edit")
    end: Optional[int] = Field(None, description="Ending line for edit")
    contents: str = Field(..., description="New content to insert")
    range_hash: Optional[str] = Field(
        None,  # None for new patches, must be explicitly set
        description="Hash of content being replaced. Empty string for insertions.",
    )

    @model_validator(mode="after")
    def validate_range_hash(self) -> "EditPatch":
        """Validate that range_hash is set and handle end field validation."""
        # range_hash must be explicitly set
        if self.range_hash is None:
            raise ValueError("range_hash is required")

        # For safety, convert None to the special range hash value
        if self.end is None and self.range_hash != "":
            # Special case: patch with end=None is allowed
            pass

        return self


class EditFileOperation(BaseModel):
    """Model for individual file edit operation."""

    path: str = Field(..., description="Path to the file")
    hash: str = Field(..., description="Hash of original contents")
    patches: List[EditPatch] = Field(..., description="Edit operations to apply")


class EditResult(BaseModel):
    """Model for edit operation result."""

    result: str = Field(..., description="Operation result (ok/error)")
    reason: Optional[str] = Field(None, description="Error message if applicable")
    hash: Optional[str] = Field(
        None, description="Current content hash (None for missing files)"
    )

    @model_validator(mode="after")
    def validate_error_result(self) -> "EditResult":
        """Remove hash when result is error."""
        if self.result == "error":
            object.__setattr__(self, "hash", None)
        return self

    def to_dict(self) -> Dict:
        """Convert EditResult to a dictionary."""
        result = {"result": self.result}
        if self.reason is not None:
            result["reason"] = self.reason
        if self.hash is not None:
            result["hash"] = self.hash
        return result


class EditTextFileContentsRequest(BaseModel):
    """Request model for editing text file contents.

    Example:
    {
        "files": [
            {
                "path": "/path/to/file",
                "hash": "abc123...",
                "patches": [
                    {
                        "start": 1,  # default: 1 (top of file)
                        "end": null,  # default: null (end of file)
                        "contents": "new content"
                    }
                ]
            }
        ]
    }
    """

    files: List[EditFileOperation] = Field(..., description="List of file operations")


class FileRange(BaseModel):
    """Represents a line range in a file."""

    start: int = Field(..., description="Starting line number (1-based)")
    end: Optional[int] = Field(
        None, description="Ending line number (null for end of file)"
    )
    range_hash: Optional[str] = Field(
        None, description="Hash of the content to be deleted"
    )


class FileRanges(BaseModel):
    """Represents a file and its line ranges."""

    file_path: str = Field(..., description="Path to the text file")
    ranges: List[FileRange] = Field(
        ..., description="List of line ranges to read from the file"
    )


class InsertTextFileContentsRequest(BaseModel):
    """Request model for inserting text into a file.

    Example:
    {
        "path": "/path/to/file",
        "file_hash": "abc123...",
        "after": 5,  # Insert after line 5
        "contents": "new content"
    }
    or
    {
        "path": "/path/to/file",
        "file_hash": "abc123...",
        "before": 5,  # Insert before line 5
        "contents": "new content"
    }
    """

    path: str = Field(..., description="Path to the text file")
    file_hash: str = Field(..., description="Hash of original contents")
    after: Optional[int] = Field(
        None, description="Line number after which to insert content"
    )
    before: Optional[int] = Field(
        None, description="Line number before which to insert content"
    )
    encoding: Optional[str] = Field(
        "utf-8", description="Text encoding (default: 'utf-8')"
    )
    contents: str = Field(..., description="Content to insert")

    @model_validator(mode="after")
    def validate_position(self) -> "InsertTextFileContentsRequest":
        """Validate that exactly one of after or before is specified."""
        if (self.after is None and self.before is None) or (
            self.after is not None and self.before is not None
        ):
            raise ValueError("Exactly one of 'after' or 'before' must be specified")
        return self

    @field_validator("after", "before")
    def validate_line_number(cls, v) -> Optional[int]:
        """Validate that line numbers are positive."""
        if v is not None and v < 1:
            raise ValueError("Line numbers must be positive")
        return v


class DeleteTextFileContentsRequest(BaseModel):
    """Request model for deleting text from a file.
    Example:
    {
        "file_path": "/path/to/file",
        "file_hash": "abc123...",
        "ranges": [
            {
                "start": 5,
                "end": 10,
                "range_hash": "def456..."
            }
        ]
    }
    """

    file_path: str = Field(..., description="Path to the text file")
    file_hash: str = Field(..., description="Hash of original contents")
    ranges: List[FileRange] = Field(..., description="List of ranges to delete")
    encoding: Optional[str] = Field(
        "utf-8", description="Text encoding (default: 'utf-8')"
    )


class PatchTextFileContentsRequest(BaseModel):
    """Request model for patching text in a file.
    Example:
    {
        "file_path": "/path/to/file",
        "file_hash": "abc123...",
        "patches": [
            {
                "start": 5,
                "end": 10,
                "contents": "new content",
                "range_hash": "def456..."
            }
        ]
    }
    """

    file_path: str = Field(..., description="Path to the text file")
    file_hash: str = Field(..., description="Hash of original contents")
    patches: List[EditPatch] = Field(..., description="List of patches to apply")
    encoding: Optional[str] = Field(
        "utf-8", description="Text encoding (default: 'utf-8')"
    )
