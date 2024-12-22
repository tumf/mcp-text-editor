"""Tests for delete text file functionality."""

from pathlib import Path

import pytest

from mcp_text_editor.models import DeleteTextFileContentsRequest, FileRange
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
async def test_delete_single_line(editor, test_file):
    """Test deleting a single line from file."""
    # Get initial content and file hash
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))
    original_lines = content.splitlines(keepends=True)

    # Get hash for line 2
    line2_hash = editor.calculate_hash(original_lines[1])

    # Create delete request
    request = DeleteTextFileContentsRequest(
        file_path=str(test_file),
        file_hash=file_hash,
        ranges=[
            FileRange(
                start=2,
                end=2,
                range_hash=line2_hash,
            )
        ],
    )

    # Delete line 2
    result = await editor.delete_text_file_contents(request)

    assert result[str(test_file)]["result"] == "ok"
    assert test_file.read_text() == "Line 1\nLine 3\nLine 4\nLine 5\n"


@pytest.mark.asyncio
async def test_delete_multiple_lines(editor, test_file):
    """Test deleting multiple consecutive lines from file."""
    # Get initial content and file hash
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))
    original_lines = content.splitlines(keepends=True)

    # Get hash for lines 2-4
    lines_hash = editor.calculate_hash("".join(original_lines[1:4]))

    # Create delete request
    request = DeleteTextFileContentsRequest(
        file_path=str(test_file),
        file_hash=file_hash,
        ranges=[
            FileRange(
                start=2,
                end=4,
                range_hash=lines_hash,
            )
        ],
    )

    # Delete lines 2-4
    result = await editor.delete_text_file_contents(request)

    assert result[str(test_file)]["result"] == "ok"
    assert test_file.read_text() == "Line 1\nLine 5\n"


@pytest.mark.asyncio
async def test_delete_with_invalid_file_hash(editor, test_file):
    """Test deleting with an invalid file hash."""
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))
    original_lines = content.splitlines(keepends=True)
    line2_hash = editor.calculate_hash(original_lines[1])

    request = DeleteTextFileContentsRequest(
        file_path=str(test_file),
        file_hash="invalid_hash",
        ranges=[
            FileRange(
                start=2,
                end=2,
                range_hash=line2_hash,
            )
        ],
    )

    result = await editor.delete_text_file_contents(request)

    assert result[str(test_file)]["result"] == "error"
    assert "hash mismatch" in result[str(test_file)]["reason"].lower()
    assert test_file.read_text() == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"


@pytest.mark.asyncio
async def test_delete_with_invalid_range_hash(editor, test_file):
    """Test deleting with an invalid range hash."""
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))

    request = DeleteTextFileContentsRequest(
        file_path=str(test_file),
        file_hash=file_hash,
        ranges=[
            FileRange(
                start=2,
                end=2,
                range_hash="invalid_hash",
            )
        ],
    )

    result = await editor.delete_text_file_contents(request)

    assert result[str(test_file)]["result"] == "error"
    assert "hash mismatch" in result[str(test_file)]["reason"].lower()
    assert test_file.read_text() == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"


@pytest.mark.asyncio
async def test_delete_with_invalid_range(editor, test_file):
    """Test deleting with invalid line range."""
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))
    line2_hash = editor.calculate_hash("Line 2\n")

    request = DeleteTextFileContentsRequest(
        file_path=str(test_file),
        file_hash=file_hash,
        ranges=[
            FileRange(
                start=2,
                end=1,  # Invalid: end before start
                range_hash=line2_hash,
            )
        ],
    )

    result = await editor.delete_text_file_contents(request)

    assert result[str(test_file)]["result"] == "error"
    assert (
        "end line" in result[str(test_file)]["reason"].lower()
        and "less than start line" in result[str(test_file)]["reason"].lower()
    )
    assert test_file.read_text() == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"


@pytest.mark.asyncio
async def test_delete_with_out_of_range(editor, test_file):
    """Test deleting lines beyond file length."""
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))

    request = DeleteTextFileContentsRequest(
        file_path=str(test_file),
        file_hash=file_hash,
        ranges=[
            FileRange(
                start=10,
                end=12,
                range_hash="any_hash",  # Hash doesn't matter as it will fail before hash check
            )
        ],
    )

    result = await editor.delete_text_file_contents(request)

    assert result[str(test_file)]["result"] == "error"
    assert (
        "start line" in result[str(test_file)]["reason"].lower()
        and "exceeds file length" in result[str(test_file)]["reason"].lower()
    )
    assert test_file.read_text() == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"


@pytest.mark.asyncio
async def test_delete_with_overlapping_ranges(editor, test_file):
    """Test deleting with overlapping ranges."""
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Prepare hashes for the ranges
    lines = content.splitlines(keepends=True)
    range1_hash = editor.calculate_hash("".join(lines[1:3]))  # Lines 2-3
    range2_hash = editor.calculate_hash("".join(lines[2:4]))  # Lines 3-4

    request = DeleteTextFileContentsRequest(
        file_path=str(test_file),
        file_hash=file_hash,
        ranges=[
            FileRange(
                start=2,
                end=3,
                range_hash=range1_hash,
            ),
            FileRange(
                start=3,
                end=4,
                range_hash=range2_hash,
            ),
        ],
    )

    result = await editor.delete_text_file_contents(request)

    assert result[str(test_file)]["result"] == "error"
    assert "overlapping ranges" in result[str(test_file)]["reason"].lower()
    assert test_file.read_text() == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"


@pytest.mark.asyncio
async def test_delete_multiple_ranges(editor, test_file):
    """Test deleting multiple non-consecutive ranges."""
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Prepare hashes for the ranges
    lines = content.splitlines(keepends=True)
    range1_hash = editor.calculate_hash(lines[1])  # Line 2
    range2_hash = editor.calculate_hash(lines[3])  # Line 4

    request = DeleteTextFileContentsRequest(
        file_path=str(test_file),
        file_hash=file_hash,
        ranges=[
            FileRange(
                start=2,
                end=2,
                range_hash=range1_hash,
            ),
            FileRange(
                start=4,
                end=4,
                range_hash=range2_hash,
            ),
        ],
    )

    result = await editor.delete_text_file_contents(request)

    assert result[str(test_file)]["result"] == "ok"
    assert test_file.read_text() == "Line 1\nLine 3\nLine 5\n"
