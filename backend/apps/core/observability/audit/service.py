"""
Audit Service
=============
Service for creating audit log entries with automatic redaction.

Usage:
    from apps.core.observability.audit import AuditService, AuditLog

    AuditService.log(
        action=AuditLog.Action.LOGIN_SUCCESS,
        actor=user,
        resource=session,
        request=request,
        details={"method": "password"}
    )
"""

from typing import TYPE_CHECKING, Any, Dict

from django.http import HttpRequest

from apps.core.observability.audit.models import AuditLog

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()


# Fields that must be redacted from audit log details/changes
REDACTED_FIELDS = frozenset(
    [
        "password",
        "password1",
        "password2",
        "old_password",
        "new_password",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "secret",
        "authorization",
        "cookie",
        "session_id",
        "csrf",
        "credit_card",
        "card_number",
        "cvv",
        "ssn",
    ]
)


def _redact_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively redact sensitive fields from a dictionary.

    Defense in depth: Even if developers forget to redact,
    this ensures no sensitive data leaks into audit logs.
    """
    if not data:
        return data

    redacted = {}
    for key, value in data.items():
        key_lower = key.lower()

        # Check if key matches any redacted field
        if any(field in key_lower for field in REDACTED_FIELDS):
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = _redact_sensitive_data(value)
        else:
            redacted[key] = value

    return redacted


class AuditService:
    """
    Service for creating audit log entries.

    Provides methods for:
        - log(): Create a general audit entry
        - log_failure(): Log a failed action
        - log_change(): Log data changes with before/after values
    """

    @staticmethod
    def log(
        *,
        action: str,
        actor: "User | None" = None,
        actor_type: str = AuditLog.ActorType.USER,
        resource: Any = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        request: HttpRequest | None = None,
        outcome: str = AuditLog.Outcome.SUCCESS,
        details: Dict[str, Any] | None = None,
        changes: Dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            action: Action type from AuditLog.Action
            actor: User performing the action (None for anonymous/system)
            actor_type: Type of actor (user, admin, system, anonymous)
            resource: Object being acted upon
            resource_type: Override resource type name
            resource_id: Override resource ID
            request: HTTP request for context extraction
            outcome: Action outcome (success, failure, denied)
            details: Additional structured details
            changes: Before/after values for updates

        Returns:
            Created AuditLog instance
        """
        # Extract actor info
        actor_id = None
        actor_email = None

        if actor:
            actor_id = getattr(actor, "id", None)
            actor_email = getattr(actor, "email", None)

            # Determine actor type
            # Policy: Both is_superuser and is_staff are treated as ADMIN
            if actor_type == AuditLog.ActorType.USER:
                if getattr(actor, "is_superuser", False):
                    actor_type = AuditLog.ActorType.ADMIN
                elif getattr(actor, "is_staff", False):
                    actor_type = AuditLog.ActorType.ADMIN
        elif actor_type == AuditLog.ActorType.USER:
            actor_type = AuditLog.ActorType.ANONYMOUS

        # Extract resource info
        resolved_resource_type = resource_type
        resolved_resource_id = resource_id
        resource_repr = ""

        if resource:
            if not resolved_resource_type:
                resolved_resource_type = resource.__class__.__name__
            if not resolved_resource_id:
                resolved_resource_id = getattr(resource, "id", None)
            resource_repr = str(resource)[:255]

        # Extract request context
        ip_address = None
        user_agent = ""
        request_id = ""

        if request:
            ip_address = AuditService._get_client_ip(request)
            user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
            request_id = getattr(request, "request_id", "") or request.META.get(
                "HTTP_X_REQUEST_ID", ""
            )

        # Redact sensitive data (defense in depth)
        safe_details = _redact_sensitive_data(details or {})
        safe_changes = _redact_sensitive_data(changes or {})

        # Create log entry
        audit_log = AuditLog.objects.create(
            action=action,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_type=actor_type,
            resource_type=resolved_resource_type or "",
            resource_id=resolved_resource_id,
            resource_repr=resource_repr,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            outcome=outcome,
            details=safe_details,
            changes=safe_changes,
        )

        return audit_log

    @staticmethod
    def log_failure(
        *,
        action: str,
        reason: str,
        actor: "User | None" = None,
        request: HttpRequest | None = None,
        details: Dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Convenience method for logging failures.

        Usage:
            AuditService.log_failure(
                action=AuditLog.Action.LOGIN_FAILED,
                reason="invalid_password",
                request=request,
                details={"email_hash": hash(email)}
            )
        """
        details = details or {}
        details["failure_reason"] = reason

        return AuditService.log(
            action=action,
            actor=actor,
            request=request,
            outcome=AuditLog.Outcome.FAILURE,
            details=details,
        )

    @staticmethod
    def log_change(
        *,
        action: str,
        actor: "User",
        resource: Any,
        before: Dict[str, Any],
        after: Dict[str, Any],
        request: HttpRequest | None = None,
    ) -> AuditLog:
        """
        Log a data change with before/after values.

        Usage:
            AuditService.log_change(
                action=AuditLog.Action.USER_UPDATED,
                actor=admin,
                resource=user,
                before={"email": "old@example.com"},
                after={"email": "new@example.com"},
                request=request,
            )
        """
        # Filter to only changed fields
        changes = {
            "before": {
                k: v for k, v in before.items() if before.get(k) != after.get(k)
            },
            "after": {k: v for k, v in after.items() if before.get(k) != after.get(k)},
        }

        return AuditService.log(
            action=action,
            actor=actor,
            resource=resource,
            request=request,
            outcome=AuditLog.Outcome.SUCCESS,
            changes=changes,
        )

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str | None:
        """Extract client IP from request, handling proxies."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # Take the first IP (client IP before proxies)
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
