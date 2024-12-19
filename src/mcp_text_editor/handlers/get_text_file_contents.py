"""Handler for getting text file contents."""

import json
import os
from typing import Any, Dict, Sequence

from mcp.types import TextContent, Tool

from .base import BaseHandler


class GetTextFileContentsHandler(BaseHandler):
    """Handler for getting text file contents."""

    name = "get_text_file_contents"
    description = (
        "Read text file contents from multiple files and line ranges. "
        "Returns file contents with hashes for concurrency control and line numbers for reference. "
        "The hashes are used to detect conflicts when editing the files. File paths must be absolute."
    )

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
                                    "description": "Path to the text file. File path must be absolute.",
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
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Text encoding (default: 'utf-8')",
                        "default": "utf-8",
                    },
                },
                "required": ["files"],
            },
        )

    async def run_tool(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Execute the tool with given arguments."""
        try:
            if "files" not in arguments:
                raise RuntimeError("Missing required argument: 'files'")

            for file_info in arguments["files"]:
                if not os.path.isabs(file_info["file_path"]):
                    raise RuntimeError(
                        f"File path must be absolute: {file_info['file_path']}"
                    )

            encoding = arguments.get("encoding", "utf-8")
            result = await self.editor.read_multiple_ranges(
                arguments["files"], encoding=encoding
            )
            response = result

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except KeyError as e:
            raise RuntimeError(f"Missing required argument: '{e}'") from e
        except Exception as e:
            raise RuntimeError(f"Error processing request: {str(e)}") from e
