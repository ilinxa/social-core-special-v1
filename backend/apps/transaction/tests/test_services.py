import pytest
from uuid import uuid4
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.utils import timezone

from apps.core.exceptions import NotFound, ConflictError, ValidationError, PermissionDenied, BusinessRuleViolation
from apps.core.types import ActorContext
from apps.core.constants import ContextType, AccountType
from apps.transaction.services import TransactionService
from apps.transaction.models import Transaction, TransactionLog
from apps.transaction.constants import (
    TransactionMode, TransactionStatus, PartyType, ApproverPolicy,
)
from apps.transaction.tests.factories import TransactionFactory, TransactionLogFactory
from apps.users.tests.factories import UserFactory


# =========================================================================
# CREATE INVITATION
# =========================================================================

@pytest.mark.django_db
class TestCreateInvitation:

    def test_happy_path_creates_pending_transaction(
        self, owner_actor_context, another_user, business, base_member_role,
    ):
        txn = TransactionService.create_invitation(
            transaction_type="business_membership_invitation",
            initiator_context=owner_actor_context,
            target_user_id=another_user.id,
            payload={"role_id": str(base_member_role.id), "message": "Welcome!"},
        )

        assert txn.status == TransactionStatus.PENDING
        assert txn.mode == TransactionMode.INVITATION
        assert txn.target_id == another_user.id
        assert txn.context_type == ContextType.BUSINESS
        assert txn.context_id == business.id
        assert txn.expires_at is not None
        assert txn.logs.count() >= 2  # created + state_changed

    def test_wrong_mode_type_raises_validation_error(
        self, owner_actor_context, another_user,
    ):
        with pytest.raises(ValidationError, match="not an invitation type"):
            TransactionService.create_invitation(
                transaction_type="business_membership_request",
                initiator_context=owner_actor_context,
                target_user_id=another_user.id,
            )

    def test_missing_permission_raises_permission_denied(
        self, another_user, business, member_membership,
    ):
        from apps.rbac.services import RBACService
        ctx = RBACService.build_actor_context(
            membership=member_membership, request=None,
        )
        with pytest.raises(PermissionDenied, match="Missing required permission"):
            TransactionService.create_invitation(
                transaction_type="business_membership_invitation",
                initiator_context=ctx,
                target_user_id=another_user.id,
            )

    def test_duplicate_active_raises_conflict_error(
        self, owner_actor_context, another_user, base_member_role,
    ):
        TransactionService.create_invitation(
            transaction_type="business_membership_invitation",
            initiator_context=owner_actor_context,
            target_user_id=another_user.id,
            payload={"role_id": str(base_member_role.id)},
        )
        with pytest.raises(ConflictError, match="already exists"):
            TransactionService.create_invitation(
                transaction_type="business_membership_invitation",
                initiator_context=owner_actor_context,
                target_user_id=another_user.id,
                payload={"role_id": str(base_member_role.id)},
            )

    def test_existing_member_raises_conflict_error(
        self, owner_actor_context, another_user, member_membership, base_member_role,
    ):
        """Inviting an already-active member raises ConflictError."""
        with pytest.raises(ConflictError, match="already an active member"):
            TransactionService.create_invitation(
                transaction_type="business_membership_invitation",
                initiator_context=owner_actor_context,
                target_user_id=another_user.id,
                payload={"role_id": str(base_member_role.id)},
            )

    def test_invitation_blocked_by_existing_request(
        self, owner_actor_context, another_user, business, base_member_role,
    ):
        """Creating invitation when user already has a pending request raises ConflictError."""
        TransactionService.create_request(
            transaction_type="business_membership_request",
            user_id=another_user.id,
            target_account_id=business.id,
        )
        with pytest.raises(ConflictError, match="cross_type_duplicate"):
            TransactionService.create_invitation(
                transaction_type="business_membership_invitation",
                initiator_context=owner_actor_context,
                target_user_id=another_user.id,
                payload={"role_id": str(base_member_role.id)},
            )

    def test_invitation_succeeds_after_request_cancelled(
        self, owner_actor_context, another_user, business, base_member_role,
        user_actor_context,
    ):
        """Invitation succeeds after conflicting request is cancelled."""
        txn = TransactionService.create_request(
            transaction_type="business_membership_request",
            user_id=another_user.id,
            target_account_id=business.id,
        )
        # Build a simple actor context for the requesting user
        from apps.core.types import ActorContext
        cancel_ctx = ActorContext.for_user_context(another_user, request=None)
        TransactionService.cancel(
            transaction_id=txn.id, actor_context=cancel_ctx,
        )
        result = TransactionService.create_invitation(
            transaction_type="business_membership_invitation",
            initiator_context=owner_actor_context,
            target_user_id=another_user.id,
            payload={"role_id": str(base_member_role.id)},
        )
        assert result.status == TransactionStatus.PENDING

    def test_invalid_payload_raises_validation_error(
        self, owner_actor_context, another_user,
    ):
        with pytest.raises(ValidationError, match="role_id"):
            TransactionService.create_invitation(
                transaction_type="business_membership_invitation",
                initiator_context=owner_actor_context,
                target_user_id=another_user.id,
                payload={},  # role_id is required for business_membership_invitation
            )

    def test_owner_only_non_owner_raises_permission_denied(
        self, another_user, business, member_membership, base_member_role,
    ):
        from apps.rbac.services import RBACService
        ctx = RBACService.build_actor_context(
            membership=member_membership, request=None,
        )
        with pytest.raises(PermissionDenied):
            TransactionService.create_invitation(
                transaction_type="business_ownership_transfer",
                initiator_context=ctx,
                target_user_id=another_user.id,
            )

    def test_sets_expires_at_from_config(
        self, owner_actor_context, another_user, base_member_role,
    ):
        before = timezone.now()
        txn = TransactionService.create_invitation(
            transaction_type="business_membership_invitation",
            initiator_context=owner_actor_context,
            target_user_id=another_user.id,
            payload={"role_id": str(base_member_role.id)},
        )
        # business_membership_invitation has expiration_days=7
        expected_min = before + timedelta(days=6, hours=23)
        expected_max = before + timedelta(days=7, minutes=1)
        assert expected_min <= txn.expires_at <= expected_max

    def test_stores_initiator_context_snapshot(
        self, owner_actor_context, another_user, base_member_role,
    ):
        txn = TransactionService.create_invitation(
            transaction_type="business_membership_invitation",
            initiator_context=owner_actor_context,
            target_user_id=another_user.id,
            payload={"role_id": str(base_member_role.id)},
        )
        ctx = ActorContext.from_dict(txn.initiator_context)
        assert ctx.user_id == owner_actor_context.user_id

    def test_role_level_validation_rejects_equal_level_role(
        self, another_user, business, base_member_role, member_membership,
    ):
        """Cannot assign a role with level equal to actor's level."""
        from apps.rbac.services import RBACService
        from apps.rbac.tests.factories import RoleFactory
        from apps.rbac.models import Permission, RolePermission
        # Give member invite permission
        perm, _ = Permission.objects.get_or_create(
            code="can_invite_member",
            defaults={"name": "Invite", "description": "Invite", "category": "membership",
                      "applicable_scopes": ["business"]},
        )
        RolePermission.objects.get_or_create(
            role=base_member_role, permission=perm, defaults={"scope": "business"},
        )
        ctx = RBACService.build_actor_context(membership=member_membership, request=None)
        # Create a role at same level (10) as the member
        same_level_role = RoleFactory(
            account_type=AccountType.BUSINESS, account_id=business.id, level=10,
        )
        with pytest.raises(BusinessRuleViolation, match="equal or higher authority"):
            TransactionService.create_invitation(
                transaction_type="business_membership_invitation",
                initiator_context=ctx,
                target_user_id=UserFactory().id,
                payload={"role_id": str(same_level_role.id)},
            )

    def test_role_level_validation_rejects_owner_role(
        self, owner_actor_context, another_user, business, owner_role,
    ):
        """Owner role (level 0) can never be assigned via invitation."""
        with pytest.raises(BusinessRuleViolation, match="Owner role cannot be assigned"):
            TransactionService.create_invitation(
                transaction_type="business_membership_invitation",
                initiator_context=owner_actor_context,
                target_user_id=another_user.id,
                payload={"role_id": str(owner_role.id)},
            )

    def test_role_level_validation_accepts_lower_role(
        self, owner_actor_context, another_user, business, base_member_role,
    ):
        """Owner (level 0) can assign Base Member (level 10)."""
        txn = TransactionService.create_invitation(
            transaction_type="business_membership_invitation",
            initiator_context=owner_actor_context,
            target_user_id=another_user.id,
            payload={"role_id": str(base_member_role.id)},
        )
        assert txn.status == TransactionStatus.PENDING


