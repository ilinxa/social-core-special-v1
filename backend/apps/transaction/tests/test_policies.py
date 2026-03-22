"""
Tests for TransactionPolicy
============================
Verifies all policy methods: can_create_invitation, can_accept, can_deny,
is_initiator, and can_view.

Uses pytest + @pytest.mark.django_db. Follows AAA (Arrange-Act-Assert) pattern.
"""

from uuid import uuid4

import pytest

from apps.core.constants import ContextType
from apps.core.exceptions import PermissionDenied, ValidationError
from apps.core.types import ActorContext
from apps.transaction.constants import (
    ApproverPolicy,
    PartyType,
    TransactionMode,
    TransactionStatus,
)
from apps.transaction.policies import TransactionPolicy
from apps.transaction.tests.factories import TransactionFactory
from apps.transaction.types import TransactionTypeConfig, get_transaction_type

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_actor(
    *,
    user_id=None,
    account_type="business",
    account_id=None,
    is_owner=False,
    permissions=None,
    role_name="Member",
    role_level=5,
):
    """Build an ActorContext without hitting the database."""
    return ActorContext(
        user_id=user_id or uuid4(),
        account_type=account_type,
        account_id=account_id or uuid4(),
        membership_id=uuid4(),
        role_id=uuid4(),
        role_name=role_name,
        role_level=role_level,
        is_owner=is_owner,
        permissions_snapshot=permissions or [],
    )


def _make_config(
    *,
    required_permissions=None,
    owner_only=False,
    approver_policy=ApproverPolicy.TARGET_ACCEPTANCE,
    approval_permission=None,
):
    """Build a minimal TransactionTypeConfig for unit tests."""
    return TransactionTypeConfig(
        id="test_type",
        name="Test Type",
        mode=TransactionMode.INVITATION,
        initiator_types=[PartyType.MEMBERSHIP_ACTOR],
        target_types=[PartyType.USER],
        context_type=ContextType.BUSINESS,
        approver_policy=approver_policy,
        required_permissions=required_permissions or [],
        approval_permission=approval_permission,
        owner_only=owner_only,
    )


# ===========================================================================
# can_create_invitation
# ===========================================================================


class TestCanCreateInvitation:
    """Tests for TransactionPolicy.can_create_invitation."""

    def test_allowed_when_actor_has_all_required_permissions(self):
        # Arrange
        actor = _make_actor(
            permissions=[("can_invite_member", "business")],
        )
        config = _make_config(required_permissions=["can_invite_member"])

        # Act / Assert — no exception means allowed
        TransactionPolicy.can_create_invitation(
            actor_context=actor,
            config=config,
        )

    def test_raises_when_missing_required_permission(self):
        # Arrange
        actor = _make_actor(permissions=[])
        config = _make_config(required_permissions=["can_invite_member"])

        # Act / Assert
        with pytest.raises(PermissionDenied, match="Missing required permission"):
            TransactionPolicy.can_create_invitation(
                actor_context=actor,
                config=config,
            )

    def test_allowed_when_no_required_permissions(self):
        # Arrange
        actor = _make_actor(permissions=[])
        config = _make_config(required_permissions=[])

        # Act / Assert — no exception
        TransactionPolicy.can_create_invitation(
            actor_context=actor,
            config=config,
        )

    def test_raises_for_owner_only_when_actor_is_not_owner(self):
        # Arrange
        actor = _make_actor(is_owner=False, permissions=[])
        config = _make_config(owner_only=True)

        # Act / Assert
        with pytest.raises(PermissionDenied, match="Only the account owner"):
            TransactionPolicy.can_create_invitation(
                actor_context=actor,
                config=config,
            )

    def test_allowed_for_owner_only_when_actor_is_owner(self):
        # Arrange
        actor = _make_actor(is_owner=True, permissions=[])
        config = _make_config(owner_only=True)

        # Act / Assert — no exception
        TransactionPolicy.can_create_invitation(
            actor_context=actor,
            config=config,
        )

    def test_multiple_required_permissions_all_present(self):
        # Arrange
        actor = _make_actor(
            permissions=[
                ("can_invite_member", "business"),
                ("can_manage_roles", "business"),
            ],
        )
        config = _make_config(
            required_permissions=["can_invite_member", "can_manage_roles"],
        )

        # Act / Assert — no exception
        TransactionPolicy.can_create_invitation(
            actor_context=actor,
            config=config,
        )

    def test_multiple_required_permissions_one_missing_raises(self):
        # Arrange
        actor = _make_actor(
            permissions=[("can_invite_member", "business")],
        )
        config = _make_config(
            required_permissions=["can_invite_member", "can_manage_roles"],
        )

        # Act / Assert
        with pytest.raises(PermissionDenied, match="can_manage_roles"):
            TransactionPolicy.can_create_invitation(
                actor_context=actor,
                config=config,
            )

    def test_owner_only_checked_after_permissions(self):
        """Even if permissions pass, owner_only still blocks non-owners."""
        # Arrange
        actor = _make_actor(
            is_owner=False,
            permissions=[("can_invite_member", "business")],
        )
        config = _make_config(
            required_permissions=["can_invite_member"],
            owner_only=True,
        )

        # Act / Assert
        with pytest.raises(PermissionDenied, match="Only the account owner"):
            TransactionPolicy.can_create_invitation(
                actor_context=actor,
                config=config,
            )


