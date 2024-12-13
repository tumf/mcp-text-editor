"""Tests for core service logic."""

import pytest

from mcp_text_editor.models import EditFileOperation, EditPatch, EditResult
from mcp_text_editor.service import TextEditorService


@pytest.fixture
def service():
    """Create TextEditorService instance."""
    return TextEditorService()


def test_calculate_hash(service):
    """Test hash calculation."""
    content = "test content"
    hash1 = service.calculate_hash(content)
    hash2 = service.calculate_hash(content)
    assert hash1 == hash2
    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA-256 hash length


def test_read_file_contents(service, test_file):
    """Test reading file contents."""
    # Test reading entire file
    content, start, end = service.read_file_contents(test_file)
    assert content == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    assert start == 1
    assert end == 5

    # Test reading specific lines
    content, start, end = service.read_file_contents(
        test_file, line_start=2, line_end=4
    )
    assert content == "Line 2\nLine 3\nLine 4\n"
    assert start == 2
    assert end == 4


def test_read_file_contents_invalid_file(service):
    """Test reading non-existent file."""
    with pytest.raises(FileNotFoundError):
        service.read_file_contents("nonexistent.txt")


def test_validate_patches(service):
    """Test patch validation."""
    # Valid patches
    patches = [
        EditPatch(line_start=1, line_end=2, contents="content1"),
        EditPatch(line_start=3, line_end=4, contents="content2"),
    ]
    assert service.validate_patches(patches, 5) is True

    # Overlapping patches
    patches = [
        EditPatch(line_start=1, line_end=3, contents="content1"),
        EditPatch(line_start=2, line_end=4, contents="content2"),
    ]
    assert service.validate_patches(patches, 5) is False

    # Out of bounds patches
    patches = [EditPatch(line_start=1, line_end=10, contents="content1")]
    assert service.validate_patches(patches, 5) is False


def test_edit_file_contents(service, tmp_path):
    """Test editing file contents."""
    # Create test file
    test_file = tmp_path / "edit_test.txt"
    test_content = "line1\nline2\nline3\n"
    test_file.write_text(test_content)
    file_path = str(test_file)

    # Calculate initial hash
    initial_hash = service.calculate_hash(test_content)

    # Create edit operation
    operation = EditFileOperation(
        path=file_path,
        hash=initial_hash,
        patches=[EditPatch(line_start=2, line_end=2, contents="new line2")],
    )

    # Apply edit
    result = service.edit_file_contents(file_path, operation)
    assert file_path in result
    edit_result = result[file_path]
    assert isinstance(edit_result, EditResult)
    assert edit_result.result == "ok"

    # Verify changes
    new_content = test_file.read_text()
    assert "new line2" in new_content


def test_edit_file_contents_hash_mismatch(service, tmp_path):
    """Test editing with hash mismatch."""
    # Create test file
    test_file = tmp_path / "hash_mismatch_test.txt"
    test_content = "line1\nline2\nline3\n"
    test_file.write_text(test_content)
    file_path = str(test_file)

    # Create edit operation with incorrect hash
    operation = EditFileOperation(
        path=file_path,
        hash="incorrect_hash",
        patches=[EditPatch(line_start=2, line_end=2, contents="new line2")],
    )

    # Attempt edit
    result = service.edit_file_contents(file_path, operation)
    assert file_path in result
    edit_result = result[file_path]
    assert edit_result.result == "error"
    assert "hash mismatch" in edit_result.reason.lower()
    assert edit_result.content == test_content


def test_edit_file_contents_invalid_patches(service, tmp_path):
    """Test editing with invalid patches."""
    # Create test file
    test_file = tmp_path / "invalid_patches_test.txt"
    test_content = "line1\nline2\nline3\n"
    test_file.write_text(test_content)
    file_path = str(test_file)

    # Calculate initial hash
    initial_hash = service.calculate_hash(test_content)

    # Create edit operation with invalid patches
    operation = EditFileOperation(
        path=file_path,
        hash=initial_hash,
        patches=[
            EditPatch(
                line_start=1, line_end=10, contents="new content"  # Beyond file length
            )
        ],
    )

    # Attempt edit
    result = service.edit_file_contents(file_path, operation)
    assert file_path in result
    edit_result = result[file_path]
    assert edit_result.result == "error"
    assert "invalid patch" in edit_result.reason.lower()


def test_edit_file_contents_file_error(service):
    """Test editing with file error."""
    file_path = "nonexistent.txt"
    # Attempt to edit non-existent file
    operation = EditFileOperation(
        path=file_path, hash="any_hash", patches=[EditPatch(contents="new content")]
    )

    # Attempt edit
    result = service.edit_file_contents(file_path, operation)
    assert file_path in result
    edit_result = result[file_path]
    assert edit_result.result == "error"
    assert "no such file" in edit_result.reason.lower()
