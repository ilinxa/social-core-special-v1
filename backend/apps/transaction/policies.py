from apps.core.exceptions import PermissionDenied, ValidationError
from apps.core.types import ActorContext
from apps.transaction.models import Transaction
from apps.transaction.types import TransactionTypeConfig, get_transaction_type
from apps.transaction.constants import TransactionStatus, ApproverPolicy, PartyType


class TransactionPolicy:

    @staticmethod
    def can_create_invitation(
        *, actor_context: ActorContext, config: TransactionTypeConfig,
    ) -> None:
        for perm_code in config.required_permissions:
            if not actor_context.has_permission(perm_code):
                raise PermissionDenied(
                    message=f"Missing required permission: {perm_code}",
                    action="create_invitation",
                    resource="Transaction",
                )
        if config.owner_only and not actor_context.is_owner:
            raise PermissionDenied(
                message="Only the account owner can initiate this transaction",
                action="create_invitation",
                resource="Transaction",
            )

    @staticmethod
    def can_accept(
        *, transaction: Transaction, actor_context: ActorContext,
        config: TransactionTypeConfig,
    ) -> None:
        if transaction.status != TransactionStatus.PENDING:
            raise ValidationError(
                message=f"Transaction is not pending (status: {transaction.status})",
                field="status",
            )

        policy = config.approver_policy

        if policy == ApproverPolicy.TARGET_ACCEPTANCE:
            if transaction.target_type != PartyType.USER:
                raise PermissionDenied(
                    message="Invalid target type",
                    action="accept",
                    resource="Transaction",
                )
            if actor_context.user_id != transaction.target_id:
                raise PermissionDenied(
                    message="Only the target user can accept this invitation",
                    action="accept",
                    resource="Transaction",
                )

        elif policy == ApproverPolicy.ACCOUNT_AUTHORITY:
            if actor_context.account_id != transaction.context_id:
                raise PermissionDenied(
                    message="Not a member of the account this transaction belongs to",
                    action="accept",
                    resource="Transaction",
                )
            if config.approval_permission and not actor_context.has_permission(
                config.approval_permission,
            ):
                raise PermissionDenied(
                    message=f"Missing permission: {config.approval_permission}",
                    action="accept",
                    resource="Transaction",
                )

        elif policy == ApproverPolicy.PLATFORM_AUTHORITY:
            if actor_context.account_type != "platform":
                raise PermissionDenied(
                    message="Platform authority required",
                    action="accept",
                    resource="Transaction",
                )
            if config.approval_permission and not actor_context.has_permission(
                config.approval_permission,
            ):
                raise PermissionDenied(
                    message=f"Missing permission: {config.approval_permission}",
                    action="accept",
                    resource="Transaction",
                )

        elif policy == ApproverPolicy.AUTO_APPROVAL:
            raise ValidationError(
                message="Auto-approval transactions don't require manual acceptance",
                field="transaction_type",
            )

    @staticmethod
    def can_deny(
        *, transaction: Transaction, actor_context: ActorContext,
        config: TransactionTypeConfig,
    ) -> None:
        # Allow deny from both PENDING and PENDING_REVIEW
        if transaction.status == TransactionStatus.PENDING_REVIEW:
            TransactionPolicy.can_approve_pending_review(
                transaction=transaction,
                actor_context=actor_context,
                config=config,
            )
        else:
            TransactionPolicy.can_accept(
                transaction=transaction,
                actor_context=actor_context,
                config=config,
            )

    @staticmethod
    def can_dismiss(
        *, transaction: Transaction, actor_context: ActorContext,
        config: TransactionTypeConfig,
    ) -> None:
        """Check authority to dismiss (status-agnostic authority check)."""
        policy = config.approver_policy

        if policy == ApproverPolicy.TARGET_ACCEPTANCE:
            if transaction.target_type != PartyType.USER:
                raise PermissionDenied(
                    message="Invalid target type",
                    action="dismiss", resource="Transaction",
                )
            if actor_context.user_id != transaction.target_id:
                raise PermissionDenied(
                    message="Only the target user can dismiss",
                    action="dismiss", resource="Transaction",
                )

        elif policy == ApproverPolicy.ACCOUNT_AUTHORITY:
            if actor_context.account_id != transaction.context_id:
                raise PermissionDenied(
                    message="Not a member of this account",
                    action="dismiss", resource="Transaction",
                )
            if config.approval_permission and not actor_context.has_permission(
                config.approval_permission,
            ):
                raise PermissionDenied(
                    message=f"Missing permission: {config.approval_permission}",
                    action="dismiss", resource="Transaction",
                )

        elif policy == ApproverPolicy.PLATFORM_AUTHORITY:
            if actor_context.account_type != "platform":
                raise PermissionDenied(
                    message="Platform authority required",
                    action="dismiss", resource="Transaction",
                )
            if config.approval_permission and not actor_context.has_permission(
                config.approval_permission,
            ):
                raise PermissionDenied(
                    message=f"Missing permission: {config.approval_permission}",
                    action="dismiss", resource="Transaction",
                )

        else:
            raise PermissionDenied(
                message="Cannot dismiss with this approval policy",
                action="dismiss", resource="Transaction",
            )

    @staticmethod
    def can_approve_pending_review(
        *, transaction: Transaction, actor_context: ActorContext,
        config: TransactionTypeConfig,
    ) -> None:
        """Check if actor can approve a PENDING_REVIEW transaction (account authority)."""
        if transaction.status != TransactionStatus.PENDING_REVIEW:
            raise ValidationError(
                message=f"Transaction is not pending review (status: {transaction.status})",
                field="status",
            )

        # For invitations that went to PENDING_REVIEW, the account authority approves
        if actor_context.account_id != transaction.context_id:
            raise PermissionDenied(
                message="Not a member of the account this transaction belongs to",
                action="approve",
                resource="Transaction",
            )

        # Check for approval permission if configured, or fall back to can_approve_membership_request
        perm = config.approval_permission or "can_approve_membership_request"
        if not actor_context.has_permission(perm) and not actor_context.is_owner:
            raise PermissionDenied(
                message=f"Missing permission: {perm}",
                action="approve",
                resource="Transaction",
            )

    @staticmethod
    def is_initiator(
        *, transaction: Transaction, actor_context: ActorContext,
    ) -> None:
        initiator_context = ActorContext.from_dict(transaction.initiator_context)
        if actor_context.user_id != initiator_context.user_id:
            raise PermissionDenied(
                message="Only the initiator can perform this action",
                action="modify",
                resource="Transaction",
            )

    @staticmethod
    def can_view(
        *, transaction: Transaction, actor_context: ActorContext,
    ) -> None:
        initiator_context = ActorContext.from_dict(transaction.initiator_context)

        # Initiator can always view
        if actor_context.user_id == initiator_context.user_id:
            return
        # Target user can view
        if (transaction.target_type == PartyType.USER
                and actor_context.user_id == transaction.target_id):
            return
        # Account member with permission can view
        if (actor_context.account_id == transaction.context_id
                and actor_context.account_type == transaction.context_type):
            if actor_context.is_owner:
                return
            if actor_context.has_permission("can_view_transactions"):
                return
        # Platform authority with global permission
        if actor_context.account_type == "platform":
            if actor_context.has_global_permission("can_view_all_transactions"):
                return

        raise PermissionDenied(
            message="Not authorized to view this transaction",
            action="view",
            resource="Transaction",
        )

    @staticmethod
    def get_viewer_permissions(
        *, transaction: Transaction, actor_context: ActorContext,
    ) -> dict:
        """Return permission booleans for Tier 1.5 _permissions injection."""
        config = get_transaction_type(transaction.transaction_type)
        initiator_ctx = ActorContext.from_dict(transaction.initiator_context)
        is_initiator = actor_context.user_id == initiator_ctx.user_id
        is_target = (
            transaction.target_type == PartyType.USER
            and actor_context.user_id == transaction.target_id
        )
        is_pending = transaction.status == TransactionStatus.PENDING
        is_pending_review = transaction.status == TransactionStatus.PENDING_REVIEW
        is_info_requested = transaction.status == TransactionStatus.INFO_REQUESTED

        def _safe_can_accept():
            try:
                TransactionPolicy.can_accept(
                    transaction=transaction,
                    actor_context=actor_context,
                    config=config,
                )
                return True
            except (PermissionDenied, ValidationError):
                return False

        def _safe_can_approve():
            try:
                TransactionPolicy.can_approve_pending_review(
                    transaction=transaction,
                    actor_context=actor_context,
                    config=config,
                )
                return True
            except (PermissionDenied, ValidationError):
                return False

        can_accept = _safe_can_accept() if is_pending else False
        can_approve = _safe_can_approve() if is_pending_review else False

        # has_authority: whether user has the role to manage this transaction
        # (ignoring current status). Used for dismiss on terminal states.
        def _check_authority() -> bool:
            policy = config.approver_policy
            if policy == ApproverPolicy.TARGET_ACCEPTANCE:
                return (
                    transaction.target_type == PartyType.USER
                    and actor_context.user_id == transaction.target_id
                )
            if policy == ApproverPolicy.ACCOUNT_AUTHORITY:
                return (
                    actor_context.account_id == transaction.context_id
                    and (
                        not config.approval_permission
                        or actor_context.has_permission(config.approval_permission)
                    )
                )
            if policy == ApproverPolicy.PLATFORM_AUTHORITY:
                return (
                    actor_context.account_type == "platform"
                    and (
                        not config.approval_permission
                        or actor_context.has_permission(config.approval_permission)
                    )
                )
            return False

        has_authority = can_accept if is_pending else _check_authority()

        # For invitations in INFO_REQUESTED, the target user can resubmit
        can_resubmit_invitation = (
            is_info_requested
            and transaction.mode == "invitation"
            and is_target
        )

        return {
            "can_accept": can_accept,
            "can_deny": can_accept or can_approve,
            "can_approve": can_approve,
            "can_cancel": (
                (is_initiator and is_pending)
                or (is_pending_review and (is_initiator or is_target))
            ),
            "can_dismiss": has_authority and transaction.status in (
                TransactionStatus.ACCEPTED, TransactionStatus.DENIED,
            ),
            "can_request_info": (
                (can_accept or can_approve)
                and (is_pending or is_pending_review)
                and transaction.form_response_id is not None
            ),
            "can_resubmit": (
                (is_initiator and is_info_requested)
                or can_resubmit_invitation
            ),
            "can_view_form": transaction.form_response_id is not None,
        }
