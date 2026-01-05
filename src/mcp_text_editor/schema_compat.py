"""Schema compatibility utilities for Gemini/Vertex AI.

This module provides utilities to convert JSON Schema with anyOf constructs
and type arrays to formats compatible with Google Gemini and Vertex AI APIs.

The issue is that Pydantic v2 generates schemas like:
    {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": null}

And some schemas use type arrays like:
    {"type": ["integer", "null"]}

But Gemini/Vertex AI requires:
    {"type": "integer", "nullable": true, "default": null}

See: https://github.com/tumf/mcp-text-editor/issues/11
"""

import copy
from typing import Any, Dict, List


def convert_anyof_to_nullable(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Convert anyOf with null type to nullable format for Gemini compatibility.

    This function recursively processes a JSON Schema and converts anyOf
    constructs that include null type to the nullable format that Gemini
    and Vertex AI can understand.

    Args:
        schema: A JSON Schema dictionary that may contain anyOf constructs.

    Returns:
        A new schema dictionary with anyOf converted to nullable format.

    Example:
        Input:
            {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": null}
        Output:
            {"type": "integer", "nullable": true, "default": null}
    """
    if not isinstance(schema, dict):
        return schema

    # Make a deep copy to avoid modifying the original
    result = copy.deepcopy(schema)
    _convert_anyof_recursive(result)
    return result


def _convert_anyof_recursive(schema: Dict[str, Any]) -> None:
    """Recursively convert anyOf and type array constructs in-place.

    Args:
        schema: Schema dictionary to modify in-place.
    """
    if not isinstance(schema, dict):
        return

    # Handle anyOf at current level
    if "anyOf" in schema:
        _convert_anyof_field(schema)

    # Handle type array at current level (e.g., "type": ["integer", "null"])
    if "type" in schema and isinstance(schema["type"], list):
        _convert_type_array_field(schema)

    # Recursively process nested structures
    for _key, value in list(schema.items()):
        if isinstance(value, dict):
            _convert_anyof_recursive(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _convert_anyof_recursive(item)


def _convert_type_array_field(schema: Dict[str, Any]) -> None:
    """Convert a type array field to nullable format in-place.

    Handles schemas like: {"type": ["integer", "null"]}
    Converts to: {"type": "integer", "nullable": true}

    Args:
        schema: Schema dictionary containing type array to convert.
    """
    type_array = schema.get("type", [])
    if not isinstance(type_array, list):
        return

    # Find non-null types
    non_null_types = [t for t in type_array if t != "null"]
    has_null = "null" in type_array

    if not non_null_types:
        # Only null type, use string as fallback
        schema["type"] = "string"
        if has_null:
            schema["nullable"] = True
        return

    # Use the first non-null type
    schema["type"] = non_null_types[0]
    if has_null:
        schema["nullable"] = True


def _convert_anyof_field(schema: Dict[str, Any]) -> None:
    """Convert a single anyOf field to nullable format in-place.

    Args:
        schema: Schema dictionary containing anyOf to convert.
    """
    any_of = schema.get("anyOf", [])
    if not any_of:
        return

    # Find the non-null type(s)
    non_null_types: List[Dict[str, Any]] = []
    has_null = False

    for item in any_of:
        if isinstance(item, dict):
            if item.get("type") == "null":
                has_null = True
            else:
                non_null_types.append(item)

    if not non_null_types:
        # Only null type, use string as fallback
        schema["type"] = "string"
        schema["nullable"] = True
        del schema["anyOf"]
        return

    if len(non_null_types) == 1:
        # Single non-null type - simple case
        non_null = non_null_types[0]

        # Copy all properties from the non-null type
        for key, value in non_null.items():
            if key not in schema or key == "type":
                schema[key] = value

        # Add nullable if null was in anyOf
        if has_null:
            schema["nullable"] = True

        # Remove anyOf
        del schema["anyOf"]

        # Recursively process nested items (for arrays)
        if "items" in schema:
            _convert_anyof_recursive(schema["items"])

    else:
        # Multiple non-null types - use the first one as primary type
        # This is a simplification, but Gemini doesn't support true union types
        primary = non_null_types[0]

        for key, value in primary.items():
            if key not in schema or key == "type":
                schema[key] = value

        if has_null:
            schema["nullable"] = True

        del schema["anyOf"]

        # Recursively process nested items
        if "items" in schema:
            _convert_anyof_recursive(schema["items"])


def make_schema_gemini_compatible(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Make a JSON Schema compatible with Gemini/Vertex AI.

    This is the main entry point for schema conversion. It applies all
    necessary transformations to make the schema work with Gemini APIs.

    Args:
        schema: A JSON Schema dictionary.

    Returns:
        A Gemini-compatible schema dictionary.

    Example:
        >>> schema = {
        ...     "type": "object",
        ...     "properties": {
        ...         "name": {"type": "string"},
        ...         "age": {
        ...             "anyOf": [{"type": "integer"}, {"type": "null"}],
        ...             "default": null
        ...         }
        ...     }
        ... }
        >>> result = make_schema_gemini_compatible(schema)
        >>> result["properties"]["age"]
        {'type': 'integer', 'nullable': True, 'default': None}
    """
    return convert_anyof_to_nullable(schema)
