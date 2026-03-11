"""
Core App
========
Shared infrastructure for all Django apps.

This app provides base classes and utilities - NO business logic.

Components:
    models: Base models (TimeStamped, SoftDelete, UserStamped, UUID)
    exceptions: Domain exceptions and DRF exception handler
    utils: JWT, password, and datetime utilities
    serializers: Base serializer classes
    pagination: Pagination classes
    permissions: Base permission classes

Quick Import:
    from apps.core.models import TimeStampedModel, BaseModel
    from apps.core.exceptions import NotFound, ValidationError
    from apps.core.utils import utc_now, hash_password, encode_token
    from apps.core.serializers import BaseInputSerializer, BaseOutputSerializer
    from apps.core.permissions import IsAuthenticated, IsOwner

Documentation:
    See guid/apps/00_core.md for detailed component documentation.
"""

# Set default app config
default_app_config = "apps.core.apps.CoreConfig"
