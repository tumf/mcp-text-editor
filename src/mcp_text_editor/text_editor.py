"""Core text editor functionality with file operation handling."""

import hashlib
import os
from typing import Any, Dict, List, Optional, Tuple

from mcp_text_editor.models import EditPatch, FileRanges


class TextEditor:
    """Handles text file operations with security checks and conflict detection."""

    def __init__(self):
        """Initialize TextEditor."""
        self._validate_environment()

    def _validate_environment(self) -> None:
        """
        Validate environment variables and setup.
        Can be extended to check for specific permissions or configurations.
        """
        # Future: Add environment validation if needed
        pass

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
                line_start = max(1, range_spec.start) - 1
                end_value = range_spec.end
                line_end = (
                    min(total_lines, end_value)
                    if end_value is not None
                    else total_lines
                )

                if line_start >= total_lines:
                    empty_content = ""
                    result[file_path]["ranges"].append(
                        {
                            "content": empty_content,
                            "start_line": line_start + 1,
                            "end_line": line_start + 1,
                            "range_hash": self.calculate_hash(empty_content),
                            "total_lines": total_lines,
                            "content_size": 0,
                        }
                    )
                    continue

                selected_lines = lines[line_start:line_end]
                content = "".join(selected_lines)
                range_hash = self.calculate_hash(content)

                result[file_path]["ranges"].append(
                    {
                        "content": content,
                        "start_line": line_start + 1,
                        "end_line": line_end,
                        "range_hash": range_hash,
                        "total_lines": total_lines,
                        "content_size": len(content),
                    }
                )

        return result

    async def read_file_contents(
        self,
        file_path: str,
        line_start: int = 1,
        line_end: Optional[int] = None,
        encoding: str = "utf-8",
    ) -> Tuple[str, int, int, str, int, int]:
        lines, file_content, total_lines = await self._read_file(
            file_path, encoding=encoding
        )

        if line_end is not None and line_end < line_start:
            raise ValueError("End line must be greater than or equal to start line")

        line_start = max(1, line_start) - 1
        line_end = total_lines if line_end is None else min(line_end, total_lines)

        if line_start >= total_lines:
            empty_content = ""
            empty_hash = self.calculate_hash(empty_content)
            return empty_content, line_start, line_start, empty_hash, total_lines, 0
        if line_end < line_start:
            raise ValueError("End line must be greater than or equal to start line")

        selected_lines = lines[line_start:line_end]
        content = "".join(selected_lines)
        content_hash = self.calculate_hash(content)
        content_size = len(content.encode(encoding))

        return (
            content,
            line_start + 1,
            line_end,
            content_hash,
            total_lines,
            content_size,
        )

    async def edit_file_contents(
        self,
        file_path: str,
        expected_hash: str,
        patches: List[Dict[str, Any]],
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        """
        Edit file contents with hash-based conflict detection and multiple patches.

        Args:
            file_path (str): Path to the file to edit
            expected_hash (str): Expected hash of the file before editing
            patches (List[EditPatch]): List of patches to apply
                - line_start (int): Starting line number (1-based, optional, default: 1)
                - line_end (Optional[int]): Ending line number (inclusive)
                - contents (str): New content to insert
        Edit file contents with hash-based conflict detection and multiple patches (supporting new file creation).

        Args:
            file_path (str): Path to the file to edit (parent directories are created automatically)
            expected_hash (str): Expected hash of the file before editing (empty string for new files)
            patches (List[Dict[str, Any]]): List of patches to apply, each containing:
                - line_start (int): Starting line number (1-based)
                - line_end (Optional[int]): Ending line number (inclusive)
                - contents (str): New content to insert
                - range_hash (str): Expected hash of the content being replaced

        Returns:
            Dict[str, Any]: Results of the operation containing:
                - result: "ok" or "error"
                - hash: New file hash if successful, None if error
                - reason: Error message if result is "error"
                    "content": None,
                }

            # Read current file content and verify hash
        """
        self._validate_file_path(file_path)
        try:
            if not os.path.exists(file_path):
                if expected_hash not in ["", None]:  # Allow null hash
                    return {
                        "result": "error",
                        "reason": "File not found and non-empty hash provided",
                        "file_hash": None,
                        "content": None,
                    }
                # Create parent directories if they don't exist
                parent_dir = os.path.dirname(file_path)
                if parent_dir:
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                    except OSError as e:
                        return {
                            "result": "error",
                            "reason": f"Failed to create directory: {str(e)}",
                            "file_hash": None,
                            "content": None,
                        }
                # Initialize empty state for new file
                current_content = ""
                current_hash = ""
                lines: List[str] = []
                encoding = "utf-8"
            else:
                # Read current file content and verify hash
                current_content, _, _, current_hash, total_lines, _ = (
                    await self.read_file_contents(file_path, encoding=encoding)
                )

                # Treat empty file as new file
                if not current_content:
                    current_content = ""
                    current_hash = ""
                    lines = []
                elif current_content and expected_hash == "":
                    return {
                        "result": "error",
                        "reason": "Unexpected error - Cannot treat existing file as new",
                        "file_hash": None,
                        "content": None,
                    }
                elif current_hash != expected_hash:
                    return {
                        "result": "error",
                        "reason": "Hash mismatch - file has been modified",
                        "file_hash": None,
                        "content": current_content,
                    }
                else:
                    lines = current_content.splitlines(keepends=True)

            # Convert patches to EditPatch objects
            patch_objects = [EditPatch.model_validate(p) for p in patches]

            # Sort patches from bottom to top to avoid line number shifts
            sorted_patches = sorted(
                patch_objects,
                key=lambda x: (
                    -(x.line_start),
                    -(x.line_end or x.line_start or float("inf")),
                ),
            )

            # Check for overlapping patches
            for i in range(len(sorted_patches)):
                for j in range(i + 1, len(sorted_patches)):
                    patch1 = sorted_patches[i]
                    patch2 = sorted_patches[j]
                    start1 = patch1.line_start
                    end1 = patch1.line_end or start1
                    start2 = patch2.line_start
                    end2 = patch2.line_end or start2

                    if (start1 <= end2 and end1 >= start2) or (
                        start2 <= end1 and end2 >= start1
                    ):
                        return {
                            "result": "error",
                            "reason": "Overlapping patches detected",
                            "hash": None,
                            "content": current_content,
                        }

            # Apply patches
            for patch in sorted_patches:
                # Get line numbers (1-based)
                line_start: int
                line_end: Optional[int]
                if isinstance(patch, EditPatch):
                    line_start = patch.line_start
                    line_end = patch.line_end
                else:
                    line_start = patch["line_start"] if "line_start" in patch else 1
                    line_end = patch["line_end"] if "line_end" in patch else line_start

                # Check for invalid line range
                if line_end is not None and line_end < line_start:
                    return {
                        "result": "error",
                        "reason": "End line must be greater than or equal to start line",
                        "file_hash": None,
                        "content": current_content,
                    }

                # Handle unexpected empty hash for existing file
                if (
                    os.path.exists(file_path)
                    and current_content
                    and expected_hash == ""
                ):
                    return {
                        "result": "error",
                        "reason": "Unexpected error",
                        "file_hash": None,
                        "content": current_content,
                    }

                # Calculate line ranges for zero-based indexing
                line_start_zero = line_start - 1
                line_end_zero = (
                    len(lines) - 1
                    if line_end is None
                    else min(line_end - 1, len(lines) - 1)
                )

                # Get expected hash for validation
                expected_range_hash = None
                if isinstance(patch, dict):
                    expected_range_hash = patch.get("range_hash")
                else:
                    # For EditPatch objects, use model fields
                    expected_range_hash = patch.range_hash

                # Determine operation type and validate hash requirements
                if not os.path.exists(file_path) or not current_content:
                    # New file or empty file - treat as insertion
                    is_insertion = True
                elif line_start_zero >= len(lines):
                    # Append mode - line_start exceeds total lines
                    is_insertion = True
                else:
                    # For existing files:
                    # range_hash is required for modifications
                    if not expected_range_hash:
                        return {
                            "result": "error",
                            "reason": "range_hash is required for file modifications",
                            "file_hash": None,
                            "content": current_content,
                        }

                    # Hash provided - verify content
                    target_lines = lines[line_start_zero : line_end_zero + 1]
                    target_content = "".join(target_lines)
                    actual_range_hash = self.calculate_hash(target_content)

                    # Compare hashes
                    # Empty range_hash means explicit insertion
                    is_insertion = (
                        not expected_range_hash
                        or expected_range_hash == self.calculate_hash("")
                    )

                    # For non-insertion operations, verify content hash
                    if not is_insertion:
                        if actual_range_hash != expected_range_hash:
                            return {
                                "result": "error",
                                "reason": f"Content hash mismatch - file has been modified since last read. Please use get_text_file_contents tool with lines {line_start}-{line_end} to get current content and hashes, then retry with the updated hashes. If you want to append content, set line_start to {len(lines)+1}.",
                                "file_hash": None,
                                "content": current_content,
                            }

                # Prepare new content
                contents: str
                if isinstance(patch, EditPatch):
                    contents = patch.contents
                else:
                    contents = patch["contents"]

                new_content = contents if contents.endswith("\n") else contents + "\n"
                new_lines = new_content.splitlines(keepends=True)

                # Apply changes - line ranges were calculated earlier
                if is_insertion:
                    # Insert at the specified line
                    lines[line_start_zero:line_start_zero] = new_lines
                else:
                    # Replace the specified range
                    lines[line_start_zero : line_end_zero + 1] = new_lines

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
            }

        except FileNotFoundError:
            return {
                "result": "error",
                "reason": f"File not found: {file_path}",
                "file_hash": None,
                "content": None,
            }
        except (IOError, UnicodeError, PermissionError) as e:
            return {
                "result": "error",
                "reason": f"Error editing file: {str(e)}",
                "file_hash": None,
                "content": None,
            }
        except Exception as e:
            return {
                "result": "error",
                "reason": f"Unexpected error: {str(e)}",
                "file_hash": None,
                "content": None,
            }
