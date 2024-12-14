"""MCP Text Editor Server implementation."""

import json
import logging
import traceback
from collections.abc import Sequence
from typing import Any, Dict, List

from mcp.server import Server
from mcp.types import TextContent, Tool

from .text_editor import TextEditor
from .version import __version__

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
            # Handle 'files' key missing
            if "files" not in arguments:
                if "file_path" not in arguments:
                    raise RuntimeError("Missing required argument: 'files'")

                # Convert legacy format to new format
                file_path = arguments["file_path"]
                line_start = arguments.get("line_start", 1)
                line_end = arguments.get("line_end")
                arguments = {
                    "files": [
                        {
                            "file_path": file_path,
                            "ranges": [
                                {
                                    "start": line_start,
                                    "end": line_end if line_end else None,
                                }
                            ],
                        }
                    ]
                }
                legacy_format = True
            else:
                legacy_format = False

            # Handle request
            result = await self.editor.read_multiple_ranges(arguments["files"])

            # Convert to legacy format if it was a legacy request
            if legacy_format:
                file_path = arguments["files"][0]["file_path"]
                file_result = result[file_path]
                range_result = file_result["ranges"][0]
                response = {
                    "file_path": file_path,
                    "contents": range_result["content"],
                    "line_start": range_result["start_line"],
                    "line_end": range_result["end_line"],
                    "file_hash": file_result["file_hash"],
                    "file_lines": range_result["total_lines"],
                    "file_size": range_result["content_size"],
                }
            else:
                response = result

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except KeyError as e:
            raise RuntimeError(f"Missing required argument: '{e}'")
        except Exception as e:
            raise RuntimeError(f"Error processing request: {str(e)}")


class EditTextFileContentsHandler:
    """Handler for editing text file contents."""

    name = "edit_text_file_contents"
    description = "A line editor that supports editing text file contents by specifying line ranges and content. It handles multiple patches in a single operation with hash-based conflict detection. IMPORTANT: (1) Before using this tool, you must first get the file's current hash using get_text_file_contents. (2) To avoid line number shifts affecting your patches, use get_text_file_contents to read the same ranges you plan to edit before making changes. (3) Patches must be specified from bottom to top to handle line number shifts correctly, as edits to lower lines don't affect the line numbers of higher lines. (4) To append content to a file, first get the total number of lines with get_text_file_contents, then specify a patch with line_start = total_lines + 1 and line_end = total_lines. This indicates an append operation and range_hash is not required. Similarly, range_hash is not required for new file creation."

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
                                "file_hash": {"type": "string"},
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
                            "required": ["path", "file_hash", "patches"],
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

            if len(files) == 0:
                return [TextContent(type="text", text=json.dumps(results, indent=2))]

            for file_operation in files:
                file_path = None
                try:
                    try:
                        file_path = file_operation["path"]
                    except KeyError as e:
                        raise RuntimeError(
                            "Missing required field: path in file operation"
                        ) from e

                    try:
                        file_hash = file_operation["file_hash"]
                    except KeyError as e:
                        raise RuntimeError(
                            f"Missing required field: file_hash for file {file_path}"
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
                            "file_hash": None,
                            "content": None,
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
                            "file_hash": None,
                            "content": None,
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
    logger.info(f"Starting MCP text editor server v{__version__}")
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