# =========================================================================
# CREATE REQUEST
# =========================================================================

@pytest.mark.django_db
class TestCreateRequest:

    def test_happy_path_account_targeted(self, another_user, business):
        txn = TransactionService.create_request(
            transaction_type="business_membership_request",
            user_id=another_user.id,
            target_account_id=business.id,
        )

        assert txn.status == TransactionStatus.PENDING
        assert txn.mode == TransactionMode.REQUEST
        assert txn.initiator_id == another_user.id
        assert txn.target_type == PartyType.ACCOUNT
        assert txn.target_id == business.id
        assert txn.context_type == ContextType.BUSINESS

    def test_happy_path_user_targeted_connection(self, user, another_user):
        txn = TransactionService.create_request(
            transaction_type="user_connection_request",
            user_id=user.id,
            target_user_id=another_user.id,
        )

        assert txn.status == TransactionStatus.PENDING
        assert txn.target_type == PartyType.USER
        assert txn.target_id == another_user.id
        assert txn.context_type == ContextType.USER
        assert txn.context_id is None

    def test_wrong_mode_type_raises_validation_error(self, user, business):
        with pytest.raises(ValidationError, match="not a request type"):
            TransactionService.create_request(
                transaction_type="business_membership_invitation",
                user_id=user.id,
                target_account_id=business.id,
            )

    def test_user_not_found_raises_not_found(self, business):
        with pytest.raises(NotFound):
            TransactionService.create_request(
                transaction_type="business_membership_request",
                user_id=uuid4(),
                target_account_id=business.id,
            )

    def test_duplicate_active_raises_conflict_error(self, another_user, business):
        TransactionService.create_request(
            transaction_type="business_membership_request",
            user_id=another_user.id,
            target_account_id=business.id,
        )
        with pytest.raises(ConflictError, match="already have an active"):
            TransactionService.create_request(
                transaction_type="business_membership_request",
                user_id=another_user.id,
                target_account_id=business.id,
            )

    def test_request_blocked_by_existing_invitation(
        self, owner_actor_context, another_user, business, base_member_role,
    ):
        """Creating request when user already has a pending invitation raises ConflictError."""
        TransactionService.create_invitation(
            transaction_type="business_membership_invitation",
            initiator_context=owner_actor_context,
            target_user_id=another_user.id,
            payload={"role_id": str(base_member_role.id)},
        )
        with pytest.raises(ConflictError, match="cross_type_duplicate"):
            TransactionService.create_request(
                transaction_type="business_membership_request",
                user_id=another_user.id,
                target_account_id=business.id,
            )

    def test_no_cross_check_for_different_businesses(
        self, owner_actor_context, another_user, business,
    ):
        """Cross-type check does not flag transactions for different businesses."""
        from apps.organization.tests.factories import BusinessAccountFactory
        other_business = BusinessAccountFactory(open_member_request=True)
        # Request to a different business
        TransactionService.create_request(
            transaction_type="business_membership_request",
            user_id=another_user.id,
            target_account_id=other_business.id,
        )
        # Request to original business should succeed
        txn = TransactionService.create_request(
            transaction_type="business_membership_request",
            user_id=another_user.id,
            target_account_id=business.id,
        )
        assert txn.status == TransactionStatus.PENDING

    def test_missing_target_for_user_request_raises(self, user):
        with pytest.raises(ValidationError, match="target_user_id"):
            TransactionService.create_request(
                transaction_type="user_connection_request",
                user_id=user.id,
            )

    def test_missing_target_for_account_request_raises(self, user):
        with pytest.raises(ValidationError, match="target_account_id"):
            TransactionService.create_request(
                transaction_type="business_membership_request",
                user_id=user.id,
            )

    def test_auto_approval_auto_accepts(self, another_user, business):
        txn = TransactionService.create_request(
            transaction_type="business_follow_request",
            user_id=another_user.id,
            target_account_id=business.id,
        )

        assert txn.status == TransactionStatus.ACCEPTED
        assert txn.outcome_executed is True
        assert txn.outcome_executed_at is not None

    def test_cooldown_active_raises_validation_error(self, another_user, business):
        # Create a denied transaction with recent resolved_at
        TransactionFactory(
            transaction_type="business_membership_request",
            mode=TransactionMode.REQUEST,
            initiator_type=PartyType.USER,
            initiator_id=another_user.id,
            target_type=PartyType.ACCOUNT,
            target_id=business.id,
            context_type=ContextType.BUSINESS,
            context_id=business.id,
            status=TransactionStatus.DENIED,
            resolved_at=timezone.now() - timedelta(days=1),
        )
        # business_membership_request has resubmission_cooldown_days=7
        with pytest.raises(ValidationError, match="Cannot resubmit"):
            TransactionService.create_request(
                transaction_type="business_membership_request",
                user_id=another_user.id,
                target_account_id=business.id,
            )


# =========================================================================
# ACCEPT
# =========================================================================

@pytest.mark.django_db
class TestAccept:

    def test_happy_path_target_acceptance(
        self, pending_invitation, another_user, base_member_role,
    ):
        target_ctx = ActorContext.for_user_context(another_user, request=None)
        result = TransactionService.accept(
            transaction_id=pending_invitation.id,
            actor_context=target_ctx,
        )
        assert result.status == TransactionStatus.ACCEPTED
        assert result.resolved_at is not None

    def test_not_pending_raises_validation_error(self, accepted_transaction, user):
        ctx = ActorContext.for_user_context(user, request=None)
        with pytest.raises((ValidationError, PermissionDenied)):
            TransactionService.accept(
                transaction_id=accepted_transaction.id,
                actor_context=ctx,
            )

    def test_wrong_actor_raises_permission_denied(
        self, pending_invitation, third_user,
    ):
        wrong_ctx = ActorContext.for_user_context(third_user, request=None)
        with pytest.raises(PermissionDenied):
            TransactionService.accept(
                transaction_id=pending_invitation.id,
                actor_context=wrong_ctx,
            )

    def test_accept_creates_log_entries(
        self, pending_invitation, another_user, base_member_role,
    ):
        target_ctx = ActorContext.for_user_context(another_user, request=None)
        result = TransactionService.accept(
            transaction_id=pending_invitation.id,
            actor_context=target_ctx,
        )
        logs = TransactionLog.objects.filter(
            transaction=result, new_status=TransactionStatus.ACCEPTED,
        )
        assert logs.exists()

    def test_accept_with_acceptance_payload_role_id(
        self, base_member_role, business, user,
        owner_membership, owner_role, can_approve_membership_perm,
    ):
        """Approving a request with acceptance_payload role_id succeeds."""
        from apps.rbac.services import RBACService
        from apps.rbac.models import RolePermission
        RolePermission.objects.get_or_create(
            role=owner_role, permission=can_approve_membership_perm,
            defaults={"scope": "business"},
        )
        approver_ctx = RBACService.build_actor_context(
            membership=owner_membership, request=None,
        )
        requester = UserFactory()
        req_ctx = ActorContext.for_user_context(requester, request=None)
        pending = TransactionFactory(
            transaction_type="business_membership_request",
            mode=TransactionMode.REQUEST,
            initiator_type=PartyType.USER,
            initiator_id=requester.id,
            initiator_context=req_ctx.to_dict(),
            target_type=PartyType.ACCOUNT,
            target_id=business.id,
            context_type=ContextType.BUSINESS,
            context_id=business.id,
            status=TransactionStatus.PENDING,
        )
        result = TransactionService.accept(
            transaction_id=pending.id,
            actor_context=approver_ctx,
            acceptance_payload={"role_id": str(base_member_role.id)},
        )
        assert result.status == TransactionStatus.ACCEPTED

    def test_accept_rejects_owner_role_in_acceptance_payload(
        self, base_member_role, business, user,
        owner_membership, owner_role, can_approve_membership_perm,
    ):
        """Cannot assign owner role via acceptance_payload."""
        from apps.rbac.services import RBACService
        from apps.rbac.models import RolePermission
        RolePermission.objects.get_or_create(
            role=owner_role, permission=can_approve_membership_perm,
            defaults={"scope": "business"},
        )
        approver_ctx = RBACService.build_actor_context(
            membership=owner_membership, request=None,
        )
        requester = UserFactory()
        req_ctx = ActorContext.for_user_context(requester, request=None)
        pending = TransactionFactory(
            transaction_type="business_membership_request",
            mode=TransactionMode.REQUEST,
            initiator_type=PartyType.USER,
            initiator_id=requester.id,
            initiator_context=req_ctx.to_dict(),
            target_type=PartyType.ACCOUNT,
            target_id=business.id,
            context_type=ContextType.BUSINESS,
            context_id=business.id,
            status=TransactionStatus.PENDING,
        )
        with pytest.raises(BusinessRuleViolation, match="Owner role cannot be assigned"):
            TransactionService.accept(
                transaction_id=pending.id,
                actor_context=approver_ctx,
                acceptance_payload={"role_id": str(owner_role.id)},
            )


