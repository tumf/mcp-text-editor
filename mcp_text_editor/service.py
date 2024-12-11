"""Core service logic for the MCP Text Editor Server."""

import hashlib
from typing import Dict, List, Optional, Tuple

from .models import EditFileOperation, EditPatch, EditResult


class TextEditorService:
    """Service class for text file operations."""

    @staticmethod
    def calculate_hash(content: str) -> str:
        """Calculate SHA-256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def read_file_contents(
        file_path: str, line_start: int = 1, line_end: Optional[int] = None
    ) -> Tuple[str, int, int]:
        """Read file contents within specified line range."""
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Adjust line numbers to 0-based index
        line_start = max(1, line_start) - 1
        line_end = len(lines) if line_end is None else min(line_end, len(lines))

        selected_lines = lines[line_start:line_end]
        content = "".join(selected_lines)

        return content, line_start + 1, line_end

    @staticmethod
    def validate_patches(patches: List[EditPatch], total_lines: int) -> bool:
        """Validate patches for overlaps and bounds."""
        # Sort patches by line_start
        sorted_patches = sorted(patches, key=lambda x: x.line_start)

        prev_end = 0
        for patch in sorted_patches:
            if patch.line_start <= prev_end:
                return False
            patch_end = patch.line_end or total_lines
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
                        content=current_content,
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
                        content=None,
                    )
                }

            # Apply patches
            new_lines = lines.copy()
            for patch in operation.patches:
                start_idx = patch.line_start - 1
                end_idx = patch.line_end if patch.line_end else len(lines)
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
                    content=None,
                    reason=None,
                )
            }

        except FileNotFoundError as e:
            return {
                file_path: EditResult(
                    result="error",
                    reason=str(e),
                    hash=None,
                    content=None,
                )
            }
        except Exception as e:
            return {
                file_path: EditResult(
                    result="error",
                    reason=str(e),
                    hash=current_hash,
                    content=None,
                )
            }
