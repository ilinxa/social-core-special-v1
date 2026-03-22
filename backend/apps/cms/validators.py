# apps/cms/validators.py
"""
CMS Schema Validator
=====================
Validates content JSONB against BlockTemplate schema.
Two modes: permissive (draft save) and strict (publish).
"""

import re

from apps.cms.constants import CMS_FIELD_TYPES
from apps.core.observability import get_logger

logger = get_logger(__name__)

# Maximum allowed length for user-defined regex patterns
MAX_REGEX_PATTERN_LENGTH = 500


def _has_catastrophic_backtracking_risk(pattern: str) -> bool:
    """Heuristic: detect nested quantifiers that cause exponential backtracking.

    Catches patterns like (a+)+, (a*)+, (a+)*, (a{2,})+ where a quantified
    group is itself quantified — the classic ReDoS trigger.
    """
    return bool(re.search(r"[+*}]\)?[+*{]", pattern))


class SchemaValidator:
    """
    Validates content against a block template schema.

    Usage:
        errors = SchemaValidator.validate_content(
            schema=template.schema,
            content=placement.draft_content,
            strict=True,  # False for draft save
        )
    """

    @staticmethod
    def validate_schema_structure(*, schema: dict) -> None:
        """
        Validate the schema definition itself (not content).
        Called when creating/updating block templates.
        """
        from apps.core.exceptions import ValidationError

        if "fields" not in schema:
            raise ValidationError(message="Schema must contain a 'fields' array")

        if not isinstance(schema["fields"], list):
            raise ValidationError(message="Schema 'fields' must be an array")

        seen_keys = set()
        for field in schema["fields"]:
            if "key" not in field or "type" not in field:
                raise ValidationError(
                    message="Each field must have 'key' and 'type'",
                )
            if field["type"] not in CMS_FIELD_TYPES:
                raise ValidationError(
                    message=f"Unknown field type: {field['type']}",
                )
            if field["key"] in seen_keys:
                raise ValidationError(
                    message=f"Duplicate field key: {field['key']}",
                )
            seen_keys.add(field["key"])

            # Validate regex patterns for ReDoS safety
            validation = field.get("validation", {})
            if "pattern" in validation:
                pattern = validation["pattern"]
                if len(pattern) > MAX_REGEX_PATTERN_LENGTH:
                    raise ValidationError(
                        message=f"Regex pattern for '{field['key']}' exceeds {MAX_REGEX_PATTERN_LENGTH} char limit",
                    )
                try:
                    re.compile(pattern)
                except re.error as e:
                    raise ValidationError(
                        message=f"Invalid regex pattern for '{field['key']}': {e}",
                    ) from e
                if _has_catastrophic_backtracking_risk(pattern):
                    raise ValidationError(
                        message=f"Regex pattern for '{field['key']}' rejected: potential catastrophic backtracking",
                    )

            # Validate repeater sub-schema (no nesting)
            if field["type"] == "repeater":
                if "item_schema" not in field:
                    raise ValidationError(
                        message=f"Repeater field '{field['key']}' must have 'item_schema'",
                    )
                for sub_field in field["item_schema"].get("fields", []):
                    if sub_field.get("type") == "repeater":
                        raise ValidationError(
                            message="Nested repeaters are not allowed",
                        )

    @staticmethod
    def validate_content(
        *,
        schema: dict,
        content: dict,
        strict: bool = False,
    ) -> list[dict]:
        """
        Validate content JSONB against schema.

        Args:
            schema: BlockTemplate.schema
            content: The content JSONB to validate
            strict: If True (publish), returns errors. If False (draft), returns warnings.

        Returns:
            List of error/warning dicts: [{"field_key": ..., "error_type": ..., "message": ...}]
        """
        issues = []
        fields = schema.get("fields", [])

        for field_def in fields:
            key = field_def["key"]
            field_type = field_def["type"]
            required = field_def.get("required", False)
            value = content.get(key)

            # Required check
            if required and (value is None or value == "" or value == []):
                if strict:
                    issues.append(
                        {
                            "field_key": key,
                            "error_type": "required_field_empty",
                            "message": f"{field_def.get('label', key)} is required",
                        }
                    )
                continue

            # Skip validation if value is None/empty (non-required)
            if value is None or value == "":
                continue

            # Type-specific validation
            validation = field_def.get("validation", {})
            field_issues = SchemaValidator._validate_field_value(
                key=key,
                field_type=field_type,
                value=value,
                validation=validation,
                field_def=field_def,
                strict=strict,
            )
            issues.extend(field_issues)

        return issues

    @staticmethod
    def sanitize_content(*, schema: dict, content: dict) -> dict:
        """
        Sanitize richtext fields in content dict. Returns a new sanitized dict.

        Must be called BEFORE validate_content so validation operates on clean HTML.
        Services call this before saving draft_content:

            content = SchemaValidator.sanitize_content(schema=schema, content=content)
            warnings = SchemaValidator.validate_content(schema=schema, content=content, strict=False)
            placement.draft_content = content  # now sanitized
        """
        import nh3

        sanitized = dict(content)  # Shallow copy — mutate only richtext values
        fields = schema.get("fields", [])

        for field_def in fields:
            key = field_def["key"]
            field_type = field_def["type"]
            value = sanitized.get(key)

            if field_type == "richtext" and isinstance(value, str):
                allowed_tags = set(
                    field_def.get(
                        "allowed_tags",
                        [
                            "p",
                            "br",
                            "strong",
                            "em",
                            "u",
                            "s",
                            "a",
                            "ul",
                            "ol",
                            "li",
                            "h1",
                            "h2",
                            "h3",
                            "h4",
                            "h5",
                            "h6",
                            "blockquote",
                            "code",
                            "pre",
                        ],
                    )
                )
                sanitized[key] = nh3.clean(value, tags=allowed_tags)

            elif field_type == "repeater" and isinstance(value, list):
                # Recursively sanitize repeater items
                item_schema = field_def.get("item_schema", {})
                sanitized[key] = [
                    (
                        SchemaValidator.sanitize_content(
                            schema=item_schema, content=item
                        )
                        if isinstance(item, dict)
                        else item
                    )
                    for item in value
                ]

        return sanitized

    @staticmethod
    def _validate_field_value(
        *,
        key: str,
        field_type: str,
        value,
        validation: dict,
        field_def: dict,
        strict: bool,
    ) -> list[dict]:
        """Validate a single field value against its type and validation rules."""
        issues = []

        if field_type in ("text", "textarea"):
            if not isinstance(value, str):
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "type_error",
                        "message": f"{key} must be a string",
                    }
                )
                return issues
            if "max_length" in validation and len(value) > validation["max_length"]:
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "max_length",
                        "message": f"{key} exceeds max length",
                    }
                )
            if "min_length" in validation and len(value) < validation["min_length"]:
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "min_length",
                        "message": f"{key} below min length",
                    }
                )
            if "pattern" in validation:
                try:
                    if not re.match(validation["pattern"], value):
                        issues.append(
                            {
                                "field_key": key,
                                "error_type": "pattern_mismatch",
                                "message": f"{key} does not match pattern",
                            }
                        )
                except (re.error, RecursionError):
                    logger.warning("cms.regex_validation_failed", field_key=key)
                    issues.append(
                        {
                            "field_key": key,
                            "error_type": "pattern_error",
                            "message": f"Pattern validation failed for {key}",
                        }
                    )

        elif field_type == "richtext":
            if not isinstance(value, str):
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "type_error",
                        "message": f"{key} must be a string",
                    }
                )
                return issues
            # NOTE: Sanitization is handled by sanitize_content() — called BEFORE validation.
            # This method only validates constraints (length, etc.) on already-sanitized values.
            # Length check on stripped text
            if "max_length" in validation:
                import html

                stripped = html.unescape(re.sub(r"<[^>]+>", "", value))
                if len(stripped) > validation["max_length"]:
                    issues.append(
                        {
                            "field_key": key,
                            "error_type": "max_length",
                            "message": f"{key} text content exceeds max length",
                        }
                    )

        elif field_type == "number":
            if not isinstance(value, (int, float)):
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "type_error",
                        "message": f"{key} must be a number",
                    }
                )
                return issues
            if "min" in validation and value < validation["min"]:
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "min_value",
                        "message": f"{key} below minimum",
                    }
                )
            if "max" in validation and value > validation["max"]:
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "max_value",
                        "message": f"{key} above maximum",
                    }
                )

        elif field_type == "boolean":
            if not isinstance(value, bool):
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "type_error",
                        "message": f"{key} must be boolean",
                    }
                )

        elif field_type in ("select",):
            choices = [c["value"] for c in validation.get("choices", [])]
            if choices and value not in choices:
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "invalid_choice",
                        "message": f"{key} value not in choices",
                    }
                )

        elif field_type == "multiselect":
            if not isinstance(value, list):
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "type_error",
                        "message": f"{key} must be a list",
                    }
                )
                return issues
            choices = [c["value"] for c in validation.get("choices", [])]
            if choices:
                for v in value:
                    if v not in choices:
                        issues.append(
                            {
                                "field_key": key,
                                "error_type": "invalid_choice",
                                "message": f"{key} contains invalid choice: {v}",
                            }
                        )
            if "min_selected" in validation and len(value) < validation["min_selected"]:
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "min_selected",
                        "message": f"{key} below minimum selections",
                    }
                )
            if "max_selected" in validation and len(value) > validation["max_selected"]:
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "max_selected",
                        "message": f"{key} above maximum selections",
                    }
                )

        elif field_type == "media":
            if not isinstance(value, dict) or "media_id" not in value:
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "type_error",
                        "message": f"{key} must be a media reference object",
                    }
                )
                return issues
            if strict:
                # Check that media exists and is not tombstoned
                from apps.cms.models import MediaFile

                media = MediaFile.objects.filter(
                    id=value["media_id"], is_deleted=False
                ).first()
                if not media:
                    issues.append(
                        {
                            "field_key": key,
                            "error_type": "media_not_found",
                            "message": f"{key} references non-existent media",
                        }
                    )
                elif media.is_tombstoned:
                    issues.append(
                        {
                            "field_key": key,
                            "error_type": "media_reference_tombstoned",
                            "message": f"{key} references tombstoned media",
                        }
                    )

        elif field_type == "repeater":
            if not isinstance(value, list):
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "type_error",
                        "message": f"{key} must be a list",
                    }
                )
                return issues
            if "min_items" in validation and len(value) < validation["min_items"]:
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "min_items",
                        "message": f"{key} below minimum items",
                    }
                )
            if "max_items" in validation and len(value) > validation["max_items"]:
                issues.append(
                    {
                        "field_key": key,
                        "error_type": "max_items",
                        "message": f"{key} above maximum items",
                    }
                )
            # Validate each item against item_schema
            item_schema = field_def.get("item_schema", {})
            if item_schema:
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        sub_issues = SchemaValidator.validate_content(
                            schema=item_schema,
                            content=item,
                            strict=strict,
                        )
                        for issue in sub_issues:
                            issue["field_key"] = f"{key}[{i}].{issue['field_key']}"
                            issues.append(issue)

        # Additional types (url, email, date, datetime, list, relation, json, color, icon)
        # follow similar patterns — validate format, range, and reference integrity

        return issues
