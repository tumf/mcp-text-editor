"""Core service logic for the MCP Text Editor Server."""

import hashlib
from typing import Dict, List, Optional, Tuple

from .models import (
    DeleteTextFileContentsRequest,
    EditFileOperation,
    EditPatch,
    EditResult,
    FileRange,
)


class TextEditorService:
    """Service class for text file operations."""

    @staticmethod
    def calculate_hash(content: str) -> str:
        """Calculate SHA-256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def read_file_contents(
        file_path: str, start: int = 1, end: Optional[int] = None
    ) -> Tuple[str, int, int]:
        """Read file contents within specified line range."""
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Adjust line numbers to 0-based index
        start = max(1, start) - 1
        end = len(lines) if end is None else min(end, len(lines))

        selected_lines = lines[start:end]
        content = "".join(selected_lines)

        return content, start + 1, end

    @staticmethod
    def validate_patches(patches: List[EditPatch], total_lines: int) -> bool:
        """Validate patches for overlaps and bounds."""
        # Sort patches by start
        sorted_patches = sorted(patches, key=lambda x: x.start)

        prev_end = 0
        for patch in sorted_patches:
            if patch.start <= prev_end:
                return False
            patch_end = patch.end or total_lines
            if patch_end > total_lines:
                return False
            prev_end = patch_end

        return True

    def edit_file_contents(
        self, file_path: str, operation: EditFileOperation
    ) -> Dict[str, EditResult]:
        """Edit file contents with conflict detection."""
        current_hash = None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                current_content = f.read()
                current_hash = self.calculate_hash(current_content)

            # Check for conflicts
            if current_hash != operation.hash:
                return {
                    file_path: EditResult(
                        result="error",
                        reason="Content hash mismatch",
                        hash=current_hash,
                    )
                }

            # Split content into lines
            lines = current_content.splitlines(keepends=True)

            # Validate patches
            if not self.validate_patches(operation.patches, len(lines)):
                return {
                    file_path: EditResult(
                        result="error",
                        reason="Invalid patch ranges",
                        hash=current_hash,
                    )
                }

            # Apply patches
            new_lines = lines.copy()
            for patch in operation.patches:
                start_idx = patch.start - 1
                end_idx = patch.end if patch.end else len(lines)
                patch_lines = patch.contents.splitlines(keepends=True)
                new_lines[start_idx:end_idx] = patch_lines

            # Write new content
            new_content = "".join(new_lines)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            new_hash = self.calculate_hash(new_content)
            return {
                file_path: EditResult(
                    result="ok",
                    hash=new_hash,
                    reason=None,
                )
            }

        except FileNotFoundError as e:
            return {
                file_path: EditResult(
                    result="error",
                    reason=str(e),
                    hash=None,
                )
            }
        except Exception as e:
            return {
                file_path: EditResult(
                    result="error",
                    reason=str(e),
                    hash=None,  # Don't return the current hash on error
                )
            }

    def delete_text_file_contents(
        self,
        request: DeleteTextFileContentsRequest,
    ) -> Dict[str, EditResult]:
        """Delete specified ranges from a text file with conflict detection."""
        current_hash = None
        try:
            with open(request.file_path, "r", encoding=request.encoding) as f:
                current_content = f.read()
                current_hash = self.calculate_hash(current_content)

            # Check for conflicts
            if current_hash != request.file_hash:
                return {
                    request.file_path: EditResult(
                        result="error",
                        reason="Content hash mismatch",
                        hash=current_hash,
                    )
                }

            # Split content into lines
            lines = current_content.splitlines(keepends=True)

            # Validate ranges
            if not request.ranges:  # Check for empty ranges list
                return {
                    request.file_path: EditResult(
                        result="error",
                        reason="Missing required argument: ranges",
                        hash=current_hash,
                    )
                }

            if not self.validate_ranges(request.ranges, len(lines)):
                return {
                    request.file_path: EditResult(
                        result="error",
                        reason="Invalid ranges",
                        hash=current_hash,
                    )
                }

            # Delete ranges in reverse order to handle line number shifts
            new_lines = lines.copy()
            sorted_ranges = sorted(request.ranges, key=lambda x: x.start, reverse=True)
            for range_ in sorted_ranges:
                start_idx = range_.start - 1
                end_idx = range_.end if range_.end else len(lines)
                target_content = "".join(lines[start_idx:end_idx])
                target_hash = self.calculate_hash(target_content)
                if target_hash != range_.range_hash:
                    return {
                        request.file_path: EditResult(
                            result="error",
                            reason=f"Content hash mismatch for range {range_.start}-{range_.end}",
                            hash=current_hash,
                        )
                    }
                del new_lines[start_idx:end_idx]

            # Write new content
            new_content = "".join(new_lines)
            with open(request.file_path, "w", encoding=request.encoding) as f:
                f.write(new_content)

            new_hash = self.calculate_hash(new_content)
            return {
                request.file_path: EditResult(
                    result="ok",
                    hash=new_hash,
                    reason=None,
                )
            }

        except FileNotFoundError as e:
            return {
                request.file_path: EditResult(
                    result="error",
                    reason=str(e),
                    hash=None,
                )
            }
        except Exception as e:
            return {
                request.file_path: EditResult(
                    result="error",
                    reason=f"Error deleting contents: {str(e)}",
                    hash=None,
                )
            }

    @staticmethod
    def validate_ranges(ranges: List[FileRange], total_lines: int) -> bool:
        """Validate ranges for overlaps and bounds."""
        # Sort ranges by start line
        sorted_ranges = sorted(ranges, key=lambda x: x.start)

        prev_end = 0
        for range_ in sorted_ranges:
            if range_.start <= prev_end:
                return False  # Overlapping ranges
            if range_.start < 1:
                return False  # Invalid start line
            range_end = range_.end or total_lines
            if range_end > total_lines:
                return False  # Exceeding file length
            if range_.end is not None and range_.end < range_.start:
                return False  # End before start
            prev_end = range_end

        return True
