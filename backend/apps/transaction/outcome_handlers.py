from typing import Callable, Dict
from django.db import transaction as db_transaction
from apps.core.observability import get_logger
from apps.core.types import ActorContext
from apps.core.constants import AccountType
from apps.transaction.models import Transaction

logger = get_logger(__name__)


class OutcomeHandlerRegistry:
    _handlers: Dict[str, Callable] = {}

    @classmethod
    def register(cls, transaction_type: str, handler: Callable):
        cls._handlers[transaction_type] = handler

    @classmethod
    def execute(
        cls, *, transaction: Transaction, actor_context: ActorContext,
        acceptance_payload: dict = None,
    ):
        handler = cls._handlers.get(transaction.transaction_type)
        if handler:
            handler(
                transaction=transaction, actor_context=actor_context,
                acceptance_payload=acceptance_payload or {},
            )


class MembershipOutcomeHandler:

    @staticmethod
    @db_transaction.atomic
    def handle_invitation_accepted(
        *, transaction: Transaction, actor_context: ActorContext,
        acceptance_payload: dict = None,
    ):
        from apps.rbac.services import RBACService
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user = User.objects.get(id=actor_context.user_id)
        initiator_ctx = ActorContext.from_dict(transaction.initiator_context)
        created_by = User.objects.filter(id=initiator_ctx.user_id).first()

        RBACService.create_membership(
            user=user,
            account_type=AccountType(transaction.context_type),
            account_id=transaction.context_id,
            role_id=transaction.payload.get("role_id"),
            created_by=created_by,
        )
        logger.info(
            "outcome.membership.invitation_accepted",
            transaction_id=str(transaction.id),
        )

    @staticmethod
    @db_transaction.atomic
    def handle_request_approved(
        *, transaction: Transaction, actor_context: ActorContext,
        acceptance_payload: dict = None,
    ):
        from apps.rbac.services import RBACService
        from apps.rbac.selectors import RoleSelector
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user = User.objects.get(id=transaction.initiator_id)
        approver = User.objects.filter(id=actor_context.user_id).first()

        # Acceptance-time role_id takes priority over transaction payload
        ap = acceptance_payload or {}
        role_id = ap.get("role_id") or transaction.payload.get("role_id")
        if role_id:
            role_id = str(role_id)
        else:
            base_role = RoleSelector.get_base_member_role(
                account_type=AccountType(transaction.context_type),
                account_id=transaction.context_id,
            )
            role_id = str(base_role.id)

        RBACService.create_membership(
            user=user,
            account_type=AccountType(transaction.context_type),
            account_id=transaction.context_id,
            role_id=role_id,
            created_by=approver,
        )
        logger.info(
            "outcome.membership.request_approved",
            transaction_id=str(transaction.id),
        )


class VerificationOutcomeHandler:

    @staticmethod
    def _resolve_business(transaction: Transaction):
        from apps.organization.business.selectors import BusinessAccountSelector
        initiator_ctx = ActorContext.from_dict(transaction.initiator_context)
        return BusinessAccountSelector.get_by_id(
            business_id=initiator_ctx.account_id,
        )

    @staticmethod
    @db_transaction.atomic
    def handle_created(
        *, transaction: Transaction, actor_context: ActorContext,
    ):
        """Set business verification_status to PENDING when request is created."""
        from apps.organization.business.services import BusinessAccountService
        from apps.core.constants import VerificationStatus
        from django.contrib.auth import get_user_model
        User = get_user_model()

        business = VerificationOutcomeHandler._resolve_business(transaction)
        actor = User.objects.get(id=actor_context.user_id)

        BusinessAccountService.update_verification_status(
            business=business,
            status=VerificationStatus.PENDING,
            actor=actor,
        )
        logger.info(
            "outcome.verification.created",
            transaction_id=str(transaction.id),
            business_id=str(business.id),
        )

    @staticmethod
    @db_transaction.atomic
    def handle_closed(
        *, transaction: Transaction, actor_context: ActorContext,
        terminal_status: str,
    ):
        """Revert business verification_status when request is denied/cancelled/dismissed."""
        from apps.organization.business.services import BusinessAccountService
        from apps.core.constants import VerificationStatus
        from apps.transaction.constants import TransactionStatus
        from django.contrib.auth import get_user_model
        User = get_user_model()

        business = VerificationOutcomeHandler._resolve_business(transaction)
        actor = User.objects.get(id=actor_context.user_id)

        new_status = (
            VerificationStatus.REJECTED
            if terminal_status == TransactionStatus.DENIED
            else VerificationStatus.UNVERIFIED
        )
        BusinessAccountService.update_verification_status(
            business=business,
            status=new_status,
            actor=actor,
        )
        logger.info(
            "outcome.verification.closed",
            transaction_id=str(transaction.id),
            terminal_status=terminal_status,
            new_verification_status=new_status,
        )

    @staticmethod
    @db_transaction.atomic
    def handle_accepted(
        *, transaction: Transaction, actor_context: ActorContext,
        acceptance_payload: dict = None,
    ):
        from apps.organization.business.services import BusinessAccountService
        from apps.core.constants import VerificationStatus
        from django.contrib.auth import get_user_model
        User = get_user_model()

        business = VerificationOutcomeHandler._resolve_business(transaction)
        actor = User.objects.get(id=actor_context.user_id)

        BusinessAccountService.update_verification_status(
            business=business,
            status=VerificationStatus.VERIFIED,
            actor=actor,
        )
        logger.info(
            "outcome.verification.accepted",
            transaction_id=str(transaction.id),
        )


