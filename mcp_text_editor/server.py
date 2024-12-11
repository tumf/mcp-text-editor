"""MCP Text Editor Server implementation."""

import json
import logging
import traceback
from collections.abc import Sequence
from typing import Any, Dict, List

from mcp.server import Server
from mcp.types import TextContent, Tool

from .text_editor import TextEditor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-text-editor")

app = Server("mcp-text-editor")


class GetTextFileContentsHandler:
    """Handler for getting text file contents."""

    name = "get_text_file_contents"
    description = "Read text file contents within a specified line range. Returns file content with a hash for concurrency control and line numbers for reference.The hash is used to detect conflicts when editing the file."

    def __init__(self):
        self.editor = TextEditor()

    def get_tool_description(self) -> Tool:
        """Get the tool description."""
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the text file",
                    },
                    "line_start": {
                        "type": "integer",
                        "description": "Starting line number (1-based)",
                        "default": 1,
                    },
                    "line_end": {
                        "type": ["integer", "null"],
                        "description": "Ending line number (null for end of file)",
                        "default": None,
                    },
                },
                "required": ["file_path"],
            },
        )

    async def run_tool(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Execute the tool with given arguments."""
        try:
            file_path = arguments["file_path"]
            line_start = arguments.get("line_start", 1)
            line_end = arguments.get("line_end")

            content, start, end, content_hash, file_lines, file_size = await self.editor.read_file_contents(
                file_path, line_start, line_end
            )

            response = {
                "contents": content,
                "line_start": start,
                "line_end": end,
                "hash": content_hash,
                "file_path": file_path,
                "file_lines": file_lines,
                "file_size": file_size,
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        except KeyError as e:
            raise RuntimeError(f"Missing required argument: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Error processing request: {str(e)}") from e


class EditTextFileContentsHandler:
    """Handler for editing text file contents."""

    name = "EditTextFileContents"
    description = "Edit text file by lines"

    def __init__(self):
        self.editor = TextEditor()

    def get_tool_description(self) -> Tool:
        """Get the tool description."""
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "object",
                        "properties": {
                            "hash": {
                                "type": "string",
                                "description": "Hash of original contents",
                            },
                            "patches": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "line_start": {
                                            "type": "integer",
                                            "description": "Starting line for edit",
                                            "default": 1,
                                        },
                                        "line_end": {
                                            "type": ["integer", "null"],
                                            "description": "Ending line for edit",
                                        },
                                        "contents": {
                                            "type": "string",
                                            "description": "New content to insert",
                                        },
                                    },
                                    "required": ["contents"],
                                },
                            },
                        },
                        "required": ["hash", "patches"],
                    }
                },
                "required": ["file_path"],
            },
        )

    async def run_tool(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Execute the tool with given arguments."""
        try:
            results = {}
            for file_path, operation in arguments.items():
                try:
                    result = await self.editor.edit_file_contents(
                        file_path,
                        operation["hash"],
                        operation["patches"],
                    )
                    results[file_path] = result
                except Exception as e:
                    results[file_path] = {
                        "result": "error",
                        "reason": str(e),
                        "hash": None,
                    }

            return [TextContent(type="text", text=json.dumps(results, indent=2))]
        except Exception as e:
            raise RuntimeError(f"Error processing request: {str(e)}") from e


# Initialize tool handlers
get_contents_handler = GetTextFileContentsHandler()
edit_contents_handler = EditTextFileContentsHandler()


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools."""
    return [
        get_contents_handler.get_tool_description(),
        edit_contents_handler.get_tool_description(),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    """Handle tool calls."""
    logger.info(f"Calling tool: {name}")
    try:
        if name == get_contents_handler.name:
            return await get_contents_handler.run_tool(arguments)
        elif name == edit_contents_handler.name:
            return await edit_contents_handler.run_tool(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except ValueError:
        logger.error(traceback.format_exc())
        raise  # ValueErrorはそのまま伝播
    except Exception as e:
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Error executing command: {str(e)}") from e


async def main() -> None:
    """Main entry point for the MCP text editor server."""
    logger.info("Starting MCP text editor server")
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
