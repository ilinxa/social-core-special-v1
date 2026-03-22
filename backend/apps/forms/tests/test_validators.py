# apps/forms/tests/test_validators.py
"""
Comprehensive tests for field-type validators.

Covers:
- validate_field_values (aggregate function)
- _validate_single_field (per-type validation)
- _check_numeric_bounds (min/max rules)
- _get_option_values (string / dict options)
- All 21 handled FieldType variants
- Hidden field skipping, empty value skipping, label prefixing
"""

from types import SimpleNamespace

import pytest

from apps.core.constants import FieldType
from apps.forms.validators import (
    _check_numeric_bounds,
    _get_option_values,
    _validate_single_field,
    validate_field_values,
)

# ---------------------------------------------------------------------------
# Helper: mock field object
# ---------------------------------------------------------------------------


def make_field(
    field_type,
    field_key="test_field",
    label="Test Field",
    validation_rules=None,
    options=None,
    is_required=False,
    is_hidden=False,
    is_readonly=False,
):
    return SimpleNamespace(
        field_type=field_type,
        field_key=field_key,
        label=label,
        validation_rules=validation_rules or {},
        options=options,
        is_required=is_required,
        is_hidden=is_hidden,
        is_readonly=is_readonly,
    )


# =============================================================================
# validate_field_values — Aggregate Function
# =============================================================================


class TestValidateFieldValues:
    """Tests for the top-level validate_field_values function."""

    def test_returns_empty_list_when_all_valid(self):
        fields = [
            make_field(FieldType.TEXT, field_key="name"),
            make_field(FieldType.EMAIL, field_key="email"),
        ]
        data = {"name": "Alice", "email": "alice@example.com"}

        errors = validate_field_values(fields, data)

        assert errors == []

    def test_returns_errors_with_label_prefix(self):
        """Error messages must start with the field label."""
        field = make_field(FieldType.EMAIL, field_key="email", label="Email Address")
        data = {"email": "not-an-email"}

        errors = validate_field_values([field], data)

        assert len(errors) == 1
        assert errors[0].startswith("Email Address: ")
        assert "Invalid email address" in errors[0]

    def test_skips_hidden_fields(self):
        """Hidden fields should be completely ignored, even if value is invalid."""
        field = make_field(FieldType.EMAIL, field_key="hidden_email", is_hidden=True)
        data = {"hidden_email": "not-valid"}

        errors = validate_field_values([field], data)

        assert errors == []

    def test_skips_none_values(self):
        """None values are skipped (required check is handled elsewhere)."""
        field = make_field(FieldType.EMAIL, field_key="email")
        data = {"email": None}

        errors = validate_field_values([field], data)

        assert errors == []

    def test_skips_empty_string_values(self):
        """Empty string values are skipped."""
        field = make_field(FieldType.TEXT, field_key="name")
        data = {"name": ""}

        errors = validate_field_values([field], data)

        assert errors == []

    def test_skips_missing_keys(self):
        """If a field key is not present in data at all, skip it."""
        field = make_field(FieldType.TEXT, field_key="not_in_data")
        data = {}

        errors = validate_field_values([field], data)

        assert errors == []

    def test_multiple_errors_collected(self):
        """Multiple invalid fields should produce multiple errors."""
        fields = [
            make_field(FieldType.EMAIL, field_key="email", label="Email"),
            make_field(FieldType.INTEGER, field_key="age", label="Age"),
            make_field(FieldType.URL, field_key="website", label="Website"),
        ]
        data = {"email": "bad", "age": "not-a-number", "website": "no-protocol"}

        errors = validate_field_values(fields, data)

        assert len(errors) == 3
        labels = [e.split(":")[0] for e in errors]
        assert "Email" in labels
        assert "Age" in labels
        assert "Website" in labels

    def test_mix_of_valid_and_invalid(self):
        """Only invalid fields produce errors; valid ones pass silently."""
        fields = [
            make_field(FieldType.TEXT, field_key="name", label="Name"),
            make_field(FieldType.EMAIL, field_key="email", label="Email"),
        ]
        data = {"name": "Valid Name", "email": "bad-email"}

        errors = validate_field_values(fields, data)

        assert len(errors) == 1
        assert errors[0].startswith("Email:")

    def test_hidden_field_with_valid_value_still_skipped(self):
        """Even a valid value on a hidden field should not be validated."""
        field = make_field(FieldType.TEXT, field_key="secret", is_hidden=True)
        data = {"secret": "valid text"}

        errors = validate_field_values([field], data)

        assert errors == []


# =============================================================================
# Text-like Fields (TEXT, TEXTAREA, LOCATION)
# =============================================================================


