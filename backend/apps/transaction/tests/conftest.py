from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.constants import AccountType, ContextType
from apps.core.types import ActorContext
from apps.rbac.models import Permission, RolePermission
from apps.rbac.services import RBACService
from apps.rbac.tests.factories import (
    BaseMemberRoleFactory,
    BusinessAccountFactory,
    MembershipFactory,
    OwnerMembershipFactory,
    OwnerRoleFactory,
    PlatformAccountFactory,
    PlatformRoleFactory,
    RoleFactory,
)
from apps.transaction.constants import PartyType, TransactionMode, TransactionStatus
from apps.transaction.tests.factories import (
    PendingInvitationFactory,
    PendingRequestFactory,
    TransactionFactory,
)
from apps.users.tests.factories import UserFactory

# =========================================================================
# API Clients
# =========================================================================


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


# =========================================================================
# Users
# =========================================================================


@pytest.fixture
def user(db):
    return UserFactory(email="txn_user@test.com")


@pytest.fixture
def another_user(db):
    return UserFactory(email="txn_another@test.com")


@pytest.fixture
def third_user(db):
    return UserFactory(email="txn_third@test.com")


# =========================================================================
# Accounts + Roles + Memberships
# =========================================================================


@pytest.fixture
def business(db, user):
    return BusinessAccountFactory(created_by=user, open_member_request=True)


@pytest.fixture
def owner_role(db, business):
    return OwnerRoleFactory(
        account_type=AccountType.BUSINESS,
        account_id=business.id,
    )


@pytest.fixture
def base_member_role(db, business):
    return BaseMemberRoleFactory(
        account_type=AccountType.BUSINESS,
        account_id=business.id,
    )


@pytest.fixture
def owner_membership(db, user, business, owner_role):
    return MembershipFactory(
        user=user,
        account_type=AccountType.BUSINESS,
        account_id=business.id,
        role=owner_role,
        is_owner=True,
    )


@pytest.fixture
def member_membership(db, another_user, business, base_member_role):
    return MembershipFactory(
        user=another_user,
        account_type=AccountType.BUSINESS,
        account_id=business.id,
        role=base_member_role,
        is_owner=False,
    )


@pytest.fixture
def platform(db):
    p = PlatformAccountFactory()
    p.open_member_request = True
    p.save(update_fields=["open_member_request"])
    return p


@pytest.fixture
def platform_owner_role(db, platform):
    return OwnerRoleFactory(
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
    )


@pytest.fixture
def platform_membership(db, third_user, platform, platform_owner_role):
    return MembershipFactory(
        user=third_user,
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
        role=platform_owner_role,
        is_owner=True,
    )


# =========================================================================
# Permissions (add to roles)
# =========================================================================


@pytest.fixture
def can_invite_member_perm(db):
    perm, _ = Permission.objects.get_or_create(
        code="can_invite_member",
        defaults={
            "name": "Invite Member",
            "description": "Invite new members",
            "category": "membership",
            "applicable_scopes": ["business", "platform_only", "global_only"],
        },
    )
    return perm


@pytest.fixture
def can_approve_membership_perm(db):
    perm, _ = Permission.objects.get_or_create(
        code="can_approve_membership_request",
        defaults={
            "name": "Approve Membership Request",
            "description": "Approve membership requests",
            "category": "membership",
            "applicable_scopes": ["business", "platform_only"],
        },
    )
    return perm


@pytest.fixture
def can_view_transactions_perm(db):
    perm, _ = Permission.objects.get_or_create(
        code="can_view_transactions",
        defaults={
            "name": "View Transactions",
            "description": "View transactions within the account",
            "category": "transaction",
            "applicable_scopes": ["business", "platform_only"],
        },
    )
    return perm


@pytest.fixture
def can_view_all_transactions_perm(db):
    perm, _ = Permission.objects.get_or_create(
        code="can_view_all_transactions",
        defaults={
            "name": "View All Transactions",
            "description": "View transactions across all accounts",
            "category": "transaction",
            "applicable_scopes": ["global_only", "platform_and_global"],
        },
    )
    return perm


@pytest.fixture
def can_configure_transactions_perm(db):
    perm, _ = Permission.objects.get_or_create(
        code="can_configure_transactions",
        defaults={
            "name": "Configure Transactions",
            "description": "Configure transaction form mappings",
            "category": "transaction",
            "applicable_scopes": ["business", "platform_only"],
        },
    )
    return perm


@pytest.fixture
def can_approve_business_creation_perm(db):
    perm, _ = Permission.objects.get_or_create(
        code="can_approve_business_creation",
        defaults={
            "name": "Approve Business Creation",
            "description": "Approve business creation permission requests",
            "category": "membership",
            "applicable_scopes": ["platform_only"],
        },
    )
    return perm


