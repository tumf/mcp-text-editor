"""Test module for patch_text_file with end=None."""

import os

import pytest

from mcp_text_editor.text_editor import TextEditor


@pytest.mark.asyncio
async def test_patch_text_file_end_none(tmp_path):
    """Test patching text file with end=None."""
    # Create a test file
    file_path = os.path.join(tmp_path, "test.txt")
    editor = TextEditor()

    # Create initial content
    content = "line1\nline2\nline3\nline4\nline5\n"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Get file hash and range hash
    file_info = await editor.read_multiple_ranges(
        [
            {
                "file_path": str(file_path),
                "ranges": [{"start": 2, "end": None}],  # Test with end=None
            }
        ]
    )

    # Extract file and range hashes
    file_content = file_info[str(file_path)]
    file_hash = file_content["file_hash"]
    range_hash = file_content["ranges"][0]["range_hash"]

    # Patch the file
    new_content = "new line2\nnew line3\nnew line4\nnew line5\n"
    patch = {
        "start": 2,
        "end": None,  # Test with end=None
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
    assert updated_content == "line1\nnew line2\nnew line3\nnew line4\nnew line5\n"
