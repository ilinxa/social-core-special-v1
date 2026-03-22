"""
Core Models
===========
Re-exports all base models for convenient importing.

Usage:
    from apps.core.models import TimeStampedModel, SoftDeleteModel, BaseModel
"""

from apps.core.models.base import (  # Individual base models; Combined base models; Managers
    AuditModel,
    BaseModel,
    SoftDeleteManager,
    SoftDeleteModel,
    TimeStampedModel,
    UserStampedModel,
    UUIDModel,
)

# Observability models
from apps.core.observability.audit.models import AuditLog

__all__ = [
    # Individual base models
    "TimeStampedModel",
    "SoftDeleteModel",
    "UserStampedModel",
    "UUIDModel",
    # Combined base models
    "BaseModel",
    "AuditModel",
    # Managers
    "SoftDeleteManager",
    # Observability
    "AuditLog",
]
