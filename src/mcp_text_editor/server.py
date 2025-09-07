"""MCP Text Editor Server implementation."""

import logging
from typing import Sequence

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from .handlers import (
    AppendTextFileContentsHandler,
    CreateTextFileHandler,
    DeleteTextFileContentsHandler,
    GetTextFileContentsHandler,
    InsertTextFileContentsHandler,
    PatchTextFileContentsHandler,
)
from .version import __version__

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-text-editor")

app = FastMCP("mcp-text-editor")

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
