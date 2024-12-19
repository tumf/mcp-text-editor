"""Handler for editing text file contents."""

import json
import logging
import os
import traceback
from typing import Any, Dict, Sequence

from mcp.types import TextContent, Tool

from .base import BaseHandler

logger = logging.getLogger("mcp-text-editor")


class EditTextFileContentsHandler(BaseHandler):
    """Handler for editing text file contents."""

    name = "edit_text_file_contents"
    description = (
        "A line editor that supports editing text file contents by specifying line ranges and content. "
        "It handles multiple patches in a single operation with hash-based conflict detection. "
        "File paths must be absolute. IMPORTANT: (1) Before using this tool, you must first get the file's "
        "current hash and range hashes and line numbers using get_text_file_contents. (2) To avoid line number "
        "shifts affecting your patches, use get_text_file_contents to read the SAME ranges you plan to edit "
        "before making changes. different line numbers have different rangehashes.(3) Patches must be specified "
        "from bottom to top to handle line number shifts correctly, as edits to lower lines don't affect the "
        "line numbers of higher lines. (4) To append content to a file, first get the total number of lines "
        "with get_text_file_contents, then specify a patch with start = total_lines + 1 and end = total_lines. "
        "This indicates an append operation and range_hash is not required. Similarly, range_hash is not "
        "required for new file creation."
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
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "Path to the text file. File path must be absolute.",
                                },
                                "file_hash": {
                                    "type": "string",
                                    "description": "Hash of the file contents when get_text_file_contents is called.",
                                },
                                "patches": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "start": {
                                                "type": "integer",
                                                "default": 1,
                                                "description": "Starting line number (1-based). it should be matched with the start line number when get_text_file_contents is called.",
                                            },
                                            "end": {
                                                "type": ["integer", "null"],
                                                "default": None,
                                                "description": "Ending line number (null for end of file). it should be matched with the end line number when get_text_file_contents is called.",
                                            },
                                            "contents": {"type": "string"},
                                            "range_hash": {
                                                "type": "string",
                                                "description": "Hash of the content being replaced from start to end (required except for new files and append operations)",
                                            },
                                        },
                                        "required": ["contents"],
                                    },
                                },
                            },
                            "required": ["path", "file_hash", "patches"],
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
                raise RuntimeError("Missing required argument: files")

            files = arguments["files"]
            results: Dict[str, Dict] = {}

            if len(files) == 0:
                return [TextContent(type="text", text=json.dumps(results, indent=2))]

            for file_operation in files:
                # First check if required fields exist
                if "path" not in file_operation:
                    raise RuntimeError("Missing required field: path")
                if "file_hash" not in file_operation:
                    raise RuntimeError("Missing required field: file_hash")
                if "patches" not in file_operation:
                    raise RuntimeError("Missing required field: patches")

                # Then check if path is absolute
                if not os.path.isabs(file_operation["path"]):
                    raise RuntimeError(
                        f"File path must be absolute: {file_operation['path']}"
                    )

                try:
                    file_path = file_operation["path"]
                    file_hash = file_operation["file_hash"]
                    patches = file_operation["patches"]

                    if not patches:
                        results[file_path] = {
                            "result": "error",
                            "reason": "Empty patches list",
                            "file_hash": file_hash,
                        }
                        continue

                    encoding = arguments.get("encoding", "utf-8")
                    # Validate patch fields first
                    for patch in patches:
                        if "contents" not in patch:
                            results[file_path] = {
                                "result": "error",
                                "reason": "Missing required field 'contents' in patch",
                                "file_hash": file_hash,
                                "content": None,
                            }
                            break
                    else:  # No break occurred
                        result = await self.editor.edit_file_contents(
                            file_path, file_hash, patches, encoding=encoding
                        )
                        results[file_path] = result
                except Exception as e:
                    error_file_path = (
                        file_path if "path" in file_operation else "unknown"
                    )
                    results[error_file_path] = {
                        "result": "error",
                        "reason": str(e),
                        "file_hash": file_operation.get(
                            "file_hash"
                        ),  # Use original hash
                        "content": None,
                    }

            return [TextContent(type="text", text=json.dumps(results, indent=2))]
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Error processing request: {str(e)}") from e
