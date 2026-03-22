"""
Field-type validators for form response data.

Validates that submitted values match their declared field types.
Called during submit_response(), create_and_submit(), and update_after_info_request().
"""

import re
from typing import Any, Dict, List

from apps.core.constants import FieldType

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
URL_REGEX = re.compile(r"^https?://.+\..+")
PHONE_REGEX = re.compile(r"^[+]?[\d\s().\-]{7,20}$")


def validate_field_values(
    fields: List,
    data: Dict[str, Any],
) -> List[str]:
    """
    Validate field values in data against their declared field types.

    Args:
        fields: QuerySet or list of FormField objects with field_key, field_type,
                validation_rules, options, is_required, is_hidden.
        data: The submitted response data dict.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []

    for field in fields:
        if field.is_hidden:
            continue

        value = data.get(field.field_key)
        is_empty = value is None or value == ""

        if is_empty:
            continue

        error = _validate_single_field(field, value)
        if error:
            errors.append(f"{field.label}: {error}")

    return errors


def _validate_single_field(field, value: Any) -> str | None:
    """Validate a single field value. Returns error string or None."""
    rules = field.validation_rules or {}
    ft = field.field_type

    # ---- Text-like ----
    if ft == FieldType.EMAIL:
        if not isinstance(value, str) or not EMAIL_REGEX.match(value):
            return "Invalid email address"

    elif ft == FieldType.URL:
        if not isinstance(value, str) or not URL_REGEX.match(value):
            return "Invalid URL (must start with http:// or https://)"

    elif ft == FieldType.PHONE:
        if not isinstance(value, str) or not PHONE_REGEX.match(value):
            return "Invalid phone number"

    elif ft in (FieldType.TEXT, FieldType.TEXTAREA, FieldType.LOCATION):
        if not isinstance(value, str):
            return "Must be text"
        min_len = rules.get("min_length")
        max_len = rules.get("max_length")
        if min_len and len(value) < min_len:
            return f"Must be at least {min_len} characters"
        if max_len and len(value) > max_len:
            return f"Must be at most {max_len} characters"

    # ---- Numeric ----
    elif ft == FieldType.INTEGER:
        if not isinstance(value, int) or isinstance(value, bool):
            return "Must be a whole number"
        _err = _check_numeric_bounds(value, rules)
        if _err:
            return _err

    elif ft in (FieldType.DECIMAL, FieldType.CURRENCY):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return "Must be a number"
        _err = _check_numeric_bounds(value, rules)
        if _err:
            return _err

    elif ft == FieldType.RATING:
        if not isinstance(value, int) or isinstance(value, bool):
            return "Must be a whole number"
        max_val = rules.get("max", 5)
        if value < 1 or value > max_val:
            return f"Must be between 1 and {max_val}"

    # ---- Boolean ----
    elif ft in (FieldType.BOOLEAN, FieldType.CHECKBOX):
        if not isinstance(value, bool):
            return "Must be true or false"

    # ---- Date/Time ----
    elif ft == FieldType.DATE:
        if not isinstance(value, str):
            return "Must be a date string"
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return "Must be in YYYY-MM-DD format"

    elif ft == FieldType.DATETIME:
        if not isinstance(value, str):
            return "Must be a datetime string"

    elif ft == FieldType.TIME:
        if not isinstance(value, str):
            return "Must be a time string"
        if not re.match(r"^\d{2}:\d{2}(:\d{2})?$", value):
            return "Must be in HH:MM format"

    # ---- Selection ----
    elif ft in (FieldType.SELECT, FieldType.RADIO):
        if not isinstance(value, str):
            return "Must be a string"
        valid_values = _get_option_values(field)
        if valid_values and value not in valid_values:
            return "Invalid option selected"

    elif ft in (FieldType.MULTISELECT, FieldType.CHECKBOX_GROUP):
        if not isinstance(value, list):
            return "Must be a list of selected values"
        valid_values = _get_option_values(field)
        if valid_values:
            invalid = [v for v in value if v not in valid_values]
            if invalid:
                return f"Invalid options: {', '.join(str(v) for v in invalid)}"

    # File/Image fields store URLs (strings) in JSON data — files are uploaded separately
    elif ft in (FieldType.FILE, FieldType.IMAGE):
        if not isinstance(value, str):
            return "Must be a file URL string"

    return None


def _check_numeric_bounds(value, rules: dict) -> str | None:
    min_val = rules.get("min")
    max_val = rules.get("max")
    if min_val is not None and value < min_val:
        return f"Must be at least {min_val}"
    if max_val is not None and value > max_val:
        return f"Must be at most {max_val}"
    return None


def _get_option_values(field) -> list[str]:
    options = field.options
    if not isinstance(options, list):
        return []
    result = []
    for opt in options:
        if isinstance(opt, str):
            result.append(opt)
        elif isinstance(opt, dict):
            result.append(str(opt.get("value", opt.get("label", ""))))
    return result
