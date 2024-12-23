"""Tests for InsertTextFileContentsHandler."""

import json

import pytest

from mcp_text_editor.handlers.insert_text_file_contents import (
    InsertTextFileContentsHandler,
)
from mcp_text_editor.text_editor import TextEditor


@pytest.fixture
def handler():
    """Create handler instance."""
    editor = TextEditor()
    return InsertTextFileContentsHandler(editor)


@pytest.mark.asyncio
async def test_missing_path(handler):
    """Test handling of missing file_path argument."""
    with pytest.raises(RuntimeError, match="Missing required argument: file_path"):
        await handler.run_tool({"file_hash": "hash", "contents": "content"})


@pytest.mark.asyncio
async def test_missing_hash(handler):
    """Test handling of missing file_hash argument."""
    with pytest.raises(RuntimeError, match="Missing required argument: file_hash"):
        await handler.run_tool({"file_path": "/tmp/test.txt", "contents": "content"})


@pytest.mark.asyncio
async def test_missing_contents(handler):
    """Test handling of missing contents argument."""
    with pytest.raises(RuntimeError, match="Missing required argument: contents"):
        await handler.run_tool({"file_path": "/tmp/test.txt", "file_hash": "hash"})


@pytest.mark.asyncio
async def test_relative_path(handler):
    """Test handling of relative file path."""
    with pytest.raises(RuntimeError, match="File path must be absolute"):
        await handler.run_tool(
            {
                "file_path": "relative/path.txt",
                "file_hash": "hash",
                "contents": "content",
                "before": 1,
            }
        )


@pytest.mark.asyncio
async def test_neither_before_nor_after(handler):
    """Test handling of neither before nor after specified."""
    with pytest.raises(
        RuntimeError, match="Exactly one of 'before' or 'after' must be specified"
    ):
        await handler.run_tool(
            {"file_path": "/tmp/test.txt", "file_hash": "hash", "contents": "content"}
        )


@pytest.mark.asyncio
async def test_both_before_and_after(handler):
    """Test handling of both before and after specified."""
    with pytest.raises(
        RuntimeError, match="Exactly one of 'before' or 'after' must be specified"
    ):
        await handler.run_tool(
            {
                "file_path": "/tmp/test.txt",
                "file_hash": "hash",
                "contents": "content",
                "before": 1,
                "after": 2,
            }
        )


@pytest.mark.asyncio
async def test_successful_insert_before(handler, tmp_path):
    """Test successful insert before line."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\n")

    file_path = str(test_file)

    # Get the current hash
    content, _, _, init_hash, _, _ = await handler.editor.read_file_contents(
        file_path=file_path, start=1
    )

    result = await handler.run_tool(
        {
            "file_path": file_path,
            "file_hash": init_hash,
            "contents": "new_line\n",
            "before": 2,
        }
    )

    assert len(result) == 1
    assert result[0].type == "text"
    response_data = json.loads(result[0].text)
    assert response_data[file_path]["result"] == "ok"

    # Verify the content
    assert test_file.read_text() == "line1\nnew_line\nline2\n"
