"""Tests for the TextEditor class."""

import pytest

from mcp_text_editor.text_editor import EditPatch, TextEditor


@pytest.fixture
def editor():
    """Create TextEditor instance."""
    return TextEditor()


@pytest.mark.asyncio
async def test_edit_file_with_edit_patch_object(editor, tmp_path):
    """Test editing a file using EditPatch object."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\n")
    file_hash = editor.calculate_hash(test_file.read_text())
    first_line_content = "line1\n"

    # Create an EditPatch object
    patch = EditPatch(
        start=1,
        end=1,
        contents="new line\n",
        range_hash=editor.calculate_hash(first_line_content),
    )

    result = await editor.edit_file_contents(str(test_file), file_hash, [patch])

    assert result["result"] == "ok"
    assert test_file.read_text() == "new line\nline2\nline3\n"


@pytest.fixture
def test_file(tmp_path):
    """Create a temporary test file."""
    file_path = tmp_path / "test.txt"
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    file_path.write_text(content)
    return file_path


@pytest.mark.asyncio
async def test_directory_creation_error(editor, tmp_path, mocker):
    """Test file creation when parent directory creation fails."""
    test_dir = tmp_path / "test_dir"
    test_file = test_dir / "test.txt"

    # Mock os.makedirs to raise an OSError
    mocker.patch("os.makedirs", side_effect=OSError("Permission denied"))

    result = await editor.edit_file_contents(
        str(test_file), "", [EditPatch(contents="test content\n", range_hash="")]
    )

    assert result["result"] == "error"
    assert "Failed to create directory" in result["reason"]
    assert result["file_hash"] is None


@pytest.mark.asyncio
async def test_missing_range_hash(editor, test_file):
    """Test editing without required range hash."""
    _, _, _, file_hash, _, _ = await editor.read_file_contents(test_file)

    # Try to edit without range_hash
    with pytest.raises(ValueError, match="range_hash is required"):
        EditPatch(start=2, end=2, contents="New content\n", range_hash=None)

    with pytest.raises(ValueError, match="range_hash is required"):
        # Trying with missing range_hash field should also raise
        EditPatch(start=2, end=2, contents="New content\n")


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
        await editor.read_file_contents(str(test_file), start=2, end=4)
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
        [{"start": 1, "contents": "test", "range_hash": "dummy_hash"}],
        encoding="utf-8",
    )

    assert result["result"] == "error"
    assert "Error editing file" in result["reason"]
    assert "decode" in result["reason"].lower()


@pytest.mark.asyncio
async def test_create_new_file(editor, tmp_path):
    """Test creating a new file."""
    new_file = tmp_path / "new_file.txt"
    content = "New file content\nLine 2\n"

    # Test creating a new file
    result = await editor.edit_file_contents(
        str(new_file),
        "",  # No hash for new file
        [
            {"start": 1, "contents": content, "range_hash": ""}
        ],  # Empty range_hash for new files
    )
    assert result["result"] == "ok"
    assert new_file.read_text() == content


@pytest.mark.asyncio
async def test_update_file(editor, tmp_path):
    """Test updating an existing file."""
    # Create a test file
    test_file = tmp_path / "test_update.txt"
    original_content = "Line 1\nLine 2\nLine 3\n"
    test_file.write_text(original_content)

    # Read the content and get hash
    content, start, end, file_hash, total_lines, size = await editor.read_file_contents(
        str(test_file)
    )

    # Update the second line
    new_content = "Updated Line 2\n"
    result = await editor.edit_file_contents(
        str(test_file),
        file_hash,
        [
            {
                "start": 2,
                "end": 2,
                "contents": new_content,
                "range_hash": editor.calculate_hash("Line 2\n"),
            }
        ],
    )

    assert result["result"] == "ok"
    assert test_file.read_text() == "Line 1\nUpdated Line 2\nLine 3\n"


@pytest.mark.asyncio
async def test_create_file_in_new_directory(editor, tmp_path):
    """Test creating a file in a new directory structure."""
    # Test file in a new directory structure
    new_file = tmp_path / "subdir" / "nested" / "test.txt"
    content = "Content in nested directory\n"

    result = await editor.edit_file_contents(
        str(new_file),
        "",  # No hash for new file
        [
            {"start": 1, "contents": content, "range_hash": ""}
        ],  # Empty range_hash for new file
    )

    assert result["result"] == "ok"
    assert new_file.read_text() == content


@pytest.mark.asyncio
async def test_file_hash_mismatch(editor, tmp_path):
    """Test handling of file hash mismatch."""
    # Create a test file
    test_file = tmp_path / "test_hash_mismatch.txt"
    original_content = "Line 1\nLine 2\nLine 3\n"
    test_file.write_text(original_content)

    result = await editor.edit_file_contents(
        str(test_file),
        "invalid_hash",  # Wrong hash
        [
            {
                "start": 2,
                "end": 2,
                "contents": "Updated Line\n",
                "range_hash": editor.calculate_hash("Line 2\n"),
            }
        ],
    )

    assert result["result"] == "error"
    assert "hash mismatch" in result["reason"].lower()
    assert test_file.read_text() == original_content  # File should remain unchanged
    assert test_file.read_text() == original_content  # File should remain unchanged


@pytest.mark.asyncio
async def test_path_traversal_prevention(editor, tmp_path):
    """Test prevention of path traversal attacks."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Some content\n")
    unsafe_path = str(test_file) + "/.."  # Try to traverse up

    # Test read operation
    with pytest.raises(ValueError) as excinfo:
        await editor.read_file_contents(unsafe_path)
    assert "Path traversal not allowed" in str(excinfo.value)

    # Test write operation
    with pytest.raises(ValueError) as excinfo:
        await editor.edit_file_contents(
            unsafe_path,
            "",
            [{"start": 1, "contents": "malicious content\n", "range_hash": None}],
        )
    assert "Path traversal not allowed" in str(excinfo.value)