# =========================================================================
# DENY
# =========================================================================

@pytest.mark.django_db
class TestDeny:

    def test_happy_path(self, pending_invitation, another_user):
        target_ctx = ActorContext.for_user_context(another_user, request=None)
        result = TransactionService.deny(
            transaction_id=pending_invitation.id,
            actor_context=target_ctx,
            reason="Not interested",
        )
        assert result.status == TransactionStatus.DENIED
        assert result.resolution_reason == "Not interested"
        assert result.resolved_at is not None

    def test_not_pending_raises(self, accepted_transaction, user):
        ctx = ActorContext.for_user_context(user, request=None)
        with pytest.raises((ValidationError, PermissionDenied)):
            TransactionService.deny(
                transaction_id=accepted_transaction.id,
                actor_context=ctx,
            )

    def test_wrong_actor_raises_permission_denied(
        self, pending_invitation, third_user,
    ):
        wrong_ctx = ActorContext.for_user_context(third_user, request=None)
        with pytest.raises(PermissionDenied):
            TransactionService.deny(
                transaction_id=pending_invitation.id,
                actor_context=wrong_ctx,
            )


# =========================================================================
# DISMISS
# =========================================================================

@pytest.mark.django_db
class TestDismiss:

    def test_happy_path(self, pending_request, member_actor_context):
        # Dismiss only works on ACCEPTED/DENIED requests
        pending_request.status = TransactionStatus.ACCEPTED
        pending_request.resolved_at = timezone.now()
        pending_request.save(update_fields=["status", "resolved_at"])
        result = TransactionService.dismiss(
            transaction_id=pending_request.id,
            actor_context=member_actor_context,
        )
        assert result.status == TransactionStatus.DISMISSED

    def test_pending_request_raises(self, pending_request, member_actor_context):
        with pytest.raises(ValidationError, match="Cannot dismiss"):
            TransactionService.dismiss(
                transaction_id=pending_request.id,
                actor_context=member_actor_context,
            )

    def test_non_request_raises(self, pending_invitation, another_user):
        target_ctx = ActorContext.for_user_context(another_user, request=None)
        with pytest.raises(ValidationError, match="Only requests"):
            TransactionService.dismiss(
                transaction_id=pending_invitation.id,
                actor_context=target_ctx,
            )


# =========================================================================
# CANCEL
# =========================================================================

@pytest.mark.django_db
class TestCancel:

    def test_happy_path(self, pending_invitation, owner_actor_context):
        result = TransactionService.cancel(
            transaction_id=pending_invitation.id,
            actor_context=owner_actor_context,
        )
        assert result.status == TransactionStatus.CANCELLED
        assert result.resolved_at is not None

    def test_not_pending_raises(self, user):
        txn = TransactionFactory(
            status=TransactionStatus.ACCEPTED,
            resolved_at=timezone.now(),
            initiator_context=ActorContext.for_user_context(user).to_dict(),
        )
        ctx = ActorContext.for_user_context(user, request=None)
        with pytest.raises((ValidationError, PermissionDenied)):
            TransactionService.cancel(
                transaction_id=txn.id, actor_context=ctx,
            )

    def test_non_initiator_raises_permission_denied(
        self, pending_invitation, another_user,
    ):
        wrong_ctx = ActorContext.for_user_context(another_user, request=None)
        with pytest.raises(PermissionDenied, match="initiator"):
            TransactionService.cancel(
                transaction_id=pending_invitation.id,
                actor_context=wrong_ctx,
            )


# =========================================================================
# EXPIRE
# =========================================================================

@pytest.mark.django_db
class TestExpire:

    def test_happy_path(self, expired_transaction):
        result = TransactionService.expire(
            transaction_id=expired_transaction.id,
        )
        assert result.status == TransactionStatus.EXPIRED

    def test_already_terminal_returns_unchanged(self, accepted_transaction):
        result = TransactionService.expire(
            transaction_id=accepted_transaction.id,
        )
        assert result.status == TransactionStatus.ACCEPTED


# =========================================================================
# INVALIDATE
# =========================================================================

@pytest.mark.django_db
class TestInvalidate:

    def test_happy_path(self):
        txn = TransactionFactory(status=TransactionStatus.PENDING)
        result = TransactionService.invalidate(
            transaction_id=txn.id,
            reason="Creator lost permission",
        )
        assert result.status == TransactionStatus.INVALIDATED
        assert result.resolution_reason == "Creator lost permission"

    def test_already_terminal_returns_unchanged(self):
        txn = TransactionFactory(
            status=TransactionStatus.ACCEPTED,
            resolved_at=timezone.now(),
        )
        result = TransactionService.invalidate(
            transaction_id=txn.id, reason="test",
        )
        assert result.status == TransactionStatus.ACCEPTED


# =========================================================================
# PRIVATE: _transition
# =========================================================================

@pytest.mark.django_db
class TestTransition:

    def test_invalid_transition_raises(self):
        txn = TransactionFactory(status=TransactionStatus.CREATED)
        ctx = ActorContext.for_system()
        with pytest.raises(ValidationError, match="Invalid transition"):
            TransactionService._transition(
                transaction=txn,
                new_status=TransactionStatus.ACCEPTED,
                actor_context=ctx,
            )

    def test_terminal_state_sets_resolved_at(self):
        txn = TransactionFactory(status=TransactionStatus.PENDING)
        ctx = ActorContext.for_system()
        result = TransactionService._transition(
            transaction=txn,
            new_status=TransactionStatus.DENIED,
            actor_context=ctx,
        )
        assert result.resolved_at is not None

    def test_creates_log_entry(self):
        txn = TransactionFactory(status=TransactionStatus.CREATED)
        ctx = ActorContext.for_system()
        TransactionService._transition(
            transaction=txn,
            new_status=TransactionStatus.PENDING,
            actor_context=ctx,
        )
        log = TransactionLog.objects.filter(
            transaction=txn, new_status=TransactionStatus.PENDING,
        ).first()
        assert log is not None
        assert log.previous_status == TransactionStatus.CREATED


# =========================================================================
# PRIVATE: _validate_payload
# =========================================================================

@pytest.mark.django_db
class TestValidatePayload:

    def test_required_field_missing_raises(self):
        from apps.transaction.types import get_transaction_type
        config = get_transaction_type("business_membership_invitation")
        with pytest.raises(ValidationError, match="role_id"):
            TransactionService._validate_payload(config, {})

    def test_type_mismatch_raises(self):
        from apps.transaction.types import get_transaction_type
        config = get_transaction_type("business_membership_invitation")
        with pytest.raises(ValidationError, match="must be a string"):
            TransactionService._validate_payload(
                config, {"role_id": 12345},
            )

    def test_max_length_exceeded_raises(self):
        from apps.transaction.types import get_transaction_type
        config = get_transaction_type("business_membership_invitation")
        with pytest.raises(ValidationError, match="max length"):
            TransactionService._validate_payload(
                config, {"role_id": str(uuid4()), "message": "x" * 501},
            )

    def test_valid_payload_passes(self):
        from apps.transaction.types import get_transaction_type
        config = get_transaction_type("business_membership_invitation")
        # Should not raise
        TransactionService._validate_payload(
            config, {"role_id": str(uuid4()), "message": "Hello"},
        )


# =========================================================================
# PRIVATE: _validate_creator_authority
# =========================================================================

@pytest.mark.django_db
class TestValidateCreatorAuthority:

    def test_user_context_skips_validation(self, user):
        """User-context transactions skip authority check."""
        ctx = ActorContext.for_user_context(user, request=None)
        txn = TransactionFactory(
            transaction_type="user_connection_request",
            initiator_context=ctx.to_dict(),
            context_type=ContextType.USER,
            context_id=None,
        )
        # Should not raise
        TransactionService._validate_creator_authority(txn)

    def test_membership_deleted_invalidates(
        self, owner_with_invite_perm, another_user, business,
        owner_actor_context,
    ):
        txn = TransactionFactory(
            transaction_type="business_membership_invitation",
            initiator_context=owner_actor_context.to_dict(),
            context_type=ContextType.BUSINESS,
            context_id=business.id,
            target_id=another_user.id,
        )
        # Delete the membership
        owner_with_invite_perm.is_deleted = True
        owner_with_invite_perm.save()

        with pytest.raises(ValidationError, match="no longer valid"):
            TransactionService._validate_creator_authority(txn)

        txn.refresh_from_db()
        assert txn.status == TransactionStatus.INVALIDATED

    def test_membership_inactive_invalidates(
        self, owner_with_invite_perm, another_user, business,
        owner_actor_context,
    ):
        txn = TransactionFactory(
            transaction_type="business_membership_invitation",
            initiator_context=owner_actor_context.to_dict(),
            context_type=ContextType.BUSINESS,
            context_id=business.id,
            target_id=another_user.id,
        )
        # Suspend membership
        owner_with_invite_perm.status = "suspended"
        owner_with_invite_perm.save()

        with pytest.raises(ValidationError, match="no longer valid"):
            TransactionService._validate_creator_authority(txn)

    def test_permission_lost_invalidates(
        self, owner_with_invite_perm, another_user, business,
        owner_actor_context,
    ):
        from apps.rbac.models import RolePermission
        txn = TransactionFactory(
            transaction_type="business_membership_invitation",
            initiator_context=owner_actor_context.to_dict(),
            context_type=ContextType.BUSINESS,
            context_id=business.id,
            target_id=another_user.id,
        )
        # Remove the permission
        RolePermission.objects.filter(
            role=owner_with_invite_perm.role,
        ).delete()
        # Clear cache
        from apps.rbac.selectors import PermissionSelector
        PermissionSelector.invalidate_membership_permissions(
            membership_id=owner_with_invite_perm.id,
        )

        with pytest.raises(ValidationError, match="no longer valid"):
            TransactionService._validate_creator_authority(txn)

    def test_all_ok_passes(
        self, owner_with_invite_perm, another_user, business,
        owner_actor_context,
    ):
        txn = TransactionFactory(
            transaction_type="business_membership_invitation",
            initiator_context=owner_actor_context.to_dict(),
            context_type=ContextType.BUSINESS,
            context_id=business.id,
            target_id=another_user.id,
        )
        # Should not raise
        TransactionService._validate_creator_authority(txn)


# =========================================================================
# PRIVATE: _execute_outcome
# =========================================================================

