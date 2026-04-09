from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from apps.core.constants import AccountType, ContextType
from apps.core.types import ActorContext
from apps.transaction.constants import PartyType, TransactionMode, TransactionStatus
from apps.transaction.outcome_handlers import (
    MembershipOutcomeHandler,
    OutcomeHandlerRegistry,
    OwnershipOutcomeHandler,
    PermissionOutcomeHandler,
    VerificationOutcomeHandler,
    register_all_handlers,
)
from apps.transaction.tests.factories import TransactionFactory
from apps.users.tests.factories import UserFactory

# =========================================================================
# REGISTRY
# =========================================================================


@pytest.mark.django_db
class TestOutcomeHandlerRegistry:

    def setup_method(self):
        self._saved_handlers = OutcomeHandlerRegistry._handlers.copy()
        OutcomeHandlerRegistry._handlers = {}

    def teardown_method(self):
        OutcomeHandlerRegistry._handlers = self._saved_handlers

    def test_register_and_execute(self):
        handler = MagicMock()
        OutcomeHandlerRegistry.register("test_type", handler)

        txn = TransactionFactory(transaction_type="test_type")
        ctx = ActorContext.for_system()
        OutcomeHandlerRegistry.execute(transaction=txn, actor_context=ctx)

        handler.assert_called_once_with(
            transaction=txn,
            actor_context=ctx,
            acceptance_payload={},
        )

    def test_execute_forwards_acceptance_payload(self):
        handler = MagicMock()
        OutcomeHandlerRegistry.register("test_type", handler)

        txn = TransactionFactory(transaction_type="test_type")
        ctx = ActorContext.for_system()
        payload = {"role_id": str(uuid4())}
        OutcomeHandlerRegistry.execute(
            transaction=txn,
            actor_context=ctx,
            acceptance_payload=payload,
        )

        handler.assert_called_once_with(
            transaction=txn,
            actor_context=ctx,
            acceptance_payload=payload,
        )

    def test_execute_no_handler_does_nothing(self):
        txn = TransactionFactory(transaction_type="unregistered_type")
        ctx = ActorContext.for_system()
        # Should not raise
        OutcomeHandlerRegistry.execute(transaction=txn, actor_context=ctx)


# =========================================================================
# MEMBERSHIP OUTCOME HANDLER
# =========================================================================