# ===========================================================================
# can_accept
# ===========================================================================


@pytest.mark.django_db
class TestCanAccept:
    """Tests for TransactionPolicy.can_accept across all ApproverPolicy types."""

    # -----------------------------------------------------------------------
    # TARGET_ACCEPTANCE policy (e.g. business_membership_invitation)
    # -----------------------------------------------------------------------

    def test_target_acceptance_target_user_can_accept_pending(self):
        """Target user can accept when status is PENDING."""
        # Arrange
        target_user_id = uuid4()
        config = get_transaction_type("business_membership_invitation")
        transaction = TransactionFactory(
            transaction_type="business_membership_invitation",
            target_type=PartyType.USER,
            target_id=target_user_id,
            status=TransactionStatus.PENDING,
        )
        actor = _make_actor(user_id=target_user_id)

        # Act / Assert — no exception
        TransactionPolicy.can_accept(
            transaction=transaction,
            actor_context=actor,
            config=config,
        )

    def test_target_acceptance_non_target_user_raises(self):
        """Non-target user cannot accept a TARGET_ACCEPTANCE transaction."""
        # Arrange
        config = get_transaction_type("business_membership_invitation")
        transaction = TransactionFactory(
            transaction_type="business_membership_invitation",
            target_type=PartyType.USER,
            target_id=uuid4(),
            status=TransactionStatus.PENDING,
        )
        actor = _make_actor(user_id=uuid4())  # different user

        # Act / Assert
        with pytest.raises(PermissionDenied, match="Only the target user"):
            TransactionPolicy.can_accept(
                transaction=transaction,
                actor_context=actor,
                config=config,
            )

    def test_target_acceptance_non_pending_raises_validation_error(self):
        """Cannot accept a transaction that is not PENDING."""
        # Arrange
        target_user_id = uuid4()
        config = get_transaction_type("business_membership_invitation")
        transaction = TransactionFactory(
            transaction_type="business_membership_invitation",
            target_type=PartyType.USER,
            target_id=target_user_id,
            status=TransactionStatus.ACCEPTED,
        )
        actor = _make_actor(user_id=target_user_id)

        # Act / Assert
        with pytest.raises(ValidationError, match="not pending"):
            TransactionPolicy.can_accept(
                transaction=transaction,
                actor_context=actor,
                config=config,
            )

    def test_target_acceptance_non_user_target_type_raises(self):
        """TARGET_ACCEPTANCE rejects when target_type is not USER."""
        # Arrange
        actor = _make_actor()
        config = _make_config(approver_policy=ApproverPolicy.TARGET_ACCEPTANCE)
        transaction = TransactionFactory(
            target_type=PartyType.ACCOUNT,
            target_id=uuid4(),
            status=TransactionStatus.PENDING,
        )

        # Act / Assert
        with pytest.raises(PermissionDenied, match="Invalid target type"):
            TransactionPolicy.can_accept(
                transaction=transaction,
                actor_context=actor,
                config=config,
            )

    # -----------------------------------------------------------------------
    # ACCOUNT_AUTHORITY policy (e.g. business_membership_request)
    # -----------------------------------------------------------------------

    def test_account_authority_member_with_approval_permission(self):
        """Account member with approval_permission can accept."""
        # Arrange
        account_id = uuid4()
        config = get_transaction_type("business_membership_request")
        transaction = TransactionFactory(
            transaction_type="business_membership_request",
            mode=TransactionMode.REQUEST,
            target_type=PartyType.ACCOUNT,
            target_id=account_id,
            context_type=ContextType.BUSINESS,
            context_id=account_id,
            status=TransactionStatus.PENDING,
        )
        actor = _make_actor(
            account_id=account_id,
            permissions=[("can_approve_membership_request", "business")],
        )

        # Act / Assert — no exception
        TransactionPolicy.can_accept(
            transaction=transaction,
            actor_context=actor,
            config=config,
        )

    def test_account_authority_member_without_approval_permission_raises(self):
        """Account member without approval_permission is rejected."""
        # Arrange
        account_id = uuid4()
        config = get_transaction_type("business_membership_request")
        transaction = TransactionFactory(
            transaction_type="business_membership_request",
            mode=TransactionMode.REQUEST,
            target_type=PartyType.ACCOUNT,
            target_id=account_id,
            context_type=ContextType.BUSINESS,
            context_id=account_id,
            status=TransactionStatus.PENDING,
        )
        actor = _make_actor(account_id=account_id, permissions=[])

        # Act / Assert
        with pytest.raises(PermissionDenied, match="Missing permission"):
            TransactionPolicy.can_accept(
                transaction=transaction,
                actor_context=actor,
                config=config,
            )

    def test_account_authority_non_member_raises(self):
        """Non-member of the account is rejected even with the right permission."""
        # Arrange
        config = get_transaction_type("business_membership_request")
        transaction = TransactionFactory(
            transaction_type="business_membership_request",
            mode=TransactionMode.REQUEST,
            target_type=PartyType.ACCOUNT,
            target_id=uuid4(),
            context_type=ContextType.BUSINESS,
            context_id=uuid4(),
            status=TransactionStatus.PENDING,
        )
        actor = _make_actor(
            account_id=uuid4(),  # different account
            permissions=[("can_approve_membership_request", "business")],
        )

        # Act / Assert
        with pytest.raises(PermissionDenied, match="Not a member"):
            TransactionPolicy.can_accept(
                transaction=transaction,
                actor_context=actor,
                config=config,
            )

    # -----------------------------------------------------------------------
    # PLATFORM_AUTHORITY policy (e.g. platform_membership_request)
    # -----------------------------------------------------------------------

    def test_platform_authority_platform_member_with_permission(self):
        """Platform member with approval_permission can accept."""
        # Arrange
        config = get_transaction_type("platform_membership_request")
        transaction = TransactionFactory(
            transaction_type="platform_membership_request",
            mode=TransactionMode.REQUEST,
            target_type=PartyType.ACCOUNT,
            target_id=uuid4(),
            context_type=ContextType.PLATFORM,
            context_id=uuid4(),
            status=TransactionStatus.PENDING,
        )
        actor = _make_actor(
            account_type="platform",
            permissions=[("can_approve_membership_request", "platform_only")],
        )

        # Act / Assert — no exception
        TransactionPolicy.can_accept(
            transaction=transaction,
            actor_context=actor,
            config=config,
        )

    def test_platform_authority_non_platform_account_type_raises(self):
        """Non-platform account_type is rejected by PLATFORM_AUTHORITY."""
        # Arrange
        config = get_transaction_type("platform_membership_request")
        transaction = TransactionFactory(
            transaction_type="platform_membership_request",
            mode=TransactionMode.REQUEST,
            target_type=PartyType.ACCOUNT,
            target_id=uuid4(),
            context_type=ContextType.PLATFORM,
            context_id=uuid4(),
            status=TransactionStatus.PENDING,
        )
        actor = _make_actor(
            account_type="business",
            permissions=[("can_approve_membership_request", "business")],
        )

        # Act / Assert
        with pytest.raises(PermissionDenied, match="Platform authority required"):
            TransactionPolicy.can_accept(
                transaction=transaction,
                actor_context=actor,
                config=config,
            )

    def test_platform_authority_platform_member_without_permission_raises(self):
        """Platform member without approval_permission is rejected."""
        # Arrange
        config = get_transaction_type("platform_membership_request")
        transaction = TransactionFactory(
            transaction_type="platform_membership_request",
            mode=TransactionMode.REQUEST,
            target_type=PartyType.ACCOUNT,
            target_id=uuid4(),
            context_type=ContextType.PLATFORM,
            context_id=uuid4(),
            status=TransactionStatus.PENDING,
        )
        actor = _make_actor(account_type="platform", permissions=[])

        # Act / Assert
        with pytest.raises(PermissionDenied, match="Missing permission"):
            TransactionPolicy.can_accept(
                transaction=transaction,
                actor_context=actor,
                config=config,
            )

    # -----------------------------------------------------------------------
    # AUTO_APPROVAL policy (e.g. business_follow_request)
    # -----------------------------------------------------------------------

    def test_auto_approval_always_raises_validation_error(self):
        """AUTO_APPROVAL transactions cannot be manually accepted."""
        # Arrange
        config = get_transaction_type("business_follow_request")
        transaction = TransactionFactory(
            transaction_type="business_follow_request",
            mode=TransactionMode.REQUEST,
            target_type=PartyType.ACCOUNT,
            target_id=uuid4(),
            context_type=ContextType.BUSINESS,
            context_id=uuid4(),
            status=TransactionStatus.PENDING,
        )
        actor = _make_actor(is_owner=True)

        # Act / Assert
        with pytest.raises(ValidationError, match="Auto-approval"):
            TransactionPolicy.can_accept(
                transaction=transaction,
                actor_context=actor,
                config=config,
            )

    # -----------------------------------------------------------------------
    # Status guard (applies to all policies)
    # -----------------------------------------------------------------------

    def test_cancelled_status_raises_validation_error(self):
        """Any non-PENDING status is rejected before policy evaluation."""
        # Arrange
        config = get_transaction_type("business_membership_invitation")
        transaction = TransactionFactory(
            status=TransactionStatus.CANCELLED,
        )
        actor = _make_actor()

        # Act / Assert
        with pytest.raises(ValidationError, match="not pending"):
            TransactionPolicy.can_accept(
                transaction=transaction,
                actor_context=actor,
                config=config,
            )

    def test_expired_status_raises_validation_error(self):
        """EXPIRED transactions cannot be accepted."""
        # Arrange
        config = get_transaction_type("business_membership_invitation")
        transaction = TransactionFactory(
            status=TransactionStatus.EXPIRED,
        )
        actor = _make_actor()

        # Act / Assert
        with pytest.raises(ValidationError, match="not pending"):
            TransactionPolicy.can_accept(
                transaction=transaction,
                actor_context=actor,
                config=config,
            )

    def test_denied_status_raises_validation_error(self):
        """DENIED transactions cannot be accepted."""
        # Arrange
        config = get_transaction_type("business_membership_invitation")
        transaction = TransactionFactory(
            status=TransactionStatus.DENIED,
        )
        actor = _make_actor()

        # Act / Assert
        with pytest.raises(ValidationError, match="not pending"):
            TransactionPolicy.can_accept(
                transaction=transaction,
                actor_context=actor,
                config=config,
            )


