import os
import pytest
from unittest.mock import patch, MagicMock

from mcp_text_editor.text_editor import TextEditor


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    file_path = tmp_path / "test.txt"
    with open(file_path, "w") as f:
        f.write("Original content\n")
    return str(file_path)


@pytest.mark.asyncio
async def test_validator_command_runs_after_edit(temp_file):
    """Test that validator command runs after editing a file."""
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Validation passed"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        editor = TextEditor(validator_command="test-validator")

        with open(temp_file, "r") as f:
            content = f.read()
        file_hash = editor.calculate_hash(content)
        result = await editor.edit_file_contents(
            file_path=temp_file,
            expected_file_hash=file_hash,  # Use actual file hash
            patches=[
                {
                    "start": 1,
                    "end": 1,
                    "contents": "Updated content\n",
                    "range_hash": editor.calculate_hash("Original content\n"),
                }
            ],
        )

        mock_run.assert_called_once_with(
            ["test-validator", temp_file], capture_output=True, text=True, check=False
        )

        assert "validator_result" in result
        assert result["validator_result"]["exit_code"] == 0
        assert result["validator_result"]["stdout"] == "Validation passed"
