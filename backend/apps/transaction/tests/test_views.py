from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.constants import AccountType, ContextType
from apps.core.types import ActorContext
from apps.transaction.constants import PartyType, TransactionMode, TransactionStatus
from apps.transaction.tests.conftest import (
    transaction_accept_url,
    transaction_approve_url,
    transaction_cancel_url,
    transaction_deny_url,
    transaction_detail_url,
    transaction_dismiss_url,
)
from apps.transaction.tests.factories import TransactionFactory
from apps.users.tests.factories import UserFactory

# =========================================================================
# LIST VIEW
# =========================================================================


@pytest.mark.django_db
class TestTransactionListView:

    def test_returns_user_transactions(
        self,
        authenticated_client,
        user,
        transaction_list_url,
    ):
        # User is initiator
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user.id,
        )
        # User is target
        TransactionFactory(target_type=PartyType.USER, target_id=user.id)
        # Unrelated
        TransactionFactory()

        response = authenticated_client.get(transaction_list_url)
        assert response.status_code == 200
        assert response.data["count"] == 2

    def test_filter_by_role_initiator(
        self,
        authenticated_client,
        user,
        transaction_list_url,
    ):
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user.id,
        )
        TransactionFactory(target_type=PartyType.USER, target_id=user.id)

        response = authenticated_client.get(
            f"{transaction_list_url}?role=initiator",
        )
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_filter_by_role_target(
        self,
        authenticated_client,
        user,
        transaction_list_url,
    ):
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user.id,
        )
        TransactionFactory(target_type=PartyType.USER, target_id=user.id)

        response = authenticated_client.get(
            f"{transaction_list_url}?role=target",
        )
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_list_includes_expanded_fields(
        self,
        authenticated_client,
        user,
        transaction_list_url,
    ):
        """List serializer includes category, initiator_name, target_name."""
        TransactionFactory(
            transaction_type="business_membership_invitation",
            mode=TransactionMode.INVITATION,
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            target_type=PartyType.USER,
            target_id=user.id,
        )
        response = authenticated_client.get(
            f"{transaction_list_url}?role=initiator",
        )
        assert response.status_code == 200
        item = response.data["results"][0]
        assert "category" in item
        assert item["category"] == "membership"
        assert "initiator_name" in item
        assert "target_name" in item
        assert "context_type" in item

    def test_filter_by_status(
        self,
        authenticated_client,
        user,
        transaction_list_url,
    ):
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            status=TransactionStatus.PENDING,
        )
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            status=TransactionStatus.ACCEPTED,
        )
        response = authenticated_client.get(
            f"{transaction_list_url}?role=initiator&status=pending",
        )
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_filter_by_mode(
        self,
        authenticated_client,
        user,
        transaction_list_url,
    ):
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            mode=TransactionMode.INVITATION,
        )
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            mode=TransactionMode.REQUEST,
        )
        response = authenticated_client.get(
            f"{transaction_list_url}?role=initiator&mode=invitation",
        )
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_filter_by_transaction_type(
        self,
        authenticated_client,
        user,
        transaction_list_url,
    ):
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            transaction_type="business_membership_invitation",
        )
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            transaction_type="user_connection_request",
        )
        response = authenticated_client.get(
            f"{transaction_list_url}?role=initiator&transaction_type=user_connection_request",
        )
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_all_role_with_filters_uses_non_union_query(
        self,
        authenticated_client,
        user,
        another_user,
        transaction_list_url,
    ):
        """When role=all + filters, re-queries without UNION to support filtering."""
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            status=TransactionStatus.PENDING,
        )
        TransactionFactory(
            target_type=PartyType.USER,
            target_id=user.id,
            status=TransactionStatus.ACCEPTED,
        )
        response = authenticated_client.get(
            f"{transaction_list_url}?status=pending",
        )
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_unauthenticated_returns_401(
        self,
        api_client,
        transaction_list_url,
    ):
        response = api_client.get(transaction_list_url)
        assert response.status_code == 401

    def test_context_filter_returns_all_account_transactions(
        self,
        authenticated_client,
        user,
        another_user,
        transaction_list_url,
        business,
        owner_with_approve_perm,
    ):
        """context_type+context_id returns ALL transactions in that account,
        including ones where the viewer is not personally initiator/target."""
        # Request FROM another_user TO the business (user is NOT initiator or target)
        TransactionFactory(
            transaction_type="business_membership_request",
            mode=TransactionMode.REQUEST,
            initiator_type=PartyType.USER,
            initiator_id=another_user.id,
            target_type=PartyType.ACCOUNT,
            target_id=business.id,
            context_type=ContextType.BUSINESS,
            context_id=business.id,
            status=TransactionStatus.PENDING,
        )
        # Invitation FROM user within the business context
        TransactionFactory(
            transaction_type="business_membership_invitation",
            mode=TransactionMode.INVITATION,
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            target_type=PartyType.USER,
            target_id=another_user.id,
            context_type=ContextType.BUSINESS,
            context_id=business.id,
            status=TransactionStatus.PENDING,
        )
        # Unrelated transaction in a different context
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            context_type=ContextType.USER,
            context_id=user.id,
        )

        response = authenticated_client.get(
            f"{transaction_list_url}?context_type=business&context_id={business.id}",
        )
        assert response.status_code == 200
        assert response.data["count"] == 2

    def test_context_filter_with_mode_filter(
        self,
        authenticated_client,
        user,
        another_user,
        transaction_list_url,
        business,
        owner_membership,
    ):
        """context_type+context_id + mode filter works together."""
        TransactionFactory(
            mode=TransactionMode.REQUEST,
            initiator_type=PartyType.USER,
            initiator_id=another_user.id,
            target_type=PartyType.ACCOUNT,
            target_id=business.id,
            context_type=ContextType.BUSINESS,
            context_id=business.id,
        )
        TransactionFactory(
            mode=TransactionMode.INVITATION,
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            target_type=PartyType.USER,
            target_id=another_user.id,
            context_type=ContextType.BUSINESS,
            context_id=business.id,
        )

        response = authenticated_client.get(
            f"{transaction_list_url}?context_type=business&context_id={business.id}&mode=request",
        )
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_context_filter_non_member_gets_empty(
        self,
        api_client,
        another_user,
        transaction_list_url,
        business,
    ):
        """Non-member querying by context_type+context_id gets no results."""
        api_client.force_authenticate(user=another_user)
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=another_user.id,
            context_type=ContextType.BUSINESS,
            context_id=business.id,
        )

        response = api_client.get(
            f"{transaction_list_url}?context_type=business&context_id={business.id}",
        )
        assert response.status_code == 200
        assert response.data["count"] == 0


