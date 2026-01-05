"""MCP Text Editor Server implementation."""

import logging
from typing import List, Sequence

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, Tool

from .handlers import (
    AppendTextFileContentsHandler,
    CreateTextFileHandler,
    DeleteTextFileContentsHandler,
    GetTextFileContentsHandler,
    InsertTextFileContentsHandler,
    PatchTextFileContentsHandler,
)
from .schema_compat import make_schema_gemini_compatible
from .version import __version__

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-text-editor")


class GeminiCompatibleFastMCP(FastMCP):
    """FastMCP subclass that produces Gemini-compatible tool schemas.

    This class overrides list_tools to convert anyOf schemas to the
    nullable format that Gemini/Vertex AI can understand.

    See: https://github.com/tumf/mcp-text-editor/issues/11
    """

    async def list_tools(self) -> List[Tool]:
        """List available tools with Gemini-compatible schemas.

        Returns:
            List of Tool objects with converted inputSchema.
        """
        tools = await super().list_tools()

        # Convert each tool's inputSchema to Gemini-compatible format
        compatible_tools = []
        for tool in tools:
            compatible_schema = make_schema_gemini_compatible(tool.inputSchema)
            compatible_tool = Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=compatible_schema,
            )
            compatible_tools.append(compatible_tool)

        return compatible_tools


app = GeminiCompatibleFastMCP("mcp-text-editor")

# Initialize handlers
get_contents_handler = GetTextFileContentsHandler()
patch_file_handler = PatchTextFileContentsHandler()
create_file_handler = CreateTextFileHandler()
append_file_handler = AppendTextFileContentsHandler()
delete_contents_handler = DeleteTextFileContentsHandler()
insert_file_handler = InsertTextFileContentsHandler()


# Register tools
@app.tool()
async def get_text_file_contents(path: str) -> Sequence[TextContent]:
    """Get the contents of a text file."""
    return await get_contents_handler.run_tool({"path": path})


@app.tool()
async def patch_text_file_contents(path: str, content: str) -> Sequence[TextContent]:
    """Patch the contents of a text file."""
    return await patch_file_handler.run_tool({"path": path, "content": content})


@app.tool()
async def create_text_file(path: str) -> Sequence[TextContent]:
    """Create a new text file."""
    return await create_file_handler.run_tool({"path": path})


@app.tool()
async def append_text_file_contents(path: str, content: str) -> Sequence[TextContent]:
    """Append content to a text file."""
    return await append_file_handler.run_tool({"path": path, "content": content})


@app.tool()
async def delete_text_file_contents(path: str) -> Sequence[TextContent]:
    """Delete the contents of a text file."""
    return await delete_contents_handler.run_tool({"path": path})


@app.tool()
async def insert_text_file_contents(
    path: str, content: str, position: int
) -> Sequence[TextContent]:
    """Insert content into a text file at a specific position."""
    return await insert_file_handler.run_tool(
        {"path": path, "content": content, "position": position}
    )


async def main() -> None:
    """Main entry point for the MCP text editor server."""
    logger.info(f"Starting MCP text editor server v{__version__}")
    await app.run()  # type: ignore[func-returns-value]


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
