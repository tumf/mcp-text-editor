"""Tests for delete_text_file_contents functionality."""

import json

import pytest

from mcp_text_editor.models import DeleteTextFileContentsRequest, FileRange
from mcp_text_editor.service import TextEditorService


@pytest.fixture
def service():
    """Create TextEditorService instance."""
    return TextEditorService()


def test_delete_text_file_contents_basic(service, tmp_path):
    """Test basic delete operation."""
    # Create test file
    test_file = tmp_path / "delete_test.txt"
    test_content = "line1\nline2\nline3\n"
    test_file.write_text(test_content)
    file_path = str(test_file)

    # Calculate initial hash
    initial_hash = service.calculate_hash(test_content)

    # Create delete request
    request = DeleteTextFileContentsRequest(
        file_path=file_path,
        file_hash=initial_hash,
        ranges=[
            FileRange(start=2, end=2, range_hash=service.calculate_hash("line2\n"))
        ],
        encoding="utf-8",
    )

    # Apply delete
    result = service.delete_text_file_contents(request)
    assert file_path in result
    delete_result = result[file_path]
    assert delete_result.result == "ok"

    # Verify changes
    new_content = test_file.read_text()
    assert new_content == "line1\nline3\n"


def test_delete_text_file_contents_hash_mismatch(service, tmp_path):
    """Test deleting with hash mismatch."""
    # Create test file
    test_file = tmp_path / "hash_mismatch_test.txt"
    test_content = "line1\nline2\nline3\n"
    test_file.write_text(test_content)
    file_path = str(test_file)

    # Create delete request with incorrect hash
    request = DeleteTextFileContentsRequest(
        file_path=file_path,
        file_hash="incorrect_hash",
        ranges=[
            FileRange(start=2, end=2, range_hash=service.calculate_hash("line2\n"))
        ],
        encoding="utf-8",
    )

    # Attempt delete
    result = service.delete_text_file_contents(request)
    assert file_path in result
    delete_result = result[file_path]
    assert delete_result.result == "error"
    assert "hash mismatch" in delete_result.reason.lower()


def test_delete_text_file_contents_invalid_ranges(service, tmp_path):
    """Test deleting with invalid ranges."""
    # Create test file
    test_file = tmp_path / "invalid_ranges_test.txt"
    test_content = "line1\nline2\nline3\n"
    test_file.write_text(test_content)
    file_path = str(test_file)

    # Calculate initial hash
    initial_hash = service.calculate_hash(test_content)

    # Create delete request with invalid ranges
    request = DeleteTextFileContentsRequest(
        file_path=file_path,
        file_hash=initial_hash,
        ranges=[FileRange(start=1, end=10, range_hash="hash1")],  # Beyond file length
        encoding="utf-8",
    )

    # Attempt delete
    result = service.delete_text_file_contents(request)
    assert file_path in result
    delete_result = result[file_path]
    assert delete_result.result == "error"
    assert "invalid ranges" in delete_result.reason.lower()


def test_delete_text_file_contents_range_hash_mismatch(service, tmp_path):
    """Test deleting with range hash mismatch."""
    # Create test file
    test_file = tmp_path / "range_hash_test.txt"
    test_content = "line1\nline2\nline3\n"
    test_file.write_text(test_content)
    file_path = str(test_file)

    # Calculate initial hash
    initial_hash = service.calculate_hash(test_content)

    # Create delete request with incorrect range hash
    request = DeleteTextFileContentsRequest(
        file_path=file_path,
        file_hash=initial_hash,
        ranges=[FileRange(start=2, end=2, range_hash="incorrect_hash")],
        encoding="utf-8",
    )

    # Attempt delete
    result = service.delete_text_file_contents(request)
    assert file_path in result
    delete_result = result[file_path]
    assert delete_result.result == "error"
    assert "hash mismatch for range" in delete_result.reason.lower()


def test_delete_text_file_contents_relative_path(service, tmp_path):
    """Test deleting with a relative file path."""
    # Create delete request with relative path
    request = DeleteTextFileContentsRequest(
        file_path="relative/path.txt",
        file_hash="some_hash",
        ranges=[FileRange(start=1, end=1, range_hash="hash1")],
        encoding="utf-8",
    )

    # Attempt delete
    result = service.delete_text_file_contents(request)
    assert "relative/path.txt" in result
    delete_result = result["relative/path.txt"]
    assert delete_result.result == "error"
    assert "no such file or directory" in delete_result.reason.lower()


def test_delete_text_file_contents_empty_ranges(service, tmp_path):
    """Test deleting with empty ranges list."""
    test_file = tmp_path / "empty_ranges.txt"
    test_content = "line1\nline2\nline3\n"
    test_file.write_text(test_content)
    file_path = str(test_file)
    content_hash = service.calculate_hash(test_content)

    # Test empty ranges
    request = DeleteTextFileContentsRequest(
        file_path=file_path,
        file_hash=content_hash,
        ranges=[],  # Empty ranges list
        encoding="utf-8",
    )

    result = service.delete_text_file_contents(request)
    assert file_path in result
    delete_result = result[file_path]
    assert delete_result.result == "error"
    assert "missing required argument: ranges" in delete_result.reason.lower()


