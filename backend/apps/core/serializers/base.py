"""
Base Serializers
================
Reusable serializer base classes and mixins.

Design Principles:
    - Separate Input and Output serializers (never use same for both)
    - Input serializers: Plain Serializer with explicit field validation
    - Output serializers: ModelSerializer for read-only representation
    - Never expose internal fields (password_hash, is_deleted, etc.)

Usage:
    from apps.core.serializers import BaseInputSerializer, BaseOutputSerializer

    class CreateUserInput(BaseInputSerializer):
        email = serializers.EmailField()
        password = serializers.CharField(write_only=True)

    class UserOutput(BaseOutputSerializer):
        class Meta:
            model = User
            fields = ["id", "email", "created_at"]
"""

from rest_framework import serializers


# =============================================================================
# BASE INPUT SERIALIZER
# =============================================================================

class BaseInputSerializer(serializers.Serializer):
    """
    Base class for input/request serializers.

    Features:
        - No model binding (explicit field definitions)
        - Automatic validation through DRF
        - Designed for write operations (create/update)

    Subclass Pattern:
        class CreateProductInput(BaseInputSerializer):
            name = serializers.CharField(max_length=255)
            price = serializers.DecimalField(max_digits=10, decimal_places=2)
            category_id = serializers.IntegerField()

            def validate_price(self, value):
                if value <= 0:
                    raise serializers.ValidationError("Price must be positive")
                return value

    Note:
        Input serializers should NOT have create() or update() methods.
        Data transformation happens in the service layer.
    """

    def create(self, validated_data):
        """
        Disabled - use service layer for creation.

        Raises:
            NotImplementedError: Always
        """
        raise NotImplementedError(
            "Input serializers should not implement create(). "
            "Use the service layer instead."
        )

    def update(self, instance, validated_data):
        """
        Disabled - use service layer for updates.

        Raises:
            NotImplementedError: Always
        """
        raise NotImplementedError(
            "Input serializers should not implement update(). "
            "Use the service layer instead."
        )


# =============================================================================
# BASE OUTPUT SERIALIZER
# =============================================================================

class BaseOutputSerializer(serializers.ModelSerializer):
    """
    Base class for output/response serializers.

    Features:
        - Read-only by default
        - Common timestamp fields included
        - Designed for representation only

    Subclass Pattern:
        class ProductOutput(BaseOutputSerializer):
            category_name = serializers.CharField(source="category.name")

            class Meta:
                model = Product
                fields = ["id", "name", "price", "category_name", "created_at"]

    Standard Fields (available from TimeStampedModel):
        - created_at: When record was created
        - updated_at: When record was last modified
    """

    class Meta:
        # Subclasses must define model and fields
        abstract = True
        read_only_fields = ["id", "created_at", "updated_at"]


# =============================================================================
# COMMON SERIALIZER FIELDS
# =============================================================================

class TimestampFieldsMixin(serializers.Serializer):
    """
    Mixin adding standard timestamp fields to serializers.

    Use with output serializers for consistent timestamp representation.

    Usage:
        class ProductOutput(TimestampFieldsMixin, serializers.ModelSerializer):
            class Meta:
                model = Product
                fields = ["id", "name", "created_at", "updated_at"]
    """

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class UserStampFieldsMixin(TimestampFieldsMixin):
    """
    Mixin adding user attribution fields to serializers.

    For models inheriting from UserStampedModel.

    Usage:
        class AuditLogOutput(UserStampFieldsMixin, serializers.ModelSerializer):
            class Meta:
                model = AuditLog
                fields = ["id", "action", "created_by", "created_at"]
    """

    # Nested representation of user (customize as needed)
    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()

    def get_created_by(self, obj):
        """Return minimal user info for created_by."""
        if obj.created_by:
            return {
                "id": obj.created_by.id,
                "email": getattr(obj.created_by, "email", None),
            }
        return None

    def get_updated_by(self, obj):
        """Return minimal user info for updated_by."""
        if obj.updated_by:
            return {
                "id": obj.updated_by.id,
                "email": getattr(obj.updated_by, "email", None),
            }
        return None


# =============================================================================
# COMMON RESPONSE SERIALIZERS
# =============================================================================

class EmptySerializer(serializers.Serializer):
    """
    Empty serializer for endpoints with no request/response body.

    Use for:
        - DELETE endpoints
        - Actions that return only status code
        - OpenAPI schema when no body is expected
    """
    pass


class MessageSerializer(serializers.Serializer):
    """
    Simple message response serializer.

    Use for endpoints returning just a status message.

    Response format:
        {"message": "Operation successful"}
    """

    message = serializers.CharField()


class IDSerializer(serializers.Serializer):
    """
    Serializer for ID-only responses.

    Use for create endpoints that return just the new ID.

    Response format:
        {"id": 123}
    """

    id = serializers.IntegerField()


class UUIDSerializer(serializers.Serializer):
    """
    Serializer for UUID-only responses.

    Use for create endpoints on UUID models.

    Response format:
        {"id": "550e8400-e29b-41d4-a716-446655440000"}
    """

    id = serializers.UUIDField()


# =============================================================================
# PAGINATION SERIALIZERS
# =============================================================================

class PaginatedResponseSerializer(serializers.Serializer):
    """
    Standard paginated response wrapper.

    Response format:
        {
            "count": 100,
            "next": "http://api.example.com/items/?page=2",
            "previous": null,
            "results": [...]
        }

    Note:
        This is for documentation purposes. DRF pagination
        automatically wraps responses in this format.
    """

    count = serializers.IntegerField(help_text="Total number of items")
    next = serializers.URLField(
        allow_null=True,
        help_text="URL for next page (null if last page)"
    )
    previous = serializers.URLField(
        allow_null=True,
        help_text="URL for previous page (null if first page)"
    )
    results = serializers.ListField(
        help_text="List of items for current page"
    )
