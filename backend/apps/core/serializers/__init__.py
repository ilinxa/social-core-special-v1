"""
Core Serializers
================
Re-exports base serializer classes.

Usage:
    from apps.core.serializers import BaseInputSerializer, BaseOutputSerializer
"""

from apps.core.serializers.base import (  # Base classes; Mixins; Common responses
    BaseInputSerializer,
    BaseOutputSerializer,
    EmptySerializer,
    IDSerializer,
    MessageSerializer,
    PaginatedResponseSerializer,
    TimestampFieldsMixin,
    UserStampFieldsMixin,
    UUIDSerializer,
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
