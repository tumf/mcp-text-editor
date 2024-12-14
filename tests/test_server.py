"""Tests for the MCP Text Editor Server."""

import json
from typing import List

import pytest
from mcp.server import stdio
from mcp.types import TextContent, Tool
from pytest_mock import MockerFixture

from mcp_text_editor.server import (
    app,
    call_tool,
    edit_contents_handler,
    get_contents_handler,
    list_tools,
    main,
)


@pytest.mark.asyncio
async def test_list_tools():
    """Test tool listing."""
    tools: List[Tool] = await list_tools()
    assert len(tools) == 2

    # Verify GetTextFileContents tool
    get_contents_tool = next(
        (tool for tool in tools if tool.name == "get_text_file_contents"), None
    )
    assert get_contents_tool is not None
    assert "file" in get_contents_tool.description.lower()
    assert "contents" in get_contents_tool.description.lower()

    # Verify EditTextFileContents tool
    edit_contents_tool = next(
        (tool for tool in tools if tool.name == "edit_text_file_contents"), None
    )
    assert edit_contents_tool is not None
    assert "edit" in edit_contents_tool.description.lower()
    assert "contents" in edit_contents_tool.description.lower()


@pytest.mark.asyncio
async def test_get_contents_handler(test_file):
    """Test GetTextFileContents handler."""
    args = {"file_path": test_file, "line_start": 1, "line_end": 3}
    result = await get_contents_handler.run_tool(args)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    content = json.loads(result[0].text)
    assert "contents" in content
    assert "line_start" in content
    assert "line_end" in content
    assert "file_hash" in content
    assert "file_lines" in content
    assert "file_size" in content


@pytest.mark.asyncio
async def test_get_contents_handler_invalid_file(test_file):
    """Test GetTextFileContents handler with invalid file."""
    args = {"file_path": "nonexistent.txt"}
    with pytest.raises(RuntimeError) as exc_info:
        await get_contents_handler.run_tool(args)
    assert "File not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_edit_contents_handler(test_file):
    """Test EditTextFileContents handler."""
    # First, get the current content and hash
    get_args = {"file_path": test_file}
    get_result = await get_contents_handler.run_tool(get_args)
    content_info = json.loads(get_result[0].text)
    initial_hash = content_info["file_hash"]

    # Get range hash for the target lines
    get_range_args = {
        "files": [{"file_path": test_file, "ranges": [{"start": 2, "end": 2}]}]
    }
    range_result = json.loads(
        (await get_contents_handler.run_tool(get_range_args))[0].text
    )
    range_hash = range_result[test_file][0]["range_hash"]

    # Create edit operation
    edit_args = {
        "files": [
            {
                "path": test_file,
                "file_hash": initial_hash,
                "patches": [
                    {
                        "line_start": 2,
                        "line_end": 2,
                        "contents": "Modified Line 2\n",
                        "range_hash": range_hash,
                    }
                ],
            }
        ]
    }

    # Apply edit
    result = await edit_contents_handler.run_tool(edit_args)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    edit_result = json.loads(result[0].text)
    assert edit_result[test_file]["result"] == "ok"


@pytest.mark.asyncio
async def test_call_tool_get_contents(test_file):
    """Test call_tool with GetTextFileContents."""
    args = {"file_path": test_file, "line_start": 1, "line_end": 3}
    result = await call_tool("get_text_file_contents", args)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    content = json.loads(result[0].text)
    assert "contents" in content
    assert "line_start" in content
    assert "line_end" in content
    assert "file_hash" in content
    assert "file_lines" in content
    assert "file_size" in content


@pytest.mark.asyncio
async def test_call_tool_unknown():
    """Test call_tool with unknown tool."""
    with pytest.raises(ValueError) as exc_info:
        await call_tool("UnknownTool", {})
    assert "Unknown tool" in str(exc_info.value)


