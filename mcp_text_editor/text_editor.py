"""Core text editor functionality with file operation handling."""

import hashlib
from typing import Any, Dict, List, Optional, Tuple


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

    async def read_file_contents(
        self, file_path: str, line_start: int = 1, line_end: Optional[int] = None
    ) -> Tuple[str, int, int, str]:
        """
        Read file contents within specified line range.

        Args:
            file_path (str): Path to the file
            line_start (int): Starting line number (1-based)
            line_end (Optional[int]): Ending line number (inclusive)

        Returns:
            Tuple[str, int, int, str]: (contents, start_line, end_line, hash)

        Raises:
            ValueError: If file path or line numbers are invalid
            FileNotFoundError: If file does not exist
            IOError: If file cannot be read
        """
        self._validate_file_path(file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Adjust line numbers to 0-based index
            line_start = max(1, line_start) - 1
            line_end = len(lines) if line_end is None else min(line_end, len(lines))

            if line_start >= len(lines):
                raise ValueError("Start line exceeds file length")
            if line_end < line_start:
                raise ValueError("End line must be greater than or equal to start line")

            selected_lines = lines[line_start:line_end]
            content = "".join(selected_lines)

            return content, line_start + 1, line_end, self.calculate_hash(content)

        except FileNotFoundError as e:
            raise FileNotFoundError(f"File not found: {file_path}") from e
        except IOError as e:
            raise IOError(f"Error reading file: {str(e)}") from e

    def _validate_patches(
        self, patches: List[Dict[str, Any]], total_lines: int
    ) -> None:
        """
        Validate patches for overlaps and bounds.

        Args:
            patches (List[Dict]): List of patch operations
            total_lines (int): Total number of lines in file

        Raises:
            ValueError: If patches are invalid
        """
        # Sort patches by line_start
        sorted_patches = sorted(patches, key=lambda x: x.get("line_start", 1))

        prev_end = 0
        for patch in sorted_patches:
            start = patch.get("line_start", 1)
            end = patch.get("line_end", total_lines)

            if start <= prev_end:
                raise ValueError("Overlapping patches are not allowed")
            if end > total_lines:
                raise ValueError(f"Line number {end} exceeds file length")
            if end < start:
                raise ValueError("End line must be greater than or equal to start line")

            prev_end = end

    async def edit_file_contents(
        self, file_path: str, content_hash: str, patches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Edit file contents with conflict detection.
        Applies patches from bottom to top to handle line number shifts correctly.

        Args:
            file_path (str): Path to the file
            content_hash (str): Expected hash of current content
            patches (List[Dict]): List of patch operations

        Returns:
            Dict: Operation result with status and details

        Raises:
            ValueError: If parameters are invalid
            FileNotFoundError: If file does not exist
            IOError: If file cannot be read or written
        """
        self._validate_file_path(file_path)

        try:
            # Read current content and verify hash
            with open(file_path, "r", encoding="utf-8") as f:
                current_content = f.read()
                current_hash = self.calculate_hash(current_content)

            if current_hash != content_hash:
                return {
                    "result": "error",
                    "reason": "Content hash mismatch - file was modified",
                    "hash": current_hash,
                    "content": current_content,
                }

            lines = current_content.splitlines(keepends=True)
            total_lines = len(lines)

            # Validate patches
            try:
                self._validate_patches(patches, total_lines)
            except ValueError as e:
                return {
                    "result": "error",
                    "reason": str(e),
                    "hash": current_hash,
                }

            # Sort patches by line number in reverse order (bottom to top)
            sorted_patches = sorted(
                patches, key=lambda x: x.get("line_start", 1), reverse=True
            )

            # Apply patches from bottom to top
            new_lines = lines.copy()
            for patch in sorted_patches:
                start = patch.get("line_start", 1) - 1
                end = patch.get("line_end", total_lines)
                patch_content = patch["contents"]

                # Ensure patch content ends with newline if original content did
                if len(lines) > 0 and lines[-1].endswith("\n"):
                    if not patch_content.endswith("\n"):
                        patch_content += "\n"

                patch_lines = patch_content.splitlines(keepends=True)
                new_lines[start:end] = patch_lines

            # Write new content
            new_content = "".join(new_lines)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return {
                "result": "ok",
                "hash": self.calculate_hash(new_content),
            }

        except FileNotFoundError:
            return {
                "result": "error",
                "reason": f"File not found: {file_path}",
                "hash": None,  # ファイルが存在しない場合はハッシュも提供できない
            }
        except (IOError, Exception) as e:
            return {
                "result": "error",
                "reason": str(e),
                "hash": current_hash if "current_hash" in locals() else None,
            }
