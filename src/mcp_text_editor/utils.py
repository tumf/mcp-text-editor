"""Security utilities for the MCP Text Editor."""

import fcntl
import hmac
import os
import pathlib
from contextlib import contextmanager
from typing import Generator


def normalize_and_validate_path(file_path: str, base_dir: str = ".") -> str:
    """
    Validate and normalize file path to prevent directory traversal attacks.
    
    Args:
        file_path (str): The file path to validate
        base_dir (str): Base directory to restrict access (default: current directory)
        
    Returns:
        str: Normalized absolute path
        
    Raises:
        ValueError: If path is invalid, contains directory traversal, or is outside base directory
    """
    if not file_path:
        raise ValueError("File path cannot be empty")
    
    # Convert to Path objects for safe manipulation
    base_path = pathlib.Path(base_dir).resolve()
    
    # Handle different path formats
    if file_path.startswith('/'):
        # Absolute path - reject for security
        raise ValueError("Absolute paths are not allowed")
    
    # Check for directory traversal patterns
    if '..' in file_path or '~' in file_path:
        raise ValueError("Directory traversal patterns (.., ~) are not allowed")
    
    # Create path relative to base directory
    full_path = base_path / file_path
    
    # Resolve to get the canonical path (handles symlinks, . and ..)
    try:
        resolved_path = full_path.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {e}")
    
    # Ensure the resolved path is within the base directory
    try:
        resolved_path.relative_to(base_path)
    except ValueError:
        raise ValueError("Path resolves outside of allowed base directory")
    
    return str(resolved_path)


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
    
    # Convert to bytes for secure comparison
    try:
        hash1_bytes = hash1.encode('utf-8')
        hash2_bytes = hash2.encode('utf-8')
        return hmac.compare_digest(hash1_bytes, hash2_bytes)
    except (UnicodeError, AttributeError):
        # Fallback for non-string inputs, though this shouldn't happen
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
    # Determine lock type based on mode
    if 'r' in mode and '+' not in mode and 'w' not in mode and 'a' not in mode:
        # Read-only mode gets shared lock
        lock_type = fcntl.LOCK_SH
    else:
        # Write modes get exclusive lock
        lock_type = fcntl.LOCK_EX
    
    file_obj = None
    try:
        file_obj = open(file_path, mode, encoding='utf-8')
        # Acquire lock
        fcntl.flock(file_obj.fileno(), lock_type)
        yield file_obj
    finally:
        if file_obj:
            try:
                # Release lock (this happens automatically on close, but explicit is better)
                fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)
            except (OSError, ValueError):
                # File may already be closed or lock already released
                pass
            file_obj.close()