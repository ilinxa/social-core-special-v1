# apps/core/observability/audit/tests/conftest.py
"""
Fixtures for audit REST API tests.
"""

import pytest
from django.utils import timezone

from apps.core.observability.audit.models import AuditLog


@pytest.fixture
def business_audit_logs(db, business_with_profile):
    """Create audit log entries for a business."""
    logs = []
    for action in [
        AuditLog.Action.BUSINESS_CREATED,
        AuditLog.Action.BUSINESS_UPDATED,
        AuditLog.Action.BUSINESS_PROFILE_UPDATED,
    ]:
        logs.append(
            AuditLog.objects.create(
                actor_id=str(business_with_profile.created_by.id),
                actor_email=business_with_profile.created_by.email,
                action=action,
                resource_type="BusinessAccount",
                resource_id=str(business_with_profile.id),
                resource_repr=str(business_with_profile),
                outcome=AuditLog.Outcome.SUCCESS,
            )
        )
    return logs


@pytest.fixture
def platform_audit_logs(db):
    """Create platform-scoped audit log entries."""
    logs = []
    for action in [
        AuditLog.Action.PLATFORM_CONFIGURED,
        AuditLog.Action.PLATFORM_SETTINGS_UPDATED,
        AuditLog.Action.PLATFORM_PROFILE_UPDATED,
    ]:
        logs.append(
            AuditLog.objects.create(
                actor_type=AuditLog.ActorType.ADMIN,
                action=action,
                resource_type="PlatformAccount",
                resource_id="platform-singleton",
                resource_repr="Platform",
                outcome=AuditLog.Outcome.SUCCESS,
            )
        )
    return logs


@pytest.fixture
def mixed_audit_logs(db, business_audit_logs, platform_audit_logs):
    """Business + platform logs combined."""
    extra = AuditLog.objects.create(
        action=AuditLog.Action.LOGIN_SUCCESS,
        actor_type=AuditLog.ActorType.USER,
        resource_type="DeviceSession",
        resource_id="some-session-id",
        outcome=AuditLog.Outcome.SUCCESS,
    )
    return business_audit_logs + platform_audit_logs + [extra]
