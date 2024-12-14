"""Tests for the TextEditor class."""

import os

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
    ranges = [{"file_path": test_file, "ranges": [{"start": 2, "end": 3}]}]
    range_result = await editor.read_multiple_ranges(ranges)
    target_range = range_result[test_file][0]
    range_hash = target_range["range_hash"]

    content, _, _, initial_hash, _, _ = await editor.read_file_contents(test_file)

    # Create edit operation
    patches = [
        {
            "line_start": 2,
            "line_end": 3,
            "contents": "Modified Line 2\n",
            "range_hash": range_hash,
        }
    ]

    # Apply edit
    result = await editor.edit_file_contents(test_file, initial_hash, patches)
    assert result["result"] == "ok"

    # Verify changes
    new_content, _, _, new_hash, _, _ = await editor.read_file_contents(test_file)
    assert "Modified Line 2" in new_content
    assert result["file_hash"] == new_hash


@pytest.mark.asyncio
async def test_edit_file_contents_conflict(editor, test_file):
    """Test editing file with conflict."""
    # Get range hashes for the area we want to modify
    ranges = [{"file_path": test_file, "ranges": [{"start": 1, "end": 2}]}]
    range_result = await editor.read_multiple_ranges(ranges)
    range_hash = range_result[test_file][0]["range_hash"]

    # Read initial file hash
    _, _, _, initial_hash, _, _ = await editor.read_file_contents(test_file)

    # Create edit operation with incorrect file hash but correct range hash
    patches = [
        {
            "line_start": 1,
            "line_end": 2,
            "contents": "New content\n",
            "range_hash": range_hash,
        }
    ]

    # Attempt edit with incorrect file hash
    result = await editor.edit_file_contents(test_file, "incorrect_hash", patches)
    assert result["result"] == "error"
    assert "hash mismatch" in result["reason"].lower()
    assert result["content"] is not None


@pytest.mark.asyncio
async def test_edit_file_contents_range_hash_mismatch(editor, test_file):
    """Test editing file with range_hash mismatch."""
    # Read initial content and hash
    content, _, _, initial_hash, _, _ = await editor.read_file_contents(test_file)

    # Create edit operation with incorrect range_hash
    patches = [
        {
            "line_start": 2,
            "line_end": 3,
            "contents": "Modified Line 2\n",
            "range_hash": "incorrect_range_hash",
        }
    ]

    # Apply edit
    result = await editor.edit_file_contents(test_file, initial_hash, patches)
    assert result["result"] == "error"
    assert "range hash mismatch" in result["reason"].lower()
    assert result["hash"] is None
    assert result["content"] is not None  # Should return original content


@pytest.mark.asyncio
async def test_edit_file_contents_missing_range_hash(editor, test_file):
    """Test editing file with missing range_hash."""
    # Read initial content and hash
    content, _, _, initial_hash, _, _ = await editor.read_file_contents(test_file)

    # Create edit operation without range_hash
    patches = [
        {
            "line_start": 2,
            "line_end": 3,
            "contents": "Modified Line 2\n",
            # range_hash is intentionally omitted
        }
    ]

    # Apply edit
    result = await editor.edit_file_contents(test_file, initial_hash, patches)
    assert result["result"] == "error"
    assert "range_hash is required" in result["reason"].lower()
    assert result["hash"] is None
    assert result["content"] is not None  # Should return original content


@pytest.mark.asyncio
async def test_edit_file_contents_overlapping_patches(editor, test_file):
    """Test editing with overlapping patches."""
    # Get range hashes for the areas we want to modify
    ranges = [
        {
            "file_path": test_file,
            "ranges": [
                {"start": 1, "end": 3},  # First three lines
                {"start": 2, "end": 4},  # Lines 2-4
            ],
        }
    ]
    range_result = await editor.read_multiple_ranges(ranges)
    range1_hash = range_result[test_file][0]["range_hash"]
    range2_hash = range_result[test_file][1]["range_hash"]

    content, _, _, initial_hash, _, _ = await editor.read_file_contents(test_file)

    # Create patches with overlap
    patches = [
        {
            "line_start": 1,
            "line_end": 3,
            "contents": "New Lines 1-2\n",
            "range_hash": range1_hash,
        },
        {
            "line_start": 2,
            "line_end": 4,
            "contents": "Overlapping Lines 2-3\n",
            "range_hash": range2_hash,
        },
    ]

    # Attempt edit
    result = await editor.edit_file_contents(test_file, initial_hash, patches)

    # Verify that overlapping patches are detected
    assert result["result"] == "error"
    assert "overlapping patches" in result["reason"].lower()
    assert result["hash"] is None
    assert result["content"] is not None