@pytest.mark.asyncio
async def test_overlapping_patches(editor, tmp_path):
    """Test handling of overlapping patches."""
    # Create a test file
    test_file = tmp_path / "test_overlap.txt"
    original_content = "Line 1\nLine 2\nLine 3\nLine 4\n"
    test_file.write_text(original_content)

    # Get file hash
    content, start, end, file_hash, total_lines, size = await editor.read_file_contents(
        str(test_file)
    )

    # Try to apply overlapping patches
    result = await editor.edit_file_contents(
        str(test_file),
        file_hash,
        [
            {
                "start": 1,
                "end": 2,
                "contents": "New Line 1-2\n",
                "range_hash": editor.calculate_hash("Line 1\nLine 2\n"),
            },
            {
                "start": 2,
                "end": 3,
                "contents": "New Line 2-3\n",
                "range_hash": editor.calculate_hash("Line 2\nLine 3\n"),
            },
        ],
    )

    assert result["result"] == "error"
    assert "overlap" in result["reason"].lower()
    assert test_file.read_text() == original_content  # File should remain unchanged


@pytest.mark.asyncio
async def test_empty_content_handling(editor, tmp_path):
    """Test handling of empty file content."""
    # Create an empty test file
    test_file = tmp_path / "empty.txt"
    test_file.write_text("")

    # Read empty file
    content, start, end, file_hash, total_lines, size = await editor.read_file_contents(
        str(test_file)
    )
    assert content == ""
    assert total_lines == 0
    assert size == 0

    # Write to empty file (treat it as a new file)
    result = await editor.edit_file_contents(
        str(test_file),
        "",  # No hash for empty file
        [
            {"line_start": 1, "contents": "New content\n", "range_hash": ""}
        ],  # Empty range_hash for new files
    )

    assert result["result"] == "ok"
    assert test_file.read_text() == "New content\n"


