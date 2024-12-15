"""Core text editor functionality with file operation handling."""

import hashlib
import os
from typing import Any, Dict, List, Optional, Tuple, TypedDict


class Range(TypedDict):
    """Represents a line range in a file."""

    start: int
    end: Optional[int]


class FileRanges(TypedDict):
    """Represents a file and its line ranges."""

    file_path: str
    ranges: List[Range]


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

    def _validate_file_path(self, file_path: str) -> None:
        """
        Validate if file path is allowed and secure.

        Args:
            file_path (str): Path to validate

        Raises:
            ValueError: If path is not allowed or contains dangerous patterns
        """
        # Check for dangerous patterns
        if ".." in file_path:
            raise ValueError("Path traversal not allowed")

    def _detect_encoding(self, file_path: str) -> str:
        """
        Detect file encoding with Shift-JIS prioritized.

        Args:
            file_path (str): Path to the file

        Returns:
            str: Detected encoding, falls back to utf-8 if detection fails.
        """

        def try_decode(data: bytes, encoding: str) -> bool:
            """Try to decode data with the given encoding."""
            try:
                data.decode(encoding)
                return True
            except UnicodeDecodeError:
                return False

        # Read file content for encoding detection
        try:
            with open(file_path, "rb") as f:
                raw_data = f.read()

                # Try encodings in order of priority
                if try_decode(raw_data, "shift_jis"):
                    return "shift_jis"
                if try_decode(raw_data, "utf-8"):
                    return "utf-8"

                # As a last resort, use chardet
                try:
                    import chardet

                    result = chardet.detect(raw_data)
                    encoding = result.get("encoding") or ""
                    encoding = encoding.lower()

                    if encoding:
                        # Map encoding aliases
                        if encoding in [
                            "shift_jis",
                            "shift-jis",
                            "shiftjis",
                            "sjis",
                            "csshiftjis",
                        ]:
                            return "shift_jis"
                        if encoding in ["ascii"]:
                            return "utf-8"
                        # Try detected encoding
                        if try_decode(raw_data, encoding):
                            return encoding
                except ImportError:
                    pass

                # Fall back to UTF-8
                return "utf-8"

        except (IOError, OSError, UnicodeDecodeError):
            return "utf-8"

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

    async def _read_file(self, file_path: str) -> Tuple[List[str], str, int]:
        """Read file and return lines, content, and total lines."""
        self._validate_file_path(file_path)
        encoding = self._detect_encoding(file_path)
        try:
            with open(file_path, "r", encoding=encoding) as f:
                lines = f.readlines()
            file_content = "".join(lines)
            return lines, file_content, len(lines)
        except FileNotFoundError as err:
            raise FileNotFoundError(f"File not found: {file_path}") from err

    async def read_multiple_ranges(
        self, ranges: List[FileRanges]
    ) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}

        for file_range in ranges:
            file_path = file_range["file_path"]
            lines, file_content, total_lines = await self._read_file(file_path)
            file_hash = self.calculate_hash(file_content)
            result[file_path] = {"ranges": [], "file_hash": file_hash}

            for range_spec in file_range["ranges"]:
                line_start = max(1, range_spec["start"]) - 1
                end_value = range_spec.get("end")
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
        self, file_path: str, line_start: int = 1, line_end: Optional[int] = None
    ) -> Tuple[str, int, int, str, int, int]:
        lines, file_content, total_lines = await self._read_file(file_path)
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
        content_size = len(content.encode(self._detect_encoding(file_path)))

        return (
            content,
            line_start + 1,
            line_end,
            content_hash,
            total_lines,
            content_size,
        )

    async def edit_file_contents(
        self, file_path: str, expected_hash: str, patches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Edit file contents with hash-based conflict detection and multiple patches.

        Args:
            file_path (str): Path to the file to edit
            expected_hash (str): Expected hash of the file before editing
            patches (List[Dict[str, Any]]): List of patches to apply, each containing:
                - line_start (int): Starting line number (1-based)
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
                if expected_hash != "":  # Only allow empty hash for new files
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
                # Initialize empty state for new file creation
                current_content = ""
                current_hash = ""
                lines = []
                encoding = "utf-8"
            else:
                # Read current file content and verify hash
                current_content, _, _, current_hash, total_lines, _ = (
                    await self.read_file_contents(file_path)
                )

                if current_hash != expected_hash:
                    return {
                        "result": "error",
                        "reason": "Hash mismatch - file has been modified",
                        "hash": None,
                        "content": current_content,
                    }

                # Convert content to lines for easier manipulation
                lines = current_content.splitlines(keepends=True)

            # Sort patches from bottom to top to avoid line number shifts
            sorted_patches = sorted(
                patches,
                key=lambda x: (
                    -(x.get("line_start", 1)),
                    -(x.get("line_end", x.get("line_start", 1))),
                ),
            )

            # Check for overlapping patches
            for i in range(len(sorted_patches)):
                for j in range(i + 1, len(sorted_patches)):
                    patch1 = sorted_patches[i]
                    patch2 = sorted_patches[j]
                    start1 = patch1.get("line_start", 1)
                    end1 = patch1.get("line_end", start1)
                    start2 = patch2.get("line_start", 1)
                    end2 = patch2.get("line_end", start2)

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
                line_start = patch.get("line_start", 1)
                line_end = patch.get("line_end", line_start)
                expected_range_hash = patch.get("range_hash")
                is_insertion = line_end < line_start

                # Skip range_hash for new files and insertions
                if not os.path.exists(file_path) or is_insertion:
                    expected_range_hash = self.calculate_hash("")
                # For existing files and non-insertions, range_hash is required
                elif expected_range_hash is None:
                    return {
                        "result": "error",
                        "reason": "range_hash is required for each patch (except for new files and append operations)",
                        "hash": None,
                        "content": current_content,
                    }

                # Handle insertion or replacement
                if is_insertion:
                    target_content = ""  # For insertion, we verify empty content

                # Convert to 0-based indexing
                line_start -= 1
                if not is_insertion:
                    if line_end is not None:
                        line_end -= 1
                    else:
                        line_end = len(lines) - 1

                    # Ensure we don't exceed file bounds for replacements
                    line_end = min(line_end, len(lines) - 1)

                    # Calculate target content for hash verification
                    target_lines = lines[line_start : line_end + 1]
                    target_content = "".join(target_lines)

                # Calculate actual range hash and verify only for non-insertions
                actual_range_hash = self.calculate_hash(target_content)
                if not is_insertion and actual_range_hash != expected_range_hash:
                    return {
                        "result": "error",
                        "reason": f"Range hash mismatch for lines {line_start + 1}-{line_end + 1}",
                        "hash": None,
                        "content": current_content,
                    }

                # Replace lines or insert content
                new_content = patch["contents"]
                if not new_content.endswith("\n"):
                    new_content += "\n"
                new_lines = new_content.splitlines(keepends=True)
                if is_insertion:
                    # For insertion, we insert at line_start
                    lines[line_start:line_start] = new_lines
                else:
                    # For replacement, we replace the range
                    lines[line_start : line_end + 1] = new_lines

            # Write the final content back to file
            final_content = "".join(lines)
            encoding = (
                "utf-8"
                if not os.path.exists(file_path)
                else self._detect_encoding(file_path)
            )
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
                "reason": str(e),
                "file_hash": None,
                "content": None,
            }