class TestTextFields:
    """Tests for TEXT, TEXTAREA, and LOCATION field types."""

    @pytest.mark.parametrize(
        "field_type", [FieldType.TEXT, FieldType.TEXTAREA, FieldType.LOCATION]
    )
    def test_valid_string(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, "hello world") is None

    @pytest.mark.parametrize(
        "field_type", [FieldType.TEXT, FieldType.TEXTAREA, FieldType.LOCATION]
    )
    def test_non_string_value(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, 123) == "Must be text"

    @pytest.mark.parametrize(
        "field_type", [FieldType.TEXT, FieldType.TEXTAREA, FieldType.LOCATION]
    )
    def test_list_value_rejected(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, ["a", "b"]) == "Must be text"

    @pytest.mark.parametrize(
        "field_type", [FieldType.TEXT, FieldType.TEXTAREA, FieldType.LOCATION]
    )
    def test_bool_value_rejected(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, True) == "Must be text"

    def test_min_length_violation(self):
        field = make_field(FieldType.TEXT, validation_rules={"min_length": 5})
        assert _validate_single_field(field, "abc") == "Must be at least 5 characters"

    def test_min_length_exact_boundary(self):
        field = make_field(FieldType.TEXT, validation_rules={"min_length": 3})
        assert _validate_single_field(field, "abc") is None

    def test_max_length_violation(self):
        field = make_field(FieldType.TEXT, validation_rules={"max_length": 5})
        assert (
            _validate_single_field(field, "too long text")
            == "Must be at most 5 characters"
        )

    def test_max_length_exact_boundary(self):
        field = make_field(FieldType.TEXT, validation_rules={"max_length": 5})
        assert _validate_single_field(field, "12345") is None

    def test_min_and_max_length_valid(self):
        field = make_field(
            FieldType.TEXT, validation_rules={"min_length": 2, "max_length": 10}
        )
        assert _validate_single_field(field, "hello") is None

    def test_min_and_max_length_too_short(self):
        field = make_field(
            FieldType.TEXT, validation_rules={"min_length": 5, "max_length": 10}
        )
        assert _validate_single_field(field, "hi") == "Must be at least 5 characters"

    def test_min_and_max_length_too_long(self):
        field = make_field(
            FieldType.TEXT, validation_rules={"min_length": 2, "max_length": 5}
        )
        assert (
            _validate_single_field(field, "way too long")
            == "Must be at most 5 characters"
        )

    def test_textarea_with_multiline_string(self):
        field = make_field(FieldType.TEXTAREA)
        assert _validate_single_field(field, "line 1\nline 2\nline 3") is None

    def test_location_with_address_string(self):
        field = make_field(FieldType.LOCATION)
        assert _validate_single_field(field, "123 Main St, New York, NY 10001") is None

    def test_no_validation_rules_defaults_to_empty(self):
        """When validation_rules is None, it defaults to {} — no length checks."""
        field = make_field(FieldType.TEXT, validation_rules=None)
        assert _validate_single_field(field, "any length text here") is None


# =============================================================================
# Email
# =============================================================================


class TestEmailField:
    """Tests for EMAIL field type."""

    @pytest.mark.parametrize(
        "email",
        [
            "user@example.com",
            "user.name+tag@domain.co",
            "a@b.c",
            "test@sub.domain.example.org",
        ],
    )
    def test_valid_emails(self, email):
        field = make_field(FieldType.EMAIL)
        assert _validate_single_field(field, email) is None

    @pytest.mark.parametrize(
        "email",
        [
            "not-an-email",
            "@example.com",
            "user@",
            "user @example.com",
            "",
            "user@.com",
        ],
    )
    def test_invalid_emails(self, email):
        field = make_field(FieldType.EMAIL)
        assert _validate_single_field(field, email) == "Invalid email address"

    def test_non_string_type(self):
        field = make_field(FieldType.EMAIL)
        assert _validate_single_field(field, 123) == "Invalid email address"

    def test_none_is_not_string(self):
        field = make_field(FieldType.EMAIL)
        assert _validate_single_field(field, None) == "Invalid email address"

    def test_list_rejected(self):
        field = make_field(FieldType.EMAIL)
        assert (
            _validate_single_field(field, ["user@example.com"])
            == "Invalid email address"
        )


# =============================================================================
# URL
# =============================================================================


