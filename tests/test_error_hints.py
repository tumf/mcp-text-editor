"""Tests for error hints and suggestions functionality."""

import pytest

from mcp_text_editor.text_editor import TextEditor


@pytest.fixture
def editor():
    """Create TextEditor instance."""
    return TextEditor()


@pytest.mark.asyncio
async def test_file_not_found_hint(editor, tmp_path):
    """Test hints when file is not found."""
    non_existent = tmp_path / "non_existent.txt"

    result = await editor.edit_file_contents(
        str(non_existent),
        "non_empty_hash",
        [{"start": 1, "contents": "test", "range_hash": ""}],
    )

    assert result["result"] == "error"
    assert "File not found" in result["reason"]
    assert result["suggestion"] == "append"
    assert "append_text_file_contents" in result["hint"]


@pytest.mark.asyncio
async def test_hash_mismatch_hint(editor, tmp_path):
    """Test hints when file hash doesn't match."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("original content\\n")

    result = await editor.edit_file_contents(
        str(test_file),
        "wrong_hash",
        [{"start": 1, "contents": "new content", "range_hash": ""}],
    )

    assert result["result"] == "error"
    assert "hash mismatch" in result["reason"].lower()
    assert result["suggestion"] == "patch"
    assert "get_text_file_contents tool" in result["hint"]


@pytest.mark.asyncio
async def test_overlapping_patches_hint(editor, tmp_path):
    """Test hints when patches overlap."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\\nline2\\nline3\\n")

    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))

    result = await editor.edit_file_contents(
        str(test_file),
        file_hash,
        [
            {
                "start": 1,
                "end": 2,
                "contents": "new1\\n",
                "range_hash": editor.calculate_hash("line1\\nline2\\n"),
            },
            {
                "start": 2,
                "end": 3,
                "contents": "new2\\n",
                "range_hash": editor.calculate_hash("line2\\nline3\\n"),
            },
        ],
    )

    assert result["result"] == "error"
    assert "overlap" in result["reason"].lower()
    assert result["suggestion"] == "patch"
    assert "not overlap" in result["hint"].lower()


@pytest.mark.asyncio
async def test_io_error_hint(editor, tmp_path, monkeypatch):
    """Test hints when IO error occurs."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("original content\\n")

    def mock_open(*args, **kwargs):
        raise IOError("Test IO Error")

    monkeypatch.setattr("builtins.open", mock_open)

    result = await editor.edit_file_contents(
        str(test_file), "", [{"start": 1, "contents": "new content\\n"}]
    )

    assert result["result"] == "error"
    assert "Error editing file" in result["reason"]
    assert result["suggestion"] == "patch"
    assert "permissions" in result["hint"].lower()


@pytest.mark.asyncio
async def test_empty_content_delete_hint(editor, tmp_path):
    """Test hints when trying to delete content using empty patch."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("original\\n")

    content, _, _, file_hash, _, _ = await editor.read_file_contents(str(test_file))

    result = await editor.edit_file_contents(
        str(test_file),
        file_hash,
        [
            {
                "start": 1,
                "end": 1,
                "contents": "",
                "range_hash": editor.calculate_hash("original\\n"),
            }
        ],
    )

    assert result["result"] == "ok"  # Note: It's "ok" but suggests using delete
    assert result["suggestion"] == "delete"
    assert "delete_text_file_contents" in result["hint"]


@pytest.mark.asyncio
async def test_append_suggestion_for_new_file(editor, tmp_path):
    """Test suggestion to use append for new files."""
    test_file = tmp_path / "new.txt"

    result = await editor.edit_file_contents(
        str(test_file),
        "",
        [{"start": 1, "contents": "new content\\n", "range_hash": ""}],
    )

    assert result["result"] == "ok"
    assert result["suggestion"] == "append"
    assert "append_text_file_contents" in result["hint"]
