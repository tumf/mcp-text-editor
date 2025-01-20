"""Tests for the MCP Text Editor Server."""

from pathlib import Path

import pytest
from mcp.server import stdio
from mcp.types import TextContent
from pytest_mock import MockerFixture

from mcp_text_editor.server import (
    app,
    append_file_handler,
    create_file_handler,
    delete_contents_handler,
    get_contents_handler,
    insert_file_handler,
    main,
    patch_file_handler,
)
from mcp_text_editor.text_editor import TextEditor


@pytest.fixture
def editor():
    return TextEditor()


@pytest.mark.asyncio
async def test_get_text_file_contents():
    """Test get_text_file_contents tool."""
    test_file = str(Path(__file__).absolute())
    result = await get_contents_handler.run_tool(
        {"files": [{"file_path": test_file, "ranges": [{"start": 1, "end": 10}]}]}
    )
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"


@pytest.mark.asyncio
async def test_patch_text_file_contents(tmp_path, editor):
    """Test patch_text_file_contents tool."""
    test_file = str(tmp_path / "test.txt")
    Path(test_file).write_text("test content\n")
    content, _, _, file_hash, _, _ = await editor.read_file_contents(test_file)

    result = await patch_file_handler.run_tool(
        {
            "file_path": test_file,
            "file_hash": file_hash,
            "patches": [
                {
                    "start": 1,
                    "end": 1,
                    "contents": "new content\n",
                    "range_hash": file_hash,
                }
            ],
        }
    )
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert Path(test_file).read_text().rstrip() == "new content"


@pytest.mark.asyncio
async def test_create_text_file(tmp_path):
    """Test create_text_file tool."""
    test_file = str(tmp_path / "new.txt")
    result = await create_file_handler.run_tool(
        {"file_path": test_file, "contents": "new file content\n"}
    )
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert Path(test_file).exists()
    assert Path(test_file).read_text().rstrip() == "new file content"


@pytest.mark.asyncio
async def test_append_text_file_contents(tmp_path, editor):
    """Test append_text_file_contents tool."""
    test_file = str(tmp_path / "test.txt")
    Path(test_file).write_text("initial content")  # Remove trailing newline
    content, _, _, file_hash, _, _ = await editor.read_file_contents(test_file)

    result = await append_file_handler.run_tool(
        {
            "file_path": test_file,
            "contents": " appended",  # Remove trailing newline
            "file_hash": file_hash,
        }
    )
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert Path(test_file).read_text().rstrip() == "initial content appended"


@pytest.mark.asyncio
async def test_delete_text_file_contents(tmp_path, editor):
    """Test delete_text_file_contents tool."""
    test_file = str(tmp_path / "test.txt")
    Path(test_file).write_text("content to delete\n")
    content, _, _, file_hash, _, _ = await editor.read_file_contents(test_file)

    result = await delete_contents_handler.run_tool(
        {
            "file_path": test_file,
            "file_hash": file_hash,
            "ranges": [{"start": 1, "end": 1, "range_hash": file_hash}],
        }
    )
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert Path(test_file).read_text().rstrip() == ""


@pytest.mark.asyncio
async def test_insert_text_file_contents(tmp_path, editor):
    """Test insert_text_file_contents tool."""
    test_file = str(tmp_path / "test.txt")
    Path(test_file).write_text("before\nafter\n")
    content, _, _, file_hash, _, _ = await editor.read_file_contents(test_file)

    result = await insert_file_handler.run_tool(
        {
            "file_path": test_file,
            "contents": "inserted\n",
            "file_hash": file_hash,
            "before": 2,  # Insert before line 2
        }
    )
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert Path(test_file).read_text().rstrip() == "before\ninserted\nafter"


@pytest.mark.asyncio
async def test_main_stdio_server_error(mocker: MockerFixture):
    """Test main function with stdio_server error."""
    mock_run = mocker.patch.object(app, "run")
    mock_run.side_effect = Exception("Stdio server error")

    with pytest.raises(Exception) as exc_info:
        await main()
    assert "Stdio server error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_main_run_error(mocker: MockerFixture):
    """Test main function with app.run error."""
    mock_stdio = mocker.patch.object(stdio, "stdio_server")
    mock_context = mocker.MagicMock()
    mock_context.__aenter__.return_value = (mocker.MagicMock(), mocker.MagicMock())
    mock_stdio.return_value = mock_context

    mock_run = mocker.patch.object(app, "run")
    mock_run.side_effect = Exception("App run error")

    with pytest.raises(Exception) as exc_info:
        await main()
    assert "App run error" in str(exc_info.value)
