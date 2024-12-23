"""Test module for patch_text_file."""

import os

import pytest

from mcp_text_editor.handlers.patch_text_file_contents import (
    PatchTextFileContentsHandler,
)
from mcp_text_editor.text_editor import TextEditor


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
async def test_patch_text_file_empty_content(tmp_path):
    """Test patching with empty content suggests using delete_text_file_contents."""
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

    # Patch the file with empty content
    patch = {
        "start": 2,
        "end": 3,
        "contents": "",
        "range_hash": range_hash,
    }
    result = await editor.edit_file_contents(
        str(file_path),
        file_hash,
        [patch],
    )

    # Verify that the operation suggests using delete_text_file_contents
    assert result["result"] == "ok"
    assert result["file_hash"] == file_hash
    assert "delete_text_file_contents" in result["hint"]
    assert result["suggestion"] == "delete"

    # Verify file content remains unchanged
    with open(file_path, "r", encoding="utf-8") as f:
        updated_content = f.read()
    assert updated_content == content


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


@pytest.mark.asyncio
async def test_patch_text_file_unexpected_error(tmp_path, mocker):
    """Test handling of unexpected errors during patching."""
    editor = TextEditor()
    handler = PatchTextFileContentsHandler(editor)
    file_path = os.path.join(tmp_path, "test.txt")

    # Create a test file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("test content\n")

    # Mock edit_file_contents to raise an unexpected error
    async def mock_edit_file_contents(*args, **kwargs):
        raise Exception("Unexpected test error")

    # Patch the editor's method using mocker
    mocker.patch.object(editor, "edit_file_contents", mock_edit_file_contents)

    # Try to patch the file with the mocked error
    with pytest.raises(
        RuntimeError, match="Error processing request: Unexpected test error"
    ):
        await handler.run_tool(
            {
                "file_path": file_path,
                "file_hash": "dummy_hash",
                "patches": [
                    {
                        "start": 1,
                        "contents": "new content\n",
                        "range_hash": "dummy_hash",
                    }
                ],
            }
        )


@pytest.mark.asyncio
async def test_patch_text_file_overlapping(tmp_path):
    """Test patching text with overlapping ranges should fail."""
    # Create a test file
    file_path = os.path.join(tmp_path, "test.txt")
    editor = TextEditor()

    # Create initial content
    content = "line1\nline2\nline3\nline4\nline5\n"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Get file hash and range hash for first patch
    file_info = await editor.read_multiple_ranges(
        [{"file_path": str(file_path), "ranges": [{"start": 2, "end": 3}]}]
    )

    # Extract hashes for first patch
    file_content = file_info[str(file_path)]
    file_hash = file_content["file_hash"]
    range_hash_1 = file_content["ranges"][0]["range_hash"]

    # Get range hash for second patch
    file_info = await editor.read_multiple_ranges(
        [{"file_path": str(file_path), "ranges": [{"start": 3, "end": 4}]}]
    )
    range_hash_2 = file_info[str(file_path)]["ranges"][0]["range_hash"]

    # Create overlapping patches
    patches = [
        {
            "start": 2,
            "end": 3,
            "contents": "new line2\nnew line3\n",
            "range_hash": range_hash_1,
        },
        {
            "start": 3,
            "end": 4,
            "contents": "another new line3\nnew line4\n",
            "range_hash": range_hash_2,
        },
    ]

    # Try to apply overlapping patches
    result = await editor.edit_file_contents(
        str(file_path),
        file_hash,
        patches,
    )

    # Verify that the operation failed due to overlapping patches
    assert result["result"] == "error"


@pytest.mark.asyncio
async def test_patch_text_file_new_file_hint(tmp_path):
    """Test patching a new file suggests using append_text_file_contents."""
    file_path = os.path.join(tmp_path, "new.txt")
    editor = TextEditor()

    # Try to patch a new file
    patch = {
        "start": 1,
        "contents": "new content\n",
        "range_hash": "",  # Empty hash for new file
    }
    result = await editor.edit_file_contents(
        str(file_path),
        "",  # Empty hash for new file
        [patch],
    )

    # Verify that the operation suggests using append_text_file_contents
    assert result["result"] == "ok"
    assert result["suggestion"] == "append"
    assert "append_text_file_contents" in result["hint"]


@pytest.mark.asyncio
async def test_patch_text_file_append_hint(tmp_path):
    """Test patching beyond file end suggests using append_text_file_contents."""
    file_path = os.path.join(tmp_path, "test.txt")
    editor = TextEditor()

    # Create initial content
    content = "line1\nline2\n"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Get file hash
    file_info = await editor.read_multiple_ranges(
        [{"file_path": str(file_path), "ranges": [{"start": 1, "end": 2}]}]
    )
    file_hash = file_info[str(file_path)]["file_hash"]

    # Try to patch beyond file end
    patch = {
        "start": 5,  # Beyond file end
        "contents": "new line\n",
        "range_hash": "",  # Empty hash for insertion
    }
    result = await editor.edit_file_contents(
        str(file_path),
        file_hash,
        [patch],
    )

    # Verify the suggestion to use append_text_file_contents
    assert result["result"] == "ok"
    assert result["suggestion"] == "append"
    assert "append_text_file_contents" in result["hint"]


@pytest.mark.asyncio
async def test_patch_text_file_insert_hint(tmp_path):
    """Test patching with insertion suggests using insert_text_file_contents."""
    file_path = os.path.join(tmp_path, "test.txt")
    editor = TextEditor()

    # Create initial content
    content = "line1\nline2\n"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Get file hash
    file_info = await editor.read_multiple_ranges(
        [{"file_path": str(file_path), "ranges": [{"start": 1, "end": 2}]}]
    )
    file_hash = file_info[str(file_path)]["file_hash"]

    # Try to insert at start
    patch = {
        "start": 1,
        "contents": "new line\n",
        "range_hash": "",  # Empty hash for insertion
    }
    result = await editor.edit_file_contents(
        str(file_path),
        file_hash,
        [patch],
    )

    # Verify the suggestion to use insert_text_file_contents
    assert result["result"] == "ok"
    assert result["suggestion"] == "insert"
    assert "insert_text_file_contents" in result["hint"]


@pytest.mark.asyncio
async def test_patch_text_file_hash_mismatch_hint(tmp_path):
    """Test patching with wrong hash suggests using get_text_file_contents."""
    file_path = os.path.join(tmp_path, "test.txt")
    editor = TextEditor()

    # Create initial content
    content = "line1\nline2\n"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Try to patch with wrong file hash
    patch = {
        "start": 1,
        "contents": "new line\n",
        "range_hash": "",
    }
    result = await editor.edit_file_contents(
        str(file_path),
        "wrong_hash",
        [patch],
    )

    # Verify the suggestion to use get_text_file_contents
    assert result["result"] == "error"
    assert "get_text_file_contents" in result["hint"]