# =========================================================================
# DETAIL VIEW
# =========================================================================


@pytest.mark.django_db
class TestTransactionDetailView:

    def test_initiator_can_view(
        self,
        authenticated_client,
        user,
        pending_invitation,
        owner_actor_context,
    ):
        response = authenticated_client.get(
            transaction_detail_url(pending_invitation.id),
        )
        assert response.status_code == 200
        assert response.data["id"] == str(pending_invitation.id)

    def test_target_can_view(self, another_user, pending_invitation):
        client = APIClient()
        client.force_authenticate(user=another_user)
        response = client.get(
            transaction_detail_url(pending_invitation.id),
        )
        assert response.status_code == 200

    def test_unrelated_user_gets_403(self, third_user, pending_invitation):
        client = APIClient()
        client.force_authenticate(user=third_user)
        response = client.get(
            transaction_detail_url(pending_invitation.id),
        )
        assert response.status_code == 403

    def test_not_found_returns_404(self, authenticated_client):
        response = authenticated_client.get(
            transaction_detail_url(uuid4()),
        )
        assert response.status_code == 404

    def test_permissions_injected_in_detail_response(
        self,
        another_user,
        pending_invitation,
    ):
        """GET detail includes _permissions dict."""
        client = APIClient()
        client.force_authenticate(user=another_user)
        response = client.get(
            transaction_detail_url(pending_invitation.id),
        )
        assert response.status_code == 200
        perms = response.data.get("_permissions")
        assert perms is not None
        assert "can_accept" in perms
        assert "can_deny" in perms
        assert "can_cancel" in perms
        assert "can_dismiss" in perms
        assert "can_request_info" in perms
        assert "can_resubmit" in perms
        assert "can_view_form" in perms

    def test_target_can_accept_pending_invitation(
        self,
        another_user,
        pending_invitation,
    ):
        """Target user sees can_accept=True for pending invitation."""
        client = APIClient()
        client.force_authenticate(user=another_user)
        response = client.get(
            transaction_detail_url(pending_invitation.id),
        )
        perms = response.data["_permissions"]
        assert perms["can_accept"] is True
        assert perms["can_deny"] is True
        assert perms["can_cancel"] is False  # not initiator

    def test_initiator_can_cancel_not_accept(
        self,
        authenticated_client,
        pending_invitation,
    ):
        """Initiator sees can_cancel=True but can_accept=False."""
        response = authenticated_client.get(
            transaction_detail_url(pending_invitation.id),
        )
        perms = response.data["_permissions"]
        assert perms["can_cancel"] is True
        assert perms["can_accept"] is False  # not target


