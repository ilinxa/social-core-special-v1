# apps/cms/tests/test_validators.py
import pytest

from apps.cms.validators import SchemaValidator, _has_catastrophic_backtracking_risk
from apps.core.exceptions import ValidationError


class TestSchemaValidatorStructure:
    """Tests for validate_schema_structure (schema definition validation)."""

    def test_valid_schema(self):
        schema = {
            "fields": [
                {"key": "title", "type": "text"},
                {"key": "body", "type": "textarea"},
            ]
        }
        SchemaValidator.validate_schema_structure(schema=schema)

    def test_missing_fields_key(self):
        with pytest.raises(ValidationError, match="fields"):
            SchemaValidator.validate_schema_structure(schema={})

    def test_fields_not_array(self):
        with pytest.raises(ValidationError, match="array"):
            SchemaValidator.validate_schema_structure(schema={"fields": "not-a-list"})

    def test_field_missing_key(self):
        schema = {"fields": [{"type": "text"}]}
        with pytest.raises(ValidationError, match="key"):
            SchemaValidator.validate_schema_structure(schema=schema)

    def test_field_missing_type(self):
        schema = {"fields": [{"key": "title"}]}
        with pytest.raises(ValidationError, match="type"):
            SchemaValidator.validate_schema_structure(schema=schema)

    def test_unknown_field_type(self):
        schema = {"fields": [{"key": "f", "type": "unknown_type"}]}
        with pytest.raises(ValidationError, match="Unknown field type"):
            SchemaValidator.validate_schema_structure(schema=schema)

    def test_duplicate_field_key(self):
        schema = {
            "fields": [
                {"key": "title", "type": "text"},
                {"key": "title", "type": "textarea"},
            ]
        }
        with pytest.raises(ValidationError, match="Duplicate field key"):
            SchemaValidator.validate_schema_structure(schema=schema)

    def test_repeater_missing_item_schema(self):
        schema = {"fields": [{"key": "items", "type": "repeater"}]}
        with pytest.raises(ValidationError, match="item_schema"):
            SchemaValidator.validate_schema_structure(schema=schema)

    def test_nested_repeaters_rejected(self):
        schema = {
            "fields": [
                {
                    "key": "parent",
                    "type": "repeater",
                    "item_schema": {
                        "fields": [
                            {
                                "key": "child",
                                "type": "repeater",
                                "item_schema": {"fields": []},
                            }
                        ]
                    },
                }
            ]
        }
        with pytest.raises(ValidationError, match="Nested repeaters"):
            SchemaValidator.validate_schema_structure(schema=schema)

    def test_valid_regex_pattern_accepted(self):
        """Schema with a valid regex pattern passes validation."""
        schema = {
            "fields": [
                {
                    "key": "code",
                    "type": "text",
                    "validation": {"pattern": r"^[A-Z]{3}-\d{4}$"},
                }
            ]
        }
        SchemaValidator.validate_schema_structure(schema=schema)

    def test_invalid_regex_pattern_rejected(self):
        """Schema with a syntactically invalid regex is rejected."""
        schema = {
            "fields": [
                {
                    "key": "code",
                    "type": "text",
                    "validation": {"pattern": r"[invalid("},
                }
            ]
        }
        with pytest.raises(ValidationError, match="Invalid regex pattern"):
            SchemaValidator.validate_schema_structure(schema=schema)

    def test_regex_pattern_exceeding_length_limit_rejected(self):
        """Schema with a regex pattern > 500 chars is rejected."""
        schema = {
            "fields": [
                {
                    "key": "code",
                    "type": "text",
                    "validation": {"pattern": "a" * 501},
                }
            ]
        }
        with pytest.raises(ValidationError, match="exceeds 500 char limit"):
            SchemaValidator.validate_schema_structure(schema=schema)

    def test_catastrophic_backtracking_pattern_rejected(self):
        """Schema with a ReDoS-prone pattern (e.g., (a+)+$) is rejected."""
        dangerous_patterns = [
            r"(a+)+$",  # classic nested quantifier
            r"(a*)*b",  # nested star quantifier
            r"(x+x+)+y",  # overlapping quantifiers
        ]
        for pattern in dangerous_patterns:
            schema = {
                "fields": [
                    {
                        "key": "code",
                        "type": "text",
                        "validation": {"pattern": pattern},
                    }
                ]
            }
            with pytest.raises(ValidationError, match="catastrophic backtracking"):
                SchemaValidator.validate_schema_structure(schema=schema)

    def test_backtracking_heuristic_safe_patterns(self):
        """Safe patterns are not flagged by the heuristic."""
        safe_patterns = [
            r"^[A-Z]+$",
            r"^\d{3}-\d{4}$",
            r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$",
            r"^https?://",
        ]
        for pattern in safe_patterns:
            assert not _has_catastrophic_backtracking_risk(
                pattern
            ), f"False positive on: {pattern}"


