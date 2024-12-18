"""Tests for core service logic."""

import os

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
    content, start, end = service.read_file_contents(test_file, start=2, end=4)
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
        EditPatch(start=1, end=2, contents="content1", range_hash="hash1"),
        EditPatch(start=3, end=4, contents="content2", range_hash="hash2"),
    ]
    assert service.validate_patches(patches, 5) is True

    # Overlapping patches
    patches = [
        EditPatch(start=1, end=3, contents="content1", range_hash="hash1"),
        EditPatch(start=2, end=4, contents="content2", range_hash="hash2"),
    ]
    assert service.validate_patches(patches, 5) is False

    # Out of bounds patches
    patches = [EditPatch(start=1, end=10, contents="content1", range_hash="hash1")]
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
        patches=[EditPatch(start=2, end=2, contents="new line2", range_hash="hash1")],
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
        patches=[EditPatch(start=2, end=2, contents="new line2", range_hash="hash1")],
    )

    # Attempt edit
    result = service.edit_file_contents(file_path, operation)
    assert file_path in result
    edit_result = result[file_path]
    assert edit_result.result == "error"
    assert "hash mismatch" in edit_result.reason.lower()


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
                start=1, end=10, contents="new content", range_hash="hash1"
            )  # Beyond file length
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
        path=file_path,
        hash="any_hash",
        patches=[EditPatch(contents="new content", range_hash="")],
    )

    # Attempt edit
    result = service.edit_file_contents(file_path, operation)
    assert file_path in result
    edit_result = result[file_path]
    assert edit_result.result == "error"
    assert "no such file" in edit_result.reason.lower()


def test_edit_file_unexpected_error(service, tmp_path):
    """Test handling of unexpected errors during file editing."""
    # Setup test file and operation
    test_file = str(tmp_path / "error_test.txt")
    operation = EditFileOperation(
        path=test_file,
        hash="dummy_hash",
        patches=[EditPatch(contents="test content\n", start=1, range_hash="")],
    )

    # Try to edit non-existent file
    result = service.edit_file_contents(test_file, operation)
    edit_result = result[test_file]

    # Verify error handling
    assert edit_result.result == "error"
    assert "no such file" in edit_result.reason.lower()
    assert edit_result.hash is None


def test_edit_file_contents_permission_error(service, tmp_path):
    """Test handling of permission errors during file editing."""
    # Create test file
    test_file = tmp_path / "general_error_test.txt"
    test_content = "line1\nline2\nline3\n"
    test_file.write_text(test_content)
    file_path = str(test_file)

    # Make the file read-only to cause a permission error
    os.chmod(file_path, 0o444)

    # Create edit operation
    operation = EditFileOperation(
        path=file_path,
        hash=service.calculate_hash(test_content),
        patches=[EditPatch(start=2, end=2, contents="new line2", range_hash="hash1")],
    )

    # Attempt edit
    result = service.edit_file_contents(file_path, operation)
    edit_result = result[file_path]

    assert edit_result.result == "error"
    assert "permission denied" in edit_result.reason.lower()
    assert edit_result.hash is None

    # Clean up
    os.chmod(file_path, 0o644)


def test_edit_file_contents_general_exception(service, mocker):
    """Test handling of general exceptions during file editing."""
    test_file = "test.txt"
    operation = EditFileOperation(
        path=test_file,
        hash="hash123",
        patches=[EditPatch(contents="new content", start=1, range_hash="")],
    )

    # Mock edit_file to raise an exception
    # Create a test file
    with open(test_file, "w") as f:
        f.write("test content\n")

    try:
        # Mock os.path.exists to return True
        mocker.patch("os.path.exists", return_value=True)
        # Mock open to raise an exception
        mocker.patch(
            "builtins.open",
            side_effect=Exception("Unexpected error during file operation"),
        )

        result = service.edit_file_contents(test_file, operation)
        edit_result = result[test_file]

        assert edit_result.result == "error"
        assert "unexpected error" in edit_result.reason.lower()

    finally:
        # Clean up
        import os

        mocker.stopall()
        if os.path.exists(test_file):
            os.remove(test_file)
    assert edit_result.hash is None