@pytest.fixture
def owner_with_invite_perm(owner_membership, owner_role, can_invite_member_perm):
    RolePermission.objects.get_or_create(
        role=owner_role,
        permission=can_invite_member_perm,
        defaults={"scope": "business"},
    )
    return owner_membership


@pytest.fixture
def owner_with_configure_perm(
    owner_with_invite_perm,
    owner_role,
    can_configure_transactions_perm,
):
    RolePermission.objects.get_or_create(
        role=owner_role,
        permission=can_configure_transactions_perm,
        defaults={"scope": "business"},
    )
    return owner_with_invite_perm


@pytest.fixture
def owner_with_approve_perm(
    owner_membership, owner_role, can_approve_membership_perm
):
    RolePermission.objects.get_or_create(
        role=owner_role,
        permission=can_approve_membership_perm,
        defaults={"scope": "business"},
    )
    return owner_membership


@pytest.fixture
def member_with_approve_perm(
    member_membership, base_member_role, can_approve_membership_perm
):
    RolePermission.objects.get_or_create(
        role=base_member_role,
        permission=can_approve_membership_perm,
        defaults={"scope": "business"},
    )
    return member_membership


# =========================================================================
# Actor Contexts
# =========================================================================


@pytest.fixture
def owner_actor_context(owner_with_invite_perm):
    return RBACService.build_actor_context(
        membership=owner_with_invite_perm,
        request=None,
    )


@pytest.fixture
def member_actor_context(member_with_approve_perm):
    return RBACService.build_actor_context(
        membership=member_with_approve_perm,
        request=None,
    )


@pytest.fixture
def user_actor_context(user):
    return ActorContext.for_user_context(user, request=None)


@pytest.fixture
def platform_actor_context(platform_membership):
    return RBACService.build_actor_context(
        membership=platform_membership,
        request=None,
    )


# =========================================================================
# Platform permission assignment (mirrors business pattern)
# =========================================================================


@pytest.fixture
def platform_base_member_role(db, platform):
    return BaseMemberRoleFactory(
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
    )


@pytest.fixture
def platform_base_membership(db, another_user, platform, platform_base_member_role):
    return MembershipFactory(
        user=another_user,
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
        role=platform_base_member_role,
        is_owner=False,
    )


@pytest.fixture
def platform_owner_with_invite_perm(
    platform_membership,
    platform_owner_role,
    can_invite_member_perm,
):
    """Platform owner with can_invite_member permission assigned."""
    RolePermission.objects.get_or_create(
        role=platform_owner_role,
        permission=can_invite_member_perm,
        defaults={"scope": "platform_only"},
    )
    return platform_membership


@pytest.fixture
def platform_owner_with_approve_perm(
    platform_owner_with_invite_perm,
    platform_owner_role,
    can_approve_membership_perm,
):
    """Platform owner with can_invite + can_approve permissions."""
    RolePermission.objects.get_or_create(
        role=platform_owner_role,
        permission=can_approve_membership_perm,
        defaults={"scope": "platform_only"},
    )
    return platform_owner_with_invite_perm


@pytest.fixture
def platform_owner_with_configure_perm(
    platform_owner_with_invite_perm,
    platform_owner_role,
    can_configure_transactions_perm,
):
    """Platform owner with can_invite + can_configure_transactions."""
    RolePermission.objects.get_or_create(
        role=platform_owner_role,
        permission=can_configure_transactions_perm,
        defaults={"scope": "platform_only"},
    )
    return platform_owner_with_invite_perm


@pytest.fixture
def platform_owner_with_all_perms(
    platform_membership,
    platform_owner_role,
    can_invite_member_perm,
    can_approve_membership_perm,
    can_approve_business_creation_perm,
):
    """Platform owner with invite + approve membership + approve business creation."""
    for perm in [
        can_invite_member_perm,
        can_approve_membership_perm,
        can_approve_business_creation_perm,
    ]:
        RolePermission.objects.get_or_create(
            role=platform_owner_role,
            permission=perm,
            defaults={"scope": "platform_only"},
        )
    return platform_membership


@pytest.fixture
def platform_owner_actor_ctx(platform_owner_with_invite_perm):
    """ActorContext for platform owner WITH permissions."""
    return RBACService.build_actor_context(
        membership=platform_owner_with_invite_perm,
        request=None,
    )


@pytest.fixture
def platform_approver_actor_ctx(platform_owner_with_approve_perm):
    """ActorContext for platform owner with approve permission."""
    return RBACService.build_actor_context(
        membership=platform_owner_with_approve_perm,
        request=None,
    )


# =========================================================================
# Platform API clients
# =========================================================================