@pytest.mark.asyncio
async def test_read_multiple_ranges_line_exceed(editor, tmp_path):
    """Test reading multiple ranges with exceeding line numbers."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    content = "Line 1\nLine 2\nLine 3\n"
    test_file.write_text(content)

    # Request ranges that exceed file length
    ranges = [
        {
            "file_path": str(test_file),
            "ranges": [{"start": 4, "end": None}, {"start": 1, "end": 2}],
        }
    ]

    result = await editor.read_multiple_ranges(ranges)

    # Check the exceeded range
    assert len(result[str(test_file)]["ranges"]) == 2
    # First range (exceeded)
    assert result[str(test_file)]["ranges"][0]["content"] == ""
    assert result[str(test_file)]["ranges"][0]["start"] == 4
    assert result[str(test_file)]["ranges"][0]["end"] == 4
    assert result[str(test_file)]["ranges"][0]["content_size"] == 0
    # Second range (normal)
    assert result[str(test_file)]["ranges"][1]["content"] == "Line 1\nLine 2\n"


@pytest.mark.asyncio
async def test_directory_creation_failure(editor, tmp_path):
    """Test failure in directory creation."""
    # Create a file in place of a directory to cause mkdir to fail
    base_dir = tmp_path / "blocked"
    base_dir.write_text("")
    test_file = base_dir / "subdir" / "test.txt"

    result = await editor.edit_file_contents(
        str(test_file),
        "",  # New file
        [{"line_start": 1, "contents": "test content\n", "range_hash": None}],
    )

    assert result["result"] == "error"
    assert "Failed to create directory" in result["reason"]
    assert result["file_hash"] is None


@pytest.mark.asyncio
async def test_invalid_encoding_file_operations(editor, tmp_path):
    """Test handling of files with invalid encoding during various operations."""
    test_file = tmp_path / "invalid_encoding.txt"
    # Create a file with Shift-JIS content that will fail UTF-8 decoding
    test_data = bytes([0x83, 0x65, 0x83, 0x58, 0x83, 0x67, 0x0A])  # シフトJISのデータ
    with open(test_file, "wb") as f:
        f.write(test_data)

    # Test encoding error in file operations
    result = await editor.edit_file_contents(
        str(test_file),
        "",  # hash doesn't matter as it will fail before hash check
        [{"line_start": 1, "contents": "new content\n", "range_hash": None}],
        encoding="utf-8",
    )

    assert result["result"] == "error"
    assert "Error editing file" in result["reason"]
    assert "decode" in result["reason"].lower()


@pytest.mark.asyncio
async def test_create_file_directory_error(editor, tmp_path, monkeypatch):
    """Test creating a file when directory creation fails."""
    # Create a path with multiple nested directories
    deep_path = tmp_path / "deeply" / "nested" / "path" / "test.txt"

    # Mock os.makedirs to raise an OSError
    def mock_makedirs(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("os.makedirs", mock_makedirs)

    # Attempt to create a new file
    result = await editor.edit_file_contents(
        str(deep_path),
        "",  # Empty hash for new file
        [
            {
                "start": 1,
                "contents": "test content\n",
            }
        ],
    )

    # Verify proper error handling
    assert result["result"] == "error"
    assert "Failed to create directory" in result["reason"]
    assert "Permission denied" in result["reason"]
    assert result["file_hash"] is None
    assert "content" not in result


@pytest.mark.asyncio
async def test_create_file_with_empty_directory(editor, tmp_path):
    """Test creating a file when parent directory is an empty string."""
    # Create a file in the current directory (no parent directory)
    file_path = tmp_path / "test.txt"

    # Attempt to create a new file
    result = await editor.edit_file_contents(
        str(file_path),
        "",  # Empty hash for new file
        [
            {
                "start": 1,
                "contents": "test content\n",
                "range_hash": "",  # Empty range_hash for new files
            }
        ],
    )

    # Verify successful file creation
    assert result["result"] == "ok"
    assert file_path.read_text() == "test content\n"
    assert result["file_hash"] is not None


@pytest.mark.asyncio
async def test_file_write_permission_error(editor, tmp_path):
    """Test file write permission error handling."""
    # Create a test file
    test_file = tmp_path / "readonly.txt"
    test_file.write_text("original content\n")
    test_file.chmod(0o444)  # Make file read-only

    # Get file hash
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Attempt to modify read-only file
    result = await editor.edit_file_contents(
        str(test_file),
        file_hash,
        [
            {
                "start": 1,
                "end": 1,
                "contents": "new content\n",
                "range_hash": editor.calculate_hash("original content\n"),
            }
        ],
    )

    # Verify proper error handling
    assert result["result"] == "error"
    assert "Error editing file" in result["reason"]
    assert "Permission" in result["reason"]
    assert result["file_hash"] is None
    assert "content" not in result


@pytest.mark.asyncio
async def test_edit_file_with_none_line_end(editor, tmp_path):
    """Test editing file with end=None."""
    test_file = tmp_path / "none_end.txt"
    test_file.write_text("line1\nline2\nline3\n")

    # Get file hash
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Test replacement with None as end
    result = await editor.edit_file_contents(
        str(test_file),
        file_hash,
        [
            {
                "start": 2,
                "end": 3,  # Replace lines 2 and 3
                "contents": "new2\nnew3\n",
                "range_hash": editor.calculate_hash("line2\nline3\n"),
            }
        ],
    )
    assert result["result"] == "ok"
    assert test_file.read_text() == "line1\nnew2\nnew3\n"


@pytest.mark.asyncio
async def test_edit_file_with_exceeding_line_end(editor, tmp_path):
    """Test editing file with end exceeding file length."""
    test_file = tmp_path / "exceed_end.txt"
    test_file.write_text("line1\nline2\nline3\n")

    # Get file hash
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Test replacement with end > file length
    result = await editor.edit_file_contents(
        str(test_file),
        file_hash,
        [
            {
                "start": 2,
                "end": 10,  # File only has 3 lines
                "contents": "new2\nnew3\n",
                "range_hash": editor.calculate_hash("line2\nline3\n"),
            }
        ],
    )

    assert result["result"] == "ok"
    assert test_file.read_text() == "line1\nnew2\nnew3\n"

    # Clean up
    test_file.chmod(0o644)  # Restore write permission for cleanup


@pytest.mark.asyncio
async def test_new_file_with_non_empty_hash(editor, tmp_path):
    """Test handling of new file creation with non-empty hash."""
    new_file = tmp_path / "nonexistent.txt"
    result = await editor.edit_file_contents(
        str(new_file),
        "non_empty_hash",  # Non-empty hash for non-existent file
        [{"start": 1, "contents": "test content\n", "range_hash": ""}],
    )

    # Verify proper error handling
    assert result["result"] == "error"
    assert result["file_hash"] is None
    assert "content" not in result


@pytest.mark.asyncio
async def test_read_file_contents_with_start_beyond_total(editor, tmp_path):
    """Test read_file_contents when start is beyond total lines."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\n")

    # Call read_file_contents with start beyond total lines
    content, start, end, content_hash, total_lines, content_size = (
        await editor.read_file_contents(str(test_file), start=10)
    )

    # Verify empty content is returned
    assert content == ""
    assert start == 9  # start is converted to 0-based indexing
    assert end == 9
    assert content_hash == editor.calculate_hash("")
    assert total_lines == 3
    assert content_size == 0


