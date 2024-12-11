"""Data models for the MCP Text Editor Server."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class GetTextFileContentsRequest(BaseModel):
    """Request model for getting text file contents."""

    file_path: str = Field(..., description="Path to the text file")
    line_start: int = Field(1, description="Starting line number (1-based)")
    line_end: Optional[int] = Field(None, description="Ending line number (inclusive)")


class GetTextFileContentsResponse(BaseModel):
    """Response model for getting text file contents."""

    contents: str = Field(..., description="File contents")
    line_start: int = Field(..., description="Starting line number")
    line_end: int = Field(..., description="Ending line number")
    hash: str = Field(..., description="Hash of the contents")


class EditPatch(BaseModel):
    """Model for a single edit patch operation."""

    line_start: int = Field(1, description="Starting line for edit")
    line_end: Optional[int] = Field(None, description="Ending line for edit")
    contents: str = Field(..., description="New content to insert")


class EditFileOperation(BaseModel):
    """Model for file edit operation."""

    hash: str = Field(..., description="Hash of original contents")
    patches: List[EditPatch] = Field(..., description="Edit operations to apply")


class EditResult(BaseModel):
    """Model for edit operation result."""

    result: str = Field(..., description="Operation result (ok/error)")
    reason: Optional[str] = Field(None, description="Error message if applicable")
    hash: Optional[str] = Field(
        None, description="Current content hash (None for missing files)"
    )
    content: Optional[str] = Field(None, description="Current content if hash error")

    def to_dict(self) -> Dict:
        """Convert EditResult to a dictionary."""
        return {
            "result": self.result,
            "reason": self.reason,
            "hash": self.hash,
            "content": self.content,
        }


class FilePathOperation(BaseModel):
    """Model for file path operation.

    Example:
    {
        "/path/to/file": {
            "hash": "abc123...",
            "patches": [...]
        }
    }
    """

    file_operations: Dict[str, EditFileOperation] = Field(
        ..., description="File path to operation mapping"
    )


class EditTextFileContentsRequest(BaseModel):
    """Request model for editing text file contents."""

    args: List[FilePathOperation] = Field(
        ..., description="List of file path operations"
    )
