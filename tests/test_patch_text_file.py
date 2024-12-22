"""Test module for patch_text_file."""

import os

import pytest

from mcp_text_editor.text_editor import TextEditor
from mcp_text_editor.handlers.patch_text_file_contents import PatchTextFileContentsHandler


@pytest.mark.asyncio
async def test_patch_text_file_middle(tmp_path):
    """Test patching text in the middle of the file."""
    # Create a test file
    file_path = os.path.join(tmp_path, "test.txt")
    editor = TextEditor()

    # Create initial content
    content = "line1\nline2\nline3\nline4\nline5\n"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Get file hash and range hash
    file_info = await editor.read_multiple_ranges(
        [{"file_path": str(file_path), "ranges": [{"start": 2, "end": 3}]}]
    )

    # Extract file and range hashes
    file_content = file_info[str(file_path)]
    file_hash = file_content["file_hash"]
    range_hash = file_content["ranges"][0]["range_hash"]

    # Patch the file
    new_content = "new line2\nnew line3\n"
    patch = {
        "start": 2,
        "end": 3,  # changed from 4 to 3 since we only want to replace lines 2-3
        "contents": new_content,
        "range_hash": range_hash,
    }
    result = await editor.edit_file_contents(
        str(file_path),
        file_hash,
        [patch],
    )

    # Verify the patch was successful
    assert result["result"] == "ok"
    with open(file_path, "r", encoding="utf-8") as f:
        updated_content = f.read()
    assert updated_content == "line1\nnew line2\nnew line3\nline4\nline5\n"


@pytest.mark.asyncio
async def test_patch_text_file_errors(tmp_path):
    """Test error handling when patching a file."""
    editor = TextEditor()
    handler = PatchTextFileContentsHandler(editor)
    file_path = os.path.join(tmp_path, "test.txt")
    non_existent_file = os.path.join(tmp_path, "non_existent.txt")
    relative_path = "test.txt"

    # Test missing file_path
    with pytest.raises(RuntimeError, match="Missing required argument: file_path"):
        await handler.run_tool({"patches": [], "file_hash": "hash"})

    # Test missing file_hash
    with pytest.raises(RuntimeError, match="Missing required argument: file_hash"):
        await handler.run_tool({"file_path": file_path, "patches": []})

    # Test missing patches
    with pytest.raises(RuntimeError, match="Missing required argument: patches"):
        await handler.run_tool({"file_path": file_path, "file_hash": "hash"})

    # Test non-absolute file path
    with pytest.raises(RuntimeError, match="File path must be absolute"):
        await handler.run_tool(
            {"file_path": relative_path, "file_hash": "hash", "patches": []}
        )

    # Test non-existent file
    with pytest.raises(RuntimeError, match="File does not exist"):
        await handler.run_tool(
            {"file_path": non_existent_file, "file_hash": "hash", "patches": []}
        )
