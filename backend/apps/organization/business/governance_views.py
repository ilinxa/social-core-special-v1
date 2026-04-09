# apps/organization/business/governance_views.py
"""
Governance Business Views - API endpoints for governance console.

All endpoints require:
    - IsAuthenticated (standard JWT)
    - GovernanceTokenRequired (governance-scoped JWT + membership check)

Endpoints:
    /api/v1/governance/businesses/                          GET
    /api/v1/governance/businesses/{uuid}/                   GET
    /api/v1/governance/businesses/{uuid}/suspend/           POST
    /api/v1/governance/businesses/{uuid}/reactivate/        POST
    /api/v1/governance/businesses/{uuid}/archive/           POST
    /api/v1/governance/businesses/{uuid}/transfer-ownership/ POST
    /api/v1/governance/verification/                        GET
    /api/v1/governance/approved-creators/                   GET
"""

from uuid import UUID

from django.db.models import IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import PermissionDenied
from apps.core.pagination import StandardPagination
from apps.core.permissions import IsAuthenticated
from apps.core.permissions.governance import GovernanceTokenRequired
from apps.organization.business.governance_serializers import (
    GovernanceBusinessDetailOutput,
    GovernanceBusinessListOutput,
    GovernanceSuspendInput,
    GovernanceTransferOwnershipInput,
)
from apps.organization.business.policies import BusinessPolicy
from apps.organization.business.selectors import BusinessAccountSelector
from apps.organization.business.services import BusinessAccountService


