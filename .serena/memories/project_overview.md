# MCP Text Editor Project Overview

## Purpose
MCP Text Editor Server provides line-oriented text file editing capabilities through the Model Context Protocol (MCP). It's optimized for LLM tools with efficient partial file access to minimize token usage.

## Key Features
- Line-based editing operations with hash-based conflict detection
- Token-efficient partial file access with line-range specifications
- Multi-file operations support
- Robust error handling with custom error types
- Comprehensive encoding support (utf-8, shift_jis, latin1, etc.)
- Safe concurrent editing with SHA-256 hash validation

## Tech Stack
- Python 3.13+
- MCP (Model Context Protocol) >= 1.2.0
- Standard libraries: asyncio, pathlib, hashlib
- Development tools: pytest, ruff, black, isort, mypy
- Package management: uv

## Architecture
- `TextEditor` class: Core functionality for file operations
- `TextEditorService`: Service layer
- Handler classes: Individual tool implementations (create, get, patch, delete, insert, append)
- Models: Data structures for requests/responses
- Server: MCP server implementation