@pytest.mark.asyncio
async def test_call_tool_error_handling():
    """Test call_tool error handling."""
    # Test with invalid arguments
    with pytest.raises(RuntimeError) as exc_info:
        await call_tool("get_text_file_contents", {"invalid": "args"})
    assert "Missing required argument" in str(exc_info.value)

    # Test with invalid file path
    with pytest.raises(RuntimeError) as exc_info:
        await call_tool("get_text_file_contents", {"file_path": "nonexistent.txt"})
    assert "File not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_edit_contents_handler_multiple_files(tmp_path):
    """Test EditTextFileContents handler with multiple files."""
    # Create test files
    test_files = []
    for i in range(2):
        file_path = tmp_path / f"test_file_{i}.txt"
        file_path.write_text("line1\nline2\nline3\n")
        test_files.append(str(file_path))

    # Get range hashes for each file
    file_operations = []
    for file_path in test_files:
        # Get file hash
        get_result = await get_contents_handler.run_tool({"file_path": file_path})
        content_info = json.loads(get_result[0].text)
        file_hash = content_info["file_hash"]

        # Get range hash
        get_range_args = {
            "files": [
                {
                    "file_path": file_path,
                    "ranges": [{"start": 2, "end": 2}],
                }
            ]
        }
        range_result = json.loads(
            (await get_contents_handler.run_tool(get_range_args))[0].text
        )
        range_hash = range_result[file_path][0]["range_hash"]

        # Create operation for this file
        file_operations.append(
            {
                "path": file_path,
                "file_hash": file_hash,
                "patches": [
                    {
                        "line_start": 2,
                        "line_end": 2,
                        "contents": f"Modified Line 2 in file {file_path}\n",
                        "range_hash": range_hash,
                    }
                ],
            }
        )

    edit_args = {"files": file_operations}

    # Apply edits
    result = await edit_contents_handler.run_tool(edit_args)
    assert len(result) == 1
    edit_results = json.loads(result[0].text)

    # Verify results for each file
    for file_path in test_files:
        assert file_path in edit_results
        assert edit_results[file_path]["result"] == "ok"


@pytest.mark.asyncio
async def test_edit_contents_handler_partial_failure(tmp_path):
    """Test EditTextFileContents handler with a mix of successful and failed edits."""
    # Create one valid file
    valid_file = tmp_path / "valid_file.txt"
    valid_file.write_text("line1\nline2\nline3\n")
    valid_path = str(valid_file)

    # Get hash for valid file
    get_result = await get_contents_handler.run_tool({"file_path": valid_path})
    content_info = json.loads(get_result[0].text)
    valid_hash = content_info["file_hash"]

    # Get range hash for the target lines
    get_range_args = {
        "files": [{"file_path": valid_path, "ranges": [{"start": 2, "end": 2}]}]
    }
    range_result = json.loads(
        (await get_contents_handler.run_tool(get_range_args))[0].text
    )
    valid_range_hash = range_result[valid_path][0]["range_hash"]

    # Create edit operations for both valid and invalid files
    edit_args = {
        "files": [
            {
                "path": valid_path,
                "file_hash": valid_hash,
                "patches": [
                    {
                        "line_start": 2,
                        "line_end": 2,
                        "contents": "Modified Line 2\n",
                        "range_hash": valid_range_hash,
                    }
                ],
            },
            {
                "path": str(tmp_path / "nonexistent.txt"),
                "file_hash": "any_hash",
                "patches": [{"contents": "New content\n", "range_hash": "any_hash"}],
            },
        ]
    }

    # Apply edits
    result = await edit_contents_handler.run_tool(edit_args)
    assert len(result) == 1
    edit_results = json.loads(result[0].text)

    # Verify valid file results
    assert edit_results[valid_path]["result"] == "ok"

    # Verify invalid file results
    nonexistent_path = str(tmp_path / "nonexistent.txt")
    assert edit_results[nonexistent_path]["result"] == "error"
    assert "File not found" in edit_results[nonexistent_path]["reason"]
    assert edit_results[nonexistent_path]["file_hash"] is None


