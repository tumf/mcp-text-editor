"""Data models for the MCP Text Editor Server."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


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
    def validate_end_line(self) -> "EditPatch":
        """Validate that end line is present when not in append mode."""
        # range_hash must be explicitly set
        if self.range_hash is None:
            raise ValueError("range_hash is required")

        # For modifications (non-empty range_hash), end is required
        if self.range_hash != "" and self.end is None:
            raise ValueError("end line is required when not in append mode")
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

    def to_dict(self) -> Dict:
        """Convert EditResult to a dictionary."""
        return {
            "result": self.result,
            "reason": self.reason,
            "hash": self.hash,
        }


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


class FileRanges(BaseModel):
    """Represents a file and its line ranges."""

    file_path: str = Field(..., description="Path to the text file")
    ranges: List[FileRange] = Field(
        ..., description="List of line ranges to read from the file"
    )
