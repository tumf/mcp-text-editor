"""Core text editor functionality with file operation handling."""

import hashlib
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from .models import DeleteTextFileContentsRequest, EditPatch, FileRanges
from .service import TextEditorService

logger = logging.getLogger(__name__)


class TextEditor:
    """Handles text file operations with security checks and conflict detection."""

    def __init__(self):
        """Initialize TextEditor."""
        self._validate_environment()
        self.service = TextEditorService()

    def create_error_response(
        self,
        error_message: str,
        content_hash: Optional[str] = None,
        file_path: Optional[str] = None,
        suggestion: Optional[str] = None,
        hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a standardized error response.

        Args:
            error_message (str): The error message to include
            content_hash (Optional[str], optional): Hash of the current content if available
            file_path (Optional[str], optional): File path to use as dictionary key
            suggestion (Optional[str], optional): Suggested operation type
            hint (Optional[str], optional): Hint message for users

        Returns:
            Dict[str, Any]: Standardized error response structure
        """
        error_response = {
            "result": "error",
            "reason": error_message,
            "file_hash": content_hash,
        }

        # Add fields if provided
        if content_hash is not None:
            error_response["file_hash"] = content_hash
        if suggestion:
            error_response["suggestion"] = suggestion
        if hint:
            error_response["hint"] = hint

        if file_path:
            return {file_path: error_response}
        return error_response

    def _validate_environment(self) -> None:
        """
        Validate environment variables and setup.
        Can be extended to check for specific permissions or configurations.
        """
        # Future: Add environment validation if needed
        pass  # pragma: no cover

    def _validate_file_path(self, file_path: str | os.PathLike) -> None:
        """
        Validate if file path is allowed and secure.

        Args:
            file_path (str | os.PathLike): Path to validate

        Raises:
            ValueError: If path is not allowed or contains dangerous patterns
        """
        # Convert path to string for checking
        path_str = str(file_path)

        # Check for dangerous patterns
        if ".." in path_str:
            raise ValueError("Path traversal not allowed")

    @staticmethod
    def calculate_hash(content: str) -> str:
        """
        Calculate SHA-256 hash of content.

        Args:
            content (str): Content to hash

        Returns:
            str: Hex digest of SHA-256 hash
        """
        return hashlib.sha256(content.encode()).hexdigest()

    async def _read_file(
        self, file_path: str, encoding: str = "utf-8"
    ) -> Tuple[List[str], str, int]:
        """Read file and return lines, content, and total lines.

        Args:
            file_path (str): Path to the file to read
            encoding (str, optional): File encoding. Defaults to "utf-8"

        Returns:
            Tuple[List[str], str, int]: Lines, content, and total line count

        Raises:
            FileNotFoundError: If file not found
            UnicodeDecodeError: If file cannot be decoded with specified encoding
        """
        self._validate_file_path(file_path)
        try:
            with open(file_path, "r", encoding=encoding) as f:
                lines = f.readlines()
            file_content = "".join(lines)
            return lines, file_content, len(lines)
        except FileNotFoundError as err:
            raise FileNotFoundError(f"File not found: {file_path}") from err
        except UnicodeDecodeError as err:
            raise UnicodeDecodeError(
                encoding,
                err.object,
                err.start,
                err.end,
                f"Failed to decode file '{file_path}' with {encoding} encoding",
            ) from err

    async def read_multiple_ranges(
        self, ranges: List[Dict[str, Any]], encoding: str = "utf-8"
    ) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}

        for file_range_dict in ranges:
            file_range = FileRanges.model_validate(file_range_dict)
            file_path = file_range.file_path
            lines, file_content, total_lines = await self._read_file(
                file_path, encoding=encoding
            )
            file_hash = self.calculate_hash(file_content)
            result[file_path] = {"ranges": [], "file_hash": file_hash}

            for range_spec in file_range.ranges:
                start = max(1, range_spec.start) - 1
                end_value = range_spec.end
                end = (
                    min(total_lines, end_value)
                    if end_value is not None
                    else total_lines
                )

                if start >= total_lines:
                    empty_content = ""
                    result[file_path]["ranges"].append(
                        {
                            "content": empty_content,
                            "start": start + 1,
                            "end": start + 1,
                            "range_hash": self.calculate_hash(empty_content),
                            "total_lines": total_lines,
                            "content_size": 0,
                        }
                    )
                    continue

                selected_lines = lines[start:end]
                content = "".join(selected_lines)
                range_hash = self.calculate_hash(content)

                result[file_path]["ranges"].append(
                    {
                        "content": content,
                        "start": start + 1,
                        "end": end,
                        "range_hash": range_hash,
                        "total_lines": total_lines,
                        "content_size": len(content),
                    }
                )

        return result

    async def read_file_contents(
        self,
        file_path: str,
        start: int = 1,
        end: Optional[int] = None,
        encoding: str = "utf-8",
    ) -> Tuple[str, int, int, str, int, int]:
        lines, file_content, total_lines = await self._read_file(
            file_path, encoding=encoding
        )

        if end is not None and end < start:
            raise ValueError("End line must be greater than or equal to start line")

        start = max(1, start) - 1
        end = total_lines if end is None else min(end, total_lines)

        if start >= total_lines:
            empty_content = ""
            empty_hash = self.calculate_hash(empty_content)
            return empty_content, start, start, empty_hash, total_lines, 0
        if end < start:
            raise ValueError("End line must be greater than or equal to start line")

        selected_lines = lines[start:end]
        content = "".join(selected_lines)
        content_hash = self.calculate_hash(content)
        content_size = len(content.encode(encoding))

        return (
            content,
            start + 1,
            end,
            content_hash,
            total_lines,
            content_size,
        )

    async def edit_file_contents(
        self,
        file_path: str,
        expected_file_hash: str,
        patches: List[Dict[str, Any]],
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        """
        Edit file contents with hash-based conflict detection and multiple patches.

        Args:
            file_path (str): Path to the file to edit
            expected_hash (str): Expected hash of the file before editing
            patches (List[Dict[str, Any]]): List of patches to apply, each containing:
                - start (int): Starting line number (1-based)
                - end (Optional[int]): Ending line number (inclusive)
                - contents (str): New content to insert (if empty string, consider using delete_text_file_contents instead)
                - range_hash (str): Expected hash of the content being replaced

        Returns:
            Dict[str, Any]: Results of the operation containing:
                - result: "ok" or "error"
                - hash: New file hash if successful, None if error
                - reason: Error message if result is "error"
                    "file_hash": None,
                }

            # Read current file content and verify hash
        """
        self._validate_file_path(file_path)
        try:
            if not os.path.exists(file_path):
                if expected_file_hash not in ["", None]:  # Allow null hash
                    return self.create_error_response(
                        "File not found and non-empty hash provided",
                        suggestion="append",
                        hint="For new files, please consider using append_text_file_contents",
                    )
                # Create parent directories if they don't exist
                parent_dir = os.path.dirname(file_path)
                if parent_dir:
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                    except OSError as e:
                        return self.create_error_response(
                            f"Failed to create directory: {str(e)}",
                            suggestion="patch",
                            hint="Please check file permissions and try again",
                        )
                # Initialize empty state for new file
                current_file_content = ""
                current_file_hash = ""
                lines: List[str] = []
                encoding = "utf-8"
            else:
                # Read current file content and verify hash
                (
                    current_file_content,
                    _,
                    _,
                    current_file_hash,
                    total_lines,
                    _,
                ) = await self.read_file_contents(file_path, encoding=encoding)

                # Treat empty file as new file
                if not current_file_content:
                    current_file_content = ""
                    current_file_hash = ""
                    lines = []
                elif current_file_content and expected_file_hash == "":
                    return self.create_error_response(
                        "Unexpected error - Cannot treat existing file as new",
                    )
                elif current_file_hash != expected_file_hash:
                    suggestion = "patch"
                    hint = "Please use get_text_file_contents tool to get the current content and hash"

                    return self.create_error_response(
                        "FileHash mismatch - Please use get_text_file_contents tool to get current content and hashes, then retry with the updated hashes.",
                        suggestion=suggestion,
                        hint=hint,
                    )
                else:
                    lines = current_file_content.splitlines(keepends=True)
                    lines = current_file_content.splitlines(keepends=True)

            # Convert patches to EditPatch objects
            patch_objects = [EditPatch.model_validate(p) for p in patches]

            # Sort patches from bottom to top to avoid line number shifts
            sorted_patches = sorted(
                patch_objects,
                key=lambda x: (
                    -(x.start),
                    -(x.end or x.start or float("inf")),
                ),
            )

            # Check for overlapping patches
            for i in range(len(sorted_patches)):
                for j in range(i + 1, len(sorted_patches)):
                    patch1 = sorted_patches[i]
                    patch2 = sorted_patches[j]
                    start1 = patch1.start
                    end1 = patch1.end or start1
                    start2 = patch2.start
                    end2 = patch2.end or start2

                    if (start1 <= end2 and end1 >= start2) or (
                        start2 <= end1 and end2 >= start1
                    ):
                        return self.create_error_response(
                            "Overlapping patches detected",
                            suggestion="patch",
                            hint="Please ensure your patches do not overlap",
                        )

            # Apply patches
            for patch in sorted_patches:
                # Get line numbers (1-based)
                start: int
                end: Optional[int]
                if isinstance(patch, EditPatch):
                    start = patch.start
                    end = patch.end
                else:
                    start = patch["start"] if "start" in patch else 1
                    end = patch["end"] if "end" in patch else start

                # Check for invalid line range
                if end is not None and end < start:
                    return {
                        "result": "error",
                        "reason": "End line must be greater than or equal to start line",
                        "file_hash": None,
                        "content": current_file_content,
                    }

                # Handle unexpected empty hash for existing file
                if (
                    os.path.exists(file_path)
                    and current_file_content
                    and expected_file_hash == ""
                ):
                    return {
                        "result": "error",
                        "reason": "File hash validation required: Empty hash provided for existing file",
                        "details": {
                            "file_path": file_path,
                            "current_file_hash": self.calculate_hash(
                                current_file_content
                            ),
                            "expected_file_hash": expected_file_hash,
                        },
                    }

                # Calculate line ranges for zero-based indexing
                start_zero = start - 1

                # Get expected hash for validation
                expected_range_hash = None
                if isinstance(patch, dict):
                    expected_range_hash = patch.get("range_hash")
                else:
                    # For EditPatch objects, use model fields
                    expected_range_hash = patch.range_hash

                # Determine operation type and validate hash requirements
                if not os.path.exists(file_path) or not current_file_content:
                    # New file or empty file - treat as insertion
                    is_insertion = True
                elif start_zero >= len(lines):
                    is_insertion = True
                else:
                    # For modification mode, check the range_hash
                    is_insertion = expected_range_hash == ""
                    if not is_insertion:
                        # Calculate end_zero for content validation
                        end_zero = (
                            len(lines) - 1
                            if end is None
                            else min(end - 1, len(lines) - 1)
                        )

                        # Hash provided - verify content
                        target_lines = lines[start_zero : end_zero + 1]
                        target_content = "".join(target_lines)
                        actual_range_hash = self.calculate_hash(target_content)

                        if actual_range_hash != expected_range_hash:
                            return {
                                "result": "error",
                                "reason": "Content range hash mismatch - Please use get_text_file_contents tool with the same start and end to get current content and hashes, then retry with the updated hashes.",
                                "suggestion": "get",
                                "hint": "Please run get_text_file_contents first to get current content and hashes",
                            }

                # Prepare new content
                if isinstance(patch, EditPatch):
                    contents = patch.contents
                else:
                    contents = patch["contents"]

                # Check if this is a deletion (empty content)
                if not contents.strip():
                    return {
                        "result": "ok",
                        "file_hash": current_file_hash,  # Return current hash since no changes made
                        "hint": "For content deletion, please consider using delete_text_file_contents instead of patch with empty content",
                        "suggestion": "delete",
                    }

                # Set suggestions for alternative tools
                suggestion_text: Optional[str] = None
                hint_text: Optional[str] = None
                if not os.path.exists(file_path) or not current_file_content:
                    suggestion_text = "append"
                    hint_text = "For new or empty files, please consider using append_text_file_contents instead"
                elif is_insertion:
                    if start_zero >= len(lines):
                        suggestion_text = "append"
                        hint_text = "For adding content at the end of file, please consider using append_text_file_contents instead"
                    else:
                        suggestion_text = "insert"
                        hint_text = "For inserting content within file, please consider using insert_text_file_contents instead"

                # Prepare the content
                new_content = contents if contents.endswith("\n") else contents + "\n"
                new_lines = new_content.splitlines(keepends=True)

                # For insertion mode, we don't need end_zero
                if is_insertion:
                    # Insert at the specified line
                    lines[start_zero:start_zero] = new_lines
                else:
                    # We already have end_zero for replacements
                    lines[start_zero : end_zero + 1] = new_lines

            # Write the final content back to file
            final_content = "".join(lines)
            with open(file_path, "w", encoding=encoding) as f:
                f.write(final_content)

            # Calculate new hash
            new_hash = self.calculate_hash(final_content)

            return {
                "result": "ok",
                "file_hash": new_hash,
                "reason": None,
                "suggestion": suggestion_text,
                "hint": hint_text,
            }

        except FileNotFoundError:
            return self.create_error_response(
                f"File not found: {file_path}",
                suggestion="append",
                hint="For new files, please use append_text_file_contents",
            )
        except (IOError, UnicodeError, PermissionError) as e:
            return self.create_error_response(
                f"Error editing file: {str(e)}",
                suggestion="patch",
                hint="Please check file permissions and try again",
            )
        except Exception as e:
            import traceback

            logger.error(f"Error: {str(e)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            return self.create_error_response(
                "Unexpected error occurred",
                suggestion="patch",
                hint="Please try again or report the issue if it persists",
            )

    async def insert_text_file_contents(
        self,
        file_path: str,
        file_hash: str,
        contents: str,
        after: Optional[int] = None,
        before: Optional[int] = None,
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        """Insert text content before or after a specific line in a file.

        Args:
            file_path (str): Path to the file to edit
            file_hash (str): Expected hash of the file before editing
            contents (str): Content to insert
            after (Optional[int]): Line number after which to insert content
            before (Optional[int]): Line number before which to insert content
            encoding (str, optional): File encoding. Defaults to "utf-8"

        Returns:
            Dict[str, Any]: Results containing:
                - result: "ok" or "error"
                - hash: New file hash if successful
                - reason: Error message if result is "error"
        """
        if (after is None and before is None) or (
            after is not None and before is not None
        ):
            return {
                "result": "error",
                "reason": "Exactly one of 'after' or 'before' must be specified",
                "hash": None,
            }

        try:
            (
                current_content,
                _,
                _,
                current_hash,
                total_lines,
                _,
            ) = await self.read_file_contents(
                file_path,
                encoding=encoding,
            )

            if current_hash != file_hash:
                return {
                    "result": "error",
                    "reason": "File hash mismatch - Please use get_text_file_contents tool to get current content and hash",
                    "hash": None,
                }

            # Split into lines, preserving line endings
            lines = current_content.splitlines(keepends=True)

            # Determine insertion point
            if after is not None:
                if after > total_lines:
                    return {
                        "result": "error",
                        "reason": f"Line number {after} is beyond end of file (total lines: {total_lines})",
                        "hash": None,
                    }
                insert_pos = after
            else:  # before must be set due to earlier validation
                assert before is not None
                if before > total_lines + 1:
                    return {
                        "result": "error",
                        "reason": f"Line number {before} is beyond end of file (total lines: {total_lines})",
                        "hash": None,
                    }
                insert_pos = before - 1

            # Ensure content ends with newline
            if not contents.endswith("\n"):
                contents += "\n"

            # Insert the content
            lines.insert(insert_pos, contents)

            # Join lines and write back to file
            final_content = "".join(lines)
            with open(file_path, "w", encoding=encoding) as f:
                f.write(final_content)

            # Calculate new hash
            new_hash = self.calculate_hash(final_content)

            return {
                "result": "ok",
                "hash": new_hash,
                "reason": None,
            }

        except FileNotFoundError:
            return {
                "result": "error",
                "reason": f"File not found: {file_path}",
                "hash": None,
            }
        except Exception as e:
            return {
                "result": "error",
                "reason": str(e),
                "hash": None,
            }

    async def delete_text_file_contents(
        self,
        request: DeleteTextFileContentsRequest,
    ) -> Dict[str, Any]:
        """Delete specified ranges from a text file with conflict detection.

        Args:
            request (DeleteTextFileContentsRequest): The request containing:
                - file_path: Path to the text file
                - file_hash: Expected hash of the file before editing
                - ranges: List of ranges to delete
                - encoding: Optional text encoding (default: utf-8)

        Returns:
            Dict[str, Any]: Results containing:
                - result: "ok" or "error"
                - hash: New file hash if successful
                - reason: Error message if result is "error"
        """
        self._validate_file_path(request.file_path)

        try:
            (
                current_content,
                _,
                _,
                current_hash,
                total_lines,
                _,
            ) = await self.read_file_contents(
                request.file_path,
                encoding=request.encoding or "utf-8",
            )

            # Check for conflicts
            if current_hash != request.file_hash:
                return {
                    request.file_path: {
                        "result": "error",
                        "reason": "File hash mismatch - Please use get_text_file_contents tool to get current content and hash",
                        "hash": current_hash,
                    }
                }

            # Split content into lines
            lines = current_content.splitlines(keepends=True)

            # Sort ranges in reverse order to handle line number shifts
            sorted_ranges = sorted(
                request.ranges,
                key=lambda x: (x.start, x.end or float("inf")),
                reverse=True,
            )

            # Validate ranges
            for i, range_ in enumerate(sorted_ranges):
                if range_.start < 1:
                    return {
                        request.file_path: {
                            "result": "error",
                            "reason": f"Invalid start line {range_.start}",
                            "hash": current_hash,
                        }
                    }

                if range_.end and range_.end < range_.start:
                    return {
                        request.file_path: {
                            "result": "error",
                            "reason": f"End line {range_.end} is less than start line {range_.start}",
                            "hash": current_hash,
                        }
                    }

                if range_.start > total_lines:
                    return {
                        request.file_path: {
                            "result": "error",
                            "reason": f"Start line {range_.start} exceeds file length {total_lines}",
                            "hash": current_hash,
                        }
                    }

                end = range_.end or total_lines
                if end > total_lines:
                    return {
                        request.file_path: {
                            "result": "error",
                            "reason": f"End line {end} exceeds file length {total_lines}",
                            "hash": current_hash,
                        }
                    }

                # Check for overlaps with next range
                if i + 1 < len(sorted_ranges):
                    next_range = sorted_ranges[i + 1]
                    next_end = next_range.end or total_lines
                    if next_end >= range_.start:
                        return {
                            request.file_path: {
                                "result": "error",
                                "reason": "Overlapping ranges detected",
                                "hash": current_hash,
                            }
                        }

            # Apply deletions
            for range_ in sorted_ranges:
                start_idx = range_.start - 1
                end_idx = range_.end if range_.end else len(lines)

                # Verify range content hash
                range_content = "".join(lines[start_idx:end_idx])
                if self.calculate_hash(range_content) != range_.range_hash:
                    return {
                        request.file_path: {
                            "result": "error",
                            "reason": f"Content hash mismatch for range {range_.start}-{range_.end}",
                            "hash": current_hash,
                        }
                    }

                del lines[start_idx:end_idx]

            # Write the final content back to file
            final_content = "".join(lines)
            with open(request.file_path, "w", encoding=request.encoding) as f:
                f.write(final_content)

            # Calculate new hash
            new_hash = self.calculate_hash(final_content)

            return {
                request.file_path: {
                    "result": "ok",
                    "hash": new_hash,
                    "reason": None,
                }
            }

        except FileNotFoundError:
            return {
                request.file_path: {
                    "result": "error",
                    "reason": f"File not found: {request.file_path}",
                    "hash": None,
                }
            }
        except Exception as e:
            return {
                request.file_path: {
                    "result": "error",
                    "reason": str(e),
                    "hash": None,
                }
            }
