# apps/core/observability/audit/serializers.py
"""
Audit Log Serializers
=====================
Read-only serializers for audit log REST API responses.
"""

from rest_framework import serializers

from apps.core.observability.audit.models import AuditLog


class AuditLogOutput(serializers.ModelSerializer):
    """Read-only output for audit log entries."""

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "timestamp",
            "actor_id",
            "actor_email",
            "actor_type",
            "action",
            "resource_type",
            "resource_id",
            "resource_repr",
            "outcome",
            "details",
            "changes",
            "ip_address",
            "request_id",
        ]
        read_only_fields = fields
