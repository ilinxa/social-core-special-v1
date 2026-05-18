"""
Exception Handler
=================
Custom DRF exception handler that converts domain exceptions to HTTP responses.

This handler:
    1. First delegates to DRF's default handler for framework exceptions
    2. Then handles our DomainException hierarchy
    3. Ensures consistent error response format across the API

Response Format:
    {
        "error": {
            "message": "Human-readable message",
            "code": "machine_readable_code",
            "details": {...}
        }
    }

Configuration:
    Add to settings.py:
        REST_FRAMEWORK = {
            "EXCEPTION_HANDLER": "apps.core.exceptions.handler.exception_handler",
        }
"""

import math

from django.conf import settings as django_settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.core.exceptions.domain import DomainException
from apps.core.observability import get_logger

logger = get_logger(__name__)


def _audit_log_authorization_denied(exc, context):
    """Log 403 responses to the audit trail. Fails silently."""
    try:
        from apps.core.observability.audit import AuditLog, AuditService

        request = context.get("request")
        user = getattr(request, "user", None) if request else None
        if user and not user.is_authenticated:
            user = None
        AuditService.log(
            action=AuditLog.Action.AUTHORIZATION_DENIED,
            actor=user,
            request=request,
            outcome=AuditLog.Outcome.DENIED,
            details={
                "view": _get_view_name(context),
                "method": request.method if request else "unknown",
                "path": request.path if request else "unknown",
            },
        )
    except Exception as e:
        logger.debug(
            "audit.authorization_denied.log_failed", error=str(e), exc_info=True
        )


# =============================================================================
# STATUS CODE MAPPING
# =============================================================================

# Maps exception codes to HTTP status codes
# This centralizes the domain -> HTTP translation
STATUS_CODE_MAP = {
    # 400 Bad Request - Client errors (validation, business rules)
    "domain_error": status.HTTP_400_BAD_REQUEST,
    "validation_error": status.HTTP_400_BAD_REQUEST,
    "business_rule_violation": status.HTTP_400_BAD_REQUEST,
    "oauth_error": status.HTTP_400_BAD_REQUEST,
    # 401 Unauthorized - Authentication failures
    "authentication_error": status.HTTP_401_UNAUTHORIZED,
    "invalid_credentials": status.HTTP_401_UNAUTHORIZED,
    "token_expired": status.HTTP_401_UNAUTHORIZED,
    "token_invalid": status.HTTP_401_UNAUTHORIZED,
    "token_already_used": status.HTTP_401_UNAUTHORIZED,
    "account_not_verified": status.HTTP_401_UNAUTHORIZED,
    "account_inactive": status.HTTP_401_UNAUTHORIZED,
    "account_locked": status.HTTP_401_UNAUTHORIZED,
    # 403 Forbidden - Authorization failures
    "permission_denied": status.HTTP_403_FORBIDDEN,
    "feature_disabled": status.HTTP_403_FORBIDDEN,
    # 404 Not Found - Resource not found
    "not_found": status.HTTP_404_NOT_FOUND,
    # 409 Conflict - Resource conflicts
    "conflict": status.HTTP_409_CONFLICT,
    # 429 Too Many Requests - Rate limiting
    "rate_limit_exceeded": status.HTTP_429_TOO_MANY_REQUESTS,
    # 503 Service Unavailable - External service issues
    "service_unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
}


def get_status_code(exception_code: str) -> int:
    """
    Get HTTP status code for a domain exception code.

    Args:
        exception_code: The exception's code attribute

    Returns:
        HTTP status code (defaults to 400 for unknown codes)
    """
    return STATUS_CODE_MAP.get(exception_code, status.HTTP_400_BAD_REQUEST)


# =============================================================================
# EXCEPTION HANDLER
# =============================================================================