# ===========================================================================
# can_deny
# ===========================================================================


@pytest.mark.django_db
class TestCanDeny:
    """Tests for TransactionPolicy.can_deny — delegates to can_accept."""

    def test_valid_deny_does_not_raise(self):
        """Authorized actor can deny a PENDING transaction."""
        # Arrange
        target_user_id = uuid4()
        config = get_transaction_type("business_membership_invitation")
        transaction = TransactionFactory(
            transaction_type="business_membership_invitation",
            target_type=PartyType.USER,
            target_id=target_user_id,
            status=TransactionStatus.PENDING,
        )
        actor = _make_actor(user_id=target_user_id)

        # Act / Assert — no exception
        TransactionPolicy.can_deny(
            transaction=transaction,
            actor_context=actor,
            config=config,
        )

    def test_unauthorized_deny_raises_permission_denied(self):
        """Unauthorized actor cannot deny."""
        # Arrange
        config = get_transaction_type("business_membership_invitation")
        transaction = TransactionFactory(
            transaction_type="business_membership_invitation",
            target_type=PartyType.USER,
            target_id=uuid4(),
            status=TransactionStatus.PENDING,
        )
        actor = _make_actor(user_id=uuid4())  # not the target

        # Act / Assert
        with pytest.raises(PermissionDenied, match="Only the target user"):
            TransactionPolicy.can_deny(
                transaction=transaction,
                actor_context=actor,
                config=config,
            )

    def test_non_pending_deny_raises_validation_error(self):
        """Cannot deny a non-PENDING transaction."""
        # Arrange
        target_user_id = uuid4()
        config = get_transaction_type("business_membership_invitation")
        transaction = TransactionFactory(
            transaction_type="business_membership_invitation",
            target_type=PartyType.USER,
            target_id=target_user_id,
            status=TransactionStatus.ACCEPTED,
        )
        actor = _make_actor(user_id=target_user_id)

        # Act / Assert
        with pytest.raises(ValidationError, match="not pending"):
            TransactionPolicy.can_deny(
                transaction=transaction,
                actor_context=actor,
                config=config,
            )


