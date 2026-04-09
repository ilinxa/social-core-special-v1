# backend_core/urls/governance.py
"""
Governance URL Group
====================
Routes for governance console endpoints.

System gate: systems.governance
Requires GovernanceTokenRequired permission on all endpoints.
"""

from django.urls import path

from apps.core.observability.audit.views import GovernanceAuditListView
from apps.organization.business import governance_views
from apps.rbac import governance_views as rbac_governance_views
from apps.transaction import governance_views as txn_governance_views

urlpatterns = [
    # Business governance
    path(
        "api/v1/governance/businesses/",
        governance_views.GovernanceBusinessListView.as_view(),
        name="governance-business-list",
    ),
    path(
        "api/v1/governance/businesses/<uuid:pk>/",
        governance_views.GovernanceBusinessDetailView.as_view(),
        name="governance-business-detail",
    ),
    path(
        "api/v1/governance/businesses/<uuid:pk>/suspend/",
        governance_views.GovernanceBusinessSuspendView.as_view(),
        name="governance-business-suspend",
    ),
    path(
        "api/v1/governance/businesses/<uuid:pk>/reactivate/",
        governance_views.GovernanceBusinessReactivateView.as_view(),
        name="governance-business-reactivate",
    ),
    path(
        "api/v1/governance/businesses/<uuid:pk>/archive/",
        governance_views.GovernanceBusinessArchiveView.as_view(),
        name="governance-business-archive",
    ),
    path(
        "api/v1/governance/businesses/<uuid:pk>/transfer-ownership/",
        governance_views.GovernanceBusinessTransferView.as_view(),
        name="governance-business-transfer",
    ),
    # Verification
    path(
        "api/v1/governance/verification/",
        governance_views.GovernanceVerificationListView.as_view(),
        name="governance-verification-list",
    ),
    # Approved creators
    path(
        "api/v1/governance/approved-creators/",
        governance_views.GovernanceApprovedCreatorsView.as_view(),
        name="governance-approved-creators",
    ),
    # Member governance
    path(
        "api/v1/governance/members/",
        rbac_governance_views.GovernanceMemberListView.as_view(),
        name="governance-member-list",
    ),
    path(
        "api/v1/governance/members/<uuid:pk>/",
        rbac_governance_views.GovernanceMemberDetailView.as_view(),
        name="governance-member-detail",
    ),
    path(
        "api/v1/governance/members/<uuid:pk>/action/",
        rbac_governance_views.GovernanceMemberActionView.as_view(),
        name="governance-member-action",
    ),
    # Transactions
    path(
        "api/v1/governance/transactions/",
        txn_governance_views.GovernanceTransactionListView.as_view(),
        name="governance-transaction-list",
    ),
    # Audit
    path(
        "api/v1/governance/audit/",
        GovernanceAuditListView.as_view(),
        name="governance-audit",
    ),
]
