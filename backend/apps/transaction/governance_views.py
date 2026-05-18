# apps/transaction/governance_views.py
"""
Governance Transaction Views - Global transaction listing for governance console.

All endpoints require:
    - IsAuthenticated (standard JWT)
    - GovernanceTokenRequired (governance-scoped JWT + membership check)

Endpoints:
    /api/v1/governance/transactions/   GET
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView

from apps.core.exceptions import PermissionDenied
from apps.core.pagination import StandardPagination
from apps.core.permissions import FeatureRequired, IsAuthenticated
from apps.core.permissions.governance import GovernanceTokenRequired
from apps.organization.business.policies import BusinessPolicy
from apps.transaction.api.serializers import TransactionListSerializer
from apps.transaction.selectors import TransactionSelector


class GovernanceTransactionListView(APIView):
    """
    List all transactions across all accounts for governance console.

    GET /api/v1/governance/transactions/
    """

    permission_classes = [
        IsAuthenticated,
        GovernanceTokenRequired,
        FeatureRequired("platform.governance.global_moderation"),
    ]

    @extend_schema(
        summary="List transactions (governance)",
        tags=["Governance"],
        parameters=[
            OpenApiParameter("status", str, description="Filter by status"),
            OpenApiParameter(
                "mode", str, description="Filter by mode (invitation/request)"
            ),
            OpenApiParameter(
                "transaction_type", str, description="Filter by transaction type"
            ),
            OpenApiParameter(
                "context_type",
                str,
                description="Filter by context type (business/platform)",
            ),
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
        responses={200: TransactionListSerializer(many=True)},
    )
    def get(self, request):
        if not BusinessPolicy._has_global_permission(
            user=request.user, permission_code="can_view_all_transactions"
        ):
            raise PermissionDenied(
                message="Permission denied: can_view_all_transactions required",
                action="list",
                resource="Transaction",
            )

        params = _extract_transaction_params(request)
        qs = TransactionSelector.list_all_transactions(**params)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = TransactionListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


def _extract_transaction_params(request) -> dict:
    """Extract governance transaction list filter params from request."""
    params = {}
    qp = request.query_params

    if qp.get("status"):
        params["status"] = qp["status"]
    if qp.get("mode"):
        params["mode"] = qp["mode"]
    if qp.get("transaction_type"):
        params["transaction_type"] = qp["transaction_type"]
    if qp.get("context_type"):
        params["context_type"] = qp["context_type"]

    return params
