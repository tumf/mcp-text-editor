"""MCP Text Editor Server implementation."""

import logging
from typing import Any, Dict, List, Optional, Sequence

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
        await super().list_tools()
        return [
            Tool(
                name=handler.name,
                description=handler.description,
                inputSchema=make_schema_gemini_compatible(
                    handler.get_tool_description().inputSchema
                ),
            )
            for handler in TOOL_HANDLERS
        ]


app = GeminiCompatibleFastMCP("mcp-text-editor")

# Initialize handlers
get_contents_handler = GetTextFileContentsHandler()
patch_file_handler = PatchTextFileContentsHandler()
create_file_handler = CreateTextFileHandler()
append_file_handler = AppendTextFileContentsHandler()
delete_contents_handler = DeleteTextFileContentsHandler()
insert_file_handler = InsertTextFileContentsHandler()
TOOL_HANDLERS = (
    get_contents_handler,
    patch_file_handler,
    create_file_handler,
    append_file_handler,
    delete_contents_handler,
    insert_file_handler,
)


# Register tools
@app.tool()
async def get_text_file_contents(
    files: List[Dict[str, Any]], encoding: str = "utf-8"
) -> Sequence[TextContent]:
    """Get the contents of text files."""
    return await get_contents_handler.run_tool({"files": files, "encoding": encoding})


@app.tool()
async def patch_text_file_contents(
    file_path: str,
    file_hash: str,
    patches: List[Dict[str, Any]],
    encoding: str = "utf-8",
) -> Sequence[TextContent]:
    """Patch the contents of a text file."""
    return await patch_file_handler.run_tool(
        {
            "file_path": file_path,
            "file_hash": file_hash,
            "patches": patches,
            "encoding": encoding,
        }
    )


@app.tool()
async def create_text_file(
    file_path: str, contents: str, encoding: str = "utf-8"
) -> Sequence[TextContent]:
    """Create a new text file."""
    return await create_file_handler.run_tool(
        {"file_path": file_path, "contents": contents, "encoding": encoding}
    )


@app.tool()
async def append_text_file_contents(
    file_path: str, file_hash: str, contents: str, encoding: str = "utf-8"
) -> Sequence[TextContent]:
    """Append content to a text file."""
    return await append_file_handler.run_tool(
        {
            "file_path": file_path,
            "file_hash": file_hash,
            "contents": contents,
            "encoding": encoding,
        }
    )


@app.tool()
async def delete_text_file_contents(
    file_path: str,
    file_hash: str,
    ranges: List[Dict[str, Any]],
    encoding: str = "utf-8",
) -> Sequence[TextContent]:
    """Delete the contents of a text file."""
    return await delete_contents_handler.run_tool(
        {
            "file_path": file_path,
            "file_hash": file_hash,
            "ranges": ranges,
            "encoding": encoding,
        }
    )


@app.tool()
async def insert_text_file_contents(
    file_path: str,
    file_hash: str,
    contents: str,
    before: Optional[int] = None,
    after: Optional[int] = None,
    encoding: str = "utf-8",
) -> Sequence[TextContent]:
    """Insert content into a text file at a specific position."""
    arguments: Dict[str, Any] = {
        "file_path": file_path,
        "file_hash": file_hash,
        "contents": contents,
        "encoding": encoding,
    }
    if before is not None:
        arguments["before"] = before
    if after is not None:
        arguments["after"] = after
    return await insert_file_handler.run_tool(arguments)


def main() -> None:
    """Main entry point for the MCP text editor server."""
    logger.info(f"Starting MCP text editor server v{__version__}")
    app.run()


if __name__ == "__main__":
    main()
