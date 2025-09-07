"""Security utilities for the MCP Text Editor."""

import fcntl
import hmac
import os
import pathlib
from contextlib import contextmanager
from typing import Generator, Optional


def _contains_traversal_patterns(s: str) -> bool:
    """Detect common directory traversal or path injection patterns."""
    if not isinstance(s, str):
        return False
    lowered = s.lower()
    # raw .. as path component or encoded forms
    if ".." in s:
        return True
    if "~" in s:
        return True
    if "%2f" in lowered or "%2e" in lowered:
        return True
    # suspicious sequences like "....//" or repeated dots
    if "...." in s:
        return True
    return False


def normalize_and_validate_path(file_path: str, base_dir: Optional[str] = None) -> str:
    """
    Validate and normalize file path to prevent directory traversal attacks.

    If base_dir is provided, the provided file_path is interpreted relative to base_dir
    and must not be an absolute path. If base_dir is None, absolute paths are allowed
    but obvious traversal patterns are rejected.

    Args:
        file_path (str): The file path to validate
        base_dir (Optional[str]): Base directory to restrict access (default: None)
    Returns:
        str: Normalized absolute path
    Raises:
        ValueError: If path is invalid, contains dangerous patterns, or is outside base directory
    """
    if not file_path:
        raise ValueError("File path cannot be empty")
    # Reject null byte injection early
    if "\x00" in file_path:
        raise ValueError("Invalid path: null byte detected")
    # If base_dir is provided, be strict: no absolute paths, no traversal/token tricks
    if base_dir is not None:
        # Absolute paths not allowed when a base directory is enforced
        if file_path.startswith(os.sep):
            raise ValueError("Absolute paths are not allowed")
        # Reject obvious traversal patterns
        if _contains_traversal_patterns(file_path):
            raise ValueError(
                "Directory traversal patterns (.., ~, encoded) are not allowed"
            )
        base_path = pathlib.Path(base_dir).resolve()
        try:
            candidate = (base_path / file_path).resolve()
        except (OSError, RuntimeError) as e:
            raise ValueError(f"Invalid path: {e}") from e
        # Ensure the resolved path is within the base directory
        try:
            candidate.relative_to(base_path)
        except ValueError as e:
            raise ValueError("Path resolves outside of allowed base directory") from e
        return str(candidate)
    # No base_dir: allow absolute or relative paths, but still check for obvious traversal attempts
    if _contains_traversal_patterns(file_path):
        raise ValueError("Path traversal not allowed")
    try:
        resolved = pathlib.Path(file_path).resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {e}") from e
    return str(resolved)


def secure_compare_hash(hash1: str | None, hash2: str | None) -> bool:
    """
    Securely compare two hash strings using hmac.compare_digest to prevent timing attacks.
    Args:
        hash1 (str | None): First hash string
        hash2 (str | None): Second hash string
    Returns:
        bool: True if hashes match, False otherwise
    """
    if hash1 is None or hash2 is None:
        return hash1 == hash2
    try:
        hash1_bytes = hash1.encode("utf-8")
        hash2_bytes = hash2.encode("utf-8")
        return hmac.compare_digest(hash1_bytes, hash2_bytes)
    except (UnicodeError, TypeError, AttributeError):
        return hash1 == hash2


@contextmanager
def locked_file(file_path: str, mode: str = "r+") -> Generator:
    """
    Context manager for file operations with exclusive/shared locking.
    Args:
        file_path (str): Path to the file
        mode (str): File open mode ('r' for shared lock, 'w'/'a'/'r+' for exclusive lock)
    Yields:
        file object: The opened and locked file
    Raises:
        OSError: If file locking fails
        IOError: If file operations fail
    """
    if "r" in mode and "+" not in mode and "w" not in mode and "a" not in mode:
        lock_type = fcntl.LOCK_SH
    else:
        lock_type = fcntl.LOCK_EX
    file_obj = None
    try:
        # When opening for write/create, ensure parent directory exists
        parent = os.path.dirname(file_path)
        if parent and ("w" in mode or "a" in mode or "+" in mode):
            os.makedirs(parent, exist_ok=True)
        # Prevent opening a directory for reading
        if (
            os.path.isdir(file_path)
            and "r" in mode
            and ("w" not in mode and "+" not in mode)
        ):
            raise ValueError("Invalid path: path points to a directory")
        file_obj = open(file_path, mode, encoding="utf-8")
        fcntl.flock(file_obj.fileno(), lock_type)
        yield file_obj
    finally:
        if file_obj:
            try:
                fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)
            except (OSError, ValueError):
                pass
            try:
                file_obj.close()
            except Exception:
                pass
