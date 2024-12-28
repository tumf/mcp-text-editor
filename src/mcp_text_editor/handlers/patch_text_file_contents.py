"""Handler for patching text file contents."""

import json
import logging
import os
import traceback
from typing import Any, Dict, Sequence

from mcp.types import TextContent, Tool

from .base import BaseHandler

logger = logging.getLogger("mcp-text-editor")


class PatchTextFileContentsHandler(BaseHandler):
    """Handler for patching a text file."""

    name = "patch_text_file_contents"
    description = "Apply patches to text files with hash-based validation for concurrency control.you need to use get_text_file_contents tool to get the file hash and range hash every time before using this tool. you can use append_text_file_contents tool to append text contents to the file without range hash, start and end. you can use insert_text_file_contents tool to insert text contents to the file without range hash, start and end."

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
                        "description": "Path to the text file. File path must be absolute.",
                    },
                    "file_hash": {
                        "type": "string",
                        "description": "Hash of the file contents for concurrency control.",
                    },
                    "patches": {
                        "type": "array",
                        "description": "List of patches to apply",
                        "items": {
                            "type": "object",
                            "properties": {
                                "start": {
                                    "type": "integer",
                                    "description": "Starting line number (1-based).it should match the range hash.",
                                },
                                "end": {
                                    "type": "integer",
                                    "description": "Ending line number (null for end of file).it should match the range hash.",
                                },
                                "contents": {
                                    "type": "string",
                                    "description": "New content to replace the range with",
                                },
                                "range_hash": {
                                    "type": "string",
                                    "description": "Hash of the content being replaced. it should get from get_text_file_contents tool with the same start and end.",
                                },
                            },
                            "required": ["start", "end", "contents", "range_hash"],
                        },
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Text encoding (default: 'utf-8')",
                        "default": "utf-8",
                    },
                },
                "required": ["file_path", "file_hash", "patches"],
            },
        )

    async def run_tool(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Execute the tool with given arguments."""
        try:
            if "file_path" not in arguments:
                raise RuntimeError("Missing required argument: file_path")
            if "file_hash" not in arguments:
                raise RuntimeError("Missing required argument: file_hash")
            if "patches" not in arguments:
                raise RuntimeError("Missing required argument: patches")

            file_path = arguments["file_path"]
            if not os.path.isabs(file_path):
                raise RuntimeError(f"File path must be absolute: {file_path}")

            # Check if file exists
            if not os.path.exists(file_path):
                raise RuntimeError(f"File does not exist: {file_path}")

            encoding = arguments.get("encoding", "utf-8")

            # Apply patches using editor.edit_file_contents
            result = await self.editor.edit_file_contents(
                file_path=file_path,
                expected_file_hash=arguments["file_hash"],
                patches=arguments["patches"],
                encoding=encoding,
            )

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Error processing request: {str(e)}") from e
