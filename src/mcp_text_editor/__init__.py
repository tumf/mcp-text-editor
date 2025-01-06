"""MCP Text Editor Server package."""

import asyncio

from .server import main
from .text_editor import TextEditor

# Create a global text editor instance
_text_editor = TextEditor()


def run() -> None:
    """Run the MCP Text Editor Server."""
    asyncio.run(main())