# ===========================================================================
# is_initiator
# ===========================================================================


@pytest.mark.django_db
class TestIsInitiator:
    """Tests for TransactionPolicy.is_initiator."""

    def test_correct_initiator_passes(self):
        """No exception when actor is the initiator."""
        # Arrange
        user_id = uuid4()
        initiator_ctx = ActorContext(
            user_id=user_id,
            account_type="business",
            account_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Admin",
            role_level=1,
            is_owner=False,
            permissions_snapshot=[],
        )
        transaction = TransactionFactory(
            initiator_context=initiator_ctx.to_dict(),
        )
        actor = _make_actor(user_id=user_id)

        # Act / Assert — no exception
        TransactionPolicy.is_initiator(
            transaction=transaction,
            actor_context=actor,
        )

    def test_wrong_user_raises_permission_denied(self):
        """Different user cannot act as the initiator."""
        # Arrange
        initiator_ctx = ActorContext(
            user_id=uuid4(),
            account_type="business",
            account_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Admin",
            role_level=1,
            is_owner=False,
            permissions_snapshot=[],
        )
        transaction = TransactionFactory(
            initiator_context=initiator_ctx.to_dict(),
        )
        actor = _make_actor(user_id=uuid4())  # different user

        # Act / Assert
        with pytest.raises(PermissionDenied, match="Only the initiator"):
            TransactionPolicy.is_initiator(
                transaction=transaction,
                actor_context=actor,
            )

    def test_system_context_raises_permission_denied(self):
        """System context (user_id=None) cannot be the initiator."""
        # Arrange
        initiator_ctx = ActorContext(
            user_id=uuid4(),
            account_type="business",
            account_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Admin",
            role_level=1,
            is_owner=False,
            permissions_snapshot=[],
        )
        transaction = TransactionFactory(
            initiator_context=initiator_ctx.to_dict(),
        )
        system_actor = ActorContext.for_system()

        # Act / Assert
        with pytest.raises(PermissionDenied, match="Only the initiator"):
            TransactionPolicy.is_initiator(
                transaction=transaction,
                actor_context=system_actor,
            )

    def test_initiator_with_none_user_id_vs_real_user_raises(self):
        """Transaction initiated by system (user_id=None) rejects real user."""
        # Arrange
        system_ctx = ActorContext.for_system()
        transaction = TransactionFactory(
            initiator_context=system_ctx.to_dict(),
        )
        actor = _make_actor(user_id=uuid4())

        # Act / Assert
        with pytest.raises(PermissionDenied, match="Only the initiator"):
            TransactionPolicy.is_initiator(
                transaction=transaction,
                actor_context=actor,
            )


