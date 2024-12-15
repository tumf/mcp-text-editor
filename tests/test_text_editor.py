"""Tests for the TextEditor class."""

import pytest

from mcp_text_editor.text_editor import TextEditor


@pytest.fixture
def editor():
    """Create TextEditor instance."""
    return TextEditor()


@pytest.fixture
def test_file(tmp_path):
    """Create a temporary test file."""
    file_path = tmp_path / "test.txt"
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def test_invalid_encoding_file(tmp_path):
    """Create a temporary file with a custom encoding to test encoding errors."""
    file_path = tmp_path / "invalid_encoding.txt"
    # Create Shift-JIS encoded file that will fail to decode with UTF-8
    test_data = bytes(
        [0x83, 0x65, 0x83, 0x58, 0x83, 0x67, 0x0A]
    )  # "テスト\n" in Shift-JIS
    with open(file_path, "wb") as f:
        f.write(test_data)
    return str(file_path)


@pytest.mark.asyncio
async def test_calculate_hash(editor):
    """Test hash calculation."""
    content = "test content"
    hash1 = editor.calculate_hash(content)
    hash2 = editor.calculate_hash(content)
    assert hash1 == hash2
    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA-256 hash length


@pytest.mark.asyncio
async def test_read_file_contents(editor, test_file):
    """Test reading file contents."""
    # Test reading entire file
    content, start, end, hash_value, total_lines, size = (
        await editor.read_file_contents(str(test_file))
    )
    assert content == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    assert start == 1
    assert end == 5
    assert isinstance(hash_value, str)
    assert total_lines == 5
    assert size == len(content)

    # Test reading specific lines
    content, start, end, hash_value, total_lines, size = (
        await editor.read_file_contents(str(test_file), line_start=2, line_end=4)
    )
    assert content == "Line 2\nLine 3\nLine 4\n"
    assert start == 2
    assert end == 4
    assert isinstance(hash_value, str)
    assert total_lines == 5  # Total lines in file should remain the same
    assert size == len(content)  # Size should match the selected content


@pytest.mark.asyncio
async def test_encoding_error(editor, test_invalid_encoding_file):
    """Test handling of encoding errors when reading a file with incorrect encoding."""
    # Try to read Shift-JIS file with UTF-8 encoding
    with pytest.raises(UnicodeDecodeError) as excinfo:
        await editor.read_file_contents(test_invalid_encoding_file, encoding="utf-8")

    assert "Failed to decode file" in str(excinfo.value)
    assert "utf-8" in str(excinfo.value)

    # Try to read Shift-JIS file with incorrect encoding in edit_file_contents
    result = await editor.edit_file_contents(
        test_invalid_encoding_file,
        "dummy_hash",
        [{"line_start": 1, "contents": "test", "range_hash": "dummy_hash"}],
        encoding="utf-8",
    )

    assert result["result"] == "error"
    assert "Error editing file" in result["reason"]
    assert "decode" in result["reason"].lower()