class TestSchemaValidatorContent:
    """Tests for validate_content (content JSONB validation)."""

    def test_permissive_draft_accepts_empty_required(self):
        """Draft mode accepts missing required fields."""
        schema = {"fields": [{"key": "title", "type": "text", "required": True}]}
        issues = SchemaValidator.validate_content(
            schema=schema, content={}, strict=False
        )
        assert len(issues) == 0

    def test_strict_publish_rejects_empty_required(self):
        """Publish mode rejects missing required fields."""
        schema = {
            "fields": [
                {"key": "title", "type": "text", "required": True, "label": "Title"}
            ]
        }
        issues = SchemaValidator.validate_content(
            schema=schema, content={}, strict=True
        )
        assert len(issues) == 1
        assert issues[0]["error_type"] == "required_field_empty"

    def test_strict_required_empty_string(self):
        schema = {"fields": [{"key": "title", "type": "text", "required": True}]}
        issues = SchemaValidator.validate_content(
            schema=schema, content={"title": ""}, strict=True
        )
        assert len(issues) == 1

    def test_strict_required_empty_list(self):
        schema = {"fields": [{"key": "items", "type": "multiselect", "required": True}]}
        issues = SchemaValidator.validate_content(
            schema=schema, content={"items": []}, strict=True
        )
        assert len(issues) == 1

    def test_optional_field_none_passes(self):
        schema = {"fields": [{"key": "title", "type": "text", "required": False}]}
        issues = SchemaValidator.validate_content(
            schema=schema, content={"title": None}, strict=True
        )
        assert len(issues) == 0

    def test_text_type_error(self):
        schema = {"fields": [{"key": "title", "type": "text", "required": False}]}
        issues = SchemaValidator.validate_content(
            schema=schema, content={"title": 42}, strict=True
        )
        assert issues[0]["error_type"] == "type_error"

    def test_max_length_validation(self):
        schema = {
            "fields": [
                {
                    "key": "title",
                    "type": "text",
                    "required": False,
                    "validation": {"max_length": 10},
                }
            ]
        }
        issues = SchemaValidator.validate_content(
            schema=schema,
            content={"title": "x" * 20},
            strict=True,
        )
        assert any(i["error_type"] == "max_length" for i in issues)

    def test_min_length_validation(self):
        schema = {
            "fields": [
                {
                    "key": "title",
                    "type": "text",
                    "required": False,
                    "validation": {"min_length": 5},
                }
            ]
        }
        issues = SchemaValidator.validate_content(
            schema=schema,
            content={"title": "ab"},
            strict=True,
        )
        assert any(i["error_type"] == "min_length" for i in issues)

    def test_pattern_validation(self):
        schema = {
            "fields": [
                {
                    "key": "code",
                    "type": "text",
                    "required": False,
                    "validation": {"pattern": r"^[A-Z]+$"},
                }
            ]
        }
        issues = SchemaValidator.validate_content(
            schema=schema,
            content={"code": "abc"},
            strict=True,
        )
        assert any(i["error_type"] == "pattern_mismatch" for i in issues)

    def test_number_type_error(self):
        schema = {"fields": [{"key": "count", "type": "number", "required": False}]}
        issues = SchemaValidator.validate_content(
            schema=schema, content={"count": "not-a-number"}, strict=True
        )
        assert issues[0]["error_type"] == "type_error"

    def test_number_min_max(self):
        schema = {
            "fields": [
                {
                    "key": "count",
                    "type": "number",
                    "required": False,
                    "validation": {"min": 1, "max": 10},
                }
            ]
        }
        issues = SchemaValidator.validate_content(
            schema=schema, content={"count": 0}, strict=True
        )
        assert any(i["error_type"] == "min_value" for i in issues)

        issues = SchemaValidator.validate_content(
            schema=schema, content={"count": 100}, strict=True
        )
        assert any(i["error_type"] == "max_value" for i in issues)

    def test_boolean_type_error(self):
        schema = {"fields": [{"key": "active", "type": "boolean", "required": False}]}
        issues = SchemaValidator.validate_content(
            schema=schema, content={"active": "yes"}, strict=True
        )
        assert issues[0]["error_type"] == "type_error"

    def test_boolean_valid(self):
        schema = {"fields": [{"key": "active", "type": "boolean", "required": False}]}
        issues = SchemaValidator.validate_content(
            schema=schema, content={"active": True}, strict=True
        )
        assert len(issues) == 0

    def test_select_invalid_choice(self):
        schema = {
            "fields": [
                {
                    "key": "color",
                    "type": "select",
                    "required": False,
                    "validation": {"choices": [{"value": "red"}, {"value": "blue"}]},
                }
            ]
        }
        issues = SchemaValidator.validate_content(
            schema=schema, content={"color": "green"}, strict=True
        )
        assert any(i["error_type"] == "invalid_choice" for i in issues)

    def test_select_valid_choice(self):
        schema = {
            "fields": [
                {
                    "key": "color",
                    "type": "select",
                    "required": False,
                    "validation": {"choices": [{"value": "red"}, {"value": "blue"}]},
                }
            ]
        }
        issues = SchemaValidator.validate_content(
            schema=schema, content={"color": "red"}, strict=True
        )
        assert len(issues) == 0

    def test_multiselect_type_error(self):
        schema = {"fields": [{"key": "tags", "type": "multiselect", "required": False}]}
        issues = SchemaValidator.validate_content(
            schema=schema, content={"tags": "not-a-list"}, strict=True
        )
        assert issues[0]["error_type"] == "type_error"

    def test_multiselect_invalid_choice(self):
        schema = {
            "fields": [
                {
                    "key": "tags",
                    "type": "multiselect",
                    "required": False,
                    "validation": {"choices": [{"value": "a"}, {"value": "b"}]},
                }
            ]
        }
        issues = SchemaValidator.validate_content(
            schema=schema, content={"tags": ["a", "c"]}, strict=True
        )
        assert any(i["error_type"] == "invalid_choice" for i in issues)

    def test_repeater_validates_items(self):
        schema = {
            "fields": [
                {
                    "key": "items",
                    "type": "repeater",
                    "required": True,
                    "validation": {"min_items": 1, "max_items": 3},
                    "item_schema": {
                        "fields": [{"key": "name", "type": "text", "required": True}]
                    },
                }
            ]
        }
        # Valid
        issues = SchemaValidator.validate_content(
            schema=schema,
            content={"items": [{"name": "Alice"}]},
            strict=True,
        )
        assert len(issues) == 0

        # Missing required sub-field
        issues = SchemaValidator.validate_content(
            schema=schema,
            content={"items": [{"name": ""}]},
            strict=True,
        )
        assert len(issues) > 0

    def test_repeater_min_items(self):
        schema = {
            "fields": [
                {
                    "key": "items",
                    "type": "repeater",
                    "required": False,
                    "validation": {"min_items": 2},
                    "item_schema": {"fields": []},
                }
            ]
        }
        issues = SchemaValidator.validate_content(
            schema=schema, content={"items": [{}]}, strict=True
        )
        assert any(i["error_type"] == "min_items" for i in issues)

    def test_repeater_max_items(self):
        schema = {
            "fields": [
                {
                    "key": "items",
                    "type": "repeater",
                    "required": False,
                    "validation": {"max_items": 1},
                    "item_schema": {"fields": []},
                }
            ]
        }
        issues = SchemaValidator.validate_content(
            schema=schema, content={"items": [{}, {}, {}]}, strict=True
        )
        assert any(i["error_type"] == "max_items" for i in issues)

    def test_repeater_nested_field_keys(self):
        """Nested errors include parent key path like items[0].name."""
        schema = {
            "fields": [
                {
                    "key": "items",
                    "type": "repeater",
                    "required": False,
                    "item_schema": {
                        "fields": [{"key": "name", "type": "text", "required": True}]
                    },
                }
            ]
        }
        issues = SchemaValidator.validate_content(
            schema=schema, content={"items": [{}]}, strict=True
        )
        assert any("items[0].name" in i["field_key"] for i in issues)