class TestUrlField:
    """Tests for URL field type."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://example.com",
            "https://example.com",
            "https://www.example.com/path",
            "http://sub.domain.co/page?q=1",
            "https://a.b",
        ],
    )
    def test_valid_urls(self, url):
        field = make_field(FieldType.URL)
        assert _validate_single_field(field, url) is None

    @pytest.mark.parametrize(
        "url",
        [
            "example.com",
            "ftp://example.com",
            "not a url",
            "//example.com",
            "http:/example.com",
        ],
    )
    def test_invalid_urls(self, url):
        field = make_field(FieldType.URL)
        result = _validate_single_field(field, url)
        assert result == "Invalid URL (must start with http:// or https://)"

    def test_non_string_type(self):
        field = make_field(FieldType.URL)
        assert (
            _validate_single_field(field, 123)
            == "Invalid URL (must start with http:// or https://)"
        )

    def test_bool_rejected(self):
        field = make_field(FieldType.URL)
        assert (
            _validate_single_field(field, True)
            == "Invalid URL (must start with http:// or https://)"
        )


# =============================================================================
# Phone
# =============================================================================


class TestPhoneField:
    """Tests for PHONE field type."""

    @pytest.mark.parametrize(
        "phone",
        [
            "+1234567890",
            "1234567890",
            "+1 (234) 567-8901",
            "123.456.7890",
            "(123) 456 7890",
            "+44 20 7946 0958",
        ],
    )
    def test_valid_phones(self, phone):
        field = make_field(FieldType.PHONE)
        assert _validate_single_field(field, phone) is None

    @pytest.mark.parametrize(
        "phone",
        [
            "123",
            "abc",
            "+1-abc-def-ghij",
            "123456789012345678901",  # 21 chars, exceeds 20
        ],
    )
    def test_invalid_phones(self, phone):
        field = make_field(FieldType.PHONE)
        assert _validate_single_field(field, phone) == "Invalid phone number"

    def test_non_string_type(self):
        field = make_field(FieldType.PHONE)
        assert _validate_single_field(field, 1234567890) == "Invalid phone number"


# =============================================================================
# Integer
# =============================================================================


class TestIntegerField:
    """Tests for INTEGER field type."""

    def test_valid_integer(self):
        field = make_field(FieldType.INTEGER)
        assert _validate_single_field(field, 42) is None

    def test_zero_is_valid(self):
        field = make_field(FieldType.INTEGER)
        assert _validate_single_field(field, 0) is None

    def test_negative_integer(self):
        field = make_field(FieldType.INTEGER)
        assert _validate_single_field(field, -5) is None

    def test_float_rejected(self):
        field = make_field(FieldType.INTEGER)
        assert _validate_single_field(field, 3.14) == "Must be a whole number"

    def test_string_rejected(self):
        field = make_field(FieldType.INTEGER)
        assert _validate_single_field(field, "42") == "Must be a whole number"

    def test_bool_rejected(self):
        """Python bool is subclass of int, but must be explicitly rejected."""
        field = make_field(FieldType.INTEGER)
        assert _validate_single_field(field, True) == "Must be a whole number"

    def test_bool_false_rejected(self):
        field = make_field(FieldType.INTEGER)
        assert _validate_single_field(field, False) == "Must be a whole number"

    def test_none_rejected(self):
        field = make_field(FieldType.INTEGER)
        assert _validate_single_field(field, None) == "Must be a whole number"

    def test_min_bound_violation(self):
        field = make_field(FieldType.INTEGER, validation_rules={"min": 10})
        assert _validate_single_field(field, 5) == "Must be at least 10"

    def test_min_bound_exact(self):
        field = make_field(FieldType.INTEGER, validation_rules={"min": 10})
        assert _validate_single_field(field, 10) is None

    def test_max_bound_violation(self):
        field = make_field(FieldType.INTEGER, validation_rules={"max": 100})
        assert _validate_single_field(field, 150) == "Must be at most 100"

    def test_max_bound_exact(self):
        field = make_field(FieldType.INTEGER, validation_rules={"max": 100})
        assert _validate_single_field(field, 100) is None

    def test_min_and_max_bounds_valid(self):
        field = make_field(FieldType.INTEGER, validation_rules={"min": 1, "max": 10})
        assert _validate_single_field(field, 5) is None

    def test_min_and_max_bounds_below(self):
        field = make_field(FieldType.INTEGER, validation_rules={"min": 1, "max": 10})
        assert _validate_single_field(field, 0) == "Must be at least 1"

    def test_min_and_max_bounds_above(self):
        field = make_field(FieldType.INTEGER, validation_rules={"min": 1, "max": 10})
        assert _validate_single_field(field, 11) == "Must be at most 10"


# =============================================================================
# Decimal / Currency
# =============================================================================


class TestDecimalCurrencyFields:
    """Tests for DECIMAL and CURRENCY field types."""

    @pytest.mark.parametrize("field_type", [FieldType.DECIMAL, FieldType.CURRENCY])
    def test_valid_float(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, 3.14) is None

    @pytest.mark.parametrize("field_type", [FieldType.DECIMAL, FieldType.CURRENCY])
    def test_integer_accepted(self, field_type):
        """Integers should be accepted since they're a subset of numeric types."""
        field = make_field(field_type)
        assert _validate_single_field(field, 42) is None

    @pytest.mark.parametrize("field_type", [FieldType.DECIMAL, FieldType.CURRENCY])
    def test_zero_valid(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, 0) is None

    @pytest.mark.parametrize("field_type", [FieldType.DECIMAL, FieldType.CURRENCY])
    def test_negative_float(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, -9.99) is None

    @pytest.mark.parametrize("field_type", [FieldType.DECIMAL, FieldType.CURRENCY])
    def test_string_rejected(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, "3.14") == "Must be a number"

    @pytest.mark.parametrize("field_type", [FieldType.DECIMAL, FieldType.CURRENCY])
    def test_bool_rejected(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, True) == "Must be a number"

    @pytest.mark.parametrize("field_type", [FieldType.DECIMAL, FieldType.CURRENCY])
    def test_none_rejected(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, None) == "Must be a number"

    def test_decimal_min_bound(self):
        field = make_field(FieldType.DECIMAL, validation_rules={"min": 0.0})
        assert _validate_single_field(field, -0.01) == "Must be at least 0.0"

    def test_decimal_max_bound(self):
        field = make_field(FieldType.DECIMAL, validation_rules={"max": 99.99})
        assert _validate_single_field(field, 100.0) == "Must be at most 99.99"

    def test_currency_min_bound(self):
        field = make_field(FieldType.CURRENCY, validation_rules={"min": 0})
        assert _validate_single_field(field, -1) == "Must be at least 0"

    def test_currency_max_bound(self):
        field = make_field(FieldType.CURRENCY, validation_rules={"max": 1000})
        assert _validate_single_field(field, 1001) == "Must be at most 1000"

    def test_float_zero_accepted(self):
        field = make_field(FieldType.DECIMAL)
        assert _validate_single_field(field, 0.0) is None