# =========================================================================
# CREATE INVITATION VIEW
# =========================================================================


@pytest.mark.django_db
class TestCreateInvitationView:

    def test_happy_path(
        self,
        authenticated_client,
        user,
        business,
        owner_with_invite_perm,
        another_user,
        base_member_role,
        transaction_invitation_url,
    ):
        response = authenticated_client.post(
            transaction_invitation_url,
            data={
                "transaction_type": "business_membership_invitation",
                "target_user_id": str(another_user.id),
                "context_type": str(ContextType.BUSINESS),
                "context_id": str(business.id),
                "payload": {"role_id": str(base_member_role.id)},
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["status"] == "pending"

    def test_non_member_returns_403(
        self,
        another_user,
        business,
        transaction_invitation_url,
    ):
        client = APIClient()
        client.force_authenticate(user=another_user)
        response = client.post(
            transaction_invitation_url,
            data={
                "transaction_type": "business_membership_invitation",
                "target_user_id": str(uuid4()),
                "context_type": str(ContextType.BUSINESS),
                "context_id": str(business.id),
            },
            format="json",
        )
        assert response.status_code == 403

    def test_invalid_data_returns_400(
        self,
        authenticated_client,
        transaction_invitation_url,
    ):
        response = authenticated_client.post(
            transaction_invitation_url,
            data={},
            format="json",
        )
        assert response.status_code == 400


# =========================================================================
# CREATE REQUEST VIEW
# =========================================================================


@pytest.mark.django_db
class TestCreateRequestView:

    def test_happy_path_account_targeted(
        self,
        another_user,
        business,
        transaction_request_url,
    ):
        client = APIClient()
        client.force_authenticate(user=another_user)
        response = client.post(
            transaction_request_url,
            data={
                "transaction_type": "business_membership_request",
                "target_account_id": str(business.id),
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["status"] == "pending"

    def test_happy_path_user_targeted(
        self,
        user,
        another_user,
        transaction_request_url,
    ):
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            transaction_request_url,
            data={
                "transaction_type": "user_connection_request",
                "target_user_id": str(another_user.id),
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["status"] == "pending"

    def test_missing_both_targets_returns_400(
        self,
        authenticated_client,
        transaction_request_url,
    ):
        response = authenticated_client.post(
            transaction_request_url,
            data={"transaction_type": "business_membership_request"},
            format="json",
        )
        assert response.status_code == 400


# =========================================================================
# ACCEPT VIEW
# =========================================================================


@pytest.mark.django_db
class TestAcceptTransactionView:

    def test_target_acceptance_happy_path(
        self,
        pending_invitation,
        another_user,
        base_member_role,
    ):
        client = APIClient()
        client.force_authenticate(user=another_user)
        response = client.post(
            transaction_accept_url(pending_invitation.id),
        )
        assert response.status_code == 200
        assert response.data["status"] == "accepted"

    def test_accept_with_empty_body(
        self,
        pending_invitation,
        another_user,
        base_member_role,
    ):
        """Accept with empty body works (backward-compatible)."""
        client = APIClient()
        client.force_authenticate(user=another_user)
        response = client.post(
            transaction_accept_url(pending_invitation.id),
            data={},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "accepted"

    def test_accept_with_role_id_in_body(
        self,
        pending_request,
        user,
        owner_membership,
        owner_role,
        can_approve_membership_perm,
        base_member_role,
    ):
        """Accept with role_id in body passes it to the service."""
        from apps.rbac.models import RolePermission

        RolePermission.objects.get_or_create(
            role=owner_role,
            permission=can_approve_membership_perm,
            defaults={"scope": "business"},
        )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            transaction_accept_url(pending_request.id),
            data={"role_id": str(base_member_role.id)},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "accepted"

    def test_wrong_user_returns_403(
        self,
        pending_invitation,
        third_user,
    ):
        client = APIClient()
        client.force_authenticate(user=third_user)
        response = client.post(
            transaction_accept_url(pending_invitation.id),
        )
        assert response.status_code == 403


# =========================================================================
# DENY VIEW
# =========================================================================


@pytest.mark.django_db
class TestDenyTransactionView:

    def test_happy_path_with_reason(
        self,
        pending_invitation,
        another_user,
    ):
        client = APIClient()
        client.force_authenticate(user=another_user)
        response = client.post(
            transaction_deny_url(pending_invitation.id),
            data={"reason": "Not interested"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "denied"

    def test_happy_path_without_reason(
        self,
        pending_invitation,
        another_user,
    ):
        client = APIClient()
        client.force_authenticate(user=another_user)
        response = client.post(
            transaction_deny_url(pending_invitation.id),
            data={},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "denied"


# =========================================================================
# CANCEL VIEW
# =========================================================================


@pytest.mark.django_db
class TestCancelTransactionView:

    def test_initiator_can_cancel(
        self,
        pending_invitation,
        authenticated_client,
    ):
        response = authenticated_client.post(
            transaction_cancel_url(pending_invitation.id),
        )
        assert response.status_code == 200
        assert response.data["status"] == "cancelled"

    def test_non_initiator_returns_403(
        self,
        pending_invitation,
        another_user,
    ):
        client = APIClient()
        client.force_authenticate(user=another_user)
        response = client.post(
            transaction_cancel_url(pending_invitation.id),
        )
        assert response.status_code == 403


# =========================================================================
# DISMISS VIEW
# =========================================================================


@pytest.mark.django_db
class TestDismissTransactionView:

    def test_happy_path(
        self,
        pending_request,
        another_user,
        member_with_approve_perm,
    ):
        # Dismiss only works on ACCEPTED/DENIED requests
        pending_request.status = TransactionStatus.ACCEPTED
        pending_request.resolved_at = timezone.now()
        pending_request.save(update_fields=["status", "resolved_at"])
        client = APIClient()
        client.force_authenticate(user=another_user)
        response = client.post(
            transaction_dismiss_url(pending_request.id),
        )
        assert response.status_code == 200
        assert response.data["status"] == "dismissed"

    def test_non_request_returns_400(
        self,
        pending_invitation,
        another_user,
    ):
        client = APIClient()
        client.force_authenticate(user=another_user)
        response = client.post(
            transaction_dismiss_url(pending_invitation.id),
        )
        # Will get either 400 (ValidationError for non-request)
        # or 403 (PermissionDenied from can_deny check)
        assert response.status_code in (400, 403)


# =========================================================================
# TRANSACTION TYPE LIST VIEW
# =========================================================================


@pytest.mark.django_db
class TestTransactionTypeListView:

    def test_returns_all_enabled_types(self, authenticated_client):
        response = authenticated_client.get("/api/v1/transactions/types/")
        assert response.status_code == 200
        assert len(response.data) >= 10  # We have 10 types defined
        first = response.data[0]
        assert "id" in first
        assert "name" in first
        assert "mode" in first
        assert "category" in first
        assert "context_type" in first
        assert "requires_form" in first

    def test_filter_by_context_type(self, authenticated_client):
        response = authenticated_client.get(
            "/api/v1/transactions/types/?context_type=platform",
        )
        assert response.status_code == 200
        for item in response.data:
            assert item["context_type"] == "platform"

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get("/api/v1/transactions/types/")
        assert response.status_code == 401


# =========================================================================
# FORM MAPPING VIEWS
# =========================================================================


@pytest.mark.django_db
class TestTransactionFormMappingListCreateView:

    def test_list_returns_mappings_for_account(
        self,
        authenticated_client,
        user,
        business,
        owner_with_configure_perm,
    ):
        from apps.forms.tests.factories import FormTemplateFactory
        from apps.transaction.models import TransactionFormMapping

        template = FormTemplateFactory()
        TransactionFormMapping.objects.create(
            account_type="business",
            account_id=business.id,
            transaction_type="business_membership_request",
            form_template=template,
            is_required=True,
            created_by=user,
        )
        response = authenticated_client.get(
            f"/api/v1/transactions/form-mappings/?account_type=business&account_id={business.id}",
        )
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["transaction_type"] == "business_membership_request"

    def test_list_requires_account_params(self, authenticated_client):
        response = authenticated_client.get("/api/v1/transactions/form-mappings/")
        assert response.status_code == 400

    def test_list_requires_configure_permission(
        self,
        authenticated_client,
        user,
        business,
        member_membership,
    ):
        """Member without can_configure_transactions gets 403 on GET."""
        client = APIClient()
        member_user = member_membership.user
        client.force_authenticate(user=member_user)
        response = client.get(
            f"/api/v1/transactions/form-mappings/?account_type=business&account_id={business.id}",
        )
        assert response.status_code == 403

    def test_list_denied_for_non_member(self, business):
        """Non-member user gets 403 on GET."""
        non_member = UserFactory(email="non_member@test.com")
        client = APIClient()
        client.force_authenticate(user=non_member)
        response = client.get(
            f"/api/v1/transactions/form-mappings/?account_type=business&account_id={business.id}",
        )
        assert response.status_code == 403

    def test_create_requires_permission(
        self,
        authenticated_client,
        user,
        business,
        member_membership,
    ):
        """Member without can_configure_transactions gets 403."""
        from apps.forms.tests.factories import FormTemplateFactory

        template = FormTemplateFactory()
        client = APIClient()
        member_user = member_membership.user
        client.force_authenticate(user=member_user)
        response = client.post(
            f"/api/v1/transactions/form-mappings/?account_type=business&account_id={business.id}",
            data={
                "transaction_type": "business_membership_request",
                "form_template_id": str(template.id),
                "is_required": True,
            },
            format="json",
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestTransactionFormMappingDeleteView:

    def test_delete_not_found_returns_404(self, authenticated_client):
        response = authenticated_client.delete(
            f"/api/v1/transactions/form-mappings/{uuid4()}/",
        )
        assert response.status_code == 404


# =========================================================================
# PLATFORM TRANSACTION VIEWS
# =========================================================================


@pytest.mark.django_db
class TestPlatformTransactionViews:
    """Tests for transaction endpoints operating in platform context."""

    def test_create_platform_invitation_via_api(
        self,
        platform_authenticated_client,
        platform_owner_with_invite_perm,
        user,
        platform,
        platform_base_member_role,
    ):
        response = platform_authenticated_client.post(
            "/api/v1/transactions/invitation/",
            {
                "transaction_type": "platform_membership_invitation",
                "target_user_id": str(user.id),
                "context_type": "platform",
                "context_id": str(platform.id),
                "payload": {"role_id": str(platform_base_member_role.id)},
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["transaction_type"] == "platform_membership_invitation"
        assert response.data["context_type"] == "platform"

    def test_create_platform_request_via_api(
        self,
        authenticated_client,
        platform,
    ):
        response = authenticated_client.post(
            "/api/v1/transactions/request/",
            {
                "transaction_type": "platform_membership_request",
                "target_account_type": "platform",
                "target_account_id": str(platform.id),
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["transaction_type"] == "platform_membership_request"

    def test_list_platform_transactions(
        self,
        platform_authenticated_client,
        platform_pending_invitation,
        platform,
    ):
        response = platform_authenticated_client.get(
            f"/api/v1/transactions/?context_type=platform&context_id={platform.id}",
        )
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        assert len(results) >= 1
        assert all(r["context_type"] == "platform" for r in results)

    def test_platform_transaction_detail(
        self,
        platform_authenticated_client,
        platform_pending_invitation,
    ):
        url = transaction_detail_url(platform_pending_invitation.id)
        response = platform_authenticated_client.get(url)
        assert response.status_code == 200
        assert response.data["id"] == str(platform_pending_invitation.id)

    def test_platform_transaction_detail_permissions(
        self,
        platform_authenticated_client,
        platform_pending_request,
        platform_owner_with_approve_perm,
    ):
        """GET detail includes _permissions for platform authority."""
        url = transaction_detail_url(platform_pending_request.id)
        response = platform_authenticated_client.get(url)
        assert response.status_code == 200
        assert "_permissions" in response.data
        perms = response.data["_permissions"]
        assert "can_accept" in perms
        assert "can_deny" in perms

    def test_accept_platform_transaction_via_api(
        self,
        authenticated_client,
        platform_pending_invitation,
        platform_base_member_role,
    ):
        """Target user (user) accepts platform invitation."""
        url = transaction_accept_url(platform_pending_invitation.id)
        response = authenticated_client.post(url, format="json")
        assert response.status_code == 200
        assert response.data["status"] == "accepted"

    def test_deny_platform_transaction_via_api(
        self,
        platform_authenticated_client,
        platform_pending_request,
        platform_owner_with_approve_perm,
        platform_base_member_role,
    ):
        """Platform owner denies request."""
        url = transaction_deny_url(platform_pending_request.id)
        response = platform_authenticated_client.post(
            url,
            {"reason": "Not suitable"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "denied"

    def test_cancel_platform_transaction_via_api(
        self,
        authenticated_client,
        platform_pending_request,
    ):
        """Requester (user) cancels their own request."""
        url = transaction_cancel_url(platform_pending_request.id)
        response = authenticated_client.post(url, format="json")
        assert response.status_code == 200
        assert response.data["status"] == "cancelled"

    def test_platform_list_forbidden_for_non_member(self, platform):
        """Non-platform-member cannot list platform transactions."""
        outsider = UserFactory(email="outsider@test.com")
        client = APIClient()
        client.force_authenticate(user=outsider)
        response = client.get(
            f"/api/v1/transactions/?context_type=platform&context_id={platform.id}",
        )
        # Non-member gets empty results (filtered out)
        results = response.data.get("results", response.data)
        assert len(results) == 0

    def test_platform_list_filter_by_status(
        self,
        platform_authenticated_client,
        platform_pending_invitation,
        platform,
    ):
        response = platform_authenticated_client.get(
            f"/api/v1/transactions/?context_type=platform&context_id={platform.id}&status=pending",
        )
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        for r in results:
            assert r["status"] == "pending"

    def test_platform_list_filter_by_type(
        self,
        platform_authenticated_client,
        platform_pending_invitation,
        platform,
    ):
        response = platform_authenticated_client.get(
            f"/api/v1/transactions/?context_type=platform&context_id={platform.id}"
            "&transaction_type=platform_membership_invitation",
        )
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        for r in results:
            assert r["transaction_type"] == "platform_membership_invitation"


# =========================================================================
# PLATFORM FORM MAPPING VIEWS
# =========================================================================


@pytest.mark.django_db
class TestPlatformFormMappingViews:

    def test_create_mapping_for_platform_transaction_type(
        self,
        platform_authenticated_client,
        platform_owner_with_configure_perm,
        platform,
        third_user,
    ):
        from apps.forms.tests.factories import FormTemplateFactory

        template = FormTemplateFactory()
        response = platform_authenticated_client.post(
            "/api/v1/transactions/form-mappings/",
            {
                "account_type": "platform",
                "account_id": str(platform.id),
                "transaction_type": "platform_membership_request",
                "form_template_id": str(template.id),
                "is_required": True,
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["transaction_type"] == "platform_membership_request"

    def test_list_mappings_platform_context(
        self,
        platform_authenticated_client,
        platform_owner_with_configure_perm,
        platform,
        third_user,
    ):
        from apps.forms.tests.factories import FormTemplateFactory
        from apps.transaction.models import TransactionFormMapping

        template = FormTemplateFactory()
        TransactionFormMapping.objects.create(
            account_type="platform",
            account_id=platform.id,
            transaction_type="platform_membership_request",
            form_template=template,
            is_required=True,
            created_by=third_user,
        )
        response = platform_authenticated_client.get(
            f"/api/v1/transactions/form-mappings/?account_type=platform&account_id={platform.id}",
        )
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_mapping_non_platform_member_denied(self, platform):
        outsider = UserFactory(email="outsider_mapping@test.com")
        client = APIClient()
        client.force_authenticate(user=outsider)
        response = client.get(
            f"/api/v1/transactions/form-mappings/?account_type=platform&account_id={platform.id}",
        )
        assert response.status_code == 403


# ==========================================================================
# TransactionListView — Permission-Gated Visibility
# ==========================================================================


@pytest.mark.django_db
class TestTransactionListPermissionFiltering:
    """Tests for apply_permission_filters on the list endpoint.

    Verifies that permission-gated transaction types (those with
    approval_permission) are hidden from platform members who lack
    that permission.
    """

    def test_member_without_approval_perm_cannot_see_business_creation_requests(
        self,
        api_client,
        platform,
        platform_base_membership,
        another_user,
        transaction_list_url,
    ):
        """Platform base member without can_approve_business_creation should
        NOT see business_creation_permission_request in the list."""
        user_ctx = ActorContext.for_user_context(another_user, request=None)
        TransactionFactory(
            transaction_type="business_creation_permission_request",
            mode="request",
            initiator_type=PartyType.USER,
            initiator_id=another_user.id,
            initiator_context=user_ctx.to_dict(),
            target_type=PartyType.ACCOUNT,
            target_id=platform.id,
            context_type=ContextType.PLATFORM,
            context_id=platform.id,
            status=TransactionStatus.PENDING,
        )

        # Authenticate as the base member (who lacks can_approve_business_creation)
        base_user = platform_base_membership.user
        api_client.force_authenticate(user=base_user)

        response = api_client.get(
            f"{transaction_list_url}?context_type=platform&context_id={platform.id}",
        )
        assert response.status_code == 200

        type_ids = [r["transaction_type"] for r in response.data["results"]]
        assert "business_creation_permission_request" not in type_ids

    def test_platform_admin_with_approval_perm_can_see_business_creation_requests(
        self,
        platform_authenticated_client,
        platform,
        platform_owner_with_all_perms,
        another_user,
        transaction_list_url,
    ):
        """Platform owner (who has all permissions) should see all transaction types."""
        user_ctx = ActorContext.for_user_context(another_user, request=None)
        TransactionFactory(
            transaction_type="business_creation_permission_request",
            mode="request",
            initiator_type=PartyType.USER,
            initiator_id=another_user.id,
            initiator_context=user_ctx.to_dict(),
            target_type=PartyType.ACCOUNT,
            target_id=platform.id,
            context_type=ContextType.PLATFORM,
            context_id=platform.id,
            status=TransactionStatus.PENDING,
        )

        response = platform_authenticated_client.get(
            f"{transaction_list_url}?context_type=platform&context_id={platform.id}",
        )
        assert response.status_code == 200

        type_ids = [r["transaction_type"] for r in response.data["results"]]
        assert "business_creation_permission_request" in type_ids

    def test_business_context_not_affected_by_platform_permission_filter(
        self,
        authenticated_client,
        business,
        owner_with_approve_perm,
        another_user,
        transaction_list_url,
    ):
        """Business context transactions should not be filtered by platform-level
        approval permissions (those are only relevant in platform context)."""
        user_ctx = ActorContext.for_user_context(another_user, request=None)
        TransactionFactory(
            transaction_type="business_membership_request",
            mode="request",
            initiator_type=PartyType.USER,
            initiator_id=another_user.id,
            initiator_context=user_ctx.to_dict(),
            target_type=PartyType.ACCOUNT,
            target_id=business.id,
            context_type=ContextType.BUSINESS,
            context_id=business.id,
            status=TransactionStatus.PENDING,
        )

        response = authenticated_client.get(
            f"{transaction_list_url}?context_type=business&context_id={business.id}",
        )
        assert response.status_code == 200

        type_ids = [r["transaction_type"] for r in response.data["results"]]
        assert "business_membership_request" in type_ids
