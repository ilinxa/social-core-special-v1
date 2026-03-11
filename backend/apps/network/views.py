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

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination
from apps.core.permissions import IsAuthenticated
from apps.core.types import ActorContext

from apps.network.selectors import FollowSelector, ConnectionSelector
from apps.network.services import FollowService, ConnectionService
from apps.network.policies import NetworkPolicy
from apps.network.serializers import (
    FollowCreateInput,
    FollowOutput,
    FollowingOutput,
    UserConnectionRequestInput,
    UserConnectionOutput,
    BusinessConnectionRequestInput,
    AccountConnectionOutput,
    NetworkStatsOutput,
)


def _get_business(slug):
    """Resolve business by slug."""
    from apps.organization.business.selectors import BusinessAccountSelector
    return BusinessAccountSelector.get_by_slug(slug=slug)


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
                pass

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

    def get(self, request):
        followee_type = request.query_params.get("type")
        qs = FollowSelector.get_following(
            user_id=request.user.id,
            followee_type=followee_type,
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = FollowingOutput(page, many=True)
        return paginator.get_paginated_response(serializer.data)


# =============================================================================
# USER CONNECTION VIEWS
# =============================================================================

class UserConnectionRequestView(APIView):
    """POST /api/v1/network/connections/request/ — Send connection request."""

    permission_classes = [IsAuthenticated]

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

    def get(self, request):
        conn_status = request.query_params.get("status", "active")
        qs = ConnectionSelector.get_user_connections(
            user_id=request.user.id,
            status=conn_status,
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = UserConnectionOutput(
            page, many=True, context={"request": request},
        )
        return paginator.get_paginated_response(serializer.data)


# =============================================================================
# BUSINESS FOLLOW MANAGEMENT VIEWS
# =============================================================================

class BusinessFollowersListView(APIView):
    """GET /api/v1/network/business/<slug>/followers/ — Business followers."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get(self, request, slug):
        business = _get_business(slug)
        qs = FollowSelector.get_followers(
            followee_type="business",
            followee_id=business.id,
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = FollowOutput(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class BusinessFollowerRemoveView(APIView):
    """DELETE /api/v1/network/business/<slug>/followers/<uuid:follow_id>/"""

    permission_classes = [IsAuthenticated]

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

    def get(self, request, slug):
        business = _get_business(slug)
        qs = ConnectionSelector.get_account_connections(
            account_type="business",
            account_id=business.id,
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = AccountConnectionOutput(
            page, many=True,
            context={
                "viewer_account_type": "business",
                "viewer_account_id": str(business.id),
            },
        )
        return paginator.get_paginated_response(serializer.data)


class BusinessConnectionRequestView(APIView):
    """POST /api/v1/network/business/<slug>/connections/request/"""

    permission_classes = [IsAuthenticated]

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
