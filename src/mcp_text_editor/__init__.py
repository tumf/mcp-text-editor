"""MCP Text Editor Server package."""

import asyncio
from typing import Any, Dict, List

from .server import main
from .text_editor import TextEditor

# Create a global text editor instance
_text_editor = TextEditor()


def run() -> None:
    """Run the MCP Text Editor Server."""
    asyncio.run(main())


# Export functions
async def get_text_file_contents(
    request: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """Get text file contents with line range specification."""
    return await _text_editor.read_multiple_ranges(
        ranges=request["files"],
        encoding="utf-8",
    )


async def insert_text_file_contents(request: Dict[str, Any]) -> Dict[str, Any]:
    """Insert text content before or after a specific line in a file."""
    return await _text_editor.insert_text_file_contents(
        file_path=request["file_path"],
        file_hash=request["file_hash"],
        after=request.get("after"),
        before=request.get("before"),
        contents=request["contents"],
    )
