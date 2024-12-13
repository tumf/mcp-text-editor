"""Tests for the TextEditor class."""

import pytest

from mcp_text_editor.text_editor import TextEditor


@pytest.fixture
def editor():
    """Create TextEditor instance."""
    return TextEditor()


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
        await editor.read_file_contents(test_file)
    )
    assert content == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    assert start == 1
    assert end == 5
    assert isinstance(hash_value, str)
    assert total_lines == 5
    assert size == len(content)

    # Test reading specific lines
    content, start, end, hash_value, total_lines, size = (
        await editor.read_file_contents(test_file, line_start=2, line_end=4)
    )
    assert content == "Line 2\nLine 3\nLine 4\n"
    assert start == 2
    assert end == 4
    assert isinstance(hash_value, str)
    assert total_lines == 5  # Total lines in file should remain the same
    assert size == len(content)  # Size should match the selected content


@pytest.mark.asyncio
async def test_read_file_contents_invalid_file(editor):
    """Test reading non-existent file."""
    with pytest.raises(FileNotFoundError):
        await editor.read_file_contents("nonexistent.txt")


@pytest.mark.asyncio
async def test_edit_file_contents(editor, test_file):
    """Test editing file contents."""
    # Read initial content and calculate hash
    content, _, _, initial_hash, _, _ = await editor.read_file_contents(test_file)

    # Create edit operation
    patches = [
        {
            "line_start": 2,
            "line_end": 3,
            "contents": "Modified Line 2\n",
        }
    ]

    # Apply edit
    result = await editor.edit_file_contents(test_file, initial_hash, patches)
    assert result["result"] == "ok"

    # Verify changes
    new_content, _, _, new_hash, _, _ = await editor.read_file_contents(test_file)
    assert "Modified Line 2" in new_content
    assert result["hash"] == new_hash


@pytest.mark.asyncio
async def test_edit_file_contents_conflict(editor, test_file):
    """Test editing file with conflict."""
    # Create operation with incorrect hash
    patches = [
        {
            "line_start": 1,
            "line_end": 2,
            "contents": "New content\n",
        }
    ]

    # Attempt edit
    result = await editor.edit_file_contents(test_file, "incorrect_hash", patches)
    assert result["result"] == "error"
    assert "hash mismatch" in result["reason"].lower()
    assert result["content"] is not None


@pytest.mark.asyncio
async def test_edit_file_contents_overlapping_patches(editor, test_file):
    """Test editing with overlapping patches."""
    content, _, _, initial_hash, _, _ = await editor.read_file_contents(test_file)

    # Create patches with overlap
    patches = [
        {
            "line_start": 1,
            "line_end": 3,
            "contents": "New Lines 1-2\n",
        },
        {
            "line_start": 2,
            "line_end": 4,
            "contents": "Overlapping Lines 2-3\n",
        },
    ]

    # Attempt edit
    result = await editor.edit_file_contents(test_file, initial_hash, patches)
    assert result["result"] == "error"
    assert "overlapping" in result["reason"].lower()


@pytest.mark.asyncio
async def test_edit_file_contents_multiple_patches(editor, tmp_path):
    """Test editing file with multiple patches applied from bottom to top."""
    # Create a test file
    test_file = tmp_path / "multiple_patches_test.txt"
    test_content = "aaaa\nbbbb\ncccc\ndddd\n"
    test_file.write_text(test_content)

    # Read initial content and hash
    content, _, _, initial_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Create patches that need to be applied from bottom to top
    patches = [
        {
            "line_start": 1,
            "line_end": 1,
            "contents": "aaaa\naaaa",
        },
        {
            "line_start": 4,
            "line_end": 4,
            "contents": "dddd\ndddd",
        },
    ]

    # Apply patches
    result = await editor.edit_file_contents(str(test_file), initial_hash, patches)
    assert result["result"] == "ok"

    # Verify the final content
    expected_content = "aaaa\naaaa\nbbbb\ncccc\ndddd\ndddd\n"
    final_content = test_file.read_text()
    assert final_content == expected_content


