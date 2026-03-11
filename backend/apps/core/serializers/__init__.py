"""
Core Serializers
================
Re-exports base serializer classes.

Usage:
    from apps.core.serializers import BaseInputSerializer, BaseOutputSerializer
"""

from apps.core.serializers.base import (
    # Base classes
    BaseInputSerializer,
    BaseOutputSerializer,
    # Mixins
    TimestampFieldsMixin,
    UserStampFieldsMixin,
    # Common responses
    EmptySerializer,
    MessageSerializer,
    IDSerializer,
    UUIDSerializer,
    PaginatedResponseSerializer,
)

__all__ = [
    # Base classes
    "BaseInputSerializer",
    "BaseOutputSerializer",
    # Mixins
    "TimestampFieldsMixin",
    "UserStampFieldsMixin",
    # Common responses
    "EmptySerializer",
    "MessageSerializer",
    "IDSerializer",
    "UUIDSerializer",
    "PaginatedResponseSerializer",
]
