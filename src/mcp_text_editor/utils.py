"""Security utilities for the MCP Text Editor."""
import fcntl
import hmac
import os
import pathlib
from contextlib import contextmanager
from typing import Generator, Optional

def normalize_and_validate_path(file_path: str, base_dir: Optional[str] = None) -> str:
    """
    Validate and normalize file path to prevent directory traversal attacks.

    If base_dir is provided, the resolved path must be inside base_dir. If base_dir
    is None, absolute and relative paths are allowed and will be resolved normally.

    Args:
        file_path (str): The file path to validate
        base_dir (Optional[str]): Base directory to restrict access (default: None - allow any resolved path)
    Returns:
        str: Normalized absolute path
    Raises:
        ValueError: If path is invalid, contains directory traversal, or is outside base directory
    """
    if not file_path:
        raise ValueError("File path cannot be empty")
    # Reject obvious user home shorthand to avoid ambiguity
    if file_path.startswith('~'):
        raise ValueError("Home directory expansion is not allowed")
    try:
        # If provided path is relative and base_dir is given, interpret it relative to base_dir
        if base_dir:
            base_path = pathlib.Path(base_dir).resolve()
            candidate = (base_path / file_path).resolve()
            # Ensure the resolved path is within the base directory
            try:
                candidate.relative_to(base_path)
            except ValueError:
                raise ValueError("Path resolves outside of allowed base directory")
            return str(candidate)
        else:
            # No base_dir restriction: resolve the path as-is (absolute or relative)
            resolved = pathlib.Path(file_path).resolve()
            return str(resolved)
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {e}") from e

def secure_compare_hash(hash1: str, hash2: str) -> bool:
    """
    Securely compare two hash strings using hmac.compare_digest to prevent timing attacks.
    Args:
        hash1 (str): First hash string
        hash2 (str): Second hash string
    Returns:
        bool: True if hashes match, False otherwise
    """
    if hash1 is None or hash2 is None:
        return hash1 == hash2
    try:
        hash1_bytes = hash1.encode('utf-8') if isinstance(hash1, str) else bytes(hash1)
        hash2_bytes = hash2.encode('utf-8') if isinstance(hash2, str) else bytes(hash2)
        return hmac.compare_digest(hash1_bytes, hash2_bytes)
    except (UnicodeError, TypeError, AttributeError):
        return hash1 == hash2

@contextmanager
def locked_file(file_path: str, mode: str = 'r+') -> Generator:
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
    if 'r' in mode and '+' not in mode and 'w' not in mode and 'a' not in mode:
        lock_type = fcntl.LOCK_SH
    else:
        lock_type = fcntl.LOCK_EX
    file_obj = None
    try:
        # Ensure parent directory exists when opening for writing
        parent = os.path.dirname(file_path)
        if parent and ('w' in mode or 'a' in mode or '+' in mode):
            os.makedirs(parent, exist_ok=True)
        file_obj = open(file_path, mode, encoding='utf-8')
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
