"""Base handler for MCP Text Editor."""

from functools import wraps
from typing import Any, Dict, Sequence, TypeVar

from mcp.types import TextContent, Tool

from ..errors import MCPError, InternalError, ValidationError
from ..text_editor import TextEditor

T = TypeVar("T")


def handle_errors(func):
    """Decorator to handle errors in handler methods."""

    @wraps(func)
    async def wrapper(*args, **kwargs) -> Sequence[TextContent]:
        try:
            return await func(*args, **kwargs)
        except MCPError as e:
            # Known application errors
            return [TextContent(text=str(e.to_dict()))]
        except Exception as e:
            # Unexpected errors
            internal_error = InternalError(
                message="An unexpected error occurred",
                details={"error": str(e), "type": e.__class__.__name__},
            )
            return [TextContent(text=str(internal_error.to_dict()))]

    return wrapper


class BaseHandler:
    """Base class for handlers."""

    name: str = ""
    description: str = ""

    def __init__(self, editor: TextEditor | None = None):
        """Initialize the handler."""
        self.editor = editor if editor is not None else TextEditor()

    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        """Validate the input arguments.

        Args:
            arguments: The arguments to validate

        Raises:
            ValidationError: If the arguments are invalid
        """
        raise NotImplementedError

    def get_tool_description(self) -> Tool:
        """Get the tool description."""
        raise NotImplementedError

    @handle_errors
    async def run_tool(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Execute the tool with given arguments.

        This method is decorated with handle_errors to provide consistent
        error handling across all handlers.

        Args:
            arguments: The arguments for the tool

        Returns:
            Sequence[TextContent]: The tool's output

        Raises:
            MCPError: For known application errors
            Exception: For unexpected errors
        """
        # Validate arguments before execution
        self.validate_arguments(arguments)
        return await self._execute_tool(arguments)

    async def _execute_tool(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Internal method to execute the tool.

        This should be implemented by each handler to provide the actual
        tool functionality.

        Args:
            arguments: The validated arguments for the tool

        Returns:
            Sequence[TextContent]: The tool's output
        """
        raise NotImplementedError
