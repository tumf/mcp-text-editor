"""Tests for the MCP Text Editor Server."""

import json
from typing import List

import pytest
from mcp.types import TextContent, Tool

from mcp_text_editor.server import (
    call_tool,
    edit_contents_handler,
    get_contents_handler,
    list_tools,
)


@pytest.mark.asyncio
async def test_list_tools():
    """Test tool listing."""
    tools: List[Tool] = await list_tools()
    assert len(tools) == 2

    # Verify GetTextFileContents tool
    get_contents_tool = next(
        (tool for tool in tools if tool.name == "GetTextFileContents"), None
    )
    assert get_contents_tool is not None
    assert "file" in get_contents_tool.description.lower()
    assert "contents" in get_contents_tool.description.lower()

    # Verify EditTextFileContents tool
    edit_contents_tool = next(
        (tool for tool in tools if tool.name == "EditTextFileContents"), None
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
    assert "hash" in content


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
    initial_hash = content_info["hash"]

    # Create edit operation
    edit_args = {
        test_file: {
            "hash": initial_hash,
            "patches": [
                {"line_start": 2, "line_end": 2, "contents": "Modified Line 2\n"}
            ],
        }
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
    result = await call_tool("GetTextFileContents", args)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    content = json.loads(result[0].text)
    assert "contents" in content


@pytest.mark.asyncio
async def test_call_tool_edit_contents(test_file):
    """Test call_tool with EditTextFileContents."""
    # First, get the current content and hash
    get_result = await call_tool("GetTextFileContents", {"file_path": test_file})
    content_info = json.loads(get_result[0].text)
    initial_hash = content_info["hash"]

    # Create edit operation
    edit_args = {
        test_file: {
            "hash": initial_hash,
            "patches": [
                {"line_start": 2, "line_end": 2, "contents": "Modified Line 2\n"}
            ],
        }
    }

    # Apply edit
    result = await call_tool("EditTextFileContents", edit_args)
    assert len(result) == 1
    edit_result = json.loads(result[0].text)
    assert edit_result[test_file]["result"] == "ok"


@pytest.mark.asyncio
async def test_call_tool_unknown():
    """Test call_tool with unknown tool."""
    with pytest.raises(ValueError) as exc_info:
        await call_tool("UnknownTool", {})
    assert "Unknown tool" in str(exc_info.value)


@pytest.mark.asyncio
async def test_call_tool_error_handling(test_file):
    """Test call_tool error handling."""
    # Test with invalid arguments
    with pytest.raises(RuntimeError) as exc_info:
        await call_tool("GetTextFileContents", {"invalid": "args"})
    assert "Missing required argument" in str(exc_info.value)

    # Test with invalid file path
    with pytest.raises(RuntimeError) as exc_info:
        await call_tool("GetTextFileContents", {"file_path": "nonexistent.txt"})
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

    # Get hashes for all files
    file_hashes = {}
    for file_path in test_files:
        get_result = await get_contents_handler.run_tool({"file_path": file_path})
        content_info = json.loads(get_result[0].text)
        file_hashes[file_path] = content_info["hash"]

    # Create edit operations for multiple files
    edit_args = {
        file_path: {
            "hash": file_hashes[file_path],
            "patches": [
                {
                    "line_start": 2,
                    "line_end": 2,
                    "contents": f"Modified Line 2 in {i}\n",
                }
            ],
        }
        for i, file_path in enumerate(test_files)
    }

    # Apply edits
    result = await edit_contents_handler.run_tool(edit_args)
    assert len(result) == 1
    edit_results = json.loads(result[0].text)

    # Verify results for each file
    for file_path in test_files:
        assert file_path in edit_results
        assert edit_results[file_path]["result"] == "ok"

        # Verify file contents were actually modified
        with open(file_path, "r") as f:
            content = f.read()
            assert "Modified Line 2" in content


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
    valid_hash = content_info["hash"]

    # Create edit operations for both valid and invalid files
    edit_args = {
        valid_path: {
            "hash": valid_hash,
            "patches": [
                {"line_start": 2, "line_end": 2, "contents": "Modified Line 2\n"}
            ],
        },
        str(tmp_path / "nonexistent.txt"): {
            "hash": "any_hash",
            "patches": [{"line_start": 1, "contents": "New content\n"}],
        },
    }

    # Apply edits
    result = await edit_contents_handler.run_tool(edit_args)
    assert len(result) == 1
    edit_results = json.loads(result[0].text)

    # Verify valid file results
    assert edit_results[valid_path]["result"] == "ok"
    with open(valid_path, "r") as f:
        content = f.read()
        assert "Modified Line 2" in content

    # Verify invalid file results
    nonexistent_path = str(tmp_path / "nonexistent.txt")
    assert edit_results[nonexistent_path]["result"] == "error"
    assert "File not found" in edit_results[nonexistent_path]["reason"]
    assert edit_results[nonexistent_path]["hash"] is None