# =============================================================================
# Rating
# =============================================================================


class TestRatingField:
    """Tests for RATING field type."""

    def test_valid_rating(self):
        field = make_field(FieldType.RATING)
        assert _validate_single_field(field, 3) is None

    def test_rating_one(self):
        field = make_field(FieldType.RATING)
        assert _validate_single_field(field, 1) is None

    def test_rating_default_max_five(self):
        """Default max is 5 when not specified in validation_rules."""
        field = make_field(FieldType.RATING)
        assert _validate_single_field(field, 5) is None

    def test_rating_above_default_max(self):
        field = make_field(FieldType.RATING)
        assert _validate_single_field(field, 6) == "Must be between 1 and 5"

    def test_rating_zero_invalid(self):
        field = make_field(FieldType.RATING)
        assert _validate_single_field(field, 0) == "Must be between 1 and 5"

    def test_rating_negative_invalid(self):
        field = make_field(FieldType.RATING)
        assert _validate_single_field(field, -1) == "Must be between 1 and 5"

    def test_custom_max_rating(self):
        field = make_field(FieldType.RATING, validation_rules={"max": 10})
        assert _validate_single_field(field, 10) is None

    def test_custom_max_rating_exceeded(self):
        field = make_field(FieldType.RATING, validation_rules={"max": 10})
        assert _validate_single_field(field, 11) == "Must be between 1 and 10"

    def test_float_rejected(self):
        field = make_field(FieldType.RATING)
        assert _validate_single_field(field, 3.5) == "Must be a whole number"

    def test_string_rejected(self):
        field = make_field(FieldType.RATING)
        assert _validate_single_field(field, "5") == "Must be a whole number"

    def test_bool_rejected(self):
        field = make_field(FieldType.RATING)
        assert _validate_single_field(field, True) == "Must be a whole number"


# =============================================================================
# Boolean / Checkbox
# =============================================================================


class TestBooleanCheckboxFields:
    """Tests for BOOLEAN and CHECKBOX field types."""

    @pytest.mark.parametrize("field_type", [FieldType.BOOLEAN, FieldType.CHECKBOX])
    def test_true_valid(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, True) is None

    @pytest.mark.parametrize("field_type", [FieldType.BOOLEAN, FieldType.CHECKBOX])
    def test_false_valid(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, False) is None

    @pytest.mark.parametrize("field_type", [FieldType.BOOLEAN, FieldType.CHECKBOX])
    def test_string_rejected(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, "true") == "Must be true or false"

    @pytest.mark.parametrize("field_type", [FieldType.BOOLEAN, FieldType.CHECKBOX])
    def test_integer_rejected(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, 1) == "Must be true or false"

    @pytest.mark.parametrize("field_type", [FieldType.BOOLEAN, FieldType.CHECKBOX])
    def test_zero_rejected(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, 0) == "Must be true or false"

    @pytest.mark.parametrize("field_type", [FieldType.BOOLEAN, FieldType.CHECKBOX])
    def test_none_rejected(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, None) == "Must be true or false"


# =============================================================================
# Date
# =============================================================================


class TestDateField:
    """Tests for DATE field type."""

    @pytest.mark.parametrize(
        "date_str",
        [
            "2024-01-01",
            "2000-12-31",
            "1999-06-15",
        ],
    )
    def test_valid_date(self, date_str):
        field = make_field(FieldType.DATE)
        assert _validate_single_field(field, date_str) is None

    @pytest.mark.parametrize(
        "date_str",
        [
            "01-01-2024",
            "2024/01/01",
            "Jan 1, 2024",
            "2024-1-1",
            "2024-01-01T00:00:00",
        ],
    )
    def test_invalid_date_format(self, date_str):
        field = make_field(FieldType.DATE)
        result = _validate_single_field(field, date_str)
        assert result == "Must be in YYYY-MM-DD format"

    def test_semantic_invalid_date_passes_format_check(self):
        """Regex checks format only, not semantic validity (e.g., month 13)."""
        field = make_field(FieldType.DATE)
        assert _validate_single_field(field, "2024-13-01") is None

    def test_non_string_type(self):
        field = make_field(FieldType.DATE)
        assert _validate_single_field(field, 20240101) == "Must be a date string"

    def test_none_rejected(self):
        field = make_field(FieldType.DATE)
        assert _validate_single_field(field, None) == "Must be a date string"

    def test_bool_rejected(self):
        field = make_field(FieldType.DATE)
        assert _validate_single_field(field, True) == "Must be a date string"

    def test_correct_format_message(self):
        field = make_field(FieldType.DATE)
        assert (
            _validate_single_field(field, "not-a-date")
            == "Must be in YYYY-MM-DD format"
        )


