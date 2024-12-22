"""Test cases for append_text_file_contents handler."""

import os
from typing import Any, Dict, Generator

import pytest

from mcp_text_editor.server import AppendTextFileContentsHandler
from mcp_text_editor.text_editor import TextEditor

# Initialize handler for tests
append_handler = AppendTextFileContentsHandler()


@pytest.fixture
def test_dir(tmp_path: str) -> str:
    """Create a temporary directory for test files."""
    return str(tmp_path)


@pytest.fixture
def cleanup_files() -> Generator[None, None, None]:
    """Clean up any test files after each test."""
    yield
    # Add cleanup code if needed


@pytest.mark.asyncio
async def test_append_text_file_success(test_dir: str, cleanup_files: None) -> None:
    """Test successful appending to a file."""
    test_file = os.path.join(test_dir, "append_test.txt")
    initial_content = "Initial content\n"
    append_content = "Appended content\n"

    # Create initial file
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(initial_content)

    # Get file hash for append operation
    editor = TextEditor()
    _, _, _, file_hash, _, _ = await editor.read_file_contents(test_file)

    # Append content using handler
    arguments: Dict[str, Any] = {
        "file_path": test_file,
        "contents": append_content,
        "file_hash": file_hash,
    }
    response = await append_handler.run_tool(arguments)

    # Check if content was appended correctly
    with open(test_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert content == initial_content + append_content

    # Parse response to check success
    assert len(response) == 1
    result = response[0].text
    assert '"result": "ok"' in result


@pytest.mark.asyncio
async def test_append_text_file_not_exists(test_dir: str, cleanup_files: None) -> None:
    """Test attempting to append to a non-existent file."""
    test_file = os.path.join(test_dir, "nonexistent.txt")

    # Try to append to non-existent file
    arguments: Dict[str, Any] = {
        "file_path": test_file,
        "contents": "Some content\n",
        "file_hash": "dummy_hash",
    }

    # Should raise error because file doesn't exist
    with pytest.raises(RuntimeError) as exc_info:
        await append_handler.run_tool(arguments)
    assert "File does not exist" in str(exc_info.value)


@pytest.mark.asyncio
async def test_append_text_file_hash_mismatch(
    test_dir: str, cleanup_files: None
) -> None:
    """Test appending with incorrect file hash."""
    test_file = os.path.join(test_dir, "hash_test.txt")
    initial_content = "Initial content\n"

    # Create initial file
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(initial_content)

    # Try to append with incorrect hash
    arguments: Dict[str, Any] = {
        "file_path": test_file,
        "contents": "New content\n",
        "file_hash": "incorrect_hash",
    }

    # Should raise error because hash doesn't match
    with pytest.raises(RuntimeError) as exc_info:
        await append_handler.run_tool(arguments)
    assert "hash mismatch" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_append_text_file_relative_path(
    test_dir: str, cleanup_files: None
) -> None:
    """Test attempting to append using a relative path."""
    arguments: Dict[str, Any] = {
        "file_path": "relative_path.txt",
        "contents": "Some content\n",
        "file_hash": "dummy_hash",
    }

    # Should raise error because path is not absolute
    with pytest.raises(RuntimeError) as exc_info:
        await append_handler.run_tool(arguments)
    assert "File path must be absolute" in str(exc_info.value)


@pytest.mark.asyncio
async def test_append_text_file_missing_args() -> None:
    """Test appending with missing arguments."""
    # Test missing path
    with pytest.raises(RuntimeError) as exc_info:
        await append_handler.run_tool({"contents": "content\n", "file_hash": "hash"})
    assert "Missing required argument: file_path" in str(exc_info.value)

    # Test missing contents
    with pytest.raises(RuntimeError) as exc_info:
        await append_handler.run_tool(
            {"file_path": "/absolute/path.txt", "file_hash": "hash"}
        )
    assert "Missing required argument: contents" in str(exc_info.value)

    # Test missing file_hash
    with pytest.raises(RuntimeError) as exc_info:
        await append_handler.run_tool(
            {"file_path": "/absolute/path.txt", "contents": "content\n"}
        )
    assert "Missing required argument: file_hash" in str(exc_info.value)


@pytest.mark.asyncio
async def test_append_text_file_custom_encoding(
    test_dir: str, cleanup_files: None
) -> None:
    """Test appending with custom encoding."""
    test_file = os.path.join(test_dir, "encode_test.txt")
    initial_content = "こんにちは\n"
    append_content = "さようなら\n"

    # Create initial file
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(initial_content)

    # Get file hash for append operation
    editor = TextEditor()
    _, _, _, file_hash, _, _ = await editor.read_file_contents(
        test_file, encoding="utf-8"
    )

    # Append content using handler with specified encoding
    arguments: Dict[str, Any] = {
        "file_path": test_file,
        "contents": append_content,
        "file_hash": file_hash,
        "encoding": "utf-8",
    }
    response = await append_handler.run_tool(arguments)

    # Check if content was appended correctly
    with open(test_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert content == initial_content + append_content

    # Parse response to check success
    assert len(response) == 1
    result = response[0].text
    assert '"result": "ok"' in result