class GovernanceBusinessListView(APIView):
    """
    List all businesses for governance console.

    GET /api/v1/governance/businesses/
    """

    permission_classes = [IsAuthenticated, GovernanceTokenRequired]

    @extend_schema(
        summary="List businesses (governance)",
        tags=["Governance"],
        parameters=[
            OpenApiParameter("status", str, description="Filter by status"),
            OpenApiParameter(
                "verification_status", str, description="Filter by verification"
            ),
            OpenApiParameter(
                "business_type", str, description="Filter by business type"
            ),
            OpenApiParameter("country", str, description="Filter by country code"),
            OpenApiParameter("search", str, description="Search by legal name"),
            OpenApiParameter(
                "include_deleted", bool, description="Include soft-deleted"
            ),
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
        responses={200: GovernanceBusinessListOutput(many=True)},
    )
    def get(self, request):
        if not BusinessPolicy._has_global_permission(
            user=request.user, permission_code="can_view_businesses"
        ):
            raise PermissionDenied(
                message="Permission denied: can_view_businesses required",
                action="list",
                resource="BusinessAccount",
            )

        params = _extract_business_params(request)
        qs = BusinessAccountSelector.list_filtered(**params)
        qs = _annotate_member_count(qs)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = GovernanceBusinessListOutput(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class GovernanceBusinessDetailView(APIView):
    """
    Get business detail for governance console.

    GET /api/v1/governance/businesses/{uuid}/
    """

    permission_classes = [IsAuthenticated, GovernanceTokenRequired]

    @extend_schema(
        summary="Get business detail (governance)",
        tags=["Governance"],
        parameters=[
            OpenApiParameter(
                "id", UUID, location=OpenApiParameter.PATH, description="Business UUID"
            ),
        ],
        responses={
            200: GovernanceBusinessDetailOutput,
            404: OpenApiResponse(description="Not found"),
        },
    )
    def get(self, request, pk: UUID):
        if not BusinessPolicy._has_global_permission(
            user=request.user, permission_code="can_view_businesses"
        ):
            raise PermissionDenied(
                message="Permission denied: can_view_businesses required",
                action="view",
                resource="BusinessAccount",
            )

        business = BusinessAccountSelector.get_by_id(
            business_id=pk, include_deleted=True
        )

        # Annotate member_count for the serializer
        from apps.rbac.selectors import MembershipSelector

        business.member_count = MembershipSelector.count_active_members(
            account_type="business", account_id=business.id
        )

        serializer = GovernanceBusinessDetailOutput(business)
        data = serializer.data
        data["_permissions"] = BusinessPolicy.get_governance_viewer_permissions(
            user=request.user
        )
        return Response(data)


class GovernanceBusinessSuspendView(APIView):
    """
    Suspend a business via governance console.

    POST /api/v1/governance/businesses/{uuid}/suspend/
    """

    permission_classes = [IsAuthenticated, GovernanceTokenRequired]

    @extend_schema(
        summary="Suspend business (governance)",
        tags=["Governance"],
        request=GovernanceSuspendInput,
        responses={
            200: GovernanceBusinessDetailOutput,
            400: OpenApiResponse(description="Validation error / invalid transition"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def post(self, request, pk: UUID):
        if not BusinessPolicy._has_global_permission(
            user=request.user, permission_code="can_suspend_business"
        ):
            raise PermissionDenied(
                message="Permission denied: can_suspend_business required",
                action="suspend",
                resource="BusinessAccount",
            )

        business = BusinessAccountSelector.get_by_id(business_id=pk)

        serializer = GovernanceSuspendInput(data=request.data)
        serializer.is_valid(raise_exception=True)

        business = BusinessAccountService.suspend(
            business=business,
            reason=serializer.validated_data["reason"],
            actor=request.user,
            request=request,
        )

        output = GovernanceBusinessDetailOutput(business)
        return Response(output.data)


class GovernanceBusinessReactivateView(APIView):
    """
    Reactivate a suspended business via governance console.

    POST /api/v1/governance/businesses/{uuid}/reactivate/
    """

    permission_classes = [IsAuthenticated, GovernanceTokenRequired]

    @extend_schema(
        summary="Reactivate business (governance)",
        tags=["Governance"],
        responses={
            200: GovernanceBusinessDetailOutput,
            400: OpenApiResponse(description="Business is not suspended"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def post(self, request, pk: UUID):
        if not BusinessPolicy._has_global_permission(
            user=request.user, permission_code="can_suspend_business"
        ):
            raise PermissionDenied(
                message="Permission denied: can_suspend_business required",
                action="reactivate",
                resource="BusinessAccount",
            )

        business = BusinessAccountSelector.get_by_id(
            business_id=pk, include_deleted=True
        )

        business = BusinessAccountService.reactivate(
            business=business,
            actor=request.user,
            request=request,
        )

        output = GovernanceBusinessDetailOutput(business)
        return Response(output.data)


class GovernanceBusinessArchiveView(APIView):
    """
    Archive a business via governance console.

    POST /api/v1/governance/businesses/{uuid}/archive/
    """

    permission_classes = [IsAuthenticated, GovernanceTokenRequired]

    @extend_schema(
        summary="Archive business (governance)",
        tags=["Governance"],
        responses={
            200: GovernanceBusinessDetailOutput,
            400: OpenApiResponse(description="Invalid transition"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def post(self, request, pk: UUID):
        if not BusinessPolicy._has_global_permission(
            user=request.user, permission_code="can_suspend_business"
        ):
            raise PermissionDenied(
                message="Permission denied: can_suspend_business required",
                action="archive",
                resource="BusinessAccount",
            )

        business = BusinessAccountSelector.get_by_id(business_id=pk)

        business = BusinessAccountService.archive(
            business=business,
            actor=request.user,
            request=request,
        )

        output = GovernanceBusinessDetailOutput(business)
        return Response(output.data)


class GovernanceBusinessTransferView(APIView):
    """
    Force transfer business ownership via governance console.

    POST /api/v1/governance/businesses/{uuid}/transfer-ownership/
    """

    permission_classes = [IsAuthenticated, GovernanceTokenRequired]

    @extend_schema(
        summary="Transfer business ownership (governance)",
        tags=["Governance"],
        request=GovernanceTransferOwnershipInput,
        responses={
            200: OpenApiResponse(description="Ownership transferred"),
            400: OpenApiResponse(description="Validation error"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def post(self, request, pk: UUID):
        if not BusinessPolicy._has_global_permission(
            user=request.user, permission_code="can_transfer_business_ownership"
        ):
            raise PermissionDenied(
                message="Permission denied: can_transfer_business_ownership required",
                action="transfer_ownership",
                resource="BusinessAccount",
            )

        # Verify business exists
        business = BusinessAccountSelector.get_by_id(business_id=pk)

        serializer = GovernanceTransferOwnershipInput(data=request.data)
        serializer.is_valid(raise_exception=True)

        from django.contrib.auth import get_user_model

        User = get_user_model()
        try:
            new_owner = User.objects.get(
                id=serializer.validated_data["new_owner_id"], is_active=True
            )
        except User.DoesNotExist:
            from apps.core.exceptions import NotFound

            raise NotFound(
                message="New owner user not found or inactive",
                resource="User",
                resource_id=str(serializer.validated_data["new_owner_id"]),
            )

        from apps.rbac.services import RBACService

        RBACService.force_transfer_ownership(
            account_type="business",
            account_id=business.id,
            new_owner_user=new_owner,
            actor=request.user,
            reason=serializer.validated_data.get("reason", ""),
            request=request,
        )

        return Response({"message": "Ownership transferred successfully"})


class GovernanceVerificationListView(APIView):
    """
    List pending verification requests for governance review.

    GET /api/v1/governance/verification/
    """

    permission_classes = [IsAuthenticated, GovernanceTokenRequired]

    @extend_schema(
        summary="List pending verifications (governance)",
        tags=["Governance"],
        parameters=[
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
        responses={200: GovernanceBusinessListOutput(many=True)},
    )
    def get(self, request):
        if not BusinessPolicy._has_global_permission(
            user=request.user, permission_code="can_approve_verification_request"
        ):
            raise PermissionDenied(
                message="Permission denied: can_approve_verification_request required",
                action="list_verification",
                resource="BusinessAccount",
            )

        qs = BusinessAccountSelector.list_pending_verification()
        qs = _annotate_member_count(qs)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = GovernanceBusinessListOutput(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class GovernanceApprovedCreatorsView(APIView):
    """
    List users approved to create businesses.

    GET /api/v1/governance/approved-creators/
    """

    permission_classes = [IsAuthenticated, GovernanceTokenRequired]

    @extend_schema(
        summary="List approved creators (governance)",
        tags=["Governance"],
        parameters=[
            OpenApiParameter("search", str, description="Search by name/email"),
            OpenApiParameter("ordering", str, description="Sort: newest, name, email"),
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
    )
    def get(self, request):
        if not BusinessPolicy._has_global_permission(
            user=request.user, permission_code="can_approve_business_creation"
        ):
            raise PermissionDenied(
                message="Permission denied: can_approve_business_creation required",
                action="list_approved_creators",
                resource="User",
            )

        from apps.users.selectors import UserSelector
        from apps.users.serializers import ApprovedCreatorSerializer

        search = request.query_params.get("search")
        ordering = request.query_params.get("ordering")

        qs = UserSelector.list_approved_business_creators(
            search=search,
            ordering=ordering,
        )

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ApprovedCreatorSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


# =========================================================================
# HELPERS
# =========================================================================


def _annotate_member_count(qs):
    """Annotate queryset with member_count via Subquery (generic relation)."""
    from django.db.models import Count as DjCount

    from apps.core.constants import MembershipStatus
    from apps.rbac.models import Membership

    return qs.annotate(
        member_count=Coalesce(
            Subquery(
                Membership.objects.filter(
                    account_type="business",
                    account_id=OuterRef("id"),
                    status__in=[
                        MembershipStatus.ACTIVE,
                        MembershipStatus.PENDING_APPROVAL,
                    ],
                    is_deleted=False,
                )
                .order_by()
                .values("account_id")
                .annotate(cnt=DjCount("id"))
                .values("cnt")[:1]
            ),
            Value(0),
            output_field=IntegerField(),
        )
    )


def _extract_business_params(request) -> dict:
    """Extract governance business list filter params from request."""
    params = {}
    qp = request.query_params

    if qp.get("status"):
        params["status"] = qp["status"]
    if qp.get("verification_status"):
        params["verification_status"] = qp["verification_status"]
    if qp.get("business_type"):
        params["business_type"] = qp["business_type"]
    if qp.get("country"):
        params["country"] = qp["country"]
    if qp.get("search"):
        params["search"] = qp["search"]
    if qp.get("include_deleted", "").lower() == "true":
        params["include_deleted"] = True

    return params
