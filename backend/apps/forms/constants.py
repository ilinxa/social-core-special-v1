from apps.core.constants import FieldType, StorageType

FIELD_STORAGE_MAP = {
    # Text storage
    FieldType.TEXT: StorageType.TEXT,
    FieldType.TEXTAREA: StorageType.TEXT,
    FieldType.EMAIL: StorageType.TEXT,
    FieldType.URL: StorageType.TEXT,
    FieldType.PHONE: StorageType.TEXT,
    FieldType.SELECT: StorageType.TEXT,
    FieldType.RADIO: StorageType.TEXT,
    FieldType.TIME: StorageType.TEXT,
    # Integer storage
    FieldType.INTEGER: StorageType.INTEGER,
    FieldType.RATING: StorageType.INTEGER,
    # Decimal storage
    FieldType.DECIMAL: StorageType.DECIMAL,
    FieldType.CURRENCY: StorageType.DECIMAL,
    # Boolean storage
    FieldType.BOOLEAN: StorageType.BOOLEAN,
    FieldType.CHECKBOX: StorageType.BOOLEAN,
    # Date/DateTime storage
    FieldType.DATE: StorageType.DATE,
    FieldType.DATETIME: StorageType.DATETIME,
    # JSON storage (not indexable)
    FieldType.MULTISELECT: StorageType.JSON,
    FieldType.CHECKBOX_GROUP: StorageType.JSON,
    FieldType.FILE: StorageType.JSON,
    FieldType.IMAGE: StorageType.JSON,
    FieldType.LOCATION: StorageType.JSON,
    FieldType.REPEATABLE: StorageType.JSON,
}

INDEXABLE_STORAGE_TYPES = frozenset(
    [
        StorageType.TEXT,
        StorageType.INTEGER,
        StorageType.DECIMAL,
        StorageType.BOOLEAN,
        StorageType.DATE,
        StorageType.DATETIME,
    ]
)

MAX_INDEXED_FIELDS = 5
