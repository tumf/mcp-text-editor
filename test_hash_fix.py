#!/usr/bin/env python3
"""Test the hash bug fix."""

import pytest

from mcp_text_editor.text_editor import TextEditor


@pytest.mark.asyncio
async def test_hash_consistency():
    """Test that hash is consistent between single and multi-line reads."""
    import os
    import tempfile

    editor = TextEditor()
    content = "line1\nline2\nline3\nline4\n"

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write(content)
        test_file = f.name

    try:
        # Test 1: Read lines 1-3
        ranges = [{"file_path": test_file, "ranges": [{"start": 1, "end": 3}]}]

        result = await editor.read_multiple_ranges(ranges)
        actual_content = result[test_file]["ranges"][0]["content"]
        actual_hash = result[test_file]["ranges"][0]["range_hash"]

        expected_content = "line1\nline2\nline3\n"
        expected_hash = editor.calculate_hash(expected_content)

        assert (
            actual_content == expected_content
        ), f"Content mismatch: {repr(actual_content)} != {repr(expected_content)}"
        assert (
            actual_hash == expected_hash
        ), f"Hash mismatch: {actual_hash} != {expected_hash}"

        # Test 2: end field should be correct
        assert result[test_file]["ranges"][0]["end"] == 3

    finally:
        os.unlink(test_file)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_hash_consistency())