@pytest.mark.asyncio
async def test_edit_file_contents_multiple_patches_different_orders(editor, tmp_path):
    """Test that patches are applied correctly regardless of input order."""
    test_cases = [
        # Case 1: Bottom to top order
        [
            {
                "line_start": 4,
                "line_end": 4,
                "contents": "dddd\ndddd",
            },
            {
                "line_start": 1,
                "line_end": 1,
                "contents": "aaaa\naaaa",
            },
        ],
        # Case 2: Top to bottom order
        [
            {
                "line_start": 1,
                "line_end": 1,
                "contents": "aaaa\naaaa",
            },
            {
                "line_start": 4,
                "line_end": 4,
                "contents": "dddd\ndddd",
            },
        ],
    ]

    expected_content = "aaaa\naaaa\nbbbb\ncccc\ndddd\ndddd\n"

    for test_number, patches in enumerate(test_cases, 1):
        # Create a fresh test file for each case
        test_file = tmp_path / f"multiple_patches_order_test_{test_number}.txt"
        test_content = "aaaa\nbbbb\ncccc\ndddd\n"
        test_file.write_text(test_content)

        # Read initial content and hash
        content, _, _, initial_hash, _, _ = await editor.read_file_contents(
            str(test_file)
        )

        # Apply patches
        result = await editor.edit_file_contents(str(test_file), initial_hash, patches)
        assert result["result"] == "ok", f"Failed for test case {test_number}"

        # Verify the final content
        final_content = test_file.read_text()
        assert final_content == expected_content, (
            f"Content mismatch for test case {test_number}\n"
            f"Expected:\n{expected_content}\n"
            f"Got:\n{final_content}"
        )


@pytest.mark.asyncio
async def test_edit_file_contents_complex_multiple_patches(editor, tmp_path):
    """Test editing with complex multiple patches including insertions and replacements."""
    # Create a test file
    test_file = tmp_path / "complex_patches_test.txt"
    test_content = "1111\n2222\n3333\n4444\n5555\n"
    test_file.write_text(test_content)

    # Read initial content and hash
    content, _, _, initial_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Create complex patches
    patches = [
        {
            "line_start": 1,
            "line_end": 2,
            "contents": "1111\n1111\n2222",  # Replace and add line at the top
        },
        {
            "line_start": 4,
            "line_end": 5,
            "contents": "4444\n4444\n5555\n5555",  # Replace and add lines at the bottom
        },
    ]

    # Apply patches
    result = await editor.edit_file_contents(str(test_file), initial_hash, patches)
    assert result["result"] == "ok"

    # Verify the final content
    expected_content = "1111\n1111\n2222\n3333\n4444\n4444\n5555\n5555\n"
    final_content = test_file.read_text()
    assert final_content == expected_content


@pytest.mark.asyncio
async def test_edit_file_contents_with_preserving_newlines(editor, tmp_path):
    """Test editing with proper newline handling."""
    # Create a test file with mixed newline endings
    test_file = tmp_path / "newline_test.txt"
    test_content = "line1\nline2\nline3\n"
    test_file.write_text(test_content)

    # Read initial content and hash
    content, _, _, initial_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Create patches that should preserve newlines
    patches = [
        {
            "line_start": 2,
            "line_end": 2,
            "contents": "new line2",  # No explicit newline
        },
    ]

    # Apply patches
    result = await editor.edit_file_contents(str(test_file), initial_hash, patches)
    assert result["result"] == "ok"

    # Verify the final content has preserved newlines
    expected_content = "line1\nnew line2\nline3\n"
    final_content = test_file.read_text()
    assert final_content == expected_content


