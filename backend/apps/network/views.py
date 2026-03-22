# apps/network/views.py
"""
Network Views — API endpoints for follow and connection management.

Endpoints:
    POST   /api/v1/network/follow/                                     → FollowCreateView
    DELETE /api/v1/network/follow/<uuid:follow_id>/                    → FollowDeleteView
    GET    /api/v1/network/following/                                   → FollowingListView

    POST   /api/v1/network/connections/request/                        → UserConnectionRequestView
    DELETE /api/v1/network/connections/<uuid:connection_id>/            → UserConnectionDeleteView
    GET    /api/v1/network/connections/                                 → UserConnectionListView

    GET    /api/v1/network/business/<slug>/followers/                   → BusinessFollowersListView
    DELETE /api/v1/network/business/<slug>/followers/<uuid:follow_id>/  → BusinessFollowerRemoveView
    GET    /api/v1/network/business/<slug>/connections/                 → BusinessConnectionListView
    POST   /api/v1/network/business/<slug>/connections/request/         → BusinessConnectionRequestView
    DELETE /api/v1/network/business/<slug>/connections/<uuid:id>/       → BusinessConnectionDeleteView

    GET    /api/v1/network/stats/                                       → UserNetworkStatsView
    GET    /api/v1/network/business/<slug>/stats/                       → BusinessNetworkStatsView
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.observability import get_logger
from apps.core.pagination import StandardPagination
from apps.core.permissions import IsAuthenticated
from apps.core.types import ActorContext
from apps.network.policies import NetworkPolicy
from apps.network.selectors import ConnectionSelector, FollowSelector
from apps.network.serializers import (
    AccountConnectionOutput,
    BusinessConnectionRequestInput,
    FollowCreateInput,
    FollowingOutput,
    FollowOutput,
    NetworkStatsOutput,
    UserConnectionOutput,
    UserConnectionRequestInput,
)
from apps.network.services import ConnectionService, FollowService

logger = get_logger(__name__)


def _get_business(slug):
    """Resolve business by slug."""
    from apps.organization.business.selectors import BusinessAccountSelector

    return BusinessAccountSelector.get_by_slug(slug=slug)


def _batch_load_followees(follows):
    """Batch-load business/platform accounts for a page of follows."""
    from apps.organization.business.models import BusinessAccount
    from apps.organization.platform.models import PlatformAccount

    biz_ids = set()
    plat_ids = set()
    for f in follows:
        if f.followee_type == "business":
            biz_ids.add(f.followee_id)
        elif f.followee_type == "platform":
            plat_ids.add(f.followee_id)

    accounts = {}
    if biz_ids:
        for a in BusinessAccount.objects.select_related("profile").filter(
            id__in=biz_ids
        ):
            accounts[a.id] = a
    if plat_ids:
        for a in PlatformAccount.objects.select_related("profile").filter(
            id__in=plat_ids
        ):
            accounts[a.id] = a
    return accounts


def _batch_load_connection_accounts(connections, viewer_type, viewer_id):
    """Batch-load 'other' accounts for a page of account connections."""
    from apps.organization.business.models import BusinessAccount
    from apps.organization.platform.models import PlatformAccount

    biz_ids = set()
    plat_ids = set()
    for c in connections:
        if c.account_a_type == viewer_type and str(c.account_a_id) == str(viewer_id):
            other_type, other_id = c.account_b_type, c.account_b_id
        else:
            other_type, other_id = c.account_a_type, c.account_a_id
        if other_type == "business":
            biz_ids.add(other_id)
        elif other_type == "platform":
            plat_ids.add(other_id)

    accounts = {}
    if biz_ids:
        for a in BusinessAccount.objects.select_related("profile").filter(
            id__in=biz_ids
        ):
            accounts[a.id] = a
    if plat_ids:
        for a in PlatformAccount.objects.select_related("profile").filter(
            id__in=plat_ids
        ):
            accounts[a.id] = a
    return accounts


# =============================================================================
# FOLLOW VIEWS
# =============================================================================


class FollowCreateView(APIView):
    """
    POST /api/v1/network/follow/

    Create a follow. Routes to the appropriate transaction type based on
    followee_type and business privacy setting.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Follow an account",
        description=(
            "Follow a business or platform account. For public businesses, creates "
            "a direct follow. For private businesses, creates a follow approval request "
            "that the business must accept."
        ),
        tags=["Network"],
        request=FollowCreateInput,
        responses={
            201: OpenApiResponse(description="Follow created or request submitted"),
            400: OpenApiResponse(
                description="Validation error or unsupported followee type"
            ),
            401: OpenApiResponse(description="Authentication required"),
            409: OpenApiResponse(description="Already following this account"),
        },
    )
    def post(self, request):
        serializer = FollowCreateInput(data=request.data)
        serializer.is_valid(raise_exception=True)

        followee_type = serializer.validated_data["followee_type"]
        followee_id = serializer.validated_data["followee_id"]

        from apps.transaction.services import TransactionService

        if followee_type == "platform":
            txn = TransactionService.create_request(
                transaction_type="platform_follow_request",
                user_id=request.user.id,
                target_account_type="platform",
                target_account_id=followee_id,
                request=request,
            )
        elif followee_type == "business":
            # Check if business is public or private
            from apps.organization.business.selectors import BusinessAccountSelector

            business = BusinessAccountSelector.get_by_id(business_id=followee_id)
            is_public = True
            try:
                is_public = business.profile.is_public
            except Exception:
                logger.warning(
                    "network.follow.profile_access_failed",
                    business_id=str(followee_id),
                )

            if is_public:
                txn = TransactionService.create_request(
                    transaction_type="business_follow_request",
                    user_id=request.user.id,
                    target_account_type="business",
                    target_account_id=followee_id,
                    request=request,
                )
            else:
                txn = TransactionService.create_request(
                    transaction_type="business_follow_approval_request",
                    user_id=request.user.id,
                    target_account_type="business",
                    target_account_id=followee_id,
                    request=request,
                )
        else:
            return Response(
                {"detail": f"Unsupported followee_type: {followee_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"transaction_id": str(txn.id), "status": txn.status},
            status=status.HTTP_201_CREATED,
        )


class FollowDeleteView(APIView):
    """DELETE /api/v1/network/follow/<uuid:follow_id>/ — Unfollow."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Unfollow an account",
        description="Remove a follow relationship by its ID.",
        tags=["Network"],
        parameters=[
            OpenApiParameter(
                name="follow_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Follow record ID",
            ),
        ],
        responses={
            204: OpenApiResponse(description="Unfollowed successfully"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Follow not found"),
        },
    )
    def delete(self, request, follow_id):
        FollowService.unfollow(
            follow_id=follow_id,
            user=request.user,
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class FollowingListView(APIView):
    """GET /api/v1/network/following/ — My followed accounts."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        summary="List accounts you follow",
        description="Paginated list of accounts the authenticated user follows. Optionally filter by type.",
        tags=["Network"],
        parameters=[
            OpenApiParameter(
                name="type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by followee type (business, platform)",
                required=False,
            ),
        ],
        responses={
            200: FollowingOutput(many=True),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def get(self, request):
        followee_type = request.query_params.get("type")
        qs = FollowSelector.get_following(
            user_id=request.user.id,
            followee_type=followee_type,
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        context = {"followee_accounts": _batch_load_followees(page)}
        serializer = FollowingOutput(page, many=True, context=context)
        return paginator.get_paginated_response(serializer.data)


# =============================================================================
# USER CONNECTION VIEWS
# =============================================================================


class UserConnectionRequestView(APIView):
    """POST /api/v1/network/connections/request/ — Send connection request."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Send a connection request",
        description="Send a user-to-user connection request. Creates a transaction that the target user must accept.",
        tags=["Network"],
        request=UserConnectionRequestInput,
        responses={
            201: OpenApiResponse(description="Connection request created"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Authentication required"),
            409: OpenApiResponse(
                description="Connection or pending request already exists"
            ),
        },
    )
    def post(self, request):
        serializer = UserConnectionRequestInput(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_user_id = serializer.validated_data["target_user_id"]
        note = serializer.validated_data.get("note", "")

        from apps.transaction.services import TransactionService

        txn = TransactionService.create_request(
            transaction_type="user_connection_request",
            user_id=request.user.id,
            target_user_id=target_user_id,
            payload={"note": note},
            request=request,
        )

        return Response(
            {"transaction_id": str(txn.id), "status": txn.status},
            status=status.HTTP_201_CREATED,
        )


class UserConnectionDeleteView(APIView):
    """DELETE /api/v1/network/connections/<uuid:connection_id>/ — Disconnect."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Remove a connection",
        description="Disconnect from another user by connection ID.",
        tags=["Network"],
        parameters=[
            OpenApiParameter(
                name="connection_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Connection record ID",
            ),
        ],
        responses={
            204: OpenApiResponse(description="Connection removed"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Connection not found"),
        },
    )
    def delete(self, request, connection_id):
        ConnectionService.disconnect_user_connection(
            connection_id=connection_id,
            user=request.user,
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserConnectionListView(APIView):
    """GET /api/v1/network/connections/ — My connections."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        summary="List your connections",
        description="Paginated list of the authenticated user's connections. Filter by status.",
        tags=["Network"],
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by connection status (active, pending). Default: active",
                required=False,
            ),
        ],
        responses={
            200: UserConnectionOutput(many=True),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def get(self, request):
        conn_status = request.query_params.get("status", "active")
        qs = ConnectionSelector.get_user_connections(
            user_id=request.user.id,
            status=conn_status,
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = UserConnectionOutput(
            page,
            many=True,
            context={"request": request},
        )
        return paginator.get_paginated_response(serializer.data)


# =============================================================================
# BUSINESS FOLLOW MANAGEMENT VIEWS
# =============================================================================


class BusinessFollowersListView(APIView):
    """GET /api/v1/network/business/<slug>/followers/ — Business followers."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        summary="List business followers",
        description="Paginated list of users following the specified business.",
        tags=["Network"],
        parameters=[
            OpenApiParameter(
                name="slug",
                type=str,
                location=OpenApiParameter.PATH,
                description="Business slug",
            ),
        ],
        responses={
            200: FollowOutput(many=True),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Business not found"),
        },
    )
    def get(self, request, slug):
        business = _get_business(slug)
        qs = FollowSelector.get_followers(
            followee_type="business",
            followee_id=business.id,
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        context = {"followee_accounts": {business.id: business}}
        serializer = FollowOutput(page, many=True, context=context)
        return paginator.get_paginated_response(serializer.data)


class BusinessFollowerRemoveView(APIView):
    """DELETE /api/v1/network/business/<slug>/followers/<uuid:follow_id>/"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Remove a follower from business",
        description="Remove a follower from the business. Requires can_manage_followers permission.",
        tags=["Network"],
        parameters=[
            OpenApiParameter(
                name="slug",
                type=str,
                location=OpenApiParameter.PATH,
                description="Business slug",
            ),
            OpenApiParameter(
                name="follow_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Follow record ID",
            ),
        ],
        responses={
            204: OpenApiResponse(description="Follower removed"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Follow not found"),
        },
    )
    def delete(self, request, slug, follow_id):
        actor_context = ActorContext.for_user_context(request.user, request=request)
        FollowService.remove_follower(
            follow_id=follow_id,
            actor=request.user,
            actor_context=actor_context,
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# BUSINESS CONNECTION VIEWS
# =============================================================================


class BusinessConnectionListView(APIView):
    """GET /api/v1/network/business/<slug>/connections/"""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        summary="List business connections",
        description="Paginated list of account-level connections for the specified business.",
        tags=["Network"],
        parameters=[
            OpenApiParameter(
                name="slug",
                type=str,
                location=OpenApiParameter.PATH,
                description="Business slug",
            ),
        ],
        responses={
            200: AccountConnectionOutput(many=True),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Business not found"),
        },
    )
    def get(self, request, slug):
        business = _get_business(slug)
        qs = ConnectionSelector.get_account_connections(
            account_type="business",
            account_id=business.id,
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        account_data = _batch_load_connection_accounts(page, "business", business.id)
        serializer = AccountConnectionOutput(
            page,
            many=True,
            context={
                "viewer_account_type": "business",
                "viewer_account_id": str(business.id),
                "account_data": account_data,
            },
        )
        return paginator.get_paginated_response(serializer.data)


class BusinessConnectionRequestView(APIView):
    """POST /api/v1/network/business/<slug>/connections/request/"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Send a business connection request",
        description=(
            "Send an account-level connection request from this business to another "
            "business or platform. Requires can_manage_connections permission on the business."
        ),
        tags=["Network"],
        parameters=[
            OpenApiParameter(
                name="slug",
                type=str,
                location=OpenApiParameter.PATH,
                description="Initiating business slug",
            ),
        ],
        request=BusinessConnectionRequestInput,
        responses={
            201: OpenApiResponse(description="Connection request created"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Permission denied"),
            409: OpenApiResponse(
                description="Connection or pending request already exists"
            ),
        },
    )
    def post(self, request, slug):
        business = _get_business(slug)

        serializer = BusinessConnectionRequestInput(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_account_type = serializer.validated_data["target_account_type"]
        target_account_id = serializer.validated_data["target_account_id"]
        note = serializer.validated_data.get("note", "")

        # RBAC check: user must have can_manage_connections on the initiating business
        from apps.core.exceptions import PermissionDenied

        if not NetworkPolicy.can_manage_connections(
            user=request.user,
            account_type="business",
            account_id=business.id,
        ):
            raise PermissionDenied(
                message="You do not have permission to manage connections for this business",
                action="create_connection_request",
                resource="Business",
            )

        from apps.transaction.services import TransactionService

        # Choose transaction type based on target
        if target_account_type == "platform":
            txn_type = "business_platform_connection_request"
            txn = TransactionService.create_request(
                transaction_type=txn_type,
                user_id=request.user.id,
                target_account_type="platform",
                target_account_id=target_account_id,
                payload={
                    "initiator_account_type": "business",
                    "initiator_account_id": str(business.id),
                    "note": note,
                },
                request=request,
            )
        else:
            # business → business
            txn_type = "business_connection_request"
            txn = TransactionService.create_request(
                transaction_type=txn_type,
                user_id=request.user.id,
                target_account_type="business",
                target_account_id=target_account_id,
                payload={
                    "initiator_account_type": "business",
                    "initiator_account_id": str(business.id),
                    "note": note,
                },
                request=request,
            )

        return Response(
            {"transaction_id": str(txn.id), "status": txn.status},
            status=status.HTTP_201_CREATED,
        )


class BusinessConnectionDeleteView(APIView):
    """DELETE /api/v1/network/business/<slug>/connections/<uuid:connection_id>/"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Remove a business connection",
        description="Disconnect this business from another account by connection ID.",
        tags=["Network"],
        parameters=[
            OpenApiParameter(
                name="slug",
                type=str,
                location=OpenApiParameter.PATH,
                description="Business slug",
            ),
            OpenApiParameter(
                name="connection_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Connection record ID",
            ),
        ],
        responses={
            204: OpenApiResponse(description="Connection removed"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Connection not found"),
        },
    )
    def delete(self, request, slug, connection_id):
        actor_context = ActorContext.for_user_context(request.user, request=request)
        ConnectionService.disconnect_account_connection(
            connection_id=connection_id,
            actor=request.user,
            actor_context=actor_context,
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# STATS VIEWS
# =============================================================================


class UserNetworkStatsView(APIView):
    """GET /api/v1/network/stats/ — Current user's network stats."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get user network statistics",
        description="Returns follower, following, and connection counts for the authenticated user.",
        tags=["Network"],
        responses={
            200: NetworkStatsOutput,
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def get(self, request):
        data = {
            "followers_count": 0,
            "following_count": FollowSelector.count_following(
                user_id=request.user.id,
            ),
            "connections_count": ConnectionSelector.count_user_connections(
                user_id=request.user.id,
            ),
        }
        serializer = NetworkStatsOutput(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BusinessNetworkStatsView(APIView):
    """GET /api/v1/network/business/<slug>/stats/"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get business network statistics",
        description="Returns follower, following, and connection counts for the specified business.",
        tags=["Network"],
        parameters=[
            OpenApiParameter(
                name="slug",
                type=str,
                location=OpenApiParameter.PATH,
                description="Business slug",
            ),
        ],
        responses={
            200: NetworkStatsOutput,
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Business not found"),
        },
    )
    def get(self, request, slug):
        business = _get_business(slug)
        data = {
            "followers_count": FollowSelector.count_followers(
                followee_type="business",
                followee_id=business.id,
            ),
            "following_count": 0,
            "connections_count": ConnectionSelector.count_account_connections(
                account_type="business",
                account_id=business.id,
            ),
        }
        serializer = NetworkStatsOutput(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
