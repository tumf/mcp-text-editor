"""Handler for inserting content into text files."""

import json
import logging
import os
import traceback
from typing import Any, Dict, Sequence

from mcp.types import TextContent, Tool

from .base import BaseHandler

logger = logging.getLogger("mcp-text-editor")


class InsertTextFileContentsHandler(BaseHandler):
    """Handler for inserting content before or after a specific line in a text file."""

    name = "insert_text_file_contents"
    description = "Insert content before or after a specific line in a text file. Uses hash-based validation for concurrency control. You need to provide the file_hash comes from get_text_file_contents."

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
                        "description": "Hash of the file contents for concurrency control. it should be matched with the file_hash when get_text_file_contents is called.",
                    },
                    "contents": {
                        "type": "string",
                        "description": "Content to insert",
                    },
                    "before": {
                        "type": "integer",
                        "description": "Line number before which to insert content (mutually exclusive with 'after')",
                    },
                    "after": {
                        "type": "integer",
                        "description": "Line number after which to insert content (mutually exclusive with 'before')",
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Text encoding (default: 'utf-8')",
                        "default": "utf-8",
                    },
                },
                "required": ["file_path", "file_hash", "contents"],
            },
        )

    async def run_tool(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Execute the tool with given arguments."""
        try:
            if "file_path" not in arguments:
                raise RuntimeError("Missing required argument: file_path")
            if "file_hash" not in arguments:
                raise RuntimeError("Missing required argument: file_hash")
            if "contents" not in arguments:
                raise RuntimeError("Missing required argument: contents")

            file_path = arguments["file_path"]
            if not os.path.isabs(file_path):
                raise RuntimeError(f"File path must be absolute: {file_path}")

            # Check if exactly one of before/after is specified
            if ("before" in arguments) == ("after" in arguments):
                raise RuntimeError(
                    "Exactly one of 'before' or 'after' must be specified"
                )

            line_number = (
                arguments.get("before")
                if "before" in arguments
                else arguments.get("after")
            )
            is_before = "before" in arguments
            encoding = arguments.get("encoding", "utf-8")

            # Get result from editor
            result = await self.editor.insert_text_file_contents(
                file_path=file_path,
                file_hash=arguments["file_hash"],
                contents=arguments["contents"],
                before=line_number if is_before else None,
                after=None if is_before else line_number,
                encoding=encoding,
            )
            # Wrap result with file_path key
            result = {file_path: result}
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Error processing request: {str(e)}") from e