# =============================================================================
# Datetime
# =============================================================================


class TestDatetimeField:
    """Tests for DATETIME field type."""

    @pytest.mark.parametrize(
        "dt_str",
        [
            "2024-01-01T00:00:00",
            "2024-01-01T12:30:45Z",
            "2024-01-01T12:30:45+05:00",
            "2024-01-01 12:30:45",
            "any-string-at-all",  # Datetime only checks isinstance(str) currently
        ],
    )
    def test_valid_datetime_strings(self, dt_str):
        """Datetime validator only checks that value is a string."""
        field = make_field(FieldType.DATETIME)
        assert _validate_single_field(field, dt_str) is None

    def test_non_string_type(self):
        field = make_field(FieldType.DATETIME)
        assert _validate_single_field(field, 1234567890) == "Must be a datetime string"

    def test_none_rejected(self):
        field = make_field(FieldType.DATETIME)
        assert _validate_single_field(field, None) == "Must be a datetime string"

    def test_list_rejected(self):
        field = make_field(FieldType.DATETIME)
        assert _validate_single_field(field, []) == "Must be a datetime string"

    def test_bool_rejected(self):
        field = make_field(FieldType.DATETIME)
        assert _validate_single_field(field, False) == "Must be a datetime string"


# =============================================================================
# Time
# =============================================================================


class TestTimeField:
    """Tests for TIME field type."""

    @pytest.mark.parametrize(
        "time_str",
        [
            "09:00",
            "23:59",
            "00:00",
            "12:30:45",  # With seconds
        ],
    )
    def test_valid_time(self, time_str):
        field = make_field(FieldType.TIME)
        assert _validate_single_field(field, time_str) is None

    @pytest.mark.parametrize(
        "time_str",
        [
            "9:00",  # Single digit hour
            "12:30:45.123",
            "noon",
            "12:30 PM",
        ],
    )
    def test_invalid_time_format(self, time_str):
        field = make_field(FieldType.TIME)
        result = _validate_single_field(field, time_str)
        assert result == "Must be in HH:MM format"

    def test_semantic_invalid_time_passes_format_check(self):
        """Regex checks format only, not semantic validity (e.g., hour 25)."""
        field = make_field(FieldType.TIME)
        assert _validate_single_field(field, "25:00") is None

    def test_non_string_type(self):
        field = make_field(FieldType.TIME)
        assert _validate_single_field(field, 900) == "Must be a time string"

    def test_format_error_message(self):
        field = make_field(FieldType.TIME)
        assert _validate_single_field(field, "not-a-time") == "Must be in HH:MM format"


# =============================================================================
# Select / Radio (Single Selection)
# =============================================================================


class TestSelectRadioFields:
    """Tests for SELECT and RADIO field types."""

    @pytest.mark.parametrize("field_type", [FieldType.SELECT, FieldType.RADIO])
    def test_valid_string_option(self, field_type):
        field = make_field(field_type, options=["red", "green", "blue"])
        assert _validate_single_field(field, "red") is None

    @pytest.mark.parametrize("field_type", [FieldType.SELECT, FieldType.RADIO])
    def test_invalid_option(self, field_type):
        field = make_field(field_type, options=["red", "green", "blue"])
        assert _validate_single_field(field, "yellow") == "Invalid option selected"

    @pytest.mark.parametrize("field_type", [FieldType.SELECT, FieldType.RADIO])
    def test_non_string_rejected(self, field_type):
        field = make_field(field_type, options=["a", "b"])
        assert _validate_single_field(field, 123) == "Must be a string"

    @pytest.mark.parametrize("field_type", [FieldType.SELECT, FieldType.RADIO])
    def test_list_rejected(self, field_type):
        field = make_field(field_type, options=["a", "b"])
        assert _validate_single_field(field, ["a"]) == "Must be a string"

    @pytest.mark.parametrize("field_type", [FieldType.SELECT, FieldType.RADIO])
    def test_dict_options_with_value_key(self, field_type):
        field = make_field(
            field_type,
            options=[
                {"label": "Red", "value": "red"},
                {"label": "Green", "value": "green"},
            ],
        )
        assert _validate_single_field(field, "red") is None

    @pytest.mark.parametrize("field_type", [FieldType.SELECT, FieldType.RADIO])
    def test_dict_options_invalid(self, field_type):
        field = make_field(
            field_type,
            options=[
                {"label": "Red", "value": "red"},
            ],
        )
        assert _validate_single_field(field, "blue") == "Invalid option selected"

    @pytest.mark.parametrize("field_type", [FieldType.SELECT, FieldType.RADIO])
    def test_no_options_skips_validation(self, field_type):
        """When options is None, skip option validation — just check string type."""
        field = make_field(field_type, options=None)
        assert _validate_single_field(field, "anything") is None

    @pytest.mark.parametrize("field_type", [FieldType.SELECT, FieldType.RADIO])
    def test_empty_list_options_skips_validation(self, field_type):
        """When options list is empty, no valid values to check — skip."""
        field = make_field(field_type, options=[])
        assert _validate_single_field(field, "anything") is None


# =============================================================================
# Multiselect / Checkbox Group (Multi Selection)
# =============================================================================


class TestMultiselectCheckboxGroupFields:
    """Tests for MULTISELECT and CHECKBOX_GROUP field types."""

    @pytest.mark.parametrize(
        "field_type", [FieldType.MULTISELECT, FieldType.CHECKBOX_GROUP]
    )
    def test_valid_list_of_options(self, field_type):
        field = make_field(field_type, options=["a", "b", "c"])
        assert _validate_single_field(field, ["a", "c"]) is None

    @pytest.mark.parametrize(
        "field_type", [FieldType.MULTISELECT, FieldType.CHECKBOX_GROUP]
    )
    def test_empty_list_valid(self, field_type):
        """An empty list is valid — it means nothing selected."""
        field = make_field(field_type, options=["a", "b"])
        assert _validate_single_field(field, []) is None

    @pytest.mark.parametrize(
        "field_type", [FieldType.MULTISELECT, FieldType.CHECKBOX_GROUP]
    )
    def test_non_list_rejected(self, field_type):
        field = make_field(field_type, options=["a", "b"])
        assert _validate_single_field(field, "a") == "Must be a list of selected values"

    @pytest.mark.parametrize(
        "field_type", [FieldType.MULTISELECT, FieldType.CHECKBOX_GROUP]
    )
    def test_integer_rejected(self, field_type):
        field = make_field(field_type, options=["a"])
        assert _validate_single_field(field, 1) == "Must be a list of selected values"

    @pytest.mark.parametrize(
        "field_type", [FieldType.MULTISELECT, FieldType.CHECKBOX_GROUP]
    )
    def test_invalid_option_in_list(self, field_type):
        field = make_field(field_type, options=["a", "b", "c"])
        result = _validate_single_field(field, ["a", "z"])
        assert result == "Invalid options: z"

    @pytest.mark.parametrize(
        "field_type", [FieldType.MULTISELECT, FieldType.CHECKBOX_GROUP]
    )
    def test_multiple_invalid_options(self, field_type):
        field = make_field(field_type, options=["a", "b"])
        result = _validate_single_field(field, ["x", "y", "z"])
        assert result == "Invalid options: x, y, z"

    @pytest.mark.parametrize(
        "field_type", [FieldType.MULTISELECT, FieldType.CHECKBOX_GROUP]
    )
    def test_dict_options_with_value_key(self, field_type):
        field = make_field(
            field_type,
            options=[
                {"label": "Opt A", "value": "a"},
                {"label": "Opt B", "value": "b"},
            ],
        )
        assert _validate_single_field(field, ["a", "b"]) is None

    @pytest.mark.parametrize(
        "field_type", [FieldType.MULTISELECT, FieldType.CHECKBOX_GROUP]
    )
    def test_dict_options_invalid(self, field_type):
        field = make_field(
            field_type,
            options=[
                {"label": "Opt A", "value": "a"},
            ],
        )
        result = _validate_single_field(field, ["a", "bad"])
        assert result == "Invalid options: bad"

    @pytest.mark.parametrize(
        "field_type", [FieldType.MULTISELECT, FieldType.CHECKBOX_GROUP]
    )
    def test_no_options_skips_option_check(self, field_type):
        """When options is None, only the list type check is enforced."""
        field = make_field(field_type, options=None)
        assert _validate_single_field(field, ["anything"]) is None

    @pytest.mark.parametrize(
        "field_type", [FieldType.MULTISELECT, FieldType.CHECKBOX_GROUP]
    )
    def test_empty_options_list_skips_check(self, field_type):
        field = make_field(field_type, options=[])
        assert _validate_single_field(field, ["anything"]) is None


# =============================================================================
# File / Image
# =============================================================================


class TestFileImageFields:
    """Tests for FILE and IMAGE field types."""

    @pytest.mark.parametrize("field_type", [FieldType.FILE, FieldType.IMAGE])
    def test_valid_url_string(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, "https://cdn.example.com/file.pdf") is None

    @pytest.mark.parametrize("field_type", [FieldType.FILE, FieldType.IMAGE])
    def test_any_string_accepted(self, field_type):
        """File/Image fields just check for string type (URL validation is loose)."""
        field = make_field(field_type)
        assert _validate_single_field(field, "/media/uploads/photo.jpg") is None

    @pytest.mark.parametrize("field_type", [FieldType.FILE, FieldType.IMAGE])
    def test_integer_rejected(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, 12345) == "Must be a file URL string"

    @pytest.mark.parametrize("field_type", [FieldType.FILE, FieldType.IMAGE])
    def test_list_rejected(self, field_type):
        field = make_field(field_type)
        assert (
            _validate_single_field(field, ["file.pdf"]) == "Must be a file URL string"
        )

    @pytest.mark.parametrize("field_type", [FieldType.FILE, FieldType.IMAGE])
    def test_none_rejected(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, None) == "Must be a file URL string"

    @pytest.mark.parametrize("field_type", [FieldType.FILE, FieldType.IMAGE])
    def test_bool_rejected(self, field_type):
        field = make_field(field_type)
        assert _validate_single_field(field, True) == "Must be a file URL string"


# =============================================================================
# _check_numeric_bounds (helper)
# =============================================================================


class TestCheckNumericBounds:
    """Tests for the _check_numeric_bounds helper."""

    def test_no_bounds(self):
        assert _check_numeric_bounds(50, {}) is None

    def test_min_only_valid(self):
        assert _check_numeric_bounds(10, {"min": 5}) is None

    def test_min_only_violation(self):
        assert _check_numeric_bounds(3, {"min": 5}) == "Must be at least 5"

    def test_min_exact_boundary(self):
        assert _check_numeric_bounds(5, {"min": 5}) is None

    def test_max_only_valid(self):
        assert _check_numeric_bounds(50, {"max": 100}) is None

    def test_max_only_violation(self):
        assert _check_numeric_bounds(150, {"max": 100}) == "Must be at most 100"

    def test_max_exact_boundary(self):
        assert _check_numeric_bounds(100, {"max": 100}) is None

    def test_both_bounds_valid(self):
        assert _check_numeric_bounds(50, {"min": 1, "max": 100}) is None

    def test_both_bounds_below(self):
        assert _check_numeric_bounds(0, {"min": 1, "max": 100}) == "Must be at least 1"

    def test_both_bounds_above(self):
        assert (
            _check_numeric_bounds(101, {"min": 1, "max": 100}) == "Must be at most 100"
        )

    def test_float_bounds(self):
        assert _check_numeric_bounds(0.5, {"min": 0.0, "max": 1.0}) is None

    def test_float_below_min(self):
        assert _check_numeric_bounds(-0.1, {"min": 0.0}) == "Must be at least 0.0"

    def test_float_above_max(self):
        assert _check_numeric_bounds(1.1, {"max": 1.0}) == "Must be at most 1.0"

    def test_min_zero_allows_zero(self):
        """When min is 0, value 0 should pass (not < 0)."""
        assert _check_numeric_bounds(0, {"min": 0}) is None

    def test_max_zero_allows_zero(self):
        """When max is 0, value 0 should pass (not > 0)."""
        assert _check_numeric_bounds(0, {"max": 0}) is None

    def test_negative_bounds(self):
        assert _check_numeric_bounds(-5, {"min": -10, "max": -1}) is None

    def test_min_none_in_rules_ignored(self):
        """If rules has min key but value is None, treat as no bound."""
        assert _check_numeric_bounds(0, {"min": None}) is None

    def test_max_none_in_rules_ignored(self):
        """If rules has max key but value is None, treat as no bound."""
        assert _check_numeric_bounds(999, {"max": None}) is None


# =============================================================================
# _get_option_values (helper)
# =============================================================================


class TestGetOptionValues:
    """Tests for the _get_option_values helper."""

    def test_string_options(self):
        field = make_field(FieldType.SELECT, options=["a", "b", "c"])
        assert _get_option_values(field) == ["a", "b", "c"]

    def test_dict_options_with_value(self):
        field = make_field(
            FieldType.SELECT,
            options=[
                {"label": "Alpha", "value": "a"},
                {"label": "Beta", "value": "b"},
            ],
        )
        assert _get_option_values(field) == ["a", "b"]

    def test_dict_options_with_label_only(self):
        """If dict has 'label' but no 'value', fallback to label."""
        field = make_field(
            FieldType.SELECT,
            options=[
                {"label": "Alpha"},
            ],
        )
        assert _get_option_values(field) == ["Alpha"]

    def test_dict_options_empty_dict(self):
        """Empty dict falls back to empty string."""
        field = make_field(FieldType.SELECT, options=[{}])
        assert _get_option_values(field) == [""]

    def test_mixed_string_and_dict(self):
        field = make_field(
            FieldType.SELECT,
            options=[
                "simple",
                {"label": "Complex", "value": "complex"},
            ],
        )
        assert _get_option_values(field) == ["simple", "complex"]

    def test_none_options(self):
        """When options is None, returns empty list."""
        field = make_field(FieldType.SELECT, options=None)
        assert _get_option_values(field) == []

    def test_non_list_options(self):
        """When options is not a list (e.g., dict or string), returns empty list."""
        field = make_field(FieldType.SELECT, options="not-a-list")
        assert _get_option_values(field) == []

    def test_int_options(self):
        """When options is an int, returns empty list."""
        field = make_field(FieldType.SELECT, options=42)
        assert _get_option_values(field) == []

    def test_empty_list(self):
        field = make_field(FieldType.SELECT, options=[])
        assert _get_option_values(field) == []

    def test_dict_value_is_integer_cast_to_string(self):
        """Dict value that is an integer should be cast to string via str()."""
        field = make_field(
            FieldType.SELECT,
            options=[
                {"label": "One", "value": 1},
            ],
        )
        assert _get_option_values(field) == ["1"]


# =============================================================================
# Edge Cases / Cross-Cutting
# =============================================================================


class TestEdgeCases:
    """Edge cases and cross-cutting concerns."""

    def test_validation_rules_none_defaults_to_empty_dict(self):
        """_validate_single_field should handle None validation_rules."""
        field = make_field(FieldType.TEXT, validation_rules=None)
        assert _validate_single_field(field, "valid") is None

    def test_unknown_field_type_passes(self):
        """Unknown field types should return None (no validation error)."""
        field = make_field("unknown_type")
        assert _validate_single_field(field, "any value") is None

    def test_integer_field_with_zero_value(self):
        """Zero is a valid integer and should not be treated as empty."""
        field = make_field(FieldType.INTEGER, field_key="count")
        data = {"count": 0}
        errors = validate_field_values([field], data)
        assert errors == []

    def test_boolean_false_not_treated_as_empty(self):
        """False is a valid boolean value and should not be skipped."""
        field = make_field(FieldType.BOOLEAN, field_key="agree")
        data = {"agree": False}
        errors = validate_field_values([field], data)
        assert errors == []

    def test_empty_list_not_treated_as_empty(self):
        """An empty list for multiselect is not None/'' so it reaches validation."""
        field = make_field(FieldType.MULTISELECT, field_key="tags", options=["a"])
        data = {"tags": []}
        errors = validate_field_values([field], data)
        assert errors == []

    def test_multiple_fields_some_hidden_some_missing(self):
        """Mixed scenario: hidden, missing, valid, and invalid fields."""
        fields = [
            make_field(FieldType.TEXT, field_key="visible", label="Visible"),
            make_field(
                FieldType.TEXT, field_key="hidden", label="Hidden", is_hidden=True
            ),
            make_field(FieldType.EMAIL, field_key="missing", label="Missing"),
            make_field(FieldType.INTEGER, field_key="bad", label="Bad Number"),
        ]
        data = {
            "visible": "ok",
            "hidden": 12345,  # Invalid but hidden, should be skipped
            # "missing" not in data, should be skipped
            "bad": "not-a-number",
        }

        errors = validate_field_values(fields, data)

        assert len(errors) == 1
        assert errors[0] == "Bad Number: Must be a whole number"

    def test_error_message_format(self):
        """Verify the exact format: 'Label: error message'."""
        field = make_field(FieldType.EMAIL, field_key="e", label="Contact Email")
        data = {"e": "bad"}

        errors = validate_field_values([field], data)

        assert errors == ["Contact Email: Invalid email address"]

    def test_select_with_numeric_string_option(self):
        """Select option values are always strings — numeric-looking is ok."""
        field = make_field(FieldType.SELECT, options=["1", "2", "3"])
        assert _validate_single_field(field, "2") is None

    def test_multiselect_with_all_valid_options(self):
        field = make_field(FieldType.MULTISELECT, options=["x", "y", "z"])
        assert _validate_single_field(field, ["x", "y", "z"]) is None

    def test_date_regex_format_only(self):
        """Date validator checks format (YYYY-MM-DD), not semantic validity."""
        field = make_field(FieldType.DATE)
        # 2024-99-99 matches the regex but is not a real date
        assert _validate_single_field(field, "2024-99-99") is None

    def test_time_with_seconds(self):
        """HH:MM:SS format should be accepted."""
        field = make_field(FieldType.TIME)
        assert _validate_single_field(field, "14:30:59") is None

    def test_time_without_seconds(self):
        """HH:MM format should be accepted."""
        field = make_field(FieldType.TIME)
        assert _validate_single_field(field, "14:30") is None

    def test_readonly_field_still_validated(self):
        """is_readonly does not affect validation — only is_hidden skips."""
        field = make_field(FieldType.EMAIL, field_key="email", is_readonly=True)
        data = {"email": "bad"}

        errors = validate_field_values([field], data)

        assert len(errors) == 1

    def test_large_number_of_fields(self):
        """Validate many fields at once to ensure no issues with scale."""
        fields = [
            make_field(FieldType.TEXT, field_key=f"field_{i}", label=f"Field {i}")
            for i in range(100)
        ]
        data = {f"field_{i}": f"value {i}" for i in range(100)}

        errors = validate_field_values(fields, data)

        assert errors == []