def test_delete_text_file_contents_nonexistent_file(service, tmp_path):
    """Test deleting content from a nonexistent file."""
    file_path = str(tmp_path / "nonexistent.txt")

    # Create delete request for nonexistent file
    request = DeleteTextFileContentsRequest(
        file_path=file_path,
        file_hash="some_hash",
        ranges=[FileRange(start=1, end=1, range_hash="hash1")],
        encoding="utf-8",
    )

    # Attempt delete
    result = service.delete_text_file_contents(request)
    assert file_path in result
    delete_result = result[file_path]
    assert delete_result.result == "error"
    assert "no such file or directory" in delete_result.reason.lower()


def test_delete_text_file_contents_multiple_ranges(service, tmp_path):
    """Test deleting multiple ranges simultaneously."""
    # Create test file
    test_file = tmp_path / "multiple_ranges_test.txt"
    test_content = "line1\nline2\nline3\nline4\nline5\n"
    test_file.write_text(test_content)
    file_path = str(test_file)

    # Calculate initial hash
    initial_hash = service.calculate_hash(test_content)

    # Create delete request with multiple ranges
    request = DeleteTextFileContentsRequest(
        file_path=file_path,
        file_hash=initial_hash,
        ranges=[
            FileRange(start=2, end=2, range_hash=service.calculate_hash("line2\n")),
            FileRange(start=4, end=4, range_hash=service.calculate_hash("line4\n")),
        ],
        encoding="utf-8",
    )

    # Apply delete
    result = service.delete_text_file_contents(request)
    assert file_path in result
    delete_result = result[file_path]
    assert delete_result.result == "ok"

    # Verify changes
    new_content = test_file.read_text()
    assert new_content == "line1\nline3\nline5\n"


@pytest.mark.asyncio
async def test_delete_text_file_contents_handler_validation():
    """Test validation in DeleteTextFileContentsHandler."""
    from mcp_text_editor.handlers.delete_text_file_contents import (
        DeleteTextFileContentsHandler,
    )
    from mcp_text_editor.text_editor import TextEditor

    editor = TextEditor()
    handler = DeleteTextFileContentsHandler(editor)

    # Test missing file_hash
    with pytest.raises(RuntimeError) as exc_info:
        arguments = {
            "file_path": "/absolute/path.txt",
            "ranges": [{"start": 1, "end": 1, "range_hash": "hash1"}],
            "encoding": "utf-8",
        }
        await handler.run_tool(arguments)
    assert "Missing required argument: file_hash" in str(exc_info.value)

    # Test missing ranges
    with pytest.raises(RuntimeError) as exc_info:
        arguments = {
            "file_path": "/absolute/path.txt",
            "file_hash": "some_hash",
            "encoding": "utf-8",
        }
        await handler.run_tool(arguments)
    assert "Missing required argument: ranges" in str(exc_info.value)

    # Test missing file_path
    with pytest.raises(RuntimeError) as exc_info:
        arguments = {
            "file_hash": "some_hash",
            "ranges": [{"start": 1, "end": 1, "range_hash": "hash1"}],
            "encoding": "utf-8",
        }
        await handler.run_tool(arguments)
    assert "Missing required argument: file_path" in str(exc_info.value)

    # Test relative file path
    with pytest.raises(RuntimeError) as exc_info:
        arguments = {
            "file_path": "relative/path.txt",
            "file_hash": "some_hash",
            "ranges": [{"start": 1, "end": 1, "range_hash": "hash1"}],
            "encoding": "utf-8",
        }
        await handler.run_tool(arguments)
    assert "File path must be absolute" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_text_file_contents_handler_runtime_error(tmp_path):
    """Test runtime error handling in DeleteTextFileContentsHandler."""
    from mcp_text_editor.handlers.delete_text_file_contents import (
        DeleteTextFileContentsHandler,
    )
    from mcp_text_editor.service import TextEditorService
    from mcp_text_editor.text_editor import TextEditor

    class MockService(TextEditorService):
        def delete_text_file_contents(self, request):
            raise RuntimeError("Mock error during delete")

    editor = TextEditor()
    editor.service = MockService()
    handler = DeleteTextFileContentsHandler(editor)

    test_file = tmp_path / "error_test.txt"
    test_file.write_text("test content")

    with pytest.raises(RuntimeError) as exc_info:
        arguments = {
            "file_path": str(test_file),
            "file_hash": "some_hash",
            "ranges": [{"start": 1, "end": 1, "range_hash": "hash1"}],
            "encoding": "utf-8",
        }
        await handler.run_tool(arguments)

    assert "Error processing request: Mock error during delete" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_text_file_contents_handler_success(tmp_path):
    """Test successful execution of DeleteTextFileContentsHandler including JSON serialization."""
    from mcp_text_editor.handlers.delete_text_file_contents import (
        DeleteTextFileContentsHandler,
    )
    from mcp_text_editor.models import EditResult
    from mcp_text_editor.service import TextEditorService
    from mcp_text_editor.text_editor import TextEditor

    class MockService(TextEditorService):
        def delete_text_file_contents(self, request):
            return {
                request.file_path: EditResult(result="ok", hash="new_hash", reason=None)
            }

    editor = TextEditor()
    editor.service = MockService()
    handler = DeleteTextFileContentsHandler(editor)

    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    arguments = {
        "file_path": str(test_file),
        "file_hash": "some_hash",
        "ranges": [{"start": 1, "end": 1, "range_hash": "hash1"}],
    }

    result = await handler.run_tool(arguments)
    assert len(result) == 1
    assert result[0].type == "text"

    # Check if response is JSON serializable
    response = json.loads(result[0].text)
    assert str(test_file) in response
    assert response[str(test_file)]["result"] == "ok"
    assert response[str(test_file)]["hash"] == "new_hash"