class TestSchemaValidatorSanitize:
    """Tests for sanitize_content (rich text sanitization)."""

    def test_sanitize_strips_script_tags(self):
        schema = {"fields": [{"key": "body", "type": "richtext"}]}
        content = {"body": "<p>Hello</p><script>alert('xss')</script>"}
        result = SchemaValidator.sanitize_content(schema=schema, content=content)
        assert "<script>" not in result["body"]
        assert "<p>Hello</p>" in result["body"]

    def test_sanitize_preserves_allowed_tags(self):
        schema = {"fields": [{"key": "body", "type": "richtext"}]}
        content = {"body": "<p><strong>Bold</strong> text</p>"}
        result = SchemaValidator.sanitize_content(schema=schema, content=content)
        assert "<strong>Bold</strong>" in result["body"]

    def test_sanitize_non_richtext_unchanged(self):
        schema = {"fields": [{"key": "title", "type": "text"}]}
        content = {"title": "<script>evil</script>"}
        result = SchemaValidator.sanitize_content(schema=schema, content=content)
        assert (
            result["title"] == "<script>evil</script>"
        )  # Not sanitized — not richtext

    def test_sanitize_repeater_recursion(self):
        schema = {
            "fields": [
                {
                    "key": "items",
                    "type": "repeater",
                    "item_schema": {"fields": [{"key": "desc", "type": "richtext"}]},
                }
            ]
        }
        content = {"items": [{"desc": "<p>ok</p><script>bad</script>"}]}
        result = SchemaValidator.sanitize_content(schema=schema, content=content)
        assert "<script>" not in result["items"][0]["desc"]
        assert "<p>ok</p>" in result["items"][0]["desc"]


class TestSchemaValidatorRegexRuntime:
    """Tests for runtime regex error handling in _validate_field_value."""

    def test_runtime_regex_error_handled_gracefully(self):
        """If a stored pattern causes re.error at runtime, it's caught and reported."""
        schema = {
            "fields": [
                {
                    "key": "code",
                    "type": "text",
                    "required": False,
                    # This pattern is syntactically invalid but somehow got stored
                    "validation": {"pattern": r"[invalid("},
                }
            ]
        }
        issues = SchemaValidator.validate_content(
            schema=schema,
            content={"code": "test"},
            strict=True,
        )
        assert any(i["error_type"] == "pattern_error" for i in issues)

    def test_valid_pattern_match_works_end_to_end(self):
        """Valid pattern that matches content produces no issues."""
        schema = {
            "fields": [
                {
                    "key": "code",
                    "type": "text",
                    "required": False,
                    "validation": {"pattern": r"^[A-Z]{3}-\d{4}$"},
                }
            ]
        }
        issues = SchemaValidator.validate_content(
            schema=schema,
            content={"code": "ABC-1234"},
            strict=True,
        )
        assert len(issues) == 0
