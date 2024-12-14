"""Core text editor functionality with file operation handling."""

import hashlib
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

        # Future: Add more path validation rules
        return

    def _detect_encoding(self, file_path: str) -> str:
        """
        Detect the encoding of a file using chardet.

        Args:
            file_path (str): Path to the file

        Returns:
            str: Detected encoding, always returns a valid encoding string.
                Falls back to utf-8 if detection fails.
        """
        try:
            import chardet
        except ImportError:
            return "utf-8"

        try:
            # Read the first 4KB of the file for encoding detection
            with open(file_path, "rb") as f:
                raw_data = f.read(4096)

            # chardetを使用してエンコーディングを検出
            result = chardet.detect(raw_data)

            # 検出結果がNoneの場合や信頼度が低い場合はUTF-8を使用
            if (
                not result
                or not result.get("encoding")
                or result.get("confidence", 0) < 0.7
            ):
                return "utf-8"

            # 検出されたエンコーディングを返す
            encoding = result["encoding"]
            return encoding if encoding else "utf-8"

        except IOError:
            # ファイル読み込みに失敗した場合はUTF-8を使用
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

    async def read_multiple_ranges(
        self, ranges: List[FileRanges]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Read multiple line ranges from multiple files.

        Args:
            ranges (List[FileRanges]): List of files and their line ranges to read

        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary with file paths as keys and
                lists of range contents as values. Each range content includes:
                - content: str
                - start_line: int
                - end_line: int
                - hash: str
                - total_lines: int
                - content_size: int

        Raises:
            ValueError: If file paths or line numbers are invalid
            FileNotFoundError: If any file does not exist
            IOError: If any file cannot be read
        """
        result: Dict[str, List[Dict[str, Any]]] = {}

        for file_range in ranges:
            file_path = file_range["file_path"]
            self._validate_file_path(file_path)
            result[file_path] = []

            try:
                # Detect the file encoding before reading
                encoding = self._detect_encoding(file_path)

                with open(file_path, "r", encoding=encoding) as f:
                    lines = f.readlines()
                    total_lines = len(lines)
                    file_content = "".join(lines)
                    file_hash = self.calculate_hash(file_content)
                for range_spec in file_range["ranges"]:
                    # Adjust line numbers to 0-based index
                    line_start = max(1, range_spec["start"]) - 1
                    end_value = range_spec.get("end")
                    line_end = (
                        min(total_lines, end_value)
                        if end_value is not None
                        else total_lines
                    )
                    line_end = (
                        total_lines
                        if end_value is None
                        else min(end_value, total_lines)
                    )

                    if line_start >= total_lines:
                        # Return empty content for out of bounds start line
                        result[file_path].append(
                            {
                                "content": "",
                                "start_line": line_start + 1,
                                "end_line": line_start + 1,
                                "hash": file_hash,
                                "total_lines": total_lines,
                                "content_size": 0,
                            }
                        )
                        continue
                    if line_end < line_start:
                        raise ValueError(
                            "End line must be greater than or equal to start line"
                        )

                    selected_lines = lines[line_start:line_end]
                    content = "".join(selected_lines)

                    result[file_path].append(
                        {
                            "content": content,
                            "start_line": line_start + 1,
                            "end_line": line_end,
                            "hash": file_hash,
                            "total_lines": total_lines,
                            "content_size": len(content),
                        }
                    )

            except FileNotFoundError as e:
                raise FileNotFoundError(f"File not found: {file_path}") from e
            except IOError as e:
                raise IOError(f"Error reading file: {str(e)}") from e

        return result

    async def read_file_contents(
        self, file_path: str, line_start: int = 1, line_end: Optional[int] = None
    ) -> Tuple[str, int, int, str, int, int]:
        """
        Read file contents within specified line range.

        Args:
            file_path (str): Path to the file
            line_start (int): Starting line number (1-based)
            line_end (Optional[int]): Ending line number (inclusive)

        Returns:
            Tuple[str, int, int, str, int, int]: (contents, start_line, end_line, hash, file_lines, file_size)

        Raises:
            ValueError: If file path or line numbers are invalid
            FileNotFoundError: If file does not exist
            IOError: If file cannot be read
        """
        self._validate_file_path(file_path)

        try:
            # Detect the file encoding before reading
            encoding = self._detect_encoding(file_path)

            with open(file_path, "r", encoding=encoding) as f:
                lines = f.readlines()
            file_content = "".join(lines)
            file_hash = self.calculate_hash(file_content)
            # Adjust line numbers to 0-based index
            line_start = max(1, line_start) - 1
            line_end = len(lines) if line_end is None else min(line_end, len(lines))

            if line_start >= len(lines):
                return "", line_start, line_start, file_hash, len(lines), 0
            if line_end < line_start:
                raise ValueError("End line must be greater than or equal to start line")

            selected_lines = lines[line_start:line_end]
            content = "".join(selected_lines)

            # 選択された行のオリジナルのバイトサイズを計算
            content_size = len(content.encode(encoding))

            return (
                content,
                line_start + 1,
                line_end,
                file_hash,
                len(lines),
                content_size,
            )

        except FileNotFoundError as e:
            raise FileNotFoundError(f"File not found: {file_path}") from e
        except (IOError, UnicodeDecodeError) as e:
            raise IOError(f"Error reading file: {str(e)}") from e

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

        Returns:
            Dict[str, Any]: Results of the operation containing:
                - result: "ok" or "error"
                - hash: New file hash if successful, None if error
                - reason: Error message if result is "error"

        Raises:
            ValueError: If file path is invalid or patches are invalid
            FileNotFoundError: If file does not exist
            # Check file permission
            if not os.access(file_path, os.W_OK):
                return {
                    "result": "error",
                    "reason": "Permission denied: File is not writable",
                    "hash": None,
                    "content": None,
                }

            # Read current file content and verify hash
        """
        self._validate_file_path(file_path)
        try:
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

                # Validate line numbers
                if line_start < 1:
                    raise ValueError("Line numbers must be positive")
                if line_end is not None and line_end < line_start:
                    raise ValueError(
                        "End line must be greater than or equal to start line"
                    )

                # Convert to 0-based indexing
                line_start -= 1
                if line_end is not None:
                    line_end -= 1
                else:
                    line_end = len(lines) - 1

                # Ensure we don't exceed file bounds
                line_end = min(line_end, len(lines) - 1)

                # Replace lines
                new_content = patch["contents"]
                if not new_content.endswith("\n"):
                    new_content += "\n"
                new_lines = new_content.splitlines(keepends=True)

                lines[line_start : line_end + 1] = new_lines

            # Write back to file
            encoding = self._detect_encoding(file_path)
            new_content = "".join(lines)
            with open(file_path, "w", encoding=encoding) as f:
                f.write(new_content)

            # Calculate new hash
            new_hash = self.calculate_hash(new_content)

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
                "content": None,
            }
        except (IOError, UnicodeError, PermissionError) as e:
            return {
                "result": "error",
                "reason": f"Error editing file: {str(e)}",
                "hash": None,
                "content": None,
            }
        except Exception as e:
            return {
                "result": "error",
                "reason": str(e),
                "hash": None,
                "content": None,
            }
