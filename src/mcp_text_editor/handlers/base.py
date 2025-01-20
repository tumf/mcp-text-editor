"""Base handler for MCP Text Editor."""

from typing import Any, Dict, Sequence

from mcp.types import TextContent

from ..text_editor import TextEditor


class BaseHandler:
    """Base class for handlers."""

    def __init__(self, editor: TextEditor | None = None):
        """Initialize the handler."""
        self.editor = editor if editor is not None else TextEditor()

    async def run_tool(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Execute the tool with given arguments."""
        raise NotImplementedError
