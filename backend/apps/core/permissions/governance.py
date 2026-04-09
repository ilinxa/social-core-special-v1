# apps/core/permissions/governance.py
"""
Governance Token Permission
===========================
DRF permission class for governance console endpoints.

Validates that the request carries a governance-scoped JWT
(token_scope == "governance") and that the user still has
active platform membership with global-scoped permissions.

Usage:
    class BusinessSuspendView(APIView):
        permission_classes = [IsAuthenticated, GovernanceTokenRequired]
"""

from rest_framework.permissions import BasePermission

from apps.core.observability import get_logger

logger = get_logger(__name__)


class GovernanceTokenRequired(BasePermission):
    """
    Validates governance-scoped JWT token on every request.

    Checks (Decision 8 — middleware membership check):
        1. request.auth contains token_scope == "governance"
        2. User has active platform membership with at least one
           global_only or platform_and_global scoped permission

    The governance token is sent as Authorization: Bearer <governance_token>
    by the frontend governance API client (separate Axios instance).
    Standard JWTAuthentication decodes it and puts the payload in request.auth.
    """

    message = "This action requires governance-level authentication."
    code = "governance_auth_required"

    def has_permission(self, request, view):
        # 1. Check governance token scope in JWT payload
        payload = request.auth
        if not payload or payload.get("token_scope") != "governance":
            logger.debug(
                "governance.permission.denied",
                reason="missing_or_invalid_token_scope",
                user_id=str(request.user.id) if request.user else None,
            )
            return False

        # 2. Real-time membership check (D8 — 1 DB query per request)
        from apps.auth.services.governance_service import GovernanceAuthService

        if not GovernanceAuthService.has_any_global_permission(request.user):
            logger.warning(
                "governance.permission.denied",
                reason="no_global_permissions",
                user_id=str(request.user.id),
            )
            return False

        return True
