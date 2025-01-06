"""Handler for deleting content from text files."""

import json
import logging
import os
import traceback
from typing import Any, Dict, Sequence

from mcp.types import TextContent, Tool

from ..models import DeleteTextFileContentsRequest, FileRange
from .base import BaseHandler

logger = logging.getLogger("mcp-text-editor")


class DeleteTextFileContentsHandler(BaseHandler):
    """Handler for deleting content from a text file."""

    name = "delete_text_file_contents"
    description = "Delete specified content ranges from a text file. The file must exist. File paths must be absolute. You need to provide the file_hash comes from get_text_file_contents."

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
                    "ranges": {
                        "type": "array",
                        "description": "List of line ranges to delete",
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
                                "range_hash": {
                                    "type": "string",
                                    "description": "Hash of the content being deleted. it should be matched with the range_hash when get_text_file_contents is called with the same range.",
                                },
                            },
                            "required": ["start", "range_hash"],
                        },
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Text encoding (default: 'utf-8')",
                        "default": "utf-8",
                    },
                },
                "required": ["file_path", "file_hash", "ranges"],
            },
        )

    async def run_tool(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Execute the tool with given arguments."""
        try:
            # Input validation
            if "file_path" not in arguments:
                raise RuntimeError("Missing required argument: file_path")
            if "file_hash" not in arguments:
                raise RuntimeError("Missing required argument: file_hash")
            if "ranges" not in arguments:
                raise RuntimeError("Missing required argument: ranges")

            file_path = arguments["file_path"]
            if not os.path.isabs(file_path):
                raise RuntimeError(f"File path must be absolute: {file_path}")

            # Check if file exists
            if not os.path.exists(file_path):
                raise RuntimeError(f"File does not exist: {file_path}")

            encoding = arguments.get("encoding", "utf-8")

            # Create file ranges for deletion
            ranges = [
                FileRange(
                    start=r["start"], end=r.get("end"), range_hash=r["range_hash"]
                )
                for r in arguments["ranges"]
            ]

            # Create delete request
            request = DeleteTextFileContentsRequest(
                file_path=file_path,
                file_hash=arguments["file_hash"],
                ranges=ranges,
                encoding=encoding,
            )

            # Execute deletion using the service
            result_dict = self.editor.service.delete_text_file_contents(request)

            # Convert EditResults to dictionaries
            serializable_result = {}
            for file_path, edit_result in result_dict.items():
                serializable_result[file_path] = edit_result.to_dict()

            return [
                TextContent(type="text", text=json.dumps(serializable_result, indent=2))
            ]

        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Error processing request: {str(e)}") from e