@pytest.mark.asyncio
async def test_create_file_directory_creation_failure(editor, tmp_path, monkeypatch):
    """Test handling of directory creation failure when creating a new file."""
    # Create a path with multiple nested directories
    deep_path = tmp_path / "deeply" / "nested" / "path" / "test.txt"

    # Mock os.makedirs to raise an OSError
    def mock_makedirs(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("os.makedirs", mock_makedirs)

    # Attempt to create a new file
    result = await editor.edit_file_contents(
        str(deep_path),
        "",  # Empty hash for new file
        [
            {
                "line_start": 1,
                "contents": "test content\n",
            }
        ],
    )

    # Verify proper error handling
    assert result["result"] == "error"
    assert "Failed to create directory" in result["reason"]
    assert "Permission denied" in result["reason"]
    assert result["file_hash"] is None
    assert "content" not in result


@pytest.mark.asyncio
async def test_io_error_handling(editor, tmp_path, monkeypatch):
    """Test handling of IO errors during file operations."""
    test_file = tmp_path / "test.txt"
    content = "test content\n"
    test_file.write_text(content)

    def mock_open(*args, **kwargs):
        raise IOError("Test IO Error")

    monkeypatch.setattr("builtins.open", mock_open)

    result = await editor.edit_file_contents(
        str(test_file),
        "",
        [{"line_start": 1, "contents": "new content\n"}],
    )

    assert result["result"] == "error"
    assert "Error editing file" in result["reason"]
    assert "Test IO Error" in result["reason"]


@pytest.mark.asyncio
async def test_exception_handling(editor, tmp_path, monkeypatch):
    """Test handling of unexpected exceptions during file operations."""
    test_file = tmp_path / "test.txt"

    def mock_open(*args, **kwargs):
        raise Exception("Unexpected error")

    monkeypatch.setattr("builtins.open", mock_open)

    result = await editor.edit_file_contents(
        str(test_file),
        "",
        [{"line_start": 1, "contents": "new content\n"}],
    )

    assert result["result"] == "error"
    assert "Unexpected error" in result["reason"]


@pytest.mark.asyncio
async def test_insert_operation(editor, tmp_path):
    """Test file insertion operations."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\n")

    # Get file hash
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Test insertion operation (inserting at line 2)
    result = await editor.edit_file_contents(
        str(test_file),
        file_hash,
        [
            {
                "start": 2,
                "end": None,  # For insertion mode (empty range_hash), end is optional
                "contents": "new line\n",
                "range_hash": "",  # Empty range_hash means insertion mode
            }
        ],
    )

    assert result["result"] == "ok"
    assert test_file.read_text() == "line1\nnew line\nline2\nline3\n"


@pytest.mark.asyncio
async def test_content_without_newline(editor, tmp_path):
    """Test handling content without trailing newline."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\n")

    # Get file hash
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Update with content that doesn't have a trailing newline
    result = await editor.edit_file_contents(
        str(test_file),
        file_hash,
        [
            {
                "start": 2,
                "end": 2,
                "contents": "new line",  # No trailing newline
                "range_hash": editor.calculate_hash("line2\n"),
            }
        ],
    )

    assert result["result"] == "ok"
    assert test_file.read_text() == "line1\nnew line\nline3\n"
    result = await editor.edit_file_contents(
        str(test_file),
        "",
        [{"start": 1, "contents": "new content\n"}],
    )

    assert result["result"] == "error"
    assert "Unexpected error" in result["reason"]