@pytest.mark.django_db
class TestExecuteOutcome:

    def test_no_handler_marks_executed(self):
        from apps.transaction.types import TransactionTypeConfig
        from apps.transaction.constants import TransactionMode, ApproverPolicy

        txn = TransactionFactory(
            status=TransactionStatus.ACCEPTED,
            transaction_type="business_membership_invitation",
        )
        ctx = ActorContext.for_system()

        with patch(
            "apps.transaction.services.get_transaction_type",
        ) as mock_get:
            mock_config = MagicMock()
            mock_config.outcome_handler = ""
            mock_get.return_value = mock_config

            TransactionService._execute_outcome(
                transaction=txn, actor_context=ctx,
            )

        txn.refresh_from_db()
        assert txn.outcome_executed is True
        assert txn.outcome_executed_at is not None

    def test_handler_success_marks_executed(self):
        from apps.users.tests.factories import UserFactory
        user_a = UserFactory()
        user_b = UserFactory()
        txn = TransactionFactory(
            status=TransactionStatus.ACCEPTED,
            transaction_type="user_connection_request",
            initiator_id=user_a.id,
            target_id=user_b.id,
        )
        ctx = ActorContext.for_system()

        from apps.transaction.outcome_handlers import register_all_handlers
        register_all_handlers()

        TransactionService._execute_outcome(
            transaction=txn, actor_context=ctx,
        )

        txn.refresh_from_db()
        assert txn.outcome_executed is True

    def test_handler_failure_stores_error(self):
        txn = TransactionFactory(
            status=TransactionStatus.ACCEPTED,
            transaction_type="business_membership_invitation",
        )
        ctx = ActorContext.for_system()

        with patch(
            "apps.transaction.outcome_handlers.OutcomeHandlerRegistry.execute",
            side_effect=ValueError("Boom"),
        ):
            with pytest.raises(ValueError, match="Boom"):
                TransactionService._execute_outcome(
                    transaction=txn, actor_context=ctx,
                )

        txn.refresh_from_db()
        assert "Boom" in txn.outcome_error


# =========================================================================
# NOTIFICATIONS
# =========================================================================

@pytest.mark.django_db
class TestNotifySafe:

    def test_import_error_graceful(self):
        txn = TransactionFactory()
        with patch(
            "apps.transaction.services.TransactionService._notify_safe",
        ) as mock:
            mock.return_value = None
            # Should not raise
            TransactionService._notify_safe("accepted", txn)

    def test_notification_error_logged_not_raised(self):
        txn = TransactionFactory()
        with patch(
            "apps.transaction.services.TransactionService._notify_accepted",
            side_effect=Exception("Notify failed"),
        ):
            # Should not raise — errors are caught
            TransactionService._notify_safe("accepted", txn)


# =========================================================================
# MANAGERS
# =========================================================================