class OwnershipOutcomeHandler:

    @staticmethod
    @db_transaction.atomic
    def handle_accepted(
        *, transaction: Transaction, actor_context: ActorContext,
        acceptance_payload: dict = None,
    ):
        from apps.rbac.services import RBACService
        from django.contrib.auth import get_user_model
        User = get_user_model()

        new_owner = User.objects.get(id=actor_context.user_id)
        RBACService.transfer_ownership(
            account_type=AccountType(transaction.context_type),
            account_id=transaction.context_id,
            new_owner=new_owner,
            transferred_by=new_owner,
        )
        logger.info(
            "outcome.ownership.transferred",
            transaction_id=str(transaction.id),
        )


class PermissionOutcomeHandler:
    """Handles permission grants when transactions are approved."""

    @staticmethod
    @db_transaction.atomic
    def handle_business_creation_approved(
        *, transaction: Transaction, actor_context: ActorContext,
        acceptance_payload: dict = None,
    ):
        from django.contrib.auth import get_user_model
        from apps.core.observability import AuditService
        from apps.core.observability.audit.models import AuditLog
        User = get_user_model()

        user = User.objects.get(id=transaction.initiator_id)
        user.can_create_business = True
        user.save(update_fields=["can_create_business"])

        approver = User.objects.filter(id=actor_context.user_id).first()
        AuditService.log(
            action=AuditLog.Action.BUSINESS_CREATION_PERMISSION_GRANTED,
            actor=approver,
            resource=user,
            details={
                "target_user_id": str(user.id),
                "transaction_id": str(transaction.id),
            },
        )

        logger.info(
            "outcome.permission.business_creation_granted",
            transaction_id=str(transaction.id),
            user_id=str(user.id),
        )


def register_all_handlers():
    from apps.network.outcome_handlers import (
        FollowOutcomeHandler as NetworkFollowHandler,
        ConnectionOutcomeHandler as NetworkConnectionHandler,
    )

    r = OutcomeHandlerRegistry.register
    r("platform_membership_invitation", MembershipOutcomeHandler.handle_invitation_accepted)
    r("platform_membership_request", MembershipOutcomeHandler.handle_request_approved)
    r("business_membership_invitation", MembershipOutcomeHandler.handle_invitation_accepted)
    r("business_membership_request", MembershipOutcomeHandler.handle_request_approved)
    r("business_verification_request", VerificationOutcomeHandler.handle_accepted)
    r("platform_ownership_transfer", OwnershipOutcomeHandler.handle_accepted)
    r("business_ownership_transfer", OwnershipOutcomeHandler.handle_accepted)
    r("business_creation_permission_request", PermissionOutcomeHandler.handle_business_creation_approved)
    # Network handlers
    r("business_follow_request", NetworkFollowHandler.handle_accepted)
    r("business_follow_approval_request", NetworkFollowHandler.handle_accepted)
    r("platform_follow_request", NetworkFollowHandler.handle_accepted)
    r("user_connection_request", NetworkConnectionHandler.handle_user_accepted)
    r("business_connection_request", NetworkConnectionHandler.handle_account_accepted)
    r("business_platform_connection_request", NetworkConnectionHandler.handle_account_accepted)
