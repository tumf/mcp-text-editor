"""MCP Text Editor Server package."""

from .server import main
from .text_editor import TextEditor

# Create a global text editor instance
_text_editor = TextEditor()


def run() -> None:
    """Run the MCP Text Editor Server."""
    main()
