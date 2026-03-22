"""
Audit Logging System
====================
Immutable audit trail for compliance and security tracking.

Public API:
    - AuditLog: Model for audit entries (immutable)
    - AuditService: Service for creating audit logs
    - AuditSelector: Query methods for audit logs
    - audited: Decorator for automatic audit logging

Components:
    - models: AuditLog database model
    - service: AuditService.log() method
    - selectors: Query methods for retrieving audit logs
    - decorators: @audited decorator for automatic logging
    - constants: Action type definitions
"""

from apps.core.observability.audit.decorators import audited
from apps.core.observability.audit.models import AuditLog
from apps.core.observability.audit.selectors import AuditSelector
from apps.core.observability.audit.service import AuditService

__all__ = [
    "AuditLog",
    "AuditService",
    "AuditSelector",
    "audited",
]
