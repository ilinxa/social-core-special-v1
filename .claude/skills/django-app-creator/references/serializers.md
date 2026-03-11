# Serializers

Read this when creating input/output serializers — validation, response shaping, base classes, file uploads, and OpenAPI schema hints.

## Quick Reference — Project Imports

```python
from rest_framework import serializers
from apps.core.serializers import (
    BaseInputSerializer,     # For request validation (no .save())
    BaseOutputSerializer,    # For responses (read-only ModelSerializer)
    EmptySerializer,         # For no-body requests/responses
    MessageSerializer,       # {"message": "..."}
    TimestampFieldsMixin,    # Adds created_at, updated_at
    UserStampFieldsMixin,    # Adds created_by, updated_by as nested user objects
)
from drf_spectacular.utils import extend_schema_field
```

---

## 1. Role of Serializers

Serializers sit at the **API boundary** — they validate incoming data and shape outgoing responses.

Serializers SHOULD: validate incoming data, transform domain objects into API responses, enforce input shape and format.

Serializers SHOULD NOT: perform database writes, contain business rules, orchestrate workflows, query the database.

> **Serializers validate and shape data — they never decide what happens.**

---

## 2. Input vs Output Separation (MANDATORY)

### Input Serializers — `BaseInputSerializer`

```python
class ProductCreateInputSerializer(BaseInputSerializer):
    """
    BaseInputSerializer:
    - No model binding (explicit field definitions)
    - create()/update() disabled — raises NotImplementedError
    - Use for request validation only, delegate persistence to services
    """
    name = serializers.CharField(max_length=255)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate_name(self, value):
        return value.strip()

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be positive")
        return value

class ProductUpdateInputSerializer(BaseInputSerializer):
    """Partial update — all fields optional"""
    name = serializers.CharField(max_length=255, required=False)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
```

### Output Serializers — `BaseOutputSerializer`

```python
class ProductOutputSerializer(BaseOutputSerializer):
    """
    BaseOutputSerializer:
    - Read-only by default
    - Pre-configured read_only_fields = ["id", "created_at", "updated_at"]
    """
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    is_affordable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'owner_name', 'is_affordable', 'created_at', 'updated_at')
        read_only_fields = fields

class ProductListSerializer(BaseOutputSerializer):
    """Minimal fields for list views"""
    class Meta:
        model = Product
        fields = ('id', 'name', 'price')
        read_only_fields = fields
```

---

## 3. Common Response Serializers

```python
from apps.core.serializers import EmptySerializer, MessageSerializer

# DELETE endpoint → 204
@extend_schema(responses={204: EmptySerializer})
def delete(self, request, product_id):
    ...
    return Response(status=status.HTTP_204_NO_CONTENT)

# Message response
return Response(MessageSerializer({"message": "Product deleted"}).data)
```

---

## 4. Validation Strategy

| Layer | Responsibility |
|-------|---------------|
| Serializer | Format, type, constraints |
| Service | Business rules, uniqueness |
| Model | Structural invariants |

- Field-level: `validate_<field>()` for normalization and format
- Object-level: `validate()` only when fields depend on each other
- **No database access** in serializers

---

## 5. No Database Access Rule

Allowed: format checks, regex, timezone validation, file metadata.
Forbidden: `Model.objects.filter(...)`, uniqueness checks, existence checks.

> DB access belongs in **services** or **selectors**.

---

## 6. Output Fields & Computed Values

```python
is_complete = serializers.BooleanField(read_only=True)

avatar_url = serializers.SerializerMethodField()

@extend_schema_field(serializers.URLField(allow_null=True))
def get_avatar_url(self, obj):
    ...
```

`SerializerMethodField` methods MUST be deterministic with no side effects.

---

## 7. Serializer Context

```python
request = self.context.get("request")
```

Usage: building absolute URLs, request-aware formatting. Serializers must work even if context is missing.

---

## 8. Nested Serializers & Performance

- Nested serializers allowed for output
- **Selectors MUST preload** related data (`select_related` / `prefetch_related`)
- Serializers MUST NOT trigger implicit queries

> Performance guarantees come from selectors, not serializers.

---

## 9. File Upload Validation

Serializers may validate: file size, content type, basic metadata.
Serializers MUST NOT: save files, delete files, perform I/O.

---

## 10. Anti-Patterns

❌ `class ProductSerializer(serializers.ModelSerializer)` for input — Use `BaseInputSerializer`
❌ Model `.save()` calls in serializers
❌ `def create(self, validated_data)` in input serializers — Delegate to services
❌ Database queries in serializers
❌ Business workflows in serializers
❌ Same serializer for input AND output