@pytest.mark.asyncio
async def test_invalid_line_range(editor, tmp_path):
    """Test handling of invalid line range where end line is less than start line."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\n")

    # Try to read with invalid line range
    with pytest.raises(ValueError) as excinfo:
        await editor.read_file_contents(str(test_file), start=3, end=2)

    assert "End line must be greater than or equal to start line" in str(excinfo.value)

    # Try to edit with invalid line range
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))

    result = await editor.edit_file_contents(
        str(test_file),
        file_hash,
        [
            {
                "start": 3,
                "end": 2,
                "contents": "new content\n",
                "range_hash": editor.calculate_hash("line3\n"),
            }
        ],
    )

    assert result["result"] == "error"
    assert "End line must be greater than or equal to start line" in result["reason"]


@pytest.mark.asyncio
async def test_append_mode(editor, tmp_path):
    """Test appending content when start exceeds total lines."""
    # Create a test file
    test_file = tmp_path / "test_append.txt"
    original_content = "Line 1\nLine 2\nLine 3\n"
    test_file.write_text(original_content)

    # Read the content and get hash
    content, start, end, file_hash, total_lines, size = await editor.read_file_contents(
        str(test_file)
    )

    # Attempt to append content with start > total_lines
    append_content = "Appended Line\n"
    result = await editor.edit_file_contents(
        str(test_file),
        file_hash,
        [
            {
                "start": total_lines + 1,  # Start beyond current line count
                "contents": append_content,
                "range_hash": "",  # Empty range_hash for append mode
            }
        ],
    )

    assert result["result"] == "ok"
    assert test_file.read_text() == original_content + append_content


@pytest.mark.asyncio
async def test_dict_patch_with_defaults(editor: TextEditor, tmp_path):
    """Test dictionary patch with default values."""
    test_file = tmp_path / "test.txt"
    original_content = "line1\nline2\nline3\n"
    test_file.write_text(original_content)

    # Get first line content and calculate hashes
    first_line_content, _, _, _, _, _ = await editor.read_file_contents(
        str(test_file), start=1, end=1
    )
    file_hash = editor.calculate_hash(original_content)

    # Edit using dict patch with missing optional fields
    patch = {
        "contents": "new line\n",  # Add newline to maintain file structure
        "start": 1,
        "end": 1,  # Explicitly specify end
        "range_hash": editor.calculate_hash(first_line_content),
    }
    result = await editor.edit_file_contents(str(test_file), file_hash, [patch])

    assert result["result"] == "ok"
    # Should replace line 1 when range_hash is provided
    assert test_file.read_text() == "new line\nline2\nline3\n"


@pytest.mark.asyncio
async def test_edit_file_without_end(editor, tmp_path):
    """Test editing a file using dictionary patch without end."""
    test_file = tmp_path / "test.txt"
    content = "line1\nline2\nline3\n"
    test_file.write_text(content)

    # Create a patch with minimal fields
    patch = EditPatch(
        contents="new line\n",
        start=1,
        end=1,
        range_hash=editor.calculate_hash("line1\n"),
    )

    # Calculate file hash from original content
    file_hash = editor.calculate_hash(content)

    result = await editor.edit_file_contents(str(test_file), file_hash, [patch])

    assert result["result"] == "ok"
    assert test_file.read_text() == "new line\nline2\nline3\n"


def test_validate_environment():
    """Test environment validation."""
    # Currently _validate_environment is a placeholder
    # This test ensures the method exists and can be called without errors
    TextEditor()._validate_environment()


@pytest.mark.asyncio
async def test_io_error_during_final_write(editor, tmp_path, monkeypatch):
    """Test handling of IO errors during final content writing."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("original content\n")

    # Get file hash
    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))

    # Mock open to raise IOError during final write
    original_open = open
    open_count = 0

    def mock_open(*args, **kwargs):
        nonlocal open_count
        open_count += 1
        if open_count > 1:  # Allow first open for reading, fail on write
            raise IOError("Failed to write file")
        return original_open(*args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)

    # Try to edit file with mocked write error
    result = await editor.edit_file_contents(
        str(test_file),
        file_hash,
        [
            {
                "start": 1,
                "end": 1,
                "contents": "new content\n",
                "range_hash": editor.calculate_hash("original content\n"),
            }
        ],
    )

    assert result["result"] == "error"
    assert "Error editing file" in result["reason"]
    assert "Failed to write file" in result["reason"]
    assert test_file.read_text() == "original content\n"  # File should be unchanged
    editor._validate_environment()


@pytest.mark.asyncio
async def test_initialization_with_environment_error(monkeypatch):
    """Test TextEditor initialization when environment validation fails."""

    def mock_validate_environment(self):
        raise EnvironmentError("Failed to validate environment")

    # Patch the _validate_environment method
    monkeypatch.setattr(TextEditor, "_validate_environment", mock_validate_environment)

    # Verify that initialization fails with the expected error
    with pytest.raises(EnvironmentError, match="Failed to validate environment"):
        TextEditor()


@pytest.mark.asyncio
async def test_read_file_not_found_error(editor, tmp_path):
    """Test FileNotFoundError handling when reading a non-existent file."""
    non_existent_file = tmp_path / "does_not_exist.txt"

    with pytest.raises(FileNotFoundError) as excinfo:
        await editor._read_file(str(non_existent_file))

    assert "File not found:" in str(excinfo.value)
    assert str(non_existent_file) in str(excinfo.value)