@pytest.mark.django_db
class TestMembershipOutcomeHandler:

    @patch("apps.rbac.services.RBACService.create_membership")
    def test_handle_invitation_accepted(self, mock_create):
        user = UserFactory()
        initiator = UserFactory()

        initiator_ctx = ActorContext.for_user_context(initiator)
        actor_ctx = ActorContext.for_user_context(user)
        context_id = uuid4()

        txn = TransactionFactory(
            transaction_type="business_membership_invitation",
            mode=TransactionMode.INVITATION,
            initiator_context=initiator_ctx.to_dict(),
            context_type=ContextType.BUSINESS,
            context_id=context_id,
            payload={"role_id": str(uuid4())},
            status=TransactionStatus.ACCEPTED,
        )

        MembershipOutcomeHandler.handle_invitation_accepted(
            transaction=txn,
            actor_context=actor_ctx,
        )

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["user"].id == user.id
        assert call_kwargs["account_type"] == AccountType.BUSINESS
        assert call_kwargs["account_id"] == context_id

    @patch("apps.rbac.services.RBACService.create_membership")
    @patch("apps.rbac.selectors.RoleSelector.get_base_member_role")
    def test_handle_request_approved_with_base_role_fallback(
        self,
        mock_get_base_role,
        mock_create,
    ):
        user = UserFactory()
        approver = UserFactory()
        context_id = uuid4()

        mock_base_role = MagicMock()
        mock_base_role.id = uuid4()
        mock_get_base_role.return_value = mock_base_role

        actor_ctx = ActorContext.for_user_context(approver)
        txn = TransactionFactory(
            transaction_type="business_membership_request",
            mode=TransactionMode.REQUEST,
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            context_type=ContextType.BUSINESS,
            context_id=context_id,
            payload={},  # No role_id — should fallback to base role
            status=TransactionStatus.ACCEPTED,
        )

        MembershipOutcomeHandler.handle_request_approved(
            transaction=txn,
            actor_context=actor_ctx,
        )

        mock_get_base_role.assert_called_once()
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["role_id"] == str(mock_base_role.id)

    @patch("apps.rbac.services.RBACService.create_membership")
    def test_handle_request_approved_with_payload_role_id(self, mock_create):
        user = UserFactory()
        approver = UserFactory()
        role_id = str(uuid4())

        actor_ctx = ActorContext.for_user_context(approver)
        txn = TransactionFactory(
            transaction_type="business_membership_request",
            mode=TransactionMode.REQUEST,
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            context_type=ContextType.BUSINESS,
            context_id=uuid4(),
            payload={"role_id": role_id},
            status=TransactionStatus.ACCEPTED,
        )

        MembershipOutcomeHandler.handle_request_approved(
            transaction=txn,
            actor_context=actor_ctx,
        )

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["role_id"] == role_id

    @patch("apps.rbac.services.RBACService.create_membership")
    def test_handle_request_approved_acceptance_payload_overrides_transaction(
        self,
        mock_create,
    ):
        """acceptance_payload role_id takes priority over transaction payload."""
        user = UserFactory()
        approver = UserFactory()
        txn_role_id = str(uuid4())
        acceptance_role_id = str(uuid4())

        actor_ctx = ActorContext.for_user_context(approver)
        txn = TransactionFactory(
            transaction_type="business_membership_request",
            mode=TransactionMode.REQUEST,
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            context_type=ContextType.BUSINESS,
            context_id=uuid4(),
            payload={"role_id": txn_role_id},
            status=TransactionStatus.ACCEPTED,
        )

        MembershipOutcomeHandler.handle_request_approved(
            transaction=txn,
            actor_context=actor_ctx,
            acceptance_payload={"role_id": acceptance_role_id},
        )

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["role_id"] == acceptance_role_id


# =========================================================================
# VERIFICATION OUTCOME HANDLER
# =========================================================================


@pytest.mark.django_db
class TestVerificationOutcomeHandler:

    @patch(
        "apps.organization.business.services.BusinessAccountService.update_verification_status"
    )
    @patch("apps.organization.business.selectors.BusinessAccountSelector.get_by_id")
    def test_handle_accepted(self, mock_get_by_id, mock_update_status):
        actor = UserFactory()
        account_id = uuid4()

        mock_business = MagicMock()
        mock_get_by_id.return_value = mock_business

        initiator_ctx = ActorContext(
            user_id=uuid4(),
            account_type="business",
            account_id=account_id,
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Owner",
            role_level=0,
            is_owner=True,
        )
        actor_ctx = ActorContext.for_user_context(actor)

        txn = TransactionFactory(
            transaction_type="business_verification_request",
            initiator_context=initiator_ctx.to_dict(),
            context_type=ContextType.PLATFORM,
            context_id=uuid4(),
            status=TransactionStatus.ACCEPTED,
        )

        VerificationOutcomeHandler.handle_accepted(
            transaction=txn,
            actor_context=actor_ctx,
        )

        mock_get_by_id.assert_called_once_with(
            business_id=account_id,
        )
        mock_update_status.assert_called_once()


# =========================================================================
# OWNERSHIP OUTCOME HANDLER
# =========================================================================


@pytest.mark.django_db
class TestOwnershipOutcomeHandler:

    @patch("apps.rbac.services.RBACService.transfer_ownership")
    def test_handle_accepted(self, mock_transfer):
        new_owner = UserFactory()
        actor_ctx = ActorContext.for_user_context(new_owner)
        context_id = uuid4()

        txn = TransactionFactory(
            transaction_type="business_ownership_transfer",
            context_type=ContextType.BUSINESS,
            context_id=context_id,
            status=TransactionStatus.ACCEPTED,
        )

        OwnershipOutcomeHandler.handle_accepted(
            transaction=txn,
            actor_context=actor_ctx,
        )

        mock_transfer.assert_called_once()
        call_kwargs = mock_transfer.call_args[1]
        assert call_kwargs["new_owner"].id == new_owner.id
        assert call_kwargs["account_id"] == context_id


