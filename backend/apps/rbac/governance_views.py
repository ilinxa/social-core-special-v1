# apps/rbac/governance_views.py
"""
Governance Member Views - API endpoints for cross-account member governance.

All endpoints require:
    - IsAuthenticated (standard JWT)
    - GovernanceTokenRequired (governance-scoped JWT + membership check)

Endpoints:
    /api/v1/governance/members/                GET
    /api/v1/governance/members/{uuid}/         GET
    /api/v1/governance/members/{uuid}/action/   POST
"""

from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.constants import MembershipStatus
from apps.core.exceptions import PermissionDenied
from apps.core.pagination import StandardPagination
from apps.core.permissions import IsAuthenticated
from apps.core.permissions.governance import GovernanceTokenRequired
from apps.organization.business.policies import BusinessPolicy
from apps.rbac.governance_serializers import (
    GovernanceMemberActionInput,
    GovernanceMemberDetailOutput,
    GovernanceMemberListOutput,
    annotate_account_context,
)
from apps.rbac.policies import MembershipPolicy
from apps.rbac.selectors import MembershipSelector
from apps.rbac.services import RBACService


def _build_governance_actor_context(request):
    """Build ActorContext from the governance user's platform membership."""
    from apps.organization.platform.models import PlatformAccount

    platform = PlatformAccount.objects.first()
    if not platform:
        raise PermissionDenied(message="Platform not configured")

    actor_membership = MembershipSelector.get_active_membership_for_user_account(
        user=request.user, account_type="platform", account_id=platform.id
    )
    if not actor_membership:
        raise PermissionDenied(message="No active platform membership")

    return RBACService.build_actor_context(membership=actor_membership, request=request)


class GovernanceMemberListView(APIView):
    """
    List all members across all accounts for governance console.

    GET /api/v1/governance/members/
    """

    permission_classes = [IsAuthenticated, GovernanceTokenRequired]

    @extend_schema(
        summary="List members (governance)",
        tags=["Governance"],
        parameters=[
            OpenApiParameter("account_type", str, description="Filter by account type"),
            OpenApiParameter("status", str, description="Filter by status"),
            OpenApiParameter(
                "search", str, description="Search by email/username/name"
            ),
            OpenApiParameter(
                "include_deleted", bool, description="Include soft-deleted"
            ),
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
        responses={200: GovernanceMemberListOutput(many=True)},
    )
    def get(self, request):
        if not BusinessPolicy._has_global_permission(
            user=request.user, permission_code="can_view_members"
        ):
            raise PermissionDenied(
                message="Permission denied: can_view_members required",
                action="list",
                resource="Membership",
            )

        params = _extract_member_params(request)
        qs = MembershipSelector.list_all_members(**params)
        qs = annotate_account_context(qs)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = GovernanceMemberListOutput(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class GovernanceMemberDetailView(APIView):
    """
    Get member detail for governance console.

    GET /api/v1/governance/members/{uuid}/
    """

    permission_classes = [IsAuthenticated, GovernanceTokenRequired]

    @extend_schema(
        summary="Get member detail (governance)",
        tags=["Governance"],
        parameters=[
            OpenApiParameter(
                "id",
                UUID,
                location=OpenApiParameter.PATH,
                description="Membership UUID",
            ),
        ],
        responses={
            200: GovernanceMemberDetailOutput,
            404: OpenApiResponse(description="Not found"),
        },
    )
    def get(self, request, pk: UUID):
        if not BusinessPolicy._has_global_permission(
            user=request.user, permission_code="can_view_members"
        ):
            raise PermissionDenied(
                message="Permission denied: can_view_members required",
                action="view",
                resource="Membership",
            )

        membership = MembershipSelector.get_membership_by_id_global(membership_id=pk)

        # Annotate account context on the single instance
        from apps.organization.business.models import BusinessAccount
        from apps.organization.platform.models import PlatformProfile

        if membership.account_type == "business":
            biz = (
                BusinessAccount.all_objects.filter(id=membership.account_id)
                .values_list("legal_name", "slug")
                .first()
            )
            membership.account_name = biz[0] if biz else "Unknown"
            membership.account_slug = biz[1] if biz else None
        else:
            pp = (
                PlatformProfile.objects.filter(platform_id=membership.account_id)
                .values_list("name", flat=True)
                .first()
            )
            membership.account_name = pp or "Platform"
            membership.account_slug = None

        serializer = GovernanceMemberDetailOutput(membership)
        data = serializer.data

        # Inject _permissions
        actor_context = _build_governance_actor_context(request)
        data["_permissions"] = MembershipPolicy.get_viewer_permissions(
            actor_context=actor_context,
            target_membership=membership,
        )
        return Response(data)


class GovernanceMemberActionView(APIView):
    """
    Governance member enforcement action.

    POST /api/v1/governance/members/{uuid}/action/

    Supports: suspend, ban, remove, reactivate
    """

    permission_classes = [IsAuthenticated, GovernanceTokenRequired]

    ACTION_STATUS_MAP = {
        "suspend": MembershipStatus.SUSPENDED,
        "ban": MembershipStatus.BANNED,
        "remove": MembershipStatus.REMOVED,
        "reactivate": MembershipStatus.ACTIVE,
    }

    @extend_schema(
        summary="Member enforcement action (governance)",
        tags=["Governance"],
        request=GovernanceMemberActionInput,
        responses={
            200: GovernanceMemberDetailOutput,
            400: OpenApiResponse(description="Validation error"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def post(self, request, pk: UUID):
        serializer = GovernanceMemberActionInput(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        reason = serializer.validated_data.get("reason", "")
        new_status = self.ACTION_STATUS_MAP[action]

        actor_context = _build_governance_actor_context(request)

        membership = RBACService.update_membership_status(
            membership_id=pk,
            new_status=new_status,
            actor_context=actor_context,
            reason=reason,
            request=request,
        )

        # Re-fetch with account context for response
        from apps.organization.business.models import BusinessAccount
        from apps.organization.platform.models import PlatformProfile

        if membership.account_type == "business":
            biz = (
                BusinessAccount.all_objects.filter(id=membership.account_id)
                .values_list("legal_name", "slug")
                .first()
            )
            membership.account_name = biz[0] if biz else "Unknown"
            membership.account_slug = biz[1] if biz else None
        else:
            pp = (
                PlatformProfile.objects.filter(platform_id=membership.account_id)
                .values_list("name", flat=True)
                .first()
            )
            membership.account_name = pp or "Platform"
            membership.account_slug = None

        output = GovernanceMemberDetailOutput(membership)
        return Response(output.data)


# =========================================================================
# HELPERS
# =========================================================================


def _extract_member_params(request) -> dict:
    """Extract governance member list filter params from request."""
    params = {}
    qp = request.query_params

    if qp.get("account_type"):
        params["account_type"] = qp["account_type"]
    if qp.get("status"):
        params["status"] = qp["status"]
    if qp.get("search"):
        params["search"] = qp["search"]
    if qp.get("include_deleted", "").lower() == "true":
        params["include_deleted"] = True

    return params
