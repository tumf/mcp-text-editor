"""Tests for delete text file functionality."""

from pathlib import Path

import pytest

from mcp_text_editor.text_editor import TextEditor


@pytest.fixture
def editor() -> TextEditor:
    """Create TextEditor instance."""
    return TextEditor()


@pytest.fixture
def test_file(tmp_path) -> Path:
    """Create a test file with sample content."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")
    return test_file


@pytest.mark.asyncio
async def test_delete_line_from_file(editor, test_file):
    """Test deleting a single line from a file."""
    # Get initial content and file hash
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Get line 2 content and hash
    line2_content, _, _, line2_hash, _, _ = await editor.read_file_contents(
        str(test_file), start=2, end=2
    )

    # Delete line 2
    result = await editor.delete_text_file_contents(
        file_path=str(test_file),
        file_hash=file_hash,
        range_hash=line2_hash,
        start_line=2,
        end_line=2,
        encoding="utf-8",
    )

    assert result["result"] == "ok"
    assert test_file.read_text() == "Line 1\nLine 3\nLine 4\nLine 5\n"


@pytest.mark.asyncio
async def test_delete_multiple_lines(editor, test_file):
    """Test deleting multiple consecutive lines from a file."""
    # Get initial content and file hash
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Get lines 2-4 content and hash
    lines_content, _, _, lines_hash, _, _ = await editor.read_file_contents(
        str(test_file), start=2, end=4
    )

    # Delete lines 2-4
    result = await editor.delete_text_file_contents(
        file_path=str(test_file),
        file_hash=file_hash,
        range_hash=lines_hash,
        start_line=2,
        end_line=4,
    )

    assert result["result"] == "ok"
    assert test_file.read_text() == "Line 1\nLine 5\n"


@pytest.mark.asyncio
async def test_delete_with_invalid_hash(editor, test_file):
    """Test deleting with an invalid file hash."""
    _, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))
    line2_content, _, _, line2_hash, _, _ = await editor.read_file_contents(
        str(test_file), start=2, end=2
    )

    result = await editor.delete_text_file_contents(
        file_path=str(test_file),
        file_hash="invalid_hash",
        range_hash=line2_hash,
        start_line=2,
        end_line=2,
    )

    assert result["result"] == "error"
    assert "hash mismatch" in result["reason"].lower()
    assert test_file.read_text() == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"


@pytest.mark.asyncio
async def test_delete_with_invalid_range_hash(editor, test_file):
    """Test deleting with an invalid range hash."""
    file_content, _, _, file_hash, _, _ = await editor.read_file_contents(
        str(test_file)
    )

    result = await editor.delete_text_file_contents(
        file_path=str(test_file),
        file_hash=file_hash,
        range_hash="invalid_hash",
        start_line=2,
        end_line=2,
    )

    assert result["result"] == "error"
    assert "range hash mismatch" in result["reason"].lower()
    assert test_file.read_text() == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"


@pytest.mark.asyncio
async def test_delete_with_invalid_range(editor, test_file):
    """Test deleting with invalid line range."""
    file_content, _, _, file_hash, _, _ = await editor.read_file_contents(
        str(test_file)
    )
    line2_content, _, _, line2_hash, _, _ = await editor.read_file_contents(
        str(test_file), start=2, end=2
    )

    result = await editor.delete_text_file_contents(
        file_path=str(test_file),
        file_hash=file_hash,
        range_hash=line2_hash,
        start_line=2,
        end_line=1,
    )

    assert result["result"] == "error"
    assert (
        "end line must be greater than or equal to start line"
        in result["reason"].lower()
    )
    assert test_file.read_text() == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"


@pytest.mark.asyncio
async def test_delete_with_out_of_range(editor, test_file):
    """Test deleting lines beyond file length."""
    file_content, _, _, file_hash, _, _ = await editor.read_file_contents(
        str(test_file)
    )

    result = await editor.delete_text_file_contents(
        file_path=str(test_file),
        file_hash=file_hash,
        range_hash="any_hash",  # Hash doesn't matter as it will fail before hash check
        start_line=10,
        end_line=12,
    )

    assert result["result"] == "error"
    assert "line number out of range" in result["reason"].lower()
    assert test_file.read_text() == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"


@pytest.mark.asyncio
async def test_delete_without_file_path(editor):
    """Test deleting without specifying file_path"""
    with pytest.raises(
        TypeError, match="missing 1 required positional argument: 'file_path'"
    ):
        await editor.delete_text_file_contents(
            file_hash="any_hash",
            range_hash="any_hash",
            start_line=1,
            end_line=1,
        )


@pytest.mark.asyncio
async def test_delete_without_file_hash(editor, test_file):
    """Test deleting without specifying file_hash"""
    with pytest.raises(
        TypeError, match="missing 1 required positional argument: 'file_hash'"
    ):
        await editor.delete_text_file_contents(
            file_path=str(test_file),
            range_hash="any_hash",
            start_line=1,
            end_line=1,
        )


@pytest.mark.asyncio
async def test_delete_without_range_hash(editor, test_file):
    """Test deleting without specifying range_hash"""
    with pytest.raises(
        TypeError, match="missing 1 required positional argument: 'range_hash'"
    ):
        await editor.delete_text_file_contents(
            file_path=str(test_file),
            file_hash="any_hash",
            start_line=1,
            end_line=1,
        )


@pytest.mark.asyncio
async def test_delete_relative_path(editor):
    """Test deleting with relative path"""
    with pytest.raises(RuntimeError, match="File path must be absolute"):
        await editor.delete_text_file_contents(
            file_path="relative/path/file.txt",
            file_hash="any_hash",
            range_hash="any_hash",
            start_line=1,
            end_line=1,
        )


@pytest.mark.asyncio
async def test_delete_nonexistent_file(editor, tmp_path):
    """Test deleting a file that doesn't exist"""
    nonexistent_file = tmp_path / "nonexistent.txt"
    with pytest.raises(RuntimeError, match="File does not exist"):
        await editor.delete_text_file_contents(
            file_path=str(nonexistent_file),
            file_hash="any_hash",
            range_hash="any_hash",
            start_line=1,
            end_line=1,
        )