def exception_handler(exc, context):
    """
    Custom exception handler for DRF views.

    Handles:
        1. DRF built-in exceptions (via default handler)
        2. DomainException and subclasses
        3. Unhandled exceptions (logged, generic response)

    Args:
        exc: The exception instance
        context: Dictionary with 'view', 'args', 'kwargs', 'request'

    Returns:
        Response object or None (None lets exception propagate)
    """
    # First, let DRF handle its own exceptions (validation, auth, etc.)
    response = drf_exception_handler(exc, context)

    if response is not None:
        # Add Retry-After header on 429 Too Many Requests
        if response.status_code == 429:
            wait = getattr(exc, "wait", None)
            if wait is not None:
                response["Retry-After"] = int(math.ceil(wait))

        # DRF handled it - wrap in our consistent format if not already
        if not isinstance(response.data, dict) or "error" not in response.data:
            # Preserve specific error code from the exception if available.
            # DRF exceptions created with code= (e.g., AuthenticationFailed(code='token_expired'))
            # expose the code via get_codes(). Use it instead of the generic status-based code.
            exc_code = getattr(exc, "get_codes", lambda: None)()
            code = (
                exc_code
                if isinstance(exc_code, str)
                else _status_to_code(response.status_code)
            )
            response.data = {
                "error": {
                    "message": _extract_message(response.data),
                    "code": code,
                    "details": _extract_details(response.data),
                }
            }
        if response.status_code == 403:
            _audit_log_authorization_denied(exc, context)
        return response

    # Handle our domain exceptions
    if isinstance(exc, DomainException):
        status_code = get_status_code(exc.code)

        # Log the exception with context
        log_method = logger.warning if status_code < 500 else logger.error
        log_method(
            "exception.domain",
            exception=str(exc),
            exception_code=exc.code,
            status_code=status_code,
            view=_get_view_name(context),
            exc_info=status_code >= 500,
        )

        if status_code == 403:
            _audit_log_authorization_denied(exc, context)

        return Response({"error": exc.to_dict()}, status=status_code)

    # Unhandled exception - log and return generic error
    # In DEBUG mode, Django will show the full traceback
    logger.exception(
        "exception.unhandled",
        view=_get_view_name(context),
        error=str(exc),
    )

    # In development: return None → Django debug traceback page
    # In production: return JSON error → consistent API contract
    if django_settings.DEBUG:
        return None

    return Response(
        {
            "error": {
                "message": "An unexpected error occurred",
                "code": "internal_error",
                "details": {},
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _extract_message(data) -> str:
    """
    Extract a human-readable message from DRF response data.

    DRF can return various formats:
        - String: "Authentication required"
        - Dict: {"detail": "Not found"}
        - Dict with list: {"field": ["Error 1", "Error 2"]}
    """
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        # Common DRF patterns
        if "detail" in data:
            detail = data["detail"]
            return str(detail) if not isinstance(detail, (list, dict)) else str(detail)
        if "non_field_errors" in data:
            errors = data["non_field_errors"]
            return errors[0] if isinstance(errors, list) and errors else str(errors)
        # Field errors - return first one
        for field, errors in data.items():
            if isinstance(errors, list) and errors:
                return f"{field}: {errors[0]}"
            return f"{field}: {errors}"
    if isinstance(data, list):
        return data[0] if data else "An error occurred"
    return "An error occurred"


def _extract_details(data) -> dict:
    """
    Extract details from DRF response data.

    For field-level errors, returns the full structure.
    """
    if isinstance(data, dict):
        # Remove 'detail' as it's already in message
        details = {k: v for k, v in data.items() if k != "detail"}
        return details if details else {}
    return {}


def _status_to_code(status_code: int) -> str:
    """
    Convert HTTP status code to a machine-readable code.
    """
    code_map = {
        400: "bad_request",
        401: "authentication_error",
        403: "permission_denied",
        404: "not_found",
        405: "method_not_allowed",
        429: "rate_limit_exceeded",
        500: "internal_error",
    }
    return code_map.get(status_code, "error")


def _get_view_name(context) -> str:
    """
    Get the view name from exception context for logging.
    """
    view = context.get("view")
    if view:
        return f"{view.__class__.__module__}.{view.__class__.__name__}"
    return "unknown"
