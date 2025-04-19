"""MCP Text Editor Server implementation."""

import asyncio
import logging
import traceback
from collections.abc import Sequence
from typing import Any, List, Optional

from mcp.server import Server
from mcp.types import TextContent, Tool

from mcp_text_editor.handlers import (
    AppendTextFileContentsHandler,
    CreateTextFileHandler,
    DeleteTextFileContentsHandler,
    GetTextFileContentsHandler,
    InsertTextFileContentsHandler,
    PatchTextFileContentsHandler,
)
from mcp_text_editor.text_editor import TextEditor
from mcp_text_editor.version import __version__

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-text-editor")

app: Server = Server("mcp-text-editor")

# Initialize tool handlers as global variables
get_contents_handler: Optional[GetTextFileContentsHandler] = None
patch_file_handler: Optional[PatchTextFileContentsHandler] = None
create_file_handler: Optional[CreateTextFileHandler] = None
append_file_handler: Optional[AppendTextFileContentsHandler] = None
delete_contents_handler: Optional[DeleteTextFileContentsHandler] = None
insert_file_handler: Optional[InsertTextFileContentsHandler] = None


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools."""
    tools = []
    if get_contents_handler:
        tools.append(get_contents_handler.get_tool_description())
    if create_file_handler:
        tools.append(create_file_handler.get_tool_description())
    if append_file_handler:
        tools.append(append_file_handler.get_tool_description())
    if delete_contents_handler:
        tools.append(delete_contents_handler.get_tool_description())
    if insert_file_handler:
        tools.append(insert_file_handler.get_tool_description())
    if patch_file_handler:
        tools.append(patch_file_handler.get_tool_description())
    return tools


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    """Handle tool calls."""
    logger.info(f"Calling tool: {name}")
    try:
        if get_contents_handler and name == get_contents_handler.name:
            return await get_contents_handler.run_tool(arguments)
        elif create_file_handler and name == create_file_handler.name:
            return await create_file_handler.run_tool(arguments)
        elif append_file_handler and name == append_file_handler.name:
            return await append_file_handler.run_tool(arguments)
        elif delete_contents_handler and name == delete_contents_handler.name:
            return await delete_contents_handler.run_tool(arguments)
        elif insert_file_handler and name == insert_file_handler.name:
            return await insert_file_handler.run_tool(arguments)
        elif patch_file_handler and name == patch_file_handler.name:
            return await patch_file_handler.run_tool(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except ValueError:
        logger.error(traceback.format_exc())
        raise
    except Exception as e:
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Error executing command: {str(e)}") from e


async def main() -> None:
    """Main entry point for the MCP text editor server."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="MCP Text Editor Server")
    parser.add_argument("--validator", help="Validator command to run after file updates")
    args = parser.parse_args()
    
    logger.info(f"Starting MCP text editor server v{__version__}")
    
    # Initialize the global text editor instance with validator command
    text_editor_instance = TextEditor(validator_command=args.validator)
    
    # Initialize the global handlers with the text editor instance
    global get_contents_handler, patch_file_handler, create_file_handler
    global append_file_handler, delete_contents_handler, insert_file_handler
    
    get_contents_handler = GetTextFileContentsHandler(editor=text_editor_instance)
    patch_file_handler = PatchTextFileContentsHandler(editor=text_editor_instance)
    create_file_handler = CreateTextFileHandler(editor=text_editor_instance)
    append_file_handler = AppendTextFileContentsHandler(editor=text_editor_instance)
    delete_contents_handler = DeleteTextFileContentsHandler(editor=text_editor_instance)
    insert_file_handler = InsertTextFileContentsHandler(editor=text_editor_instance)
    
    try:
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