@pytest.mark.asyncio
async def test_edit_contents_handler_empty_args():
    """Test EditTextFileContents handler with empty files."""
    edit_args = {"files": []}
    result = await edit_contents_handler.run_tool(edit_args)
    assert len(result) == 1
    edit_results = json.loads(result[0].text)
    assert isinstance(edit_results, dict)
    assert len(edit_results) == 0


@pytest.mark.asyncio
async def test_edit_contents_handler_malformed_input():
    """Test EditTextFileContents handler with malformed input."""
    with pytest.raises(RuntimeError) as exc_info:
        await edit_contents_handler.run_tool({"invalid": "args"})
    assert "processing request" in str(exc_info.value)


@pytest.mark.asyncio
async def test_edit_contents_handler_empty_patches():
    """Test EditTextFileContents handler with empty patches."""
    edit_args = {"files": [{"path": "test.txt", "hash": "any_hash", "patches": []}]}
    result = await edit_contents_handler.run_tool(edit_args)
    edit_results = json.loads(result[0].text)
    assert edit_results["test.txt"]["result"] == "error"
    assert edit_results["test.txt"]["file_hash"] is None
    edit_results = json.loads(result[0].text)
    assert edit_results["test.txt"]["result"] == "error"
    assert edit_results["test.txt"]["file_hash"] is None


@pytest.mark.asyncio
async def test_get_contents_handler_legacy_missing_args():
    """Test GetTextFileContents handler with legacy single file request missing arguments."""
    with pytest.raises(RuntimeError) as exc_info:
        await get_contents_handler.run_tool({})
    assert "Missing required argument: files" in str(exc_info.value)


@pytest.mark.asyncio
async def test_edit_contents_handler_missing_path():
    """Test EditTextFileContents handler with missing path in file operation."""
    edit_args = {
        "files": [
            {
                "hash": "any_hash",
                "patches": [{"contents": "New content\n"}],
            }
        ]
    }

    with pytest.raises(RuntimeError) as exc_info:
        await edit_contents_handler.run_tool(edit_args)
    assert "Missing required field: path" in str(exc_info.value)


@pytest.mark.asyncio
async def test_edit_contents_handler_missing_hash(tmp_path):
    """Test EditTextFileContents handler with missing hash in file operation."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    edit_args = {
        "files": [
            {
                "path": str(test_file),
                "patches": [{"contents": "New content\n"}],
            }
        ]
    }

    result = await edit_contents_handler.run_tool(edit_args)
    edit_results = json.loads(result[0].text)
    assert edit_results[str(test_file)]["result"] == "error"
    assert "Missing required field: file_hash" in edit_results[str(test_file)]["reason"]


@pytest.mark.asyncio
async def test_main_stdio_server_error(mocker: MockerFixture):
    """Test main function with stdio_server error."""
    # Mock the stdio_server to raise an exception
    mock_stdio = mocker.patch.object(stdio, "stdio_server")
    mock_stdio.side_effect = Exception("Stdio server error")

    with pytest.raises(Exception) as exc_info:
        await main()
    assert "Stdio server error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_main_run_error(mocker: MockerFixture):
    """Test main function with app.run error."""
    # Mock the stdio_server context manager
    mock_stdio = mocker.patch.object(stdio, "stdio_server")
    mock_context = mocker.MagicMock()
    mock_context.__aenter__.return_value = (mocker.MagicMock(), mocker.MagicMock())
    mock_stdio.return_value = mock_context

    # Mock app.run to raise an exception
    mock_run = mocker.patch.object(app, "run")
    mock_run.side_effect = Exception("App run error")

    with pytest.raises(Exception) as exc_info:
        await main()
    assert "App run error" in str(exc_info.value)