@pytest.mark.asyncio
async def test_edit_file_contents_multiple_patches(editor, tmp_path):
    """Test editing file with multiple patches applied from bottom to top."""
    # Create a test file
    test_file = tmp_path / "multiple_patches_test.txt"
    test_content = "aaaa\nbbbb\ncccc\ndddd\n"
    test_file.write_text(test_content)

    # Get range hashes for the areas we want to modify
    ranges = [
        {
            "file_path": str(test_file),
            "ranges": [{"start": 1, "end": 1}, {"start": 4, "end": 4}],
        }
    ]
    range_result = await editor.read_multiple_ranges(ranges)
    range1_hash = range_result[str(test_file)][0]["range_hash"]
    range2_hash = range_result[str(test_file)][1]["range_hash"]

    # Read initial content and hash
    content, _, _, initial_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Create patches that need to be applied from bottom to top
    patches = [
        {
            "line_start": 1,
            "line_end": 1,
            "contents": "aaaa\naaaa",
            "range_hash": range1_hash,
        },
        {
            "line_start": 4,
            "line_end": 4,
            "contents": "dddd\ndddd",
            "range_hash": range2_hash,
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
    expected_content = "aaaa\naaaa\nbbbb\ncccc\ndddd\ndddd\n"

    # Function to get range hashes for the test file
    async def get_range_hashes(file_path):
        ranges = [
            {
                "file_path": file_path,
                "ranges": [{"start": 1, "end": 1}, {"start": 4, "end": 4}],
            }
        ]
        range_result = await editor.read_multiple_ranges(ranges)
        return (
            range_result[file_path][0]["range_hash"],
            range_result[file_path][1]["range_hash"],
        )

    for test_number in range(1, 3):
        # Create a fresh test file for each case
        test_file = tmp_path / f"multiple_patches_order_test_{test_number}.txt"
        test_content = "aaaa\nbbbb\ncccc\ndddd\n"
        test_file.write_text(test_content)

        # Get range hashes
        range1_hash, range2_hash = await get_range_hashes(str(test_file))

        # Read initial content and hash
        content, _, _, initial_hash, _, _ = await editor.read_file_contents(
            str(test_file)
        )

        # Create test case patches with the appropriate hashes
        patches = [
            {
                "line_start": 4 if test_number == 1 else 1,
                "line_end": 4 if test_number == 1 else 1,
                "contents": "dddd\ndddd" if test_number == 1 else "aaaa\naaaa",
                "range_hash": range2_hash if test_number == 1 else range1_hash,
            },
            {
                "line_start": 1 if test_number == 1 else 4,
                "line_end": 1 if test_number == 1 else 4,
                "contents": "aaaa\naaaa" if test_number == 1 else "dddd\ndddd",
                "range_hash": range1_hash if test_number == 1 else range2_hash,
            },
        ]

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
@pytest.mark.asyncio
async def test_edit_file_contents_complex_multiple_patches(editor, tmp_path):
    """Test editing with complex multiple patches including insertions and replacements."""
    # Create a test file
    test_file = tmp_path / "complex_patches_test.txt"
    test_content = "1111\n2222\n3333\n4444\n5555\n"
    test_file.write_text(test_content)

    # Get range hashes for the areas we want to modify
    ranges = [
        {
            "file_path": str(test_file),
            "ranges": [{"start": 1, "end": 2}, {"start": 4, "end": 5}],
        }
    ]
    range_result = await editor.read_multiple_ranges(ranges)
    range1_hash = range_result[str(test_file)][0]["range_hash"]
    range2_hash = range_result[str(test_file)][1]["range_hash"]

    # Read initial content and hash
    content, _, _, initial_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Create complex patches
    patches = [
        {
            "line_start": 1,
            "line_end": 2,
            "contents": "1111\n1111\n2222",  # Replace and add line at the top
            "range_hash": range1_hash,
        },
        {
            "line_start": 4,
            "line_end": 5,
            "contents": "4444\n4444\n5555\n5555",  # Replace and add lines at the bottom
            "range_hash": range2_hash,
        },
    ]

    # Apply patches
    result = await editor.edit_file_contents(str(test_file), initial_hash, patches)
    assert result["result"] == "ok"

    # Verify the final content
    expected_content = "1111\n1111\n2222\n3333\n4444\n4444\n5555\n5555\n"
    final_content = test_file.read_text()
    assert final_content == expected_content
    """Test editing with proper newline handling."""
    # Create a test file with mixed newline endings
    test_file = tmp_path / "newline_test.txt"
    test_content = "line1\nline2\nline3\n"
    test_file.write_text(test_content)

    # Get range hash for line 2
    ranges = [{"file_path": str(test_file), "ranges": [{"start": 2, "end": 2}]}]
    range_result = await editor.read_multiple_ranges(ranges)
    range_hash = range_result[str(test_file)][0]["range_hash"]

    # Read initial content and hash
    content, _, _, initial_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Create patches that should preserve newlines
    patches = [
        {
            "line_start": 2,
            "line_end": 2,
            "contents": "new line2",  # No explicit newline
            "range_hash": range_hash,
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

    # Get the range hash first
    ranges = [{"file_path": str(test_file), "ranges": [{"start": 1, "end": 1}]}]
    range_result = await editor.read_multiple_ranges(ranges)
    range_hash = range_result[str(test_file)][0]["range_hash"]

    # Make file read-only
    test_file.chmod(0o444)

    result = await editor.edit_file_contents(
        str(test_file),
        editor.calculate_hash("test content"),
        [
            {
                "line_start": 1,
                "line_end": 1,
                "contents": "new content",
                "range_hash": range_hash,
            }
        ],
    )

    assert result["result"] == "error"
    assert "permission denied" in result["reason"].lower()
    # Restore permissions for cleanup
    test_file.chmod(0o644)


@pytest.mark.asyncio
async def test_read_file_contents_sjis(editor, test_file_sjis):
    """Test reading Shift-JIS encoded file.

    This test verifies that:
    1. The text editor can detect and read Shift-JIS encoded files
    2. The content is correctly decoded to Unicode
    3. Line counting works correctly with multi-byte characters
    """
    # Test reading entire file
    content, start, end, hash_value, total_lines, size = (
        await editor.read_file_contents(test_file_sjis)
    )

    # The expected string contains Japanese characters '\u30c6\u30b9\u30c8' (test)
    # followed by numbers 1-3, each on a new line
    expected = "\u30c6\u30b9\u30c81\n\u30c6\u30b9\u30c82\n\u30c6\u30b9\u30c83\n"
    assert content == expected
    assert start == 1
    assert end == 3  # 3 lines total
    assert isinstance(hash_value, str)
    assert len(hash_value) == 64  # SHA-256 hash
    assert total_lines == 3
    actual_size = os.path.getsize(test_file_sjis)
    assert size == actual_size

    # Test reading specific lines
    content, start, end, hash_value, total_lines, size = (
        await editor.read_file_contents(test_file_sjis, line_start=2, line_end=3)
    )
    expected_partial = "\u30c6\u30b9\u30c82\n\u30c6\u30b9\u30c83\n"
    assert content == expected_partial
    assert start == 2
    assert end == 3
    assert isinstance(hash_value, str)
    assert len(hash_value) == 64
    assert total_lines == 3  # Total lines in file should remain the same
    assert size == len(content.encode("shift-jis"))


@pytest.mark.asyncio
async def test_range_hash_calculation(editor, test_file):
    """Test range hash calculation functionality."""
    # Test reading entire file first
    content, start, end, file_hash, total_lines, size = await editor.read_file_contents(
        test_file
    )

    # Then read multiple ranges
    ranges = [
        {
            "file_path": test_file,
            "ranges": [
                {"start": 1, "end": 3},  # First three lines
                {"start": 4, "end": 5},  # Last two lines
            ],
        }
    ]

    result = await editor.read_multiple_ranges(ranges)
    ranges_result = result[test_file]

    # Verify that each range has a range_hash
    for range_data in ranges_result:
        assert "range_hash" in range_data, "range_hash should be present in results"
        assert isinstance(range_data["range_hash"], str)
        assert len(range_data["range_hash"]) == 64  # SHA-256 hash length

    # Verify that range_hash is different for different ranges
    assert ranges_result[0]["range_hash"] != ranges_result[1]["range_hash"]

    # Verify that range_hash remains consistent for same content
    repeat_result = await editor.read_multiple_ranges(ranges)
    assert (
        result[test_file][0]["range_hash"] == repeat_result[test_file][0]["range_hash"]
    )
    assert (
        result[test_file][1]["range_hash"] == repeat_result[test_file][1]["range_hash"]
    )


@pytest.mark.asyncio
async def test_edit_new_file(editor, tmp_path):
    """Test creating and editing a new file."""
    new_file = tmp_path / "new_file.txt"
    initial_content = "This is a new file\n"

    # Create edit operation for new file
    result = await editor.edit_file_contents(
        str(new_file),
        "",  # Empty hash for new file
        [
            {
                "line_start": 1,
                "line_end": 1,
                "contents": initial_content,
                "range_hash": editor.calculate_hash(
                    ""
                ),  # Empty content hash for new file
            }
        ],
    )

    # Verify file creation was successful
    assert result["result"] == "ok"
    assert result["file_hash"] is not None
    assert new_file.exists()

    # Verify content
    content = new_file.read_text()
    assert content == initial_content

    # Try to append content
    second_content = "This is the second line\n"
    result = await editor.edit_file_contents(
        str(new_file),
        result["file_hash"],  # Use hash from previous operation
        [
            {
                "line_start": 2,
                "line_end": 1,  # End before start indicates append
                "contents": second_content,
                "range_hash": editor.calculate_hash(""),  # Empty hash for append
            }
        ],
    )

    # Verify append was successful
    assert result["result"] == "ok"
    assert result["file_hash"] is not None

    # Final content check
    content = new_file.read_text()
    assert content == initial_content + second_content


@pytest.mark.asyncio
async def test_append_content_without_range_hash(editor, tmp_path):
    """Test appending content to an existing file without range_hash.

    This test verifies that:
    1. Content can be appended to an existing file
    2. Appending works when line_end < line_start
    3. Range hash is not required for appending
    4. File hash consistency is maintained
    """
    # Create a test file with initial content
    test_file = tmp_path / "append_test.txt"
    initial_content = "Initial line 1\nInitial line 2\n"
    test_file.write_text(initial_content)

    # Get file hash and total lines
    content, _, _, initial_hash, total_lines, _ = await editor.read_file_contents(
        str(test_file)
    )

    # Append new content without range_hash
    new_content = "New line 3\nNew line 4\n"
    result = await editor.edit_file_contents(
        str(test_file),
        initial_hash,
        [
            {
                "line_start": total_lines + 1,
                "line_end": total_lines,  # end < start indicates append
                "contents": new_content,
                # No range_hash needed for append operation
            }
        ],
    )

    # Verify append was successful
    assert result["result"] == "ok"
    assert result["file_hash"] is not None

    # Verify content
    content = test_file.read_text()
    assert content == initial_content + new_content


@pytest.mark.asyncio
async def test_create_empty_file(editor, tmp_path):
    """Test creating an empty file."""
    empty_file = tmp_path / "empty.txt"

    # Create an empty file
    result = await editor.edit_file_contents(
        str(empty_file),
        "",  # Empty hash for new file
        [{"line_start": 1, "contents": ""}],  # No range_hash needed for new file
    )

    # Verify file creation was successful
    assert result["result"] == "ok"
    assert result["file_hash"] is not None
    assert empty_file.exists()

    # Verify file is empty except for a newline
    content = empty_file.read_text()
    assert content == "\n"  # Should contain just a newline

    # Verify file stats
    file_stats = await editor.read_file_contents(str(empty_file))
    content, start, end, hash_value, total_lines, size = file_stats
    assert content == "\n"
    assert total_lines == 1
    assert size == len(content)
