# apps/core/tests/test_serializers.py
"""
Tests for core base serializers and mixins.

Covers:
    - BaseInputSerializer: blocks create/update
    - BaseOutputSerializer: read-only Meta defaults
    - TimestampFieldsMixin: created_at/updated_at fields
    - UserStampFieldsMixin: created_by/updated_by method fields
    - EmptySerializer: no fields
    - MessageSerializer: message field
    - IDSerializer: integer id field
    - UUIDSerializer: UUID id field
    - PaginatedResponseSerializer: pagination fields
"""

import uuid

import pytest
from rest_framework import serializers

from apps.core.serializers.base import (
    BaseInputSerializer,
    BaseOutputSerializer,
    EmptySerializer,
    IDSerializer,
    MessageSerializer,
    PaginatedResponseSerializer,
    TimestampFieldsMixin,
    UUIDSerializer,
    UserStampFieldsMixin,
)


# =============================================================================
# BASE INPUT SERIALIZER
# =============================================================================


class TestBaseInputSerializer:
    """Tests for BaseInputSerializer."""

    def test_create_raises_not_implemented(self):
        """create() raises NotImplementedError."""
        serializer = BaseInputSerializer()

        with pytest.raises(NotImplementedError, match="service layer"):
            serializer.create({})

    def test_update_raises_not_implemented(self):
        """update() raises NotImplementedError."""
        serializer = BaseInputSerializer()

        with pytest.raises(NotImplementedError, match="service layer"):
            serializer.update(None, {})

    def test_subclass_inherits_create_block(self):
        """Subclass also raises NotImplementedError on create()."""

        class TestInput(BaseInputSerializer):
            name = serializers.CharField()

        serializer = TestInput(data={"name": "test"})
        serializer.is_valid()

        with pytest.raises(NotImplementedError):
            serializer.create(serializer.validated_data)

    def test_subclass_inherits_update_block(self):
        """Subclass also raises NotImplementedError on update()."""

        class TestInput(BaseInputSerializer):
            name = serializers.CharField()

        serializer = TestInput(data={"name": "test"})
        serializer.is_valid()

        with pytest.raises(NotImplementedError):
            serializer.update(None, serializer.validated_data)

    def test_validation_still_works(self):
        """Validation on subclass works normally."""

        class TestInput(BaseInputSerializer):
            email = serializers.EmailField()
            name = serializers.CharField(max_length=50)

        serializer = TestInput(data={"email": "test@example.com", "name": "Test"})

        assert serializer.is_valid() is True
        assert serializer.validated_data["email"] == "test@example.com"

    def test_validation_catches_invalid_data(self):
        """Validation correctly rejects invalid data."""

        class TestInput(BaseInputSerializer):
            email = serializers.EmailField()

        serializer = TestInput(data={"email": "not-an-email"})

        assert serializer.is_valid() is False
        assert "email" in serializer.errors

    def test_inherits_from_serializer(self):
        """Inherits from DRF Serializer (not ModelSerializer)."""
        assert issubclass(BaseInputSerializer, serializers.Serializer)
        assert not issubclass(BaseInputSerializer, serializers.ModelSerializer)

    def test_missing_required_field_invalid(self):
        """Missing required field makes serializer invalid."""

        class TestInput(BaseInputSerializer):
            name = serializers.CharField()
            age = serializers.IntegerField()

        serializer = TestInput(data={"name": "Test"})

        assert serializer.is_valid() is False
        assert "age" in serializer.errors


# =============================================================================
# BASE OUTPUT SERIALIZER
# =============================================================================


class TestBaseOutputSerializer:
    """Tests for BaseOutputSerializer."""

    def test_inherits_from_model_serializer(self):
        """Inherits from DRF ModelSerializer."""
        assert issubclass(BaseOutputSerializer, serializers.ModelSerializer)

    def test_meta_has_read_only_fields(self):
        """Meta class has read_only_fields for id, created_at, updated_at."""
        assert "id" in BaseOutputSerializer.Meta.read_only_fields
        assert "created_at" in BaseOutputSerializer.Meta.read_only_fields
        assert "updated_at" in BaseOutputSerializer.Meta.read_only_fields


# =============================================================================
# TIMESTAMP FIELDS MIXIN
# =============================================================================