# ===========================================================================
# can_view
# ===========================================================================


@pytest.mark.django_db
class TestCanView:
    """Tests for TransactionPolicy.can_view."""

    def test_initiator_can_view_own_transaction(self):
        """The user who created the transaction can always view it."""
        # Arrange
        user_id = uuid4()
        initiator_ctx = ActorContext(
            user_id=user_id,
            account_type="business",
            account_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Admin",
            role_level=1,
            is_owner=False,
            permissions_snapshot=[],
        )
        transaction = TransactionFactory(
            initiator_context=initiator_ctx.to_dict(),
            target_type=PartyType.USER,
            target_id=uuid4(),
        )
        actor = _make_actor(user_id=user_id)

        # Act / Assert — no exception
        TransactionPolicy.can_view(
            transaction=transaction,
            actor_context=actor,
        )

    def test_target_user_can_view(self):
        """The target user of a transaction can view it."""
        # Arrange
        target_user_id = uuid4()
        initiator_ctx = ActorContext(
            user_id=uuid4(),
            account_type="business",
            account_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Admin",
            role_level=1,
            is_owner=False,
            permissions_snapshot=[],
        )
        transaction = TransactionFactory(
            initiator_context=initiator_ctx.to_dict(),
            target_type=PartyType.USER,
            target_id=target_user_id,
        )
        actor = _make_actor(user_id=target_user_id)

        # Act / Assert — no exception
        TransactionPolicy.can_view(
            transaction=transaction,
            actor_context=actor,
        )

    def test_account_owner_can_view(self):
        """Account owner can view transactions in their account context."""
        # Arrange
        account_id = uuid4()
        initiator_ctx = ActorContext(
            user_id=uuid4(),
            account_type="business",
            account_id=account_id,
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Member",
            role_level=5,
            is_owner=False,
            permissions_snapshot=[],
        )
        transaction = TransactionFactory(
            initiator_context=initiator_ctx.to_dict(),
            target_type=PartyType.USER,
            target_id=uuid4(),
            context_type=ContextType.BUSINESS,
            context_id=account_id,
        )
        actor = _make_actor(
            account_type="business",
            account_id=account_id,
            is_owner=True,
        )

        # Act / Assert — no exception
        TransactionPolicy.can_view(
            transaction=transaction,
            actor_context=actor,
        )

    def test_account_member_with_view_permission_can_view(self):
        """Account member with can_view_transactions permission can view."""
        # Arrange
        account_id = uuid4()
        initiator_ctx = ActorContext(
            user_id=uuid4(),
            account_type="business",
            account_id=account_id,
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Member",
            role_level=5,
            is_owner=False,
            permissions_snapshot=[],
        )
        transaction = TransactionFactory(
            initiator_context=initiator_ctx.to_dict(),
            target_type=PartyType.USER,
            target_id=uuid4(),
            context_type=ContextType.BUSINESS,
            context_id=account_id,
        )
        actor = _make_actor(
            account_type="business",
            account_id=account_id,
            is_owner=False,
            permissions=[("can_view_transactions", "business")],
        )

        # Act / Assert — no exception
        TransactionPolicy.can_view(
            transaction=transaction,
            actor_context=actor,
        )

    def test_platform_member_with_global_permission_can_view(self):
        """Platform member with global can_view_all_transactions can view any transaction."""
        # Arrange
        initiator_ctx = ActorContext(
            user_id=uuid4(),
            account_type="business",
            account_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Member",
            role_level=5,
            is_owner=False,
            permissions_snapshot=[],
        )
        transaction = TransactionFactory(
            initiator_context=initiator_ctx.to_dict(),
            target_type=PartyType.USER,
            target_id=uuid4(),
            context_type=ContextType.BUSINESS,
            context_id=uuid4(),
        )
        actor = _make_actor(
            account_type="platform",
            permissions=[
                ("can_view_all_transactions", "platform_and_global"),
            ],
        )

        # Act / Assert — no exception
        TransactionPolicy.can_view(
            transaction=transaction,
            actor_context=actor,
        )

    def test_platform_member_with_global_only_scope_can_view(self):
        """global_only scope also satisfies has_global_permission."""
        # Arrange
        initiator_ctx = ActorContext(
            user_id=uuid4(),
            account_type="business",
            account_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Member",
            role_level=5,
            is_owner=False,
            permissions_snapshot=[],
        )
        transaction = TransactionFactory(
            initiator_context=initiator_ctx.to_dict(),
            target_type=PartyType.USER,
            target_id=uuid4(),
            context_type=ContextType.BUSINESS,
            context_id=uuid4(),
        )
        actor = _make_actor(
            account_type="platform",
            permissions=[
                ("can_view_all_transactions", "global_only"),
            ],
        )

        # Act / Assert — no exception
        TransactionPolicy.can_view(
            transaction=transaction,
            actor_context=actor,
        )

    def test_unrelated_user_raises_permission_denied(self):
        """User with no relation to the transaction cannot view it."""
        # Arrange
        initiator_ctx = ActorContext(
            user_id=uuid4(),
            account_type="business",
            account_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Member",
            role_level=5,
            is_owner=False,
            permissions_snapshot=[],
        )
        transaction = TransactionFactory(
            initiator_context=initiator_ctx.to_dict(),
            target_type=PartyType.USER,
            target_id=uuid4(),
            context_type=ContextType.BUSINESS,
            context_id=uuid4(),
        )
        actor = _make_actor(
            account_type="business",
            account_id=uuid4(),  # different account
            is_owner=False,
            permissions=[],
        )

        # Act / Assert
        with pytest.raises(PermissionDenied, match="Not authorized to view"):
            TransactionPolicy.can_view(
                transaction=transaction,
                actor_context=actor,
            )

    def test_account_member_without_view_permission_raises(self):
        """Account member without can_view_transactions (and not owner) is rejected."""
        # Arrange
        account_id = uuid4()
        initiator_ctx = ActorContext(
            user_id=uuid4(),
            account_type="business",
            account_id=account_id,
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Member",
            role_level=5,
            is_owner=False,
            permissions_snapshot=[],
        )
        transaction = TransactionFactory(
            initiator_context=initiator_ctx.to_dict(),
            target_type=PartyType.USER,
            target_id=uuid4(),
            context_type=ContextType.BUSINESS,
            context_id=account_id,
        )
        actor = _make_actor(
            account_type="business",
            account_id=account_id,
            is_owner=False,
            permissions=[],  # no can_view_transactions
        )

        # Act / Assert
        with pytest.raises(PermissionDenied, match="Not authorized to view"):
            TransactionPolicy.can_view(
                transaction=transaction,
                actor_context=actor,
            )


