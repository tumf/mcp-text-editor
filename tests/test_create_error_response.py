"""Tests for error response creation and hint/suggestion functionality."""

import pytest

from mcp_text_editor.text_editor import TextEditor


@pytest.fixture
def editor():
    """Create TextEditor instance."""
    return TextEditor()


def test_create_error_response_basic(editor):
    """Test basic error response without hint/suggestion."""
    response = editor.create_error_response("Test error")
    assert response["result"] == "error"
    assert response["reason"] == "Test error"
    assert response["file_hash"] is None
    assert "hint" not in response
    assert "suggestion" not in response


def test_create_error_response_with_hint_suggestion(editor):
    """Test error response with hint and suggestion."""
    response = editor.create_error_response(
        "Test error", suggestion="append", hint="Please use append_text_file_contents"
    )
    assert response["result"] == "error"
    assert response["reason"] == "Test error"
    assert response["suggestion"] == "append"
    assert response["hint"] == "Please use append_text_file_contents"


def test_create_error_response_with_file_path(editor):
    """Test error response with file path."""
    response = editor.create_error_response(
        "Test error",
        file_path="/test/file.txt",
        suggestion="patch",
        hint="Please try again",
    )
    assert "/test/file.txt" in response
    assert response["/test/file.txt"]["result"] == "error"
    assert response["/test/file.txt"]["reason"] == "Test error"
    assert response["/test/file.txt"]["suggestion"] == "patch"
    assert response["/test/file.txt"]["hint"] == "Please try again"


def test_create_error_response_with_hash(editor):
    """Test error response with content hash."""
    test_hash = "test_hash_value"
    response = editor.create_error_response("Test error", content_hash=test_hash)
    assert response["result"] == "error"
    assert response["reason"] == "Test error"
    assert response["file_hash"] == test_hash
