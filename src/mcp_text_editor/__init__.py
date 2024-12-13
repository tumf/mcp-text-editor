"""MCP Text Editor Server package."""

import asyncio

from .server import main


def run() -> None:
    """Run the MCP Text Editor Server."""
    asyncio.run(main())