# =========================================================================
# PERMISSION OUTCOME HANDLER
# =========================================================================


@pytest.mark.django_db
class TestPermissionOutcomeHandler:

    def test_grants_can_create_business_flag(self):
        """Handler sets can_create_business=True on the initiating user."""
        user = UserFactory()
        assert user.can_create_business is False

        approver = UserFactory()
        actor_ctx = ActorContext.for_user_context(approver)

        txn = TransactionFactory(
            transaction_type="business_creation_permission_request",
            mode=TransactionMode.REQUEST,
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            context_type=ContextType.PLATFORM,
            context_id=uuid4(),
            status=TransactionStatus.ACCEPTED,
        )

        PermissionOutcomeHandler.handle_business_creation_approved(
            transaction=txn,
            actor_context=actor_ctx,
        )

        user.refresh_from_db()
        assert user.can_create_business is True

    def test_creates_audit_log(self):
        """Handler creates BUSINESS_CREATION_PERMISSION_GRANTED audit entry."""
        from apps.core.observability.audit.models import AuditLog

        user = UserFactory()
        approver = UserFactory()
        actor_ctx = ActorContext.for_user_context(approver)

        txn = TransactionFactory(
            transaction_type="business_creation_permission_request",
            mode=TransactionMode.REQUEST,
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            context_type=ContextType.PLATFORM,
            context_id=uuid4(),
            status=TransactionStatus.ACCEPTED,
        )

        PermissionOutcomeHandler.handle_business_creation_approved(
            transaction=txn,
            actor_context=actor_ctx,
        )

        log = AuditLog.objects.filter(
            action=AuditLog.Action.BUSINESS_CREATION_PERMISSION_GRANTED,
        ).first()
        assert log is not None
        assert log.details["target_user_id"] == str(user.id)
        assert log.details["transaction_id"] == str(txn.id)

    def test_idempotent_for_already_approved_user(self):
        """Handler works even if user already has the flag."""
        user = UserFactory()
        user.can_create_business = True
        user.save(update_fields=["can_create_business"])

        actor_ctx = ActorContext.for_user_context(UserFactory())
        txn = TransactionFactory(
            transaction_type="business_creation_permission_request",
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            status=TransactionStatus.ACCEPTED,
        )

        PermissionOutcomeHandler.handle_business_creation_approved(
            transaction=txn,
            actor_context=actor_ctx,
        )

        user.refresh_from_db()
        assert user.can_create_business is True


# =========================================================================
# REGISTER ALL HANDLERS
# =========================================================================


@pytest.mark.django_db
class TestRegisterAllHandlers:

    def test_all_types_registered(self):
        saved = OutcomeHandlerRegistry._handlers.copy()
        try:
            OutcomeHandlerRegistry._handlers = {}
            register_all_handlers()

            expected_types = [
                "platform_membership_invitation",
                "platform_membership_request",
                "business_membership_invitation",
                "business_membership_request",
                "business_verification_request",
                "platform_ownership_transfer",
                "business_ownership_transfer",
                "user_connection_request",
                "business_follow_request",
                "business_creation_permission_request",
                # Network handlers
                "business_follow_approval_request",
                "platform_follow_request",
                "business_connection_request",
                "business_platform_connection_request",
                # CMS handlers
                "cms_activation_request",
            ]
            for t in expected_types:
                assert t in OutcomeHandlerRegistry._handlers, f"Missing handler for {t}"

            assert len(OutcomeHandlerRegistry._handlers) == 15
        finally:
            OutcomeHandlerRegistry._handlers = saved