@pytest.mark.django_db
class TestTransactionQuerySet:

    def test_active_excludes_terminal(self):
        TransactionFactory(status=TransactionStatus.PENDING)
        TransactionFactory(
            status=TransactionStatus.ACCEPTED, resolved_at=timezone.now(),
        )
        assert Transaction.objects.active().count() == 1

    def test_pending_filters(self):
        TransactionFactory(status=TransactionStatus.PENDING)
        TransactionFactory(status=TransactionStatus.CREATED)
        assert Transaction.objects.pending().count() == 1

    def test_expired_needing_update(self):
        TransactionFactory(
            status=TransactionStatus.PENDING,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        TransactionFactory(
            status=TransactionStatus.PENDING,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        TransactionFactory(
            status=TransactionStatus.ACCEPTED,
            expires_at=timezone.now() - timedelta(hours=1),
            resolved_at=timezone.now(),
        )
        assert Transaction.objects.expired_needing_update().count() == 1

    def test_for_context(self):
        ctx_id = uuid4()
        TransactionFactory(
            context_type=ContextType.BUSINESS, context_id=ctx_id,
        )
        TransactionFactory(
            context_type=ContextType.BUSINESS, context_id=uuid4(),
        )
        result = Transaction.objects.for_context(
            ContextType.BUSINESS, ctx_id,
        )
        assert result.count() == 1

    def test_for_initiator(self):
        uid = uuid4()
        TransactionFactory(
            initiator_type=PartyType.USER, initiator_id=uid,
        )
        TransactionFactory(
            initiator_type=PartyType.USER, initiator_id=uuid4(),
        )
        assert Transaction.objects.for_initiator(
            PartyType.USER, uid,
        ).count() == 1

    def test_for_target(self):
        uid = uuid4()
        TransactionFactory(target_type=PartyType.USER, target_id=uid)
        assert Transaction.objects.for_target(
            PartyType.USER, uid,
        ).count() == 1

    def test_of_type(self):
        TransactionFactory(
            transaction_type="business_membership_invitation",
        )
        TransactionFactory(
            transaction_type="user_connection_request",
            context_type=ContextType.USER,
            context_id=None,
        )
        assert Transaction.objects.of_type(
            "business_membership_invitation",
        ).count() == 1

    def test_needing_outcome_execution(self):
        TransactionFactory(
            status=TransactionStatus.ACCEPTED,
            outcome_executed=False,
            resolved_at=timezone.now(),
        )
        TransactionFactory(
            status=TransactionStatus.ACCEPTED,
            outcome_executed=True,
            resolved_at=timezone.now(),
        )
        assert Transaction.objects.needing_outcome_execution().count() == 1

    def test_with_logs(self):
        txn = TransactionFactory()
        TransactionLogFactory(transaction=txn)
        result = Transaction.objects.with_logs().get(id=txn.id)
        # Accessing .logs should not cause extra queries (prefetched)
        assert result.logs.all().count() == 1

    def test_soft_delete_filtering(self):
        txn = TransactionFactory()
        txn.is_deleted = True
        txn.save()
        assert Transaction.objects.filter(id=txn.id).count() == 0
        assert Transaction.all_objects.filter(id=txn.id).count() == 1

    def test_create_transaction_defaults(self):
        txn = Transaction.objects.create_transaction(
            transaction_type="test",
            mode=TransactionMode.REQUEST,
            initiator_type=PartyType.USER,
            initiator_id=uuid4(),
            target_type=PartyType.ACCOUNT,
            target_id=uuid4(),
            context_type=ContextType.BUSINESS,
            context_id=uuid4(),
        )
        assert txn.status == TransactionStatus.CREATED
        assert txn.payload == {}


# =========================================================================
# PLATFORM TRANSACTION SERVICES
# =========================================================================

@pytest.mark.django_db
class TestPlatformTransactionServices:
    """Tests for transaction services operating in platform context."""

    # --- Create Invitation ---

    def test_create_platform_invitation_happy_path(
        self, platform_owner_actor_ctx, user, platform, platform_base_member_role,
    ):
        txn = TransactionService.create_invitation(
            transaction_type="platform_membership_invitation",
            initiator_context=platform_owner_actor_ctx,
            target_user_id=user.id,
            payload={"role_id": str(platform_base_member_role.id)},
        )
        assert txn.status == TransactionStatus.PENDING
        assert txn.context_type == ContextType.PLATFORM
        assert txn.context_id == platform.id
        assert txn.target_id == user.id
        assert txn.transaction_type == "platform_membership_invitation"

    # --- Create Request ---

    def test_create_platform_request_happy_path(
        self, user_actor_context, platform,
    ):
        txn = TransactionService.create_request(
            transaction_type="platform_membership_request",
            user_id=user_actor_context.user_id,
            target_account_type="platform",
            target_account_id=platform.id,
        )
        assert txn.status == TransactionStatus.PENDING
        assert txn.context_type == ContextType.PLATFORM
        assert txn.context_id == platform.id

    # --- Accept ---

    def test_accept_platform_invitation(
        self, platform_pending_invitation, user,
    ):
        """Target user accepts platform invitation → membership created."""
        target_ctx = ActorContext.for_user_context(user, request=None)
        txn = TransactionService.accept(
            transaction_id=platform_pending_invitation.id,
            actor_context=target_ctx,
        )
        assert txn.status == TransactionStatus.ACCEPTED

    def test_accept_platform_request_by_authority(
        self, platform_pending_request, platform_approver_actor_ctx,
        platform_base_member_role,
    ):
        """Platform owner with approve permission accepts request."""
        txn = TransactionService.accept(
            transaction_id=platform_pending_request.id,
            actor_context=platform_approver_actor_ctx,
        )
        assert txn.status == TransactionStatus.ACCEPTED

    # --- Deny ---

    def test_deny_platform_request(
        self, platform_pending_request, platform_approver_actor_ctx,
    ):
        txn = TransactionService.deny(
            transaction_id=platform_pending_request.id,
            actor_context=platform_approver_actor_ctx,
            reason="Not a good fit",
        )
        assert txn.status == TransactionStatus.DENIED

    # --- Cancel ---

    def test_cancel_platform_request(
        self, platform_pending_request, user,
    ):
        """Requester cancels their own request."""
        user_ctx = ActorContext.for_user_context(user, request=None)
        txn = TransactionService.cancel(
            transaction_id=platform_pending_request.id,
            actor_context=user_ctx,
        )
        assert txn.status == TransactionStatus.CANCELLED

    # --- Conflict Detection ---

    def test_platform_duplicate_active_raises_conflict(
        self, platform_pending_invitation, platform_owner_actor_ctx, user,
        platform, platform_base_member_role,
    ):
        """Second invitation for same user raises ConflictError."""
        with pytest.raises(ConflictError):
            TransactionService.create_invitation(
                transaction_type="platform_membership_invitation",
                initiator_context=platform_owner_actor_ctx,
                target_user_id=user.id,
                payload={"role_id": str(platform_base_member_role.id)},
            )

    def test_platform_cross_type_conflict(
        self, platform_pending_invitation, user_actor_context, platform,
    ):
        """User has pending invitation → request raises ConflictError."""
        with pytest.raises(ConflictError):
            TransactionService.create_request(
                transaction_type="platform_membership_request",
                user_id=user_actor_context.user_id,
                target_account_type="platform",
                target_account_id=platform.id,
            )

    # --- Quota & Open Member Request ---

    def test_platform_quota_blocks_invitation(
        self, platform_owner_actor_ctx, user, platform, platform_base_member_role,
    ):
        """Platform at max_members → invitation blocked."""
        # platform_membership already exists (owner), set max_members=1
        platform.max_members = 1
        platform.save(update_fields=["max_members"])

        with pytest.raises(BusinessRuleViolation) as exc:
            TransactionService.create_invitation(
                transaction_type="platform_membership_invitation",
                initiator_context=platform_owner_actor_ctx,
                target_user_id=user.id,
                payload={"role_id": str(platform_base_member_role.id)},
            )
        assert exc.value.details["rule"] == "member_quota_exceeded"

    def test_platform_quota_blocks_request(
        self, user_actor_context, platform, platform_membership,
    ):
        """Platform at max_members → request blocked."""
        platform.max_members = 1
        platform.save(update_fields=["max_members"])

        with pytest.raises(BusinessRuleViolation) as exc:
            TransactionService.create_request(
                transaction_type="platform_membership_request",
                user_id=user_actor_context.user_id,
                target_account_type="platform",
                target_account_id=platform.id,
            )
        assert exc.value.details["rule"] == "member_quota_exceeded"

    def test_platform_closed_request_blocked(
        self, user_actor_context, platform,
    ):
        """open_member_request=False → request blocked."""
        platform.open_member_request = False
        platform.save(update_fields=["open_member_request"])

        with pytest.raises(BusinessRuleViolation) as exc:
            TransactionService.create_request(
                transaction_type="platform_membership_request",
                user_id=user_actor_context.user_id,
                target_account_type="platform",
                target_account_id=platform.id,
            )
        assert exc.value.details["rule"] == "member_requests_closed"

    # --- Ownership Transfer ---

    def test_platform_ownership_transfer(
        self, platform_owner_actor_ctx, user, platform,
    ):
        """Owner creates ownership transfer → target accepts → transferred."""
        txn = TransactionService.create_invitation(
            transaction_type="platform_ownership_transfer",
            initiator_context=platform_owner_actor_ctx,
            target_user_id=user.id,
        )
        assert txn.status == TransactionStatus.PENDING
        assert txn.transaction_type == "platform_ownership_transfer"

    def test_platform_ownership_transfer_non_owner_denied(
        self, platform_base_membership, platform,
    ):
        """Non-owner cannot create ownership transfer."""
        from apps.rbac.services import RBACService

        base_ctx = RBACService.build_actor_context(
            membership=platform_base_membership, request=None,
        )
        with pytest.raises(PermissionDenied):
            TransactionService.create_invitation(
                transaction_type="platform_ownership_transfer",
                initiator_context=base_ctx,
                target_user_id=uuid4(),
            )


# =========================================================================
# MEMBER QUOTA PRE-CHECKS
# =========================================================================

@pytest.mark.django_db
class TestMemberQuotaPreCheck:
    """Tests for member quota pre-checks in create_invitation/create_request."""

    def test_create_invitation_blocked_when_at_quota(
        self, user, another_user, third_user,
    ):
        """Invitation is blocked when business is at max_members."""
        from apps.rbac.tests.factories import BusinessAccountFactory, MembershipFactory
        from apps.rbac.models import Permission, Role, RolePermission, Membership
        from apps.rbac.services import RBACService

        business = BusinessAccountFactory(max_members=1, created_by=user)
        owner_role = Role.objects.create(
            name="Owner", account_type=AccountType.BUSINESS,
            account_id=business.id, level=0, is_system_role=True,
        )
        Role.objects.create(
            name="Base Member", account_type=AccountType.BUSINESS,
            account_id=business.id, level=10, is_system_role=True,
        )
        owner_mem = Membership.objects.create(
            user=user, account_type=AccountType.BUSINESS,
            account_id=business.id, role=owner_role,
            is_owner=True, status="active",
        )
        perm, _ = Permission.objects.get_or_create(
            code="can_invite_member",
            defaults={
                "name": "Invite Member",
                "description": "Invite new members",
                "category": "membership",
                "applicable_scopes": ["business", "platform_only", "global_only"],
            },
        )
        RolePermission.objects.get_or_create(
            role=owner_role, permission=perm, defaults={"scope": "business"},
        )
        ctx = RBACService.build_actor_context(membership=owner_mem, request=None)

        with pytest.raises(BusinessRuleViolation) as exc_info:
            TransactionService.create_invitation(
                transaction_type="business_membership_invitation",
                initiator_context=ctx,
                target_user_id=another_user.id,
                payload={"role_id": str(uuid4())},
            )
        assert exc_info.value.details["rule"] == "member_quota_exceeded"

    def test_create_invitation_allowed_when_below_quota(
        self, owner_actor_context, another_user, base_member_role,
    ):
        """Invitation succeeds when below max_members (factory default=6)."""
        txn = TransactionService.create_invitation(
            transaction_type="business_membership_invitation",
            initiator_context=owner_actor_context,
            target_user_id=another_user.id,
            payload={"role_id": str(base_member_role.id)},
        )
        assert txn.status == TransactionStatus.PENDING

    def test_create_request_blocked_when_at_quota(
        self, another_user,
    ):
        """Request is blocked when business is at max_members."""
        from apps.rbac.tests.factories import BusinessAccountFactory
        from apps.rbac.models import Role, Membership

        owner = UserFactory(email="quota_owner@test.com")
        business = BusinessAccountFactory(max_members=1, open_member_request=True, created_by=owner)
        owner_role = Role.objects.create(
            name="Owner", account_type=AccountType.BUSINESS,
            account_id=business.id, level=0, is_system_role=True,
        )
        Role.objects.create(
            name="Base Member", account_type=AccountType.BUSINESS,
            account_id=business.id, level=10, is_system_role=True,
        )
        Membership.objects.create(
            user=owner, account_type=AccountType.BUSINESS,
            account_id=business.id, role=owner_role,
            is_owner=True, status="active",
        )

        with pytest.raises(BusinessRuleViolation) as exc_info:
            TransactionService.create_request(
                transaction_type="business_membership_request",
                user_id=another_user.id,
                target_account_type=AccountType.BUSINESS,
                target_account_id=business.id,
            )
        assert exc_info.value.details["rule"] == "member_quota_exceeded"

    def test_create_request_allowed_when_below_quota(
        self, another_user, business,
    ):
        """Request succeeds when below max_members (factory default=6)."""
        txn = TransactionService.create_request(
            transaction_type="business_membership_request",
            user_id=another_user.id,
            target_account_type=AccountType.BUSINESS,
            target_account_id=business.id,
        )
        assert txn.status == TransactionStatus.PENDING