class TestTimestampFieldsMixin:
    """Tests for TimestampFieldsMixin."""

    def test_has_created_at_field(self):
        """Mixin declares created_at field."""
        fields = TimestampFieldsMixin().get_fields()

        assert "created_at" in fields

    def test_has_updated_at_field(self):
        """Mixin declares updated_at field."""
        fields = TimestampFieldsMixin().get_fields()

        assert "updated_at" in fields

    def test_created_at_is_read_only(self):
        """created_at field is read-only."""
        fields = TimestampFieldsMixin().get_fields()

        assert fields["created_at"].read_only is True

    def test_updated_at_is_read_only(self):
        """updated_at field is read-only."""
        fields = TimestampFieldsMixin().get_fields()

        assert fields["updated_at"].read_only is True

    def test_created_at_is_datetime_field(self):
        """created_at is a DateTimeField."""
        fields = TimestampFieldsMixin().get_fields()

        assert isinstance(fields["created_at"], serializers.DateTimeField)

    def test_updated_at_is_datetime_field(self):
        """updated_at is a DateTimeField."""
        fields = TimestampFieldsMixin().get_fields()

        assert isinstance(fields["updated_at"], serializers.DateTimeField)


# =============================================================================
# USER STAMP FIELDS MIXIN
# =============================================================================


class TestUserStampFieldsMixin:
    """Tests for UserStampFieldsMixin."""

    def test_inherits_timestamp_fields(self):
        """Mixin inherits from TimestampFieldsMixin."""
        assert issubclass(UserStampFieldsMixin, TimestampFieldsMixin)

    def test_has_created_by_field(self):
        """Mixin declares created_by field."""
        fields = UserStampFieldsMixin().get_fields()

        assert "created_by" in fields

    def test_has_updated_by_field(self):
        """Mixin declares updated_by field."""
        fields = UserStampFieldsMixin().get_fields()

        assert "updated_by" in fields

    def test_get_created_by_with_user(self):
        """get_created_by returns id and email when user exists."""
        mixin = UserStampFieldsMixin()

        class MockUser:
            id = 42
            email = "user@example.com"

        class MockObj:
            created_by = MockUser()

        result = mixin.get_created_by(MockObj())

        assert result == {"id": 42, "email": "user@example.com"}

    def test_get_created_by_without_user(self):
        """get_created_by returns None when created_by is None."""
        mixin = UserStampFieldsMixin()

        class MockObj:
            created_by = None

        result = mixin.get_created_by(MockObj())

        assert result is None

    def test_get_updated_by_with_user(self):
        """get_updated_by returns id and email when user exists."""
        mixin = UserStampFieldsMixin()

        class MockUser:
            id = 99
            email = "admin@example.com"

        class MockObj:
            updated_by = MockUser()

        result = mixin.get_updated_by(MockObj())

        assert result == {"id": 99, "email": "admin@example.com"}

    def test_get_updated_by_without_user(self):
        """get_updated_by returns None when updated_by is None."""
        mixin = UserStampFieldsMixin()

        class MockObj:
            updated_by = None

        result = mixin.get_updated_by(MockObj())

        assert result is None

    def test_get_created_by_user_without_email(self):
        """get_created_by handles user without email attribute gracefully."""
        mixin = UserStampFieldsMixin()

        class MockUser:
            id = 10

        class MockObj:
            created_by = MockUser()

        result = mixin.get_created_by(MockObj())

        assert result == {"id": 10, "email": None}

    def test_get_updated_by_user_without_email(self):
        """get_updated_by handles user without email attribute gracefully."""
        mixin = UserStampFieldsMixin()

        class MockUser:
            id = 20

        class MockObj:
            updated_by = MockUser()

        result = mixin.get_updated_by(MockObj())

        assert result == {"id": 20, "email": None}


# =============================================================================
# EMPTY SERIALIZER
# =============================================================================


class TestEmptySerializer:
    """Tests for EmptySerializer."""

    def test_has_no_fields(self):
        """No fields declared."""
        serializer = EmptySerializer()

        assert len(serializer.get_fields()) == 0

    def test_valid_with_no_data(self):
        """Valid when no data provided."""
        serializer = EmptySerializer(data={})

        assert serializer.is_valid() is True

    def test_inherits_from_serializer(self):
        """Inherits from DRF Serializer."""
        assert issubclass(EmptySerializer, serializers.Serializer)


# =============================================================================
# MESSAGE SERIALIZER
# =============================================================================


