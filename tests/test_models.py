"""Tests for data models."""

import pytest
from pydantic import ValidationError

from mcp_text_editor.models import (
    EditFileOperation,
    EditPatch,
    EditResult,
    EditTextFileContentsRequest,
    GetTextFileContentsRequest,
    GetTextFileContentsResponse,
)


def test_get_text_file_contents_request():
    """Test GetTextFileContentsRequest model."""
    # Test with only required field
    request = GetTextFileContentsRequest(file_path="/path/to/file.txt")
    assert request.file_path == "/path/to/file.txt"
    assert request.line_start == 1  # Default value
    assert request.line_end is None  # Default value

    # Test with all fields
    request = GetTextFileContentsRequest(
        file_path="/path/to/file.txt", line_start=5, line_end=10
    )
    assert request.file_path == "/path/to/file.txt"
    assert request.line_start == 5
    assert request.line_end == 10

    # Test validation error - missing required field
    with pytest.raises(ValidationError):
        GetTextFileContentsRequest()


def test_get_text_file_contents_response():
    """Test GetTextFileContentsResponse model."""
    response = GetTextFileContentsResponse(
        contents="file content", line_start=1, line_end=10, hash="hash123"
    )
    assert response.contents == "file content"
    assert response.line_start == 1
    assert response.line_end == 10
    assert response.hash == "hash123"

    # Test validation error - missing required fields
    with pytest.raises(ValidationError):
        GetTextFileContentsResponse()


def test_edit_patch():
    """Test EditPatch model."""
    # Test with only required field
    patch = EditPatch(contents="new content")
    assert patch.contents == "new content"
    assert patch.line_start == 1  # Default value
    assert patch.line_end is None  # Default value

    # Test with all fields
    patch = EditPatch(line_start=5, line_end=10, contents="new content")
    assert patch.line_start == 5
    assert patch.line_end == 10
    assert patch.contents == "new content"

    # Test validation error - missing required field
    with pytest.raises(ValidationError):
        EditPatch()


def test_edit_file_operation():
    """Test EditFileOperation model."""
    patches = [
        EditPatch(contents="content1"),
        EditPatch(line_start=2, line_end=3, contents="content2"),
    ]
    operation = EditFileOperation(
        path="/path/to/file.txt", hash="hash123", patches=patches
    )
    assert operation.path == "/path/to/file.txt"
    assert operation.hash == "hash123"
    assert len(operation.patches) == 2
    assert operation.patches[0].contents == "content1"
    assert operation.patches[1].line_start == 2

    # Test validation error - missing required fields
    with pytest.raises(ValidationError):
        EditFileOperation()

    # Test validation error - invalid patches type
    with pytest.raises(ValidationError):
        EditFileOperation(path="/path/to/file.txt", hash="hash123", patches="invalid")


def test_edit_result():
    """Test EditResult model."""
    # Test successful result
    result = EditResult(result="ok", hash="newhash123")
    assert result.result == "ok"
    assert result.hash == "newhash123"
    assert result.reason is None
    assert result.content is None

    # Test error result with reason and content
    result = EditResult(
        result="error",
        reason="hash mismatch",
        hash="currenthash123",
        content="current content",
    )
    assert result.result == "error"
    assert result.reason == "hash mismatch"
    assert result.hash == "currenthash123"
    assert result.content == "current content"

    # Test validation error - missing required fields
    with pytest.raises(ValidationError):
        EditResult()


def test_edit_text_file_contents_request():
    """Test EditTextFileContentsRequest model."""
    # Test with single file operation
    request = EditTextFileContentsRequest(
        files=[
            EditFileOperation(
                path="/path/to/file.txt",
                hash="hash123",
                patches=[EditPatch(contents="new content")],
            )
        ]
    )
    assert len(request.files) == 1
    assert request.files[0].path == "/path/to/file.txt"
    assert request.files[0].hash == "hash123"
    assert len(request.files[0].patches) == 1
    assert request.files[0].patches[0].contents == "new content"

    # Test with multiple file operations
    request = EditTextFileContentsRequest(
        files=[
            EditFileOperation(
                path="/path/to/file1.txt",
                hash="hash123",
                patches=[EditPatch(contents="content1")],
            ),
            EditFileOperation(
                path="/path/to/file2.txt",
                hash="hash456",
                patches=[EditPatch(line_start=2, contents="content2")],
            ),
        ]
    )
    assert len(request.files) == 2
    assert request.files[0].path == "/path/to/file1.txt"
    assert request.files[1].path == "/path/to/file2.txt"

    # Test validation error - missing required field
    with pytest.raises(ValidationError):
        EditTextFileContentsRequest()
