"""Handler for appending content to text files."""

import json
import logging
import os
import traceback
from typing import Any, Dict, Sequence

from mcp.types import TextContent, Tool

from .base import BaseHandler

logger = logging.getLogger("mcp-text-editor")


class AppendTextFileContentsHandler(BaseHandler):
    """Handler for appending content to an existing text file."""

    name = "append_text_file_contents"
    description = "Append content to an existing text file. The file must exist."

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
                    "contents": {
                        "type": "string",
                        "description": "Content to append to the file",
                    },
                    "file_hash": {
                        "type": "string",
                        "description": "Hash of the file contents for concurrency control. it should be matched with the file_hash when get_text_file_contents is called.",
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Text encoding (default: 'utf-8')",
                        "default": "utf-8",
                    },
                },
                "required": ["file_path", "contents", "file_hash"],
            },
        )

    async def run_tool(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Execute the tool with given arguments."""
        try:
            if "file_path" not in arguments:
                raise RuntimeError("Missing required argument: file_path")
            if "contents" not in arguments:
                raise RuntimeError("Missing required argument: contents")
            if "file_hash" not in arguments:
                raise RuntimeError("Missing required argument: file_hash")

            file_path = arguments["file_path"]
            if not os.path.isabs(file_path):
                raise RuntimeError(f"File path must be absolute: {file_path}")

            # Check if file exists
            if not os.path.exists(file_path):
                raise RuntimeError(f"File does not exist: {file_path}")

            encoding = arguments.get("encoding", "utf-8")

            # Check file contents and hash before modification
            # Get file information and verify hash
            content, _, _, current_hash, total_lines, _ = (
                await self.editor.read_file_contents(file_path, encoding=encoding)
            )

            # Verify file hash
            if current_hash != arguments["file_hash"]:
                raise RuntimeError("File hash mismatch - file may have been modified")

            # Ensure the append content ends with newline
            append_content = arguments["contents"]
            if not append_content.endswith("\n"):
                append_content += "\n"

            # Create patch for append operation
            result = await self.editor.edit_file_contents(
                file_path,
                expected_file_hash=arguments["file_hash"],
                patches=[
                    {
                        "start": total_lines + 1,
                        "end": None,
                        "contents": append_content,
                        "range_hash": "",
                    }
                ],
                encoding=encoding,
            )

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Error processing request: {str(e)}") from e
