"""Handler for patching text file contents."""

import json
import logging
import os
from typing import Any, Dict, Sequence

from mcp.types import TextContent, Tool

from ..errors import (
    ErrorCode,
    FileOperationError,
    ValidationError,
    ContentOperationError,
)
from .base import BaseHandler

logger = logging.getLogger("mcp-text-editor")


class PatchTextFileContentsHandler(BaseHandler):
    """Handler for patching a text file."""

    name = "patch_text_file_contents"
    description = "Apply patches to text files with hash-based validation for concurrency control.you need to use get_text_file_contents tool to get the file hash and range hash every time before using this tool. you can use append_text_file_contents tool to append text contents to the file without range hash, start and end. you can use insert_text_file_contents tool to insert text contents to the file without range hash, start and end."  # noqa: E501

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
                                    "description": "Hash of the content being replaced. it should get from get_text_file_contents tool with the same start and end.",  # noqa: E501
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

    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        """Validate the input arguments.

        Args:
            arguments: The arguments to validate

        Raises:
            ValidationError: If the arguments are invalid
            FileOperationError: If the file does not exist or is not accessible
        """
        required_fields = ["file_path", "file_hash", "patches"]
        for field in required_fields:
            if field not in arguments:
                raise ValidationError(
                    f"Missing required argument: {field}",
                    code=ErrorCode.INVALID_REQUEST,
                    details={"field": field},
                )

        file_path = arguments["file_path"]
        if not os.path.isabs(file_path):
            raise ValidationError(
                "File path must be absolute",
                code=ErrorCode.INVALID_REQUEST,
                details={"file_path": file_path},
            )

        if not os.path.exists(file_path):
            raise FileOperationError(
                "File does not exist",
                code=ErrorCode.FILE_NOT_FOUND,
                details={"file_path": file_path},
            )

        # Validate patches
        patches = arguments["patches"]
        if not isinstance(patches, list):
            raise ValidationError(
                "Patches must be a list",
                code=ErrorCode.INVALID_SCHEMA,
                details={"patches": type(patches).__name__},
            )

        required_patch_fields = ["start", "end", "contents", "range_hash"]
        for i, patch in enumerate(patches):
            for field in required_patch_fields:
                if field not in patch:
                    raise ValidationError(
                        f"Missing required field in patch {i}: {field}",
                        code=ErrorCode.INVALID_FIELD,
                        details={
                            "patch_index": i,
                            "field": field,
                        },
                    )

            # Validate line numbers
            if not isinstance(patch["start"], int) or patch["start"] < 1:
                raise ValidationError(
                    f"Invalid start line in patch {i}",
                    code=ErrorCode.INVALID_LINE_RANGE,
                    details={
                        "patch_index": i,
                        "start": patch["start"],
                        "message": "Start line must be a positive integer",
                    },
                )

            if not isinstance(patch["end"], int) or patch["end"] < patch["start"]:
                raise ValidationError(
                    f"Invalid end line in patch {i}",
                    code=ErrorCode.INVALID_LINE_RANGE,
                    details={
                        "patch_index": i,
                        "start": patch["start"],
                        "end": patch["end"],
                        "message": "End line must be an integer greater than or equal to start line",
                    },
                )

    async def _execute_tool(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Execute the patch text file contents tool.

        Args:
            arguments: The validated arguments for the tool

        Returns:
            Sequence[TextContent]: The tool's output

        Raises:
            ContentOperationError: If there are content-related errors
            FileOperationError: If there are file operation errors
        """
        try:
            # Apply patches using editor.edit_file_contents
            result = await self.editor.edit_file_contents(
                file_path=arguments["file_path"],
                expected_hash=arguments["file_hash"],
                patches=arguments["patches"],
                encoding=arguments.get("encoding", "utf-8"),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except FileOperationError as e:
            logger.error(f"File operation error: {str(e)}")
            raise

        except ContentOperationError as e:
            logger.error(f"Content operation error: {str(e)}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise
