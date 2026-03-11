# apps/forms/tests/test_indexing.py
"""
Tests for IndexService — extract, store, clear, and rebuild typed field indexes.

Covers value coercion, per-type index table creation, edge cases (None, missing
keys, non-indexable fields, coercion failures), and the clear/rebuild lifecycle.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from apps.core.constants import FieldType, StorageType, ResponseStatus
from apps.forms.indexing import IndexService, INDEX_TABLE_MAP
from apps.forms.models import (
    FormField,
    TextFieldIndex,
    IntegerFieldIndex,
    DecimalFieldIndex,
    BooleanFieldIndex,
    DateFieldIndex,
    DateTimeFieldIndex,
)
from apps.forms.tests.factories import (
    ActiveFormTemplateFactory,
    FormFieldFactory,
    FormResponseFactory,
)


# =============================================================================
# IndexService.extract_and_store
# =============================================================================


@pytest.mark.django_db
class TestIndexServiceExtractAndStore:
    """Tests for extracting response data and storing typed index entries."""

    def test_extract_text_field(self):
        """Indexed text field creates TextFieldIndex with the correct value."""
        form = ActiveFormTemplateFactory()
        FormFieldFactory(
            form_template=form,
            field_key="name",
            field_type=FieldType.TEXT,
            is_indexed=True,
        )
        response = FormResponseFactory(
            form_template=form,
            data={"name": "John"},
        )

        count = IndexService.extract_and_store(response=response)

        assert count == 1
        idx = TextFieldIndex.objects.get(response=response, field_key="name")
        assert idx.value == "John"

    def test_extract_integer_field(self):
        """Indexed integer field creates IntegerFieldIndex with the correct value."""
        form = ActiveFormTemplateFactory()
        FormFieldFactory(
            form_template=form,
            field_key="age",
            field_type=FieldType.INTEGER,
            is_indexed=True,
        )
        response = FormResponseFactory(
            form_template=form,
            data={"age": 25},
        )

        count = IndexService.extract_and_store(response=response)

        assert count == 1
        idx = IntegerFieldIndex.objects.get(response=response, field_key="age")
        assert idx.value == 25

    def test_extract_decimal_field(self):
        """Indexed currency (decimal) field creates DecimalFieldIndex."""
        form = ActiveFormTemplateFactory()
        FormFieldFactory(
            form_template=form,
            field_key="amount",
            field_type=FieldType.CURRENCY,
            is_indexed=True,
        )
        response = FormResponseFactory(
            form_template=form,
            data={"amount": "99.99"},
        )

        count = IndexService.extract_and_store(response=response)

        assert count == 1
        idx = DecimalFieldIndex.objects.get(response=response, field_key="amount")
        assert idx.value == Decimal("99.99")

    def test_extract_boolean_field(self):
        """Indexed boolean field creates BooleanFieldIndex."""
        form = ActiveFormTemplateFactory()
        FormFieldFactory(
            form_template=form,
            field_key="active",
            field_type=FieldType.BOOLEAN,
            is_indexed=True,
        )
        response = FormResponseFactory(
            form_template=form,
            data={"active": True},
        )

        count = IndexService.extract_and_store(response=response)

        assert count == 1
        idx = BooleanFieldIndex.objects.get(response=response, field_key="active")
        assert idx.value is True

    def test_extract_date_field(self):
        """Indexed date field creates DateFieldIndex with the parsed date."""
        form = ActiveFormTemplateFactory()
        FormFieldFactory(
            form_template=form,
            field_key="dob",
            field_type=FieldType.DATE,
            is_indexed=True,
        )
        response = FormResponseFactory(
            form_template=form,
            data={"dob": "2000-01-15"},
        )

        count = IndexService.extract_and_store(response=response)

        assert count == 1
        idx = DateFieldIndex.objects.get(response=response, field_key="dob")
        assert idx.value == date(2000, 1, 15)

    def test_extract_datetime_field(self):
        """Indexed datetime field creates DateTimeFieldIndex."""
        form = ActiveFormTemplateFactory()
        FormFieldFactory(
            form_template=form,
            field_key="ts",
            field_type=FieldType.DATETIME,
            is_indexed=True,
        )
        response = FormResponseFactory(
            form_template=form,
            data={"ts": "2025-06-01T12:00:00+00:00"},
        )

        count = IndexService.extract_and_store(response=response)

        assert count == 1
        assert DateTimeFieldIndex.objects.filter(
            response=response, field_key="ts",
        ).exists()

    def test_skip_none_value(self):
        """Indexed field with None value in data is skipped."""
        form = ActiveFormTemplateFactory()
        FormFieldFactory(
            form_template=form,
            field_key="name",
            field_type=FieldType.TEXT,
            is_indexed=True,
        )
        response = FormResponseFactory(
            form_template=form,
            data={"name": None},
        )

        count = IndexService.extract_and_store(response=response)

        assert count == 0

    def test_skip_missing_key(self):
        """Indexed field whose key is absent from response data is skipped."""
        form = ActiveFormTemplateFactory()
        FormFieldFactory(
            form_template=form,
            field_key="name",
            field_type=FieldType.TEXT,
            is_indexed=True,
        )
        response = FormResponseFactory(
            form_template=form,
            data={"other_field": "hello"},
        )

        count = IndexService.extract_and_store(response=response)

        assert count == 0

    def test_skip_non_indexable_field(self):
        """Non-indexed MULTISELECT field (JSON storage) creates no index entry."""
        form = ActiveFormTemplateFactory()
        FormFieldFactory(
            form_template=form,
            field_key="tags",
            field_type=FieldType.MULTISELECT,
            is_indexed=False,
        )
        response = FormResponseFactory(
            form_template=form,
            data={"tags": ["a", "b"]},
        )

        count = IndexService.extract_and_store(response=response)

        assert count == 0

    def test_multiple_indexed_fields(self):
        """Three indexed fields all create their respective index entries."""
        form = ActiveFormTemplateFactory()
        FormFieldFactory(
            form_template=form,
            field_key="name",
            field_type=FieldType.TEXT,
            is_indexed=True,
        )
        FormFieldFactory(
            form_template=form,
            field_key="age",
            field_type=FieldType.INTEGER,
            is_indexed=True,
        )
        FormFieldFactory(
            form_template=form,
            field_key="active",
            field_type=FieldType.BOOLEAN,
            is_indexed=True,
        )
        response = FormResponseFactory(
            form_template=form,
            data={"name": "Alice", "age": 30, "active": True},
        )

        count = IndexService.extract_and_store(response=response)

        assert count == 3
        assert TextFieldIndex.objects.filter(response=response).count() == 1
        assert IntegerFieldIndex.objects.filter(response=response).count() == 1
        assert BooleanFieldIndex.objects.filter(response=response).count() == 1

    def test_coercion_failure_skips(self):
        """Integer field with non-numeric string value is skipped (coercion fails)."""
        form = ActiveFormTemplateFactory()
        FormFieldFactory(
            form_template=form,
            field_key="age",
            field_type=FieldType.INTEGER,
            is_indexed=True,
        )
        response = FormResponseFactory(
            form_template=form,
            data={"age": "not-a-number"},
        )

        count = IndexService.extract_and_store(response=response)

        assert count == 0
        assert not IntegerFieldIndex.objects.filter(response=response).exists()


# =============================================================================
# IndexService.clear_indexes / rebuild_indexes
# =============================================================================


@pytest.mark.django_db
class TestIndexServiceClearAndRebuild:
    """Tests for clearing and rebuilding index entries."""

    def test_clear_indexes(self):
        """clear_indexes removes all typed index entries for the response."""
        form = ActiveFormTemplateFactory()
        FormFieldFactory(
            form_template=form,
            field_key="name",
            field_type=FieldType.TEXT,
            is_indexed=True,
        )
        response = FormResponseFactory(
            form_template=form,
            data={"name": "Alice"},
        )
        # Manually create index entries
        TextFieldIndex.objects.create(
            response=response, field_key="name", value="Alice",
        )
        assert TextFieldIndex.objects.filter(response=response).count() == 1

        IndexService.clear_indexes(response=response)

        assert TextFieldIndex.objects.filter(response=response).count() == 0

    def test_rebuild_indexes(self):
        """rebuild_indexes clears old entries and creates fresh ones."""
        form = ActiveFormTemplateFactory()
        FormFieldFactory(
            form_template=form,
            field_key="name",
            field_type=FieldType.TEXT,
            is_indexed=True,
        )
        response = FormResponseFactory(
            form_template=form,
            data={"name": "Bob"},
        )
        # Seed stale index with wrong value
        TextFieldIndex.objects.create(
            response=response, field_key="name", value="OldValue",
        )

        count = IndexService.rebuild_indexes(response=response)

        assert count == 1
        idx = TextFieldIndex.objects.get(response=response, field_key="name")
        assert idx.value == "Bob"
        # Only one entry should remain (old cleared, new created)
        assert TextFieldIndex.objects.filter(response=response).count() == 1


# =============================================================================
# IndexService._coerce_value
# =============================================================================


@pytest.mark.django_db
class TestCoerceValue:
    """Tests for the private _coerce_value helper."""

    def test_coerce_text(self):
        """Numeric value coerced to text returns string representation."""
        result = IndexService._coerce_value(
            value=123, storage_type=StorageType.TEXT, field_key="f",
        )
        assert result == "123"

    def test_coerce_integer(self):
        """String numeric value coerced to integer returns int."""
        result = IndexService._coerce_value(
            value="42", storage_type=StorageType.INTEGER, field_key="f",
        )
        assert result == 42

    def test_coerce_decimal(self):
        """String decimal value coerced to decimal returns Decimal."""
        result = IndexService._coerce_value(
            value="3.14", storage_type=StorageType.DECIMAL, field_key="f",
        )
        assert result == Decimal("3.14")

    def test_coerce_boolean_true(self):
        """Python True coerced to boolean returns True."""
        result = IndexService._coerce_value(
            value=True, storage_type=StorageType.BOOLEAN, field_key="f",
        )
        assert result is True

    def test_coerce_boolean_string(self):
        """String 'yes' coerced to boolean returns True."""
        result = IndexService._coerce_value(
            value="yes", storage_type=StorageType.BOOLEAN, field_key="f",
        )
        assert result is True

    def test_coerce_boolean_false(self):
        """String 'no' coerced to boolean returns False."""
        result = IndexService._coerce_value(
            value="no", storage_type=StorageType.BOOLEAN, field_key="f",
        )
        assert result is False

    def test_coerce_date(self):
        """ISO date string coerced to date returns a date object."""
        result = IndexService._coerce_value(
            value="2025-01-15", storage_type=StorageType.DATE, field_key="f",
        )
        assert result == date(2025, 1, 15)

    def test_coerce_datetime(self):
        """ISO datetime string coerced to datetime returns a datetime object."""
        result = IndexService._coerce_value(
            value="2025-01-15T10:30:00",
            storage_type=StorageType.DATETIME,
            field_key="f",
        )
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_coerce_invalid_integer(self):
        """Non-numeric string coerced to integer returns None."""
        result = IndexService._coerce_value(
            value="abc", storage_type=StorageType.INTEGER, field_key="f",
        )
        assert result is None

    def test_coerce_invalid_date(self):
        """Non-date string coerced to date returns None."""
        result = IndexService._coerce_value(
            value="not-a-date", storage_type=StorageType.DATE, field_key="f",
        )
        assert result is None
