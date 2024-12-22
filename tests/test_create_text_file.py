"""Test cases for create_text_file handler."""

import os
from typing import Any, Dict, Generator

import pytest

from mcp_text_editor.server import CreateTextFileHandler

# Initialize handlers for tests
create_file_handler = CreateTextFileHandler()


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
async def test_create_text_file_success(test_dir: str, cleanup_files: None) -> None:
    """Test successful creation of a new text file."""
    test_file = os.path.join(test_dir, "new_file.txt")
    content = "Hello, World!\n"

    # Create file using handler
    arguments: Dict[str, Any] = {
        "file_path": test_file,
        "contents": content,
    }
    response = await create_file_handler.run_tool(arguments)

    # Check if file was created with correct content
    assert os.path.exists(test_file)
    with open(test_file, "r", encoding="utf-8") as f:
        assert f.read() == content

    # Parse response to check success
    assert len(response) == 1
    result = response[0].text
    assert '"result": "ok"' in result


@pytest.mark.asyncio
async def test_create_text_file_exists(test_dir: str, cleanup_files: None) -> None:
    """Test attempting to create a file that already exists."""
    test_file = os.path.join(test_dir, "existing_file.txt")

    # Create file first
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("Existing content\n")

    # Try to create file using handler
    arguments: Dict[str, Any] = {
        "file_path": test_file,
        "contents": "New content\n",
    }

    # Should raise error because file exists
    with pytest.raises(RuntimeError):
        await create_file_handler.run_tool(arguments)


@pytest.mark.asyncio
async def test_create_text_file_relative_path(
    test_dir: str, cleanup_files: None
) -> None:
    """Test attempting to create a file with a relative path."""
    # Try to create file using relative path
    arguments: Dict[str, Any] = {
        "file_path": "relative_path.txt",
        "contents": "Some content\n",
    }

    # Should raise error because path is not absolute
    with pytest.raises(RuntimeError) as exc_info:
        await create_file_handler.run_tool(arguments)
    assert "File path must be absolute" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_text_file_missing_args() -> None:
    """Test creating a file with missing arguments."""
    # Test missing path
    with pytest.raises(RuntimeError) as exc_info:
        await create_file_handler.run_tool({"contents": "content\n"})
    assert "Missing required argument: file_path" in str(exc_info.value)

    # Test missing contents
    with pytest.raises(RuntimeError) as exc_info:
        await create_file_handler.run_tool({"file_path": "/absolute/path.txt"})
    assert "Missing required argument: contents" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_text_file_custom_encoding(
    test_dir: str, cleanup_files: None
) -> None:
    """Test creating a file with custom encoding."""
    test_file = os.path.join(test_dir, "encoded_file.txt")
    content = "こんにちは\n"  # Japanese text

    # Create file using handler with specified encoding
    arguments: Dict[str, Any] = {
        "file_path": test_file,
        "contents": content,
        "encoding": "utf-8",
    }
    response = await create_file_handler.run_tool(arguments)

    # Check if file was created with correct content
    assert os.path.exists(test_file)
    with open(test_file, "r", encoding="utf-8") as f:
        assert f.read() == content

    # Parse response to check success
    assert len(response) == 1
    result = response[0].text
    assert '"result": "ok"' in result