@pytest.mark.asyncio
async def test_read_multiple_ranges(editor, test_file):
    """Test reading multiple ranges including ranges with no end specified."""
    ranges = [
        {
            "file_path": test_file,
            "ranges": [
                {"start": 1},  # Read from start to end (no end specified)
                {"start": 2, "end": 4},  # Read specific range
            ],
        }
    ]

    result = await editor.read_multiple_ranges(ranges)

    # Check first range (entire file)
    first_range = result[test_file][0]
    assert first_range["content"] == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    assert first_range["start_line"] == 1
    assert first_range["end_line"] == 5
    assert first_range["total_lines"] == 5

    # Check second range (specific lines)
    second_range = result[test_file][1]
    assert second_range["content"] == "Line 2\nLine 3\nLine 4\n"
    assert second_range["start_line"] == 2
    assert second_range["end_line"] == 4


@pytest.mark.asyncio
async def test_read_multiple_ranges_out_of_bounds_start(editor, test_file):
    """Test reading ranges where start line exceeds file length."""
    ranges = [
        {
            "file_path": test_file,
            "ranges": [
                {"start": 1000},  # Way beyond file end
                {"start": 6},  # Just beyond file end
            ],
        }
    ]

    result = await editor.read_multiple_ranges(ranges)

    # Check first range (start line way beyond file end)
    first_range = result[test_file][0]
    assert first_range["content"] == ""
    assert first_range["start_line"] == 1000
    assert first_range["end_line"] == 1000
    assert first_range["total_lines"] == 5
    assert first_range["content_size"] == 0

    # Check second range (start line just beyond file end)
    second_range = result[test_file][1]
    assert second_range["content"] == ""
    assert second_range["start_line"] == 6
    assert second_range["end_line"] == 6
    assert second_range["total_lines"] == 5
    assert second_range["content_size"] == 0


@pytest.mark.asyncio
async def test_read_multiple_ranges_out_of_bounds_end(editor, test_file):
    """Test reading ranges where end line exceeds file length."""
    ranges = [
        {
            "file_path": test_file,
            "ranges": [
                {"start": 1, "end": 1000},  # End way beyond file end
                {"start": 2, "end": 6},  # End just beyond file end
            ],
        }
    ]

    result = await editor.read_multiple_ranges(ranges)

    # Check first range (end line way beyond file end)
    first_range = result[test_file][0]
    assert first_range["content"] == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    assert first_range["start_line"] == 1
    assert first_range["end_line"] == 5
    assert first_range["total_lines"] == 5
    assert first_range["content_size"] == len(first_range["content"])

    # Check second range (end line just beyond file end)
    second_range = result[test_file][1]
    assert second_range["content"] == "Line 2\nLine 3\nLine 4\nLine 5\n"
    assert second_range["start_line"] == 2
    assert second_range["end_line"] == 5
    assert second_range["total_lines"] == 5
    assert second_range["content_size"] == len(second_range["content"])


@pytest.mark.asyncio
async def test_validate_file_path(editor):
    """Test file path validation."""
    # Valid path
    editor._validate_file_path("/path/to/file.txt")

    # Test path traversal attempt
    with pytest.raises(ValueError, match="Path traversal not allowed"):
        editor._validate_file_path("../path/to/file.txt")
    with pytest.raises(ValueError, match="Path traversal not allowed"):
        editor._validate_file_path("folder/../file.txt")


@pytest.mark.asyncio
async def test_validate_environment():
    """Test environment validation."""
    editor = TextEditor()
    # Currently just verifies it can be called without error
    editor._validate_environment()


@pytest.mark.asyncio
async def test_edit_file_contents_io_error(editor, tmp_path):
    """Test editing file with IO error."""
    test_file = tmp_path / "io_error_test.txt"
    test_file.write_text("test content")

    # Make file read-only
    test_file.chmod(0o444)

    result = await editor.edit_file_contents(
        str(test_file),
        editor.calculate_hash("test content"),
        [{"line_start": 1, "contents": "new content"}],
    )

    assert result["result"] == "error"
    assert "permission denied" in result["reason"].lower()

    # Restore permissions for cleanup
    test_file.chmod(0o644)
