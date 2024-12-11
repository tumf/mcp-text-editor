"""Test configuration and fixtures."""

import os
import tempfile
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from mcp.server import Server

from mcp_text_editor.server import app


@pytest.fixture
def test_file() -> Generator[str, None, None]:
    """Create a temporary test file."""
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write(content)
        file_path = f.name

    yield file_path

    # Cleanup
    if os.path.exists(file_path):
        os.unlink(file_path)


class MockStream:
    """Mock stream for testing."""

    def __init__(self):
        self.data = []

    async def write(self, data: str) -> None:
        """Mock write method."""
        self.data.append(data)

    async def drain(self) -> None:
        """Mock drain method."""
        pass


@pytest_asyncio.fixture
async def mock_server() -> AsyncGenerator[tuple[Server, MockStream], None]:
    """Create a mock server for testing."""
    mock_write_stream = MockStream()
    yield app, mock_write_stream
