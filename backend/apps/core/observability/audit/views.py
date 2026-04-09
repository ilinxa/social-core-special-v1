# apps/core/observability/audit/views.py
"""
Audit Log Views
===============
Read-only REST API endpoints for audit log access.

Three scoped endpoints (Decision 4):
    - Business: /api/v1/business/{slug}/audit/
    - Platform: /api/v1/platform/audit/
    - Governance: /api/v1/governance/audit/

All endpoints are GET-only (audit logs are immutable).
"""

from datetime import datetime

from django.http import HttpRequest
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import PermissionDenied
from apps.core.observability import get_logger
from apps.core.observability.audit.selectors import AuditSelector
from apps.core.observability.audit.serializers import AuditLogOutput
from apps.core.pagination import LargeResultsPagination, StandardPagination
from apps.core.permissions import GovernanceTokenRequired, IsAuthenticated

logger = get_logger(__name__)

# =============================================================================
# SHARED HELPERS
# =============================================================================

_AUDIT_QUERY_PARAMS = [
    OpenApiParameter("action", str, description="Filter by action code"),
    OpenApiParameter(
        "outcome", str, description="Filter by outcome (success/failure/denied)"
    ),
    OpenApiParameter("actor_id", str, description="Filter by actor UUID"),
    OpenApiParameter("since", str, description="Filter logs after ISO datetime"),
    OpenApiParameter("until", str, description="Filter logs before ISO datetime"),
    OpenApiParameter("resource_type", str, description="Filter by resource type"),
]


def _extract_audit_filters(request: HttpRequest) -> dict:
    """Extract common audit filter params from request query string."""
    filters = {}

    action = request.query_params.get("action")
    if action:
        filters["action"] = action

    outcome = request.query_params.get("outcome")
    if outcome:
        filters["outcome"] = outcome

    actor_id = request.query_params.get("actor_id")
    if actor_id:
        filters["actor_id"] = actor_id

    since = request.query_params.get("since")
    if since:
        try:
            filters["since"] = datetime.fromisoformat(since)
        except (ValueError, TypeError):
            pass  # Ignore invalid date

    until = request.query_params.get("until")
    if until:
        try:
            filters["until"] = datetime.fromisoformat(until)
        except (ValueError, TypeError):
            pass

    resource_type = request.query_params.get("resource_type")
    if resource_type:
        filters["resource_type"] = resource_type

    return filters


# =============================================================================
# BUSINESS-SCOPED AUDIT
# =============================================================================


class BusinessAuditListView(APIView):
    """
    List audit logs for a specific business.

    GET /api/v1/business/{slug}/audit/

    Returns business lifecycle actions: created, updated, suspended,
    reactivated, archived, profile_updated, verification.
    Requires can_view_audit_logs permission (business scope).
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        summary="List business audit logs",
        parameters=_AUDIT_QUERY_PARAMS,
        responses={200: AuditLogOutput(many=True)},
        tags=["Audit"],
    )
    def get(self, request, slug: str):
        from apps.organization.business.policies import BusinessPolicy
        from apps.organization.business.selectors import BusinessAccountSelector

        business = BusinessAccountSelector.get_by_slug(slug=slug)

        # Check permission: business member with can_view_audit_logs
        has_business_perm = BusinessPolicy._has_business_permission(
            user=request.user,
            business=business,
            permission_code="can_view_audit_logs",
        )
        has_global_perm = BusinessPolicy._has_global_permission(
            user=request.user,
            permission_code="can_view_audit_logs",
        )

        if not has_business_perm and not has_global_perm:
            raise PermissionDenied(
                message="You do not have permission to view audit logs for this business",
                action="view_audit",
                resource="AuditLog",
            )

        filters = _extract_audit_filters(request)
        qs = AuditSelector.list_for_business(business.id, **filters)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)

        if page is not None:
            serializer = AuditLogOutput(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AuditLogOutput(qs, many=True)
        return Response(serializer.data)


# =============================================================================
# PLATFORM-SCOPED AUDIT
# =============================================================================


class PlatformAuditListView(APIView):
    """
    List audit logs for the platform.

    GET /api/v1/platform/audit/

    Returns platform-related actions: configuration changes, admin
    actions, governance session events.
    Requires can_view_audit_logs permission (platform_only scope).
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        summary="List platform audit logs",
        parameters=_AUDIT_QUERY_PARAMS,
        responses={200: AuditLogOutput(many=True)},
        tags=["Audit"],
    )
    def get(self, request):
        from apps.organization.platform.policies import PlatformPolicy

        if not PlatformPolicy._has_platform_permission(
            user=request.user,
            permission_code="can_view_audit_logs",
        ):
            raise PermissionDenied(
                message="You do not have permission to view platform audit logs",
                action="view_audit",
                resource="AuditLog",
            )

        filters = _extract_audit_filters(request)
        qs = AuditSelector.list_for_platform(**filters)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)

        if page is not None:
            serializer = AuditLogOutput(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AuditLogOutput(qs, many=True)
        return Response(serializer.data)


# =============================================================================
# GOVERNANCE-SCOPED AUDIT
# =============================================================================


class GovernanceAuditListView(APIView):
    """
    List all audit logs (governance scope).

    GET /api/v1/governance/audit/

    Full cross-account visibility. Requires governance token +
    can_view_audit_logs permission (global scope).
    """

    permission_classes = [IsAuthenticated, GovernanceTokenRequired]
    pagination_class = LargeResultsPagination

    @extend_schema(
        summary="List all audit logs (governance)",
        parameters=_AUDIT_QUERY_PARAMS,
        responses={200: AuditLogOutput(many=True)},
        tags=["Governance Audit"],
    )
    def get(self, request):
        from apps.organization.business.policies import BusinessPolicy

        if not BusinessPolicy._has_global_permission(
            user=request.user,
            permission_code="can_view_audit_logs",
        ):
            raise PermissionDenied(
                message="You do not have permission to view global audit logs",
                action="view_audit",
                resource="AuditLog",
            )

        filters = _extract_audit_filters(request)
        qs = AuditSelector.list_all(**filters)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)

        if page is not None:
            serializer = AuditLogOutput(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AuditLogOutput(qs, many=True)
        return Response(serializer.data)
