"""Test insert_text_file_contents function."""

from pathlib import Path

import pytest

from mcp_text_editor import get_text_file_contents, insert_text_file_contents


@pytest.mark.asyncio
async def test_insert_after_line(tmp_path: Path) -> None:
    """Test inserting text after a specific line."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\n")

    # Get the current hash
    result = await get_text_file_contents(
        {"files": [{"file_path": str(test_file), "ranges": [{"start": 1}]}]}
    )
    file_hash = result[str(test_file)]["file_hash"]

    # Insert text after line 2
    result = await insert_text_file_contents(
        {
            "file_path": str(test_file),
            "file_hash": file_hash,
            "after": 2,
            "contents": "new_line\n",
        }
    )

    assert result["result"] == "ok"
    assert result["hash"] is not None

    # Verify the content
    content = test_file.read_text()
    assert content == "line1\nline2\nnew_line\nline3\n"


@pytest.mark.asyncio
async def test_insert_before_line(tmp_path: Path) -> None:
    """Test inserting text before a specific line."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\n")

    # Get the current hash
    result = await get_text_file_contents(
        {"files": [{"file_path": str(test_file), "ranges": [{"start": 1}]}]}
    )
    file_hash = result[str(test_file)]["file_hash"]

    # Insert text before line 2
    result = await insert_text_file_contents(
        {
            "file_path": str(test_file),
            "file_hash": file_hash,
            "before": 2,
            "contents": "new_line\n",
        }
    )

    assert result["result"] == "ok"
    assert result["hash"] is not None

    # Verify the content
    content = test_file.read_text()
    assert content == "line1\nnew_line\nline2\nline3\n"


@pytest.mark.asyncio
async def test_insert_beyond_file_end(tmp_path: Path) -> None:
    """Test inserting text beyond the end of file."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\n")

    # Get the current hash
    result = await get_text_file_contents(
        {"files": [{"file_path": str(test_file), "ranges": [{"start": 1}]}]}
    )
    file_hash = result[str(test_file)]["file_hash"]

    # Try to insert text after line 10 (file has only 3 lines)
    result = await insert_text_file_contents(
        {
            "file_path": str(test_file),
            "file_hash": file_hash,
            "after": 10,
            "contents": "new_line\n",
        }
    )

    assert result["result"] == "error"
    assert "beyond end of file" in result["reason"]


@pytest.mark.asyncio
async def test_file_not_found(tmp_path: Path) -> None:
    """Test inserting text into a non-existent file."""
    # Try to insert text into a non-existent file
    result = await insert_text_file_contents(
        {
            "file_path": str(tmp_path / "nonexistent.txt"),
            "file_hash": "any_hash",
            "after": 1,
            "contents": "new_line\n",
        }
    )

    assert result["result"] == "error"
    assert "File not found" in result["reason"]


@pytest.mark.asyncio
async def test_hash_mismatch(tmp_path: Path) -> None:
    """Test inserting text with incorrect file hash."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\n")

    # Try to insert text with incorrect hash
    result = await insert_text_file_contents(
        {
            "file_path": str(test_file),
            "file_hash": "incorrect_hash",
            "after": 1,
            "contents": "new_line\n",
        }
    )

    assert result["result"] == "error"
    assert "hash mismatch" in result["reason"]
