"""MCP Text Editor Server implementation."""

import json
import logging
import os
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
    description = "Read text file contents from multiple files and line ranges. Returns file contents with hashes for concurrency control and line numbers for reference. The hashes are used to detect conflicts when editing the files."

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
                    "files": {
                        "type": "array",
                        "description": "List of files and their line ranges to read",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "Path to the text file",
                                },
                                "ranges": {
                                    "type": "array",
                                    "description": "List of line ranges to read from the file",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "start": {
                                                "type": "integer",
                                                "description": "Starting line number (1-based)",
                                            },
                                            "end": {
                                                "type": ["integer", "null"],
                                                "description": "Ending line number (null for end of file)",
                                            },
                                        },
                                        "required": ["start"],
                                    },
                                },
                            },
                            "required": ["file_path", "ranges"],
                        },
                    }
                },
                "required": ["files"],
            },
        )

    async def run_tool(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Execute the tool with given arguments."""
        try:
            if "files" not in arguments:
                # Handle legacy single file request
                if "file_path" in arguments:
                    file_path = arguments["file_path"]
                    line_start = arguments.get("line_start", 1)
                    line_end = arguments.get("line_end")

                    content, start, end, content_hash, file_lines, file_size = (
                        await self.editor.read_file_contents(
                            file_path, line_start, line_end
                        )
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

                    return [
                        TextContent(type="text", text=json.dumps(response, indent=2))
                    ]
                else:
                    raise RuntimeError("Missing required argument: files")

            # Handle multi-file request
            result = await self.editor.read_multiple_ranges(arguments["files"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except KeyError as e:
            raise RuntimeError(f"Missing required argument: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Error processing request: {str(e)}") from e


class EditTextFileContentsHandler:
    """Handler for editing text file contents."""

    name = "edit_text_file_contents"
    description = "A line editor that supports editing text file contents by specifying line ranges and content. It handles multiple patches in a single operation with hash-based conflict detection. IMPORTANT: (1) Before using this tool, you must first get the file's current hash using get_text_file_contents. (2) To avoid line number shifts affecting your patches, use get_text_file_contents to read the same ranges you plan to edit before making changes. (3) Patches must be specified from bottom to top to handle line number shifts correctly, as edits to lower lines don't affect the line numbers of higher lines."

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
                    "files": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "hash": {"type": "string"},
                                "patches": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "line_start": {
                                                "type": "integer",
                                                "default": 1,
                                            },
                                            "line_end": {
                                                "type": ["integer", "null"],
                                                "default": None,
                                            },
                                            "contents": {"type": "string"},
                                        },
                                        "required": ["contents"],
                                    },
                                },
                            },
                            "required": ["path", "hash", "patches"],
                        },
                    }
                },
                "required": ["files"],
            },
        )

    async def run_tool(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Execute the tool with given arguments."""
        try:
            if "files" not in arguments:
                raise RuntimeError("Missing required argument: files")

            files = arguments["files"]
            results: Dict[str, Dict] = {}

            for file_operation in files:
                file_path = None
                try:
                    try:
                        file_path = file_operation["path"]
                    except KeyError as e:
                        raise RuntimeError(
                            "Missing required field: path in file operation"
                        ) from e

                    # Ensure the file exists
                    if not os.path.exists(file_path):
                        results[file_path] = {
                            "result": "error",
                            "reason": "File not found",
                            "hash": None,
                        }
                        continue

                    try:
                        file_hash = file_operation["hash"]
                    except KeyError as e:
                        raise RuntimeError(
                            f"Missing required field: hash for file {file_path}"
                        ) from e

                    # Ensure patches list is not empty
                    try:
                        patches = file_operation["patches"]
                    except KeyError as e:
                        raise RuntimeError(
                            f"Missing required field: patches for file {file_path}"
                        ) from e

                    if not patches:
                        results[file_path] = {
                            "result": "error",
                            "reason": "Empty patches list",
                            "hash": None,
                        }
                        continue

                    result = await self.editor.edit_file_contents(
                        file_path, file_hash, patches
                    )
                    results[file_path] = result
                except Exception as e:
                    if file_path:
                        results[file_path] = {
                            "result": "error",
                            "reason": str(e),
                            "hash": None,
                        }
                    else:
                        raise

            return [TextContent(type="text", text=json.dumps(results, indent=2))]
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            logger.error(traceback.format_exc())
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
        raise
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
