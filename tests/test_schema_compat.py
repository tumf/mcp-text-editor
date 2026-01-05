"""Tests for schema compatibility utilities."""

from mcp_text_editor.schema_compat import (
    convert_anyof_to_nullable,
    make_schema_gemini_compatible,
)


class TestConvertAnyofToNullable:
    """Tests for convert_anyof_to_nullable function."""

    def test_simple_anyof_with_null(self):
        """Test conversion of simple anyOf with null type."""
        schema = {
            "anyOf": [{"type": "integer"}, {"type": "null"}],
            "default": None,
        }
        result = convert_anyof_to_nullable(schema)

        assert result == {
            "type": "integer",
            "nullable": True,
            "default": None,
        }

    def test_anyof_string_with_null(self):
        """Test conversion of string anyOf with null type."""
        schema = {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "default": None,
            "title": "Description",
        }
        result = convert_anyof_to_nullable(schema)

        assert result["type"] == "string"
        assert result["nullable"] is True
        assert result["default"] is None
        assert result["title"] == "Description"
        assert "anyOf" not in result

    def test_anyof_without_null(self):
        """Test anyOf without null type preserves first type."""
        schema = {
            "anyOf": [{"type": "string"}, {"type": "integer"}],
        }
        result = convert_anyof_to_nullable(schema)

        assert result["type"] == "string"
        assert "nullable" not in result
        assert "anyOf" not in result

    def test_nested_anyof_in_properties(self):
        """Test conversion of nested anyOf in object properties."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "default": None,
                },
            },
        }
        result = convert_anyof_to_nullable(schema)

        assert result["type"] == "object"
        assert result["properties"]["name"] == {"type": "string"}
        assert result["properties"]["age"] == {
            "type": "integer",
            "nullable": True,
            "default": None,
        }

    def test_anyof_with_array_type(self):
        """Test conversion of anyOf with array type."""
        schema = {
            "anyOf": [
                {"type": "array", "items": {"type": "string"}},
                {"type": "null"},
            ],
            "default": None,
        }
        result = convert_anyof_to_nullable(schema)

        assert result["type"] == "array"
        assert result["items"] == {"type": "string"}
        assert result["nullable"] is True
        assert "anyOf" not in result

    def test_deeply_nested_anyof(self):
        """Test conversion of deeply nested anyOf structures."""
        schema = {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "properties": {
                        "value": {
                            "anyOf": [{"type": "number"}, {"type": "null"}],
                            "default": None,
                        }
                    },
                }
            },
        }
        result = convert_anyof_to_nullable(schema)

        value_schema = result["properties"]["data"]["properties"]["value"]
        assert value_schema["type"] == "number"
        assert value_schema["nullable"] is True
        assert "anyOf" not in value_schema

    def test_anyof_in_array_items(self):
        """Test conversion of anyOf inside array items."""
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "anyOf": [{"type": "integer"}, {"type": "null"}],
                        "default": None,
                    }
                },
            },
        }
        result = convert_anyof_to_nullable(schema)

        id_schema = result["items"]["properties"]["id"]
        assert id_schema["type"] == "integer"
        assert id_schema["nullable"] is True

    def test_only_null_type_in_anyof(self):
        """Test anyOf with only null type uses string as fallback."""
        schema = {
            "anyOf": [{"type": "null"}],
            "default": None,
        }
        result = convert_anyof_to_nullable(schema)

        assert result["type"] == "string"
        assert result["nullable"] is True

    def test_preserves_other_schema_properties(self):
        """Test that other schema properties are preserved."""
        schema = {
            "anyOf": [{"type": "integer"}, {"type": "null"}],
            "default": None,
            "title": "Age",
            "description": "Person's age",
            "minimum": 0,
        }
        result = convert_anyof_to_nullable(schema)

        assert result["type"] == "integer"
        assert result["nullable"] is True
        assert result["title"] == "Age"
        assert result["description"] == "Person's age"
        # Note: minimum from anyOf schema should be preserved
        assert "anyOf" not in result

    def test_schema_without_anyof_unchanged(self):
        """Test that schemas without anyOf are unchanged."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["name"],
        }
        result = convert_anyof_to_nullable(schema)

        assert result == schema

    def test_empty_schema(self):
        """Test that empty schema is handled correctly."""
        schema = {}
        result = convert_anyof_to_nullable(schema)
        assert result == {}

    def test_original_schema_not_modified(self):
        """Test that the original schema is not modified."""
        schema = {
            "anyOf": [{"type": "integer"}, {"type": "null"}],
            "default": None,
        }
        original = schema.copy()
        convert_anyof_to_nullable(schema)

        assert schema == original


