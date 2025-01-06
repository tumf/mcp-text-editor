"""Base handler for MCP Text Editor."""

from typing import Any, Dict, Sequence

from mcp.types import TextContent, Tool

from ..text_editor import TextEditor


class BaseHandler:
    """Base class for handlers."""

    name: str = ""
    description: str = ""

    def __init__(self, editor: TextEditor | None = None):
        """Initialize the handler."""
        self.editor = editor if editor is not None else TextEditor()

    def get_tool_description(self) -> Tool:
        """Get the tool description."""
        raise NotImplementedError

    async def run_tool(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Execute the tool with given arguments."""
        raise NotImplementedError
