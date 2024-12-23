"""Tests for data models."""

import pytest
from pydantic import ValidationError

from mcp_text_editor.models import (
    EditFileOperation,
    EditPatch,
    EditResult,
    EditTextFileContentsRequest,
    FileRange,
    FileRanges,
    GetTextFileContentsRequest,
    GetTextFileContentsResponse,
)


def test_get_text_file_contents_request():
    """Test GetTextFileContentsRequest model."""
    # Test with only required field
    request = GetTextFileContentsRequest(file_path="/path/to/file.txt")
    assert request.file_path == "/path/to/file.txt"
    assert request.start == 1  # Default value
    assert request.end is None  # Default value

    # Test with all fields
    request = GetTextFileContentsRequest(file_path="/path/to/file.txt", start=5, end=10)
    assert request.file_path == "/path/to/file.txt"
    assert request.start == 5
    assert request.end == 10

    # Test validation error - missing required field
    with pytest.raises(ValidationError):
        GetTextFileContentsRequest()


def test_get_text_file_contents_response():
    """Test GetTextFileContentsResponse model."""
    response = GetTextFileContentsResponse(
        contents="file content", start=1, end=10, hash="hash123"
    )
    assert response.contents == "file content"
    assert response.start == 1
    assert response.end == 10
    assert response.hash == "hash123"

    # Test validation error - missing required fields
    with pytest.raises(ValidationError):
        GetTextFileContentsResponse()


def test_edit_patch():
    """Test EditPatch model."""
    # Test that range_hash is required
    with pytest.raises(ValueError, match="range_hash is required"):
        EditPatch(contents="new content")
    with pytest.raises(ValueError, match="range_hash is required"):
        EditPatch(contents="new content", start=1)

    # Test append mode with empty range_hash
    patch = EditPatch(contents="new content", start=1, range_hash="")
    assert patch.contents == "new content"
    assert patch.start == 1
    assert patch.end is None

    # Test modification mode (requires end when range_hash is present)
    patch = EditPatch(start=5, end=10, contents="new content", range_hash="somehash")
    assert patch.start == 5
    assert patch.end == 10
    assert patch.contents == "new content"
    assert patch.range_hash == "somehash"

    # Test validation error - missing required field
    with pytest.raises(ValidationError):
        EditPatch()


def test_edit_file_operation():
    """Test EditFileOperation model."""
    patches = [
        EditPatch(contents="content1", range_hash=""),  # append mode
        EditPatch(start=2, end=3, contents="content2", range_hash="somehash"),
    ]
    operation = EditFileOperation(
        path="/path/to/file.txt", hash="hash123", patches=patches
    )
    assert operation.path == "/path/to/file.txt"
    assert operation.hash == "hash123"
    assert len(operation.patches) == 2
    assert operation.patches[0].contents == "content1"
    assert operation.patches[0].range_hash == ""  # append mode
    assert operation.patches[1].start == 2
    assert operation.patches[1].range_hash == "somehash"  # modification mode

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
    result_dict = result.to_dict()
    assert result_dict["result"] == "ok"
    assert result_dict["hash"] == "newhash123"
    assert "reason" not in result_dict

    # Test error result with reason
    result = EditResult(
        result="error",
        reason="hash mismatch",
        hash="currenthash123",
    )
    assert result.result == "error"
    assert result.reason == "hash mismatch"
    assert result.hash is None
    result_dict = result.to_dict()
    assert result_dict["result"] == "error"
    assert result_dict["reason"] == "hash mismatch"
    assert "hash" not in result_dict

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
                patches=[EditPatch(contents="new content", range_hash="")],
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
                patches=[EditPatch(contents="content1", range_hash="")],
            ),
            EditFileOperation(
                path="/path/to/file2.txt",
                hash="hash456",
                patches=[EditPatch(start=2, contents="content2", range_hash="")],
            ),
        ]
    )
    assert len(request.files) == 2
    assert request.files[0].path == "/path/to/file1.txt"
    assert request.files[1].path == "/path/to/file2.txt"

    # Test validation error - missing required field
    with pytest.raises(ValidationError):
        EditTextFileContentsRequest()


def test_edit_result_to_dict():
    """Test EditResult's to_dict method."""
    # Test successful result
    result = EditResult(result="ok", hash="newhash123")
    result_dict = result.to_dict()
    assert result_dict == {"result": "ok", "hash": "newhash123"}

    # Test error result
    result = EditResult(
        result="error",
        reason="hash mismatch",
        hash="currenthash123",
    )
    result_dict = result.to_dict()
    assert result_dict == {"result": "error", "reason": "hash mismatch"}


def test_file_range():
    """Test FileRange model."""
    # Test with only required field
    range_ = FileRange(start=1)
    assert range_.start == 1
    assert range_.end is None  # Default value

    # Test with all fields
    range_ = FileRange(start=5, end=10)
    assert range_.start == 5
    assert range_.end == 10

    # Test validation error - missing required field
    with pytest.raises(ValidationError):
        FileRange()


def test_file_ranges():
    """Test FileRanges model."""
    ranges = [
        FileRange(start=1),
        FileRange(start=5, end=10),
    ]
    file_ranges = FileRanges(file_path="/path/to/file.txt", ranges=ranges)
    assert file_ranges.file_path == "/path/to/file.txt"
    assert len(file_ranges.ranges) == 2
    assert file_ranges.ranges[0].start == 1
    assert file_ranges.ranges[0].end is None
    assert file_ranges.ranges[1].start == 5
    assert file_ranges.ranges[1].end == 10

    # Test validation error - missing required fields
    with pytest.raises(ValidationError):
        FileRanges()

    # Test validation error - invalid ranges type
    with pytest.raises(ValidationError):
        FileRanges(file_path="/path/to/file.txt", ranges="invalid")