class TestMakeSchemaGeminiCompatible:
    """Tests for make_schema_gemini_compatible function."""

    def test_full_tool_schema_conversion(self):
        """Test conversion of a realistic tool schema."""
        # This mimics what Pydantic generates for Optional[int]
        schema = {
            "properties": {
                "start": {"title": "Start", "type": "integer"},
                "end": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "default": None,
                    "title": "End",
                },
            },
            "required": ["start"],
            "title": "test_toolArguments",
            "type": "object",
        }
        result = make_schema_gemini_compatible(schema)

        assert result["properties"]["start"] == {"title": "Start", "type": "integer"}
        assert result["properties"]["end"] == {
            "type": "integer",
            "nullable": True,
            "default": None,
            "title": "End",
        }
        assert result["required"] == ["start"]
        assert result["type"] == "object"

    def test_complex_nested_schema(self):
        """Test conversion of complex nested schema with multiple anyOf."""
        schema = {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "patches": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "start": {"type": "integer"},
                                        "end": {
                                            "anyOf": [
                                                {"type": "integer"},
                                                {"type": "null"},
                                            ],
                                            "default": None,
                                        },
                                        "range_hash": {
                                            "anyOf": [
                                                {"type": "string"},
                                                {"type": "null"},
                                            ],
                                            "default": None,
                                        },
                                    },
                                },
                            },
                        },
                    },
                }
            },
        }
        result = make_schema_gemini_compatible(schema)

        patch_props = result["properties"]["files"]["items"]["properties"]["patches"][
            "items"
        ]["properties"]
        assert patch_props["end"]["type"] == "integer"
        assert patch_props["end"]["nullable"] is True
        assert "anyOf" not in patch_props["end"]

        assert patch_props["range_hash"]["type"] == "string"
        assert patch_props["range_hash"]["nullable"] is True
        assert "anyOf" not in patch_props["range_hash"]


class TestTypeArrayConversion:
    """Tests for type array conversion (e.g., type: ["integer", "null"])."""

    def test_simple_type_array_with_null(self):
        """Test conversion of simple type array with null."""
        schema = {
            "type": ["integer", "null"],
            "description": "Optional integer",
        }
        result = convert_anyof_to_nullable(schema)

        assert result == {
            "type": "integer",
            "nullable": True,
            "description": "Optional integer",
        }

    def test_type_array_string_with_null(self):
        """Test conversion of string type array with null."""
        schema = {
            "type": ["string", "null"],
            "default": None,
        }
        result = convert_anyof_to_nullable(schema)

        assert result["type"] == "string"
        assert result["nullable"] is True
        assert result["default"] is None

    def test_type_array_without_null(self):
        """Test type array without null uses first type."""
        schema = {
            "type": ["string", "integer"],
        }
        result = convert_anyof_to_nullable(schema)

        assert result["type"] == "string"
        assert "nullable" not in result

    def test_nested_type_array_in_properties(self):
        """Test conversion of nested type array in object properties."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "end": {
                    "type": ["integer", "null"],
                    "description": "Ending line number",
                },
            },
        }
        result = convert_anyof_to_nullable(schema)

        assert result["type"] == "object"
        assert result["properties"]["name"] == {"type": "string"}
        assert result["properties"]["end"] == {
            "type": "integer",
            "nullable": True,
            "description": "Ending line number",
        }

    def test_type_array_in_array_items(self):
        """Test type array inside array items properties."""
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start": {"type": "integer"},
                    "end": {
                        "type": ["integer", "null"],
                        "description": "End line",
                    },
                },
            },
        }
        result = convert_anyof_to_nullable(schema)

        end_schema = result["items"]["properties"]["end"]
        assert end_schema["type"] == "integer"
        assert end_schema["nullable"] is True

    def test_only_null_in_type_array(self):
        """Test type array with only null uses string fallback."""
        schema = {
            "type": ["null"],
        }
        result = convert_anyof_to_nullable(schema)

        assert result["type"] == "string"
        assert result["nullable"] is True

    def test_realistic_handler_schema(self):
        """Test conversion of realistic handler schema with type arrays."""
        # This is the actual schema format used in get_text_file_contents
        schema = {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string"},
                            "ranges": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "start": {"type": "integer"},
                                        "end": {
                                            "type": ["integer", "null"],
                                            "description": "Ending line number",
                                        },
                                    },
                                    "required": ["start"],
                                },
                            },
                        },
                    },
                },
            },
        }
        result = make_schema_gemini_compatible(schema)

        end_schema = result["properties"]["files"]["items"]["properties"]["ranges"][
            "items"
        ]["properties"]["end"]
        assert end_schema["type"] == "integer"
        assert end_schema["nullable"] is True
        assert "Ending line number" in end_schema["description"]


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_anyof_with_object_type(self):
        """Test anyOf with object type containing additional properties."""
        schema = {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {"key": {"type": "string"}},
                    "additionalProperties": True,
                },
                {"type": "null"},
            ],
            "default": None,
        }
        result = convert_anyof_to_nullable(schema)

        assert result["type"] == "object"
        assert result["nullable"] is True
        assert result["properties"] == {"key": {"type": "string"}}

    def test_multiple_non_null_types_uses_first(self):
        """Test that multiple non-null types use the first one."""
        schema = {
            "anyOf": [
                {"type": "string"},
                {"type": "integer"},
                {"type": "null"},
            ],
        }
        result = convert_anyof_to_nullable(schema)

        assert result["type"] == "string"
        assert result["nullable"] is True

    def test_anyof_with_enum(self):
        """Test anyOf with enum type."""
        schema = {
            "anyOf": [
                {"type": "string", "enum": ["a", "b", "c"]},
                {"type": "null"},
            ],
            "default": None,
        }
        result = convert_anyof_to_nullable(schema)

        assert result["type"] == "string"
        assert result["enum"] == ["a", "b", "c"]
        assert result["nullable"] is True

    def test_non_dict_input_returns_unchanged(self):
        """Test that non-dict input is returned unchanged."""
        assert convert_anyof_to_nullable("string") == "string"
        assert convert_anyof_to_nullable(123) == 123
        assert convert_anyof_to_nullable(None) is None
        assert convert_anyof_to_nullable([1, 2, 3]) == [1, 2, 3]