class TestMessageSerializer:
    """Tests for MessageSerializer."""

    def test_has_message_field(self):
        """Has a 'message' field."""
        fields = MessageSerializer().get_fields()

        assert "message" in fields

    def test_message_is_char_field(self):
        """Message field is a CharField."""
        fields = MessageSerializer().get_fields()

        assert isinstance(fields["message"], serializers.CharField)

    def test_valid_with_message(self):
        """Valid when message is provided."""
        serializer = MessageSerializer(data={"message": "Operation successful"})

        assert serializer.is_valid() is True
        assert serializer.validated_data["message"] == "Operation successful"

    def test_invalid_without_message(self):
        """Invalid when message is missing."""
        serializer = MessageSerializer(data={})

        assert serializer.is_valid() is False
        assert "message" in serializer.errors

    def test_serialization_output(self):
        """Serialization produces correct output format."""
        serializer = MessageSerializer({"message": "Done"})

        assert serializer.data == {"message": "Done"}


# =============================================================================
# ID SERIALIZER
# =============================================================================


class TestIDSerializer:
    """Tests for IDSerializer."""

    def test_has_id_field(self):
        """Has an 'id' field."""
        fields = IDSerializer().get_fields()

        assert "id" in fields

    def test_id_is_integer_field(self):
        """ID field is an IntegerField."""
        fields = IDSerializer().get_fields()

        assert isinstance(fields["id"], serializers.IntegerField)

    def test_valid_with_integer_id(self):
        """Valid when integer ID is provided."""
        serializer = IDSerializer(data={"id": 42})

        assert serializer.is_valid() is True
        assert serializer.validated_data["id"] == 42

    def test_invalid_with_string_id(self):
        """Invalid when non-integer ID is provided."""
        serializer = IDSerializer(data={"id": "not-a-number"})

        assert serializer.is_valid() is False

    def test_valid_with_zero_id(self):
        """Valid when ID is 0."""
        serializer = IDSerializer(data={"id": 0})

        assert serializer.is_valid() is True

    def test_valid_with_negative_id(self):
        """Valid when ID is negative (IntegerField allows it)."""
        serializer = IDSerializer(data={"id": -1})

        assert serializer.is_valid() is True


# =============================================================================
# UUID SERIALIZER
# =============================================================================


class TestUUIDSerializer:
    """Tests for UUIDSerializer."""

    def test_has_id_field(self):
        """Has an 'id' field."""
        fields = UUIDSerializer().get_fields()

        assert "id" in fields

    def test_id_is_uuid_field(self):
        """ID field is a UUIDField."""
        fields = UUIDSerializer().get_fields()

        assert isinstance(fields["id"], serializers.UUIDField)

    def test_valid_with_uuid(self):
        """Valid when UUID is provided."""
        test_uuid = str(uuid.uuid4())
        serializer = UUIDSerializer(data={"id": test_uuid})

        assert serializer.is_valid() is True

    def test_invalid_with_non_uuid(self):
        """Invalid when non-UUID string is provided."""
        serializer = UUIDSerializer(data={"id": "not-a-uuid"})

        assert serializer.is_valid() is False

    def test_valid_with_uuid_object(self):
        """Valid when UUID object (not string) is provided."""
        serializer = UUIDSerializer(data={"id": uuid.uuid4()})

        assert serializer.is_valid() is True


# =============================================================================
# PAGINATED RESPONSE SERIALIZER
# =============================================================================


class TestPaginatedResponseSerializer:
    """Tests for PaginatedResponseSerializer."""

    def test_has_count_field(self):
        """Has a 'count' field."""
        fields = PaginatedResponseSerializer().get_fields()

        assert "count" in fields

    def test_has_next_field(self):
        """Has a 'next' field."""
        fields = PaginatedResponseSerializer().get_fields()

        assert "next" in fields

    def test_has_previous_field(self):
        """Has a 'previous' field."""
        fields = PaginatedResponseSerializer().get_fields()

        assert "previous" in fields

    def test_has_results_field(self):
        """Has a 'results' field."""
        fields = PaginatedResponseSerializer().get_fields()

        assert "results" in fields

    def test_count_is_integer_field(self):
        """Count is an IntegerField."""
        fields = PaginatedResponseSerializer().get_fields()

        assert isinstance(fields["count"], serializers.IntegerField)

    def test_next_allows_null(self):
        """Next field allows null."""
        fields = PaginatedResponseSerializer().get_fields()

        assert fields["next"].allow_null is True

    def test_previous_allows_null(self):
        """Previous field allows null."""
        fields = PaginatedResponseSerializer().get_fields()

        assert fields["previous"].allow_null is True

    def test_results_is_list_field(self):
        """Results is a ListField."""
        fields = PaginatedResponseSerializer().get_fields()

        assert isinstance(fields["results"], serializers.ListField)

    def test_has_exactly_four_fields(self):
        """Serializer has exactly 4 fields."""
        fields = PaginatedResponseSerializer().get_fields()

        assert len(fields) == 4
