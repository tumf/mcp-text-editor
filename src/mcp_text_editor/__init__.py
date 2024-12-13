"""MCP Text Editor Server package."""

import asyncio

from .server import main

__version__ = "0.1.0"


def run() -> None:
    """Run the MCP Text Editor Server."""
    asyncio.run(main())
