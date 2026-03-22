"""
Index Service
=============
Extracts indexed field values from form responses and stores them
in typed index tables for efficient querying.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from apps.core.constants import StorageType
from apps.core.observability import get_logger
from apps.forms.constants import FIELD_STORAGE_MAP
from apps.forms.models import (
    BooleanFieldIndex,
    DateFieldIndex,
    DateTimeFieldIndex,
    DecimalFieldIndex,
    FormField,
    FormResponse,
    IntegerFieldIndex,
    TextFieldIndex,
)

logger = get_logger(__name__)

INDEX_TABLE_MAP = {
    StorageType.TEXT: TextFieldIndex,
    StorageType.INTEGER: IntegerFieldIndex,
    StorageType.DECIMAL: DecimalFieldIndex,
    StorageType.BOOLEAN: BooleanFieldIndex,
    StorageType.DATE: DateFieldIndex,
    StorageType.DATETIME: DateTimeFieldIndex,
}


class IndexService:
    """Manages typed index tables for form response data."""

    @staticmethod
    def extract_and_store(*, response: FormResponse) -> int:
        """
        Extract indexed field values from a response and store in typed tables.

        Returns:
            Number of index entries created.
        """
        indexed_fields = FormField.objects.filter(
            form_template_id=response.form_template_id,
            is_indexed=True,
        )

        count = 0
        for field in indexed_fields:
            value = response.data.get(field.field_key)
            if value is None:
                continue

            storage_type = FIELD_STORAGE_MAP.get(field.field_type)
            if not storage_type:
                logger.warning(
                    "forms.index.unknown_field_type",
                    field_type=field.field_type,
                    field_key=field.field_key,
                )
                continue

            index_model = INDEX_TABLE_MAP.get(storage_type)
            if not index_model:
                continue

            coerced = IndexService._coerce_value(
                value=value,
                storage_type=storage_type,
                field_key=field.field_key,
            )
            if coerced is None:
                continue

            index_model.objects.create(
                response=response,
                field_key=field.field_key,
                value=coerced,
            )
            count += 1

        return count

    @staticmethod
    def clear_indexes(*, response: FormResponse) -> None:
        """Remove all index entries for a response."""
        for index_model in INDEX_TABLE_MAP.values():
            index_model.objects.filter(response=response).delete()

    @staticmethod
    def rebuild_indexes(*, response: FormResponse) -> int:
        """Clear and rebuild indexes for a response."""
        IndexService.clear_indexes(response=response)
        return IndexService.extract_and_store(response=response)

    @staticmethod
    def _coerce_value(*, value, storage_type: str, field_key: str):
        """Coerce a raw value to the correct type for the index table."""
        try:
            if storage_type == StorageType.TEXT:
                return str(value)
            elif storage_type == StorageType.INTEGER:
                return int(value)
            elif storage_type == StorageType.DECIMAL:
                return Decimal(str(value))
            elif storage_type == StorageType.BOOLEAN:
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ("true", "1", "yes")
            elif storage_type == StorageType.DATE:
                if isinstance(value, date):
                    return value
                return date.fromisoformat(str(value))
            elif storage_type == StorageType.DATETIME:
                if isinstance(value, datetime):
                    return value
                return datetime.fromisoformat(str(value))
        except (ValueError, TypeError, InvalidOperation):
            logger.warning(
                "forms.index.coercion_failed",
                field_key=field_key,
                storage_type=storage_type,
                value_type=type(value).__name__,
            )
            return None
        return None
