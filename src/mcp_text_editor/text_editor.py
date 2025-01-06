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
            ValidationError: If path is invalid or contains dangerous patterns
            FileOperationError: If path cannot be accessed
        """
        # Convert path to string for checking
        path_str = str(file_path)

        # Check for dangerous patterns
        if ".." in path_str:
            raise ValidationError(
                "Path traversal not allowed",
                code=ErrorCode.INVALID_REQUEST,
                details={"file_path": path_str},
            )

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
            FileOperationError: If file cannot be read or accessed
            ValidationError: If file path is invalid
        """
        self._validate_file_path(file_path)
        try:
            with open(file_path, "r", encoding=encoding) as f:
                lines = f.readlines()
            file_content = "".join(lines)
            return lines, file_content, len(lines)
        except FileNotFoundError:
            raise FileOperationError(
                "File not found",
                code=ErrorCode.FILE_NOT_FOUND,
                details={"file_path": file_path},
            )
        except UnicodeDecodeError as err:
            raise FileOperationError(
                "Failed to decode file content",
                code=ErrorCode.FILE_ACCESS_DENIED,
                details={
                    "file_path": file_path,
                    "encoding": encoding,
                    "error": str(err),
                },
            )
        except OSError as err:
            raise FileOperationError(
                "Failed to read file",
                code=ErrorCode.FILE_ACCESS_DENIED,
                details={
                    "file_path": file_path,
                    "error": str(err),
                },
            )

    async def read_multiple_ranges(
        self, ranges: List[Dict[str, Any]], encoding: str = "utf-8"
    ) -> Dict[str, Dict[str, Any]]:
        """Read multiple ranges from files.

        Args:
            ranges: List of file range specifications
            encoding: File encoding (default: utf-8)

        Returns:
            Dict containing file contents and metadata

        Raises:
            ValidationError: If range specifications are invalid
            FileOperationError: If file operations fail
            ContentOperationError: If content operations fail
        """
        try:
            result: Dict[str, Dict[str, Any]] = {}

            # First validate all ranges
            for file_range_dict in ranges:
                try:
                    file_range = FileRanges.model_validate(file_range_dict)
                except Exception as e:
                    raise ValidationError(
                        "Invalid range specification",
                        code=ErrorCode.INVALID_SCHEMA,
                        details={
                            "error": str(e),
                            "range": file_range_dict,
                        },
                    )

                # Validate line ranges
                for range_spec in file_range.ranges:
                    if range_spec.start < 1:
                        raise ValidationError(
                            "Invalid line number",
                            code=ErrorCode.INVALID_LINE_RANGE,
                            details={
                                "start": range_spec.start,
                                "message": "Line numbers must be positive integers",
                            },
                        )
                    if range_spec.end is not None and range_spec.end < range_spec.start:
                        raise ValidationError(
                            "Invalid line range",
                            code=ErrorCode.INVALID_LINE_RANGE,
                            details={
                                "start": range_spec.start,
                                "end": range_spec.end,
                                "message": "End line must be greater than or equal to start line",
                            },
    def _validate_patches(
        self,
        patches: List[Dict[str, Any]],
        total_lines: Optional[int] = None
    ) -> List[EditPatch]:
        """Validate and convert patches to EditPatch objects.

        Args:
            patches: List of patch specifications to validate
            total_lines: Total number of lines in the file (optional, for range validation)

        Returns:
            List of validated EditPatch objects, sorted from bottom to top

        Raises:
            ValidationError: If patches are invalid, overlapping, or have invalid line numbers
        """
        try:
            # Convert to EditPatch objects
            try:
                patch_objects = [EditPatch.model_validate(p) for p in patches]
            except Exception as e:
    async def _check_file_hash(
        self,
        file_path: str,
        expected_hash: str,
        encoding: str = "utf-8",
    ) -> tuple[List[str], str, str]:
        """Check file existence and verify hash.

        Args:
            file_path: Path to the file
            expected_hash: Expected hash of the file
            encoding: File encoding (default: utf-8)

        Returns:
            tuple containing:
                - List of lines from the file
                - File content as a string
                - Content hash

        Raises:
            FileOperationError: If file cannot be accessed, read, or hash mismatch
            ValidationError: If file path is invalid
        """
        self._validate_file_path(file_path)

        # Handle non-existent file
        if not os.path.exists(file_path):
            if expected_hash not in ["", None]:
                raise FileOperationError(
                    "File not found and non-empty hash provided",
                    code=ErrorCode.FILE_NOT_FOUND,
                    details={
                        "file_path": file_path,
                        "expected_hash": expected_hash,
                    },
                )

            # Try to create parent directories if needed
            parent_dir = os.path.dirname(file_path)
            if parent_dir:
                try:
                    os.makedirs(parent_dir, exist_ok=True)
                except OSError as e:
                    raise FileOperationError(
                        "Failed to create directory",
                        code=ErrorCode.FILE_ACCESS_DENIED,
                        details={
                            "file_path": parent_dir,
                            "error": str(e),
                        },
                    )

            return [], "", ""

        try:
            # Read and validate existing file
            lines: List[str]
            content: str
            lines, content, _ = await self._read_file(file_path, encoding)

            if not content:
                return [], "", ""

            current_hash = self.calculate_hash(content)

            if expected_hash == "":
                raise FileOperationError(
                    "Cannot treat existing file as new",
                    code=ErrorCode.INVALID_REQUEST,
                    details={
                        "file_path": file_path,
                        "current_hash": current_hash,
                    },
                )
    async def _apply_patches(
        self,
        lines: List[str],
        patches: List[EditPatch],
        encoding: str = "utf-8",
    ) -> tuple[List[str], str, str]:
        """Apply patches to file content.

        The patches should be pre-validated and sorted using _validate_patches.

        Args:
            lines: Current file content as list of lines
            patches: List of validated and sorted EditPatch objects
            encoding: File encoding for content handling

        Returns:
            tuple containing:
                - Updated list of lines
                - Final content as string
                - New content hash

        Raises:
            ContentOperationError: If patch application fails or content validation errors occur
        """
        current_lines = lines.copy()  # Work on a copy to avoid modifying original

        try:
            # Apply each patch (already sorted from bottom to top)
            for patch in patches:
                start_idx = patch.start - 1  # Convert to 0-based indexing
                end_idx = patch.end - 1 if patch.end is not None else len(current_lines) - 1

                # Validate content range if hash is provided
                if patch.range_hash and current_lines:  # Skip check for empty files
                    target_content = "".join(current_lines[start_idx:end_idx + 1])
                    actual_hash = self.calculate_hash(target_content)
                    if actual_hash != patch.range_hash:
                        raise ContentOperationError(
                            "Content range hash mismatch",
                            code=ErrorCode.CONTENT_HASH_MISMATCH,
                            details={
                                "start": patch.start,
                                "end": patch.end,
                                "expected_hash": patch.range_hash,
                                "actual_hash": actual_hash,
                            },
                        )

                # Add newline to patch content if missing
                new_content = patch.contents
                if not new_content.endswith("\n"):
                    new_content += "\n"

                # Apply the patch
                new_lines = new_content.splitlines(keepends=True)
                if patch.range_hash:  # Replace mode
                    current_lines[start_idx:end_idx + 1] = new_lines
                else:  # Insert mode
                    current_lines[start_idx:start_idx] = new_lines

            # Join lines and calculate new hash
            final_content = "".join(current_lines)
            new_hash = self.calculate_hash(final_content)

            return current_lines, final_content, new_hash

        except IndexError as e:
            raise ContentOperationError(
                "Invalid line range in patch",
                code=ErrorCode.INVALID_LINE_RANGE,
                details={"error": str(e)},
            )
        except Exception as e:
            raise ContentOperationError(
                "Failed to apply patches",
                code=ErrorCode.INTERNAL_ERROR,
                details={"error": str(e)},
            )
        # Check for overlapping patches
        for i in range(len(sorted_patches)):
            patch1 = sorted_patches[i]
            if patch1.start < 1:
                raise ValidationError(
                    "Invalid line number",
                    code=ErrorCode.INVALID_LINE_RANGE,
                    details={
                        "patch_index": i,
                        "start": patch1.start,
                        "message": "Line numbers must be positive integers",
                    },
                )
            if patch1.end is not None and patch1.end < patch1.start:
                raise ValidationError(
                    "Invalid line range",
                    code=ErrorCode.INVALID_LINE_RANGE,
                    details={
                        "patch_index": i,
                        "start": patch1.start,
                        "end": patch1.end,
                        "message": "End line must be greater than or equal to start line",
                    },
                )

            for j in range(i + 1, len(sorted_patches)):
                patch2 = sorted_patches[j]
                if self._patches_overlap(patch1, patch2):
                    raise ValidationError(
                        "Overlapping patches detected",
                        code=ErrorCode.INVALID_REQUEST,
                        details={
                            "patch1": {"start": patch1.start, "end": patch1.end},
                            "patch2": {"start": patch2.start, "end": patch2.end},
                        },
                    )

        return sorted_patches

    def _patches_overlap(
        self, patch1: EditPatch, patch2: EditPatch
    ) -> bool:
        """Check if two patches overlap.

        Args:
            patch1: First patch
            patch2: Second patch

        Returns:
            True if patches overlap, False otherwise
        """
        end1 = patch1.end or patch1.start
        end2 = patch2.end or patch2.start
        return (patch1.start <= end2 and end1 >= patch2.start) or (
            patch2.start <= end1 and end2 >= patch1.start
        )

    async def _check_file_hash(
        self,
        file_path: str,
        expected_hash: str,
        encoding: str = "utf-8",
    ) -> tuple[str, str, list[str]]:
        """Check file existence and verify hash.

        Args:
            file_path: Path to the file
            expected_hash: Expected hash of the file
            encoding: File encoding

        Returns:
            Tuple of (current_content, current_hash, lines)

        Raises:
            FileOperationError: If file cannot be accessed or hash mismatch
        """
        if not os.path.exists(file_path):
            if expected_hash not in ["", None]:
                raise FileOperationError(
                    "File not found and non-empty hash provided",
                    code=ErrorCode.FILE_NOT_FOUND,
                    details={"file_path": file_path},
                )

            # Create parent directories if needed
            parent_dir = os.path.dirname(file_path)
            if parent_dir:
                try:
                    os.makedirs(parent_dir, exist_ok=True)
                except OSError as e:
                    raise FileOperationError(
                        "Failed to create directory",
                        code=ErrorCode.FILE_ACCESS_DENIED,
                        details={
                            "file_path": parent_dir,
                            "error": str(e),
                        },
                    )

            return "", "", []

        try:
            current_content, _, _, current_hash, _, _ = await self.read_file_contents(
                file_path, encoding=encoding
            )
        except FileOperationError:
            raise
        except Exception as e:
            raise FileOperationError(
                "Failed to read file",
                code=ErrorCode.FILE_ACCESS_DENIED,
                details={"file_path": file_path, "error": str(e)},
            )

        if not current_content:
            return "", "", []

        if expected_hash == "":
            raise FileOperationError(
                "Cannot treat existing file as new",
                code=ErrorCode.INVALID_REQUEST,
                details={"file_path": file_path},
            )

        if current_hash != expected_hash:
            raise FileOperationError(
                "File hash mismatch",
                code=ErrorCode.FILE_HASH_MISMATCH,
                details={
                    "file_path": file_path,
                    "expected": expected_hash,
                    "actual": current_hash,
                },
            )

        return (
            current_content,
            current_hash,
            current_content.splitlines(keepends=True),
        )

    async def edit_file_contents(
        self,
        file_path: str,
        expected_file_hash: str,
        patches: List[Dict[str, Any]],
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        """Edit file contents with hash-based conflict detection and multiple patches.

        Args:
            file_path: Path to the file to edit
            expected_hash: Expected hash of the file before editing
            patches: List of patches to apply, each containing:
                - start (int): Starting line number (1-based)
                - end (Optional[int]): Ending line number (inclusive)
                - contents (str): New content to insert
                - range_hash (str): Expected hash of the content being replaced
            encoding: File encoding (default: utf-8)

        Returns:
            Dict containing:
                - result: "ok" or "error"
                - file_hash: New file hash if successful
                - reason: Error message if result is "error"
                - suggestion: Optional suggested alternative tool
                - hint: Optional hint message for users
        """
        try:
            # Step 1: Check file and validate hash
            lines, current_content, current_hash = await self._check_file_hash(
                file_path, expected_hash, encoding
            )

            total_lines = len(lines) if lines else 0

            # Step 2: Validate patches
            validated_patches = self._validate_patches(patches, total_lines)

            # Early return for empty content deletion
            if any(not patch.contents.strip() for patch in validated_patches):
                return {
                    "result": "ok",
                    "file_hash": current_hash,
                    "hint": "For content deletion, please consider using delete_text_file_contents",
                    "suggestion": "delete",
                }

            # Step 3: Apply patches
            updated_lines, final_content, new_hash = await self._apply_patches(
                lines, validated_patches, encoding
            )

            # Step 4: Write final content
            try:
                with open(file_path, "w", encoding=encoding) as f:
                    f.write(final_content)
            except IOError as e:
                raise FileOperationError(
                    "Failed to write file",
                    code=ErrorCode.FILE_ACCESS_DENIED,
                    details={"file_path": file_path, "error": str(e)},
                )

            # Determine suggestion for alternative tools
            suggestion = None
            hint = None
            if not os.path.exists(file_path) or not current_content:
                suggestion = "append"
                hint = "For new files, please consider using append_text_file_contents"
            elif all(not p.range_hash for p in validated_patches):
                if all(p.start >= total_lines for p in validated_patches):
                    suggestion = "append"
                    hint = "For adding content at the end of file, please consider using append_text_file_contents"
                else:
                    suggestion = "insert"
                    hint = "For inserting content within file, please consider using insert_text_file_contents"

            return {
                "result": "ok",
                "file_hash": new_hash,
                "suggestion": suggestion,
                "hint": hint,
            }

        except (ValidationError, FileOperationError, ContentOperationError) as e:
            return self.create_error_response(
                str(e),
                file_hash=getattr(e, "details", {}).get("actual", None),
                file_path=file_path,
                suggestion="patch",
                hint="Please check the error details and try again",
            )
        except Exception as e:
            return self.create_error_response(
                "Unexpected error occurred",
                suggestion="patch",
                hint="Please try again or report the issue if it persists",
            )
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
                f"Error: {str(e)}",
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