# ===========================================================================
# get_viewer_permissions
# ===========================================================================


@pytest.mark.django_db
class TestGetViewerPermissions:

    def test_target_of_pending_invitation(self):
        """Target user can accept/deny but not cancel."""
        target_user_id = uuid4()
        initiator_ctx = _make_actor()
        actor = ActorContext(
            user_id=target_user_id,
            account_type=None,
            account_id=None,
            membership_id=None,
            role_id=None,
            role_name=None,
            role_level=None,
            is_owner=False,
            permissions_snapshot=[],
        )
        txn = TransactionFactory(
            transaction_type="business_membership_invitation",
            mode=TransactionMode.INVITATION,
            initiator_context=initiator_ctx.to_dict(),
            target_type=PartyType.USER,
            target_id=target_user_id,
            status=TransactionStatus.PENDING,
        )
        perms = TransactionPolicy.get_viewer_permissions(
            transaction=txn,
            actor_context=actor,
        )
        assert perms["can_accept"] is True
        assert perms["can_deny"] is True
        assert perms["can_cancel"] is False
        assert perms["can_view_form"] is False

    def test_initiator_of_pending_invitation(self):
        """Initiator can cancel but not accept."""
        user_id = uuid4()
        initiator_ctx = _make_actor(user_id=user_id)
        actor = ActorContext(
            user_id=user_id,
            account_type=None,
            account_id=None,
            membership_id=None,
            role_id=None,
            role_name=None,
            role_level=None,
            is_owner=False,
            permissions_snapshot=[],
        )
        txn = TransactionFactory(
            transaction_type="business_membership_invitation",
            mode=TransactionMode.INVITATION,
            initiator_context=initiator_ctx.to_dict(),
            target_type=PartyType.USER,
            target_id=uuid4(),
            status=TransactionStatus.PENDING,
        )
        perms = TransactionPolicy.get_viewer_permissions(
            transaction=txn,
            actor_context=actor,
        )
        assert perms["can_accept"] is False
        assert perms["can_cancel"] is True

    def test_accepted_transaction_no_actions(self):
        """No accept/deny/cancel available on accepted transactions."""
        target_user_id = uuid4()
        initiator_ctx = _make_actor()
        actor = ActorContext(
            user_id=target_user_id,
            account_type=None,
            account_id=None,
            membership_id=None,
            role_id=None,
            role_name=None,
            role_level=None,
            is_owner=False,
            permissions_snapshot=[],
        )
        txn = TransactionFactory(
            transaction_type="business_membership_invitation",
            initiator_context=initiator_ctx.to_dict(),
            target_type=PartyType.USER,
            target_id=target_user_id,
            status=TransactionStatus.ACCEPTED,
        )
        perms = TransactionPolicy.get_viewer_permissions(
            transaction=txn,
            actor_context=actor,
        )
        assert perms["can_accept"] is False
        assert perms["can_cancel"] is False
        assert perms["can_resubmit"] is False
