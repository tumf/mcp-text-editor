"""Tests for path validation security utilities."""

import os
import tempfile
from pathlib import Path

import pytest

from mcp_text_editor.utils import normalize_and_validate_path


class TestPathValidation:
    """Test path validation security features."""

    def test_valid_relative_path(self):
        """Test that valid relative paths are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = normalize_and_validate_path("test.txt", tmpdir)
            expected = str(Path(tmpdir).resolve() / "test.txt")
            assert result == expected

    def test_valid_nested_relative_path(self):
        """Test that valid nested relative paths are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = normalize_and_validate_path("subdir/test.txt", tmpdir)
            expected = str(Path(tmpdir).resolve() / "subdir" / "test.txt")
            assert result == expected

    def test_reject_absolute_path(self):
        """Test that absolute paths are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Absolute paths are not allowed"):
                normalize_and_validate_path("/etc/passwd", tmpdir)

    def test_reject_directory_traversal_dotdot(self):
        """Test that directory traversal with .. is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Directory traversal patterns"):
                normalize_and_validate_path("../etc/passwd", tmpdir)

            with pytest.raises(ValueError, match="Directory traversal patterns"):
                normalize_and_validate_path("subdir/../../../etc/passwd", tmpdir)

    def test_reject_home_directory_expansion(self):
        """Test that home directory expansion ~ is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Directory traversal patterns"):
                normalize_and_validate_path("~/test.txt", tmpdir)

    def test_reject_empty_path(self):
        """Test that empty paths are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="File path cannot be empty"):
                normalize_and_validate_path("", tmpdir)

    def test_reject_path_outside_base_directory(self):
        """Test that paths resolving outside base directory are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a symlink that points outside the base directory
            outside_file = "/tmp/outside.txt"
            try:
                with open(outside_file, "w") as f:
                    f.write("test")

                symlink_path = Path(tmpdir) / "symlink.txt"
                symlink_path.symlink_to(outside_file)

                with pytest.raises(
                    ValueError, match="Path resolves outside of allowed base directory"
                ):
                    normalize_and_validate_path("symlink.txt", tmpdir)
            finally:
                # Clean up
                if os.path.exists(outside_file):
                    os.unlink(outside_file)

    def test_path_with_current_directory_refs(self):
        """Test paths with . references are normalized correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = normalize_and_validate_path("./test.txt", tmpdir)
            expected = str(Path(tmpdir).resolve() / "test.txt")
            assert result == expected

    def test_windows_style_paths_rejected(self):
        """Test that Windows-style paths with backslashes are handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # This should work as it's just a filename with backslashes
            result = normalize_and_validate_path("test\\file.txt", tmpdir)
            expected = str(Path(tmpdir).resolve() / "test\\file.txt")
            assert result == expected

    def test_path_injection_attempts(self):
        """Test various path injection attempts are blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            malicious_paths = [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\config\\sam",
                "..%2F..%2F..%2Fetc%2Fpasswd",  # URL encoded
                "....//....//....//etc/passwd",  # Double dots
                "..\\..\\..",
                "~/../../../etc/passwd",
                "/..",
                "/./../../etc/passwd",
            ]

            for path in malicious_paths:
                with pytest.raises(ValueError):
                    normalize_and_validate_path(path, tmpdir)

    def test_null_byte_injection(self):
        """Test that null byte injection is handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises((ValueError, OSError)):
                normalize_and_validate_path("test.txt\x00../../etc/passwd", tmpdir)

    def test_base_directory_normalization(self):
        """Test that base directory is properly normalized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use a base directory with .. in it
            weird_base = os.path.join(tmpdir, "subdir", "..", "actual")
            os.makedirs(os.path.join(tmpdir, "actual"), exist_ok=True)

            result = normalize_and_validate_path("test.txt", weird_base)
            expected = str(Path(tmpdir).resolve() / "actual" / "test.txt")
            assert result == expected