@pytest.fixture
def platform_authenticated_client(api_client, third_user):
    """Client authenticated as platform owner (third_user)."""
    api_client.force_authenticate(user=third_user)
    return api_client


# =========================================================================
# Transactions
# =========================================================================


@pytest.fixture
def pending_invitation(
    db, owner_with_invite_perm, another_user, business, owner_actor_context
):
    return TransactionFactory(
        transaction_type="business_membership_invitation",
        mode=TransactionMode.INVITATION,
        initiator_type=PartyType.MEMBERSHIP_ACTOR,
        initiator_id=owner_with_invite_perm.id,
        initiator_context=owner_actor_context.to_dict(),
        target_type=PartyType.USER,
        target_id=another_user.id,
        context_type=ContextType.BUSINESS,
        context_id=business.id,
        status=TransactionStatus.PENDING,
        payload={"role_id": str(uuid4())},
    )


@pytest.fixture
def pending_request(db, another_user, business):
    user_ctx = ActorContext.for_user_context(another_user, request=None)
    return TransactionFactory(
        transaction_type="business_membership_request",
        mode=TransactionMode.REQUEST,
        initiator_type=PartyType.USER,
        initiator_id=another_user.id,
        initiator_context=user_ctx.to_dict(),
        target_type=PartyType.ACCOUNT,
        target_id=business.id,
        context_type=ContextType.BUSINESS,
        context_id=business.id,
        status=TransactionStatus.PENDING,
    )


@pytest.fixture
def expired_transaction(db, user, another_user, business):
    return TransactionFactory(
        transaction_type="business_membership_invitation",
        initiator_id=uuid4(),
        target_id=another_user.id,
        context_type=ContextType.BUSINESS,
        context_id=business.id,
        status=TransactionStatus.PENDING,
        expires_at=timezone.now() - timedelta(days=1),
    )


@pytest.fixture
def accepted_transaction(db, user, another_user, business):
    return TransactionFactory(
        transaction_type="business_membership_invitation",
        initiator_id=uuid4(),
        target_id=another_user.id,
        context_type=ContextType.BUSINESS,
        context_id=business.id,
        status=TransactionStatus.ACCEPTED,
        resolved_at=timezone.now(),
    )


# =========================================================================
# URL Helpers
# =========================================================================


@pytest.fixture
def transaction_list_url():
    return "/api/v1/transactions/"


@pytest.fixture
def transaction_invitation_url():
    return "/api/v1/transactions/invitation/"


@pytest.fixture
def transaction_request_url():
    return "/api/v1/transactions/request/"


def transaction_detail_url(txn_id):
    return f"/api/v1/transactions/{txn_id}/"


def transaction_accept_url(txn_id):
    return f"/api/v1/transactions/{txn_id}/accept/"


def transaction_deny_url(txn_id):
    return f"/api/v1/transactions/{txn_id}/deny/"


def transaction_cancel_url(txn_id):
    return f"/api/v1/transactions/{txn_id}/cancel/"


def transaction_dismiss_url(txn_id):
    return f"/api/v1/transactions/{txn_id}/dismiss/"


def transaction_approve_url(txn_id):
    return f"/api/v1/transactions/{txn_id}/approve/"


# =========================================================================
# Platform Transactions
# =========================================================================


@pytest.fixture
def platform_pending_invitation(
    db,
    platform_owner_with_invite_perm,
    platform_base_member_role,
    user,
    platform,
    platform_owner_actor_ctx,
):
    """Platform membership invitation: platform owner (third_user) invites user."""
    return TransactionFactory(
        transaction_type="platform_membership_invitation",
        mode=TransactionMode.INVITATION,
        initiator_type=PartyType.MEMBERSHIP_ACTOR,
        initiator_id=platform_owner_with_invite_perm.id,
        initiator_context=platform_owner_actor_ctx.to_dict(),
        target_type=PartyType.USER,
        target_id=user.id,
        context_type=ContextType.PLATFORM,
        context_id=platform.id,
        status=TransactionStatus.PENDING,
        payload={"role_id": str(platform_base_member_role.id)},
    )


@pytest.fixture
def platform_pending_request(db, user, platform):
    """Platform membership request: user requests to join platform."""
    user_ctx = ActorContext.for_user_context(user, request=None)
    return TransactionFactory(
        transaction_type="platform_membership_request",
        mode=TransactionMode.REQUEST,
        initiator_type=PartyType.USER,
        initiator_id=user.id,
        initiator_context=user_ctx.to_dict(),
        target_type=PartyType.ACCOUNT,
        target_id=platform.id,
        context_type=ContextType.PLATFORM,
        context_id=platform.id,
        status=TransactionStatus.PENDING,
    )
