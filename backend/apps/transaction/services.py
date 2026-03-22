"""
Transaction Service — state machine for membership and network transactions.

Manages the full lifecycle of transactions: creation (invitations, requests),
state transitions (accept, deny, cancel, expire), form requirements
(info-request/resubmit), and outcome execution via OutcomeHandlerRegistry.

Key methods:
    create_invitation — create an invitation transaction (initiator invites target)
    create_request — create a request transaction (initiator requests to join)
    accept — accept a pending transaction (may trigger PENDING_REVIEW if form-required)
    approve_pending_review — approve a transaction in PENDING_REVIEW status
    deny — deny a pending/pending_review transaction
    cancel — cancel a transaction (by the initiator)
    dismiss — dismiss a transaction (by the target)
    expire — expire a transaction past its deadline
    invalidate — force-invalidate a transaction with reason
    request_info — move transaction to INFO_REQUESTED (form needed)
    resubmit_after_info_request — resubmit with updated form response

Guards:
    _check_member_quota — enforce member limits before creating membership transactions
    _check_open_member_request — prevent duplicate requests when requests are closed
    _validate_role_level_for_membership — ensure role assignment is valid

All public methods use @staticmethod + @transaction.atomic with keyword-only args.
"""
from datetime import timedelta
from typing import Any, Dict
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.core.constants import AccountType, MembershipStatus
from apps.core.exceptions import (
    BusinessRuleViolation,
    ConflictError,
    NotFound,
    ValidationError,
)
from apps.core.observability import AuditService, get_logger
from apps.core.observability.audit.models import AuditLog
from apps.core.types import ActorContext
from apps.transaction.constants import (
    TERMINAL_STATES,
    ApproverPolicy,
    PartyType,
    TransactionMode,
    TransactionStatus,
)
from apps.transaction.models import Transaction, TransactionLog
from apps.transaction.outcome_handlers import OutcomeHandlerRegistry
from apps.transaction.policies import TransactionPolicy
from apps.transaction.selectors import TransactionSelector
from apps.transaction.types import get_transaction_type

User = get_user_model()
logger = get_logger(__name__)


def _resolve_actor(actor_context: ActorContext):
    """Resolve User object from ActorContext for AuditService.log(actor=...)."""
    if not actor_context or not actor_context.user_id:
        return None
    try:
        return User.objects.get(id=actor_context.user_id)
    except User.DoesNotExist:
        return None


class TransactionService:

    # =========================================================================
    # CREATION
    # =========================================================================

    @staticmethod
    @db_transaction.atomic
    def create_invitation(
        *,
        transaction_type: str,
        initiator_context: ActorContext,
        target_user_id: UUID,
        payload: Dict[str, Any] | None = None,
        form_response_id: UUID | None = None,
        request: HttpRequest | None = None,
    ) -> Transaction:
        """Create invitation. Transitions CREATED -> PENDING atomically."""
        config = get_transaction_type(transaction_type)

        if config.mode != TransactionMode.INVITATION:
            raise ValidationError(
                message=f"{transaction_type} is not an invitation type",
                field="transaction_type",
            )
        if not config.enabled:
            raise ValidationError(
                message=f"Transaction type {transaction_type} is disabled",
                field="transaction_type",
            )

        TransactionPolicy.can_create_invitation(
            actor_context=initiator_context,
            config=config,
        )

        if TransactionSelector.exists_active(
            transaction_type=transaction_type,
            initiator_id=initiator_context.membership_id or initiator_context.user_id,
            target_id=target_user_id,
        ):
            raise ConflictError(
                message="An active transaction already exists for this target",
                resource="Transaction",
                conflict_type="duplicate",
            )

        # Cross-type conflict check (e.g., pending request blocks invitation)
        if config.conflict_group and initiator_context.account_id:
            conflicting = TransactionSelector.has_active_in_conflict_group(
                conflict_group=config.conflict_group,
                user_id=target_user_id,
                context_type=config.context_type,
                context_id=initiator_context.account_id,
            )
            if conflicting:
                raise ConflictError(
                    message=(
                        f"A conflicting active transaction already exists: "
                        f"{conflicting.transaction_type} ({conflicting.status})"
                    ),
                    resource="Transaction",
                    conflict_type="cross_type_duplicate",
                )

        # Check if target user is already an active member of the context account
        # Only applies to membership invitation types (not ownership transfers)
        is_membership_invitation = (
            "MembershipOutcomeHandler.handle_invitation_accepted"
            in (config.outcome_handler or "")
        )
        if is_membership_invitation and config.context_type not in ("user", None):
            from apps.rbac.selectors import MembershipSelector

            existing_membership = (
                MembershipSelector.get_active_membership_for_user_account(
                    user=User.objects.filter(id=target_user_id).first(),
                    account_type=config.context_type,
                    account_id=initiator_context.account_id,
                )
            )
            if existing_membership:
                raise ConflictError(
                    message="Target user is already an active member of this account",
                    resource="Transaction",
                    conflict_type="existing_membership",
                )

        # Quota pre-check for membership invitations
        if is_membership_invitation and config.context_type not in ("user", None):
            TransactionService._check_member_quota(
                account_type=config.context_type,
                account_id=initiator_context.account_id,
            )

        TransactionService._validate_payload(config, payload or {})
        TransactionService._validate_form_requirement(
            config=config,
            form_response_id=form_response_id,
        )

        # Role level validation for membership invitations
        role_id_from_payload = (payload or {}).get("role_id")
        if is_membership_invitation and role_id_from_payload:
            TransactionService._validate_role_level_for_membership(
                actor_context=initiator_context,
                role_id_str=str(role_id_from_payload),
                account_type=config.context_type,
                account_id=initiator_context.account_id,
            )

        context_id = (
            initiator_context.account_id if config.context_type != "user" else None
        )

        txn = Transaction.objects.create_transaction(
            transaction_type=transaction_type,
            mode=TransactionMode.INVITATION,
            initiator_type=PartyType.MEMBERSHIP_ACTOR,
            initiator_id=initiator_context.membership_id or initiator_context.user_id,
            initiator_context=initiator_context.to_dict(),
            target_type=PartyType.USER,
            target_id=target_user_id,
            context_type=config.context_type,
            context_id=context_id,
            payload=payload or {},
            form_response_id=form_response_id,
            expires_at=timezone.now() + timedelta(days=config.expiration_days),
            created_by=_resolve_actor(initiator_context),
        )

        # Bidirectional form linking
        if form_response_id:
            TransactionService._link_form_response(
                form_response_id=form_response_id,
                transaction_id=txn.id,
            )

        TransactionService._log_event(
            transaction=txn,
            event_type="created",
            actor_context=initiator_context,
            new_status=TransactionStatus.CREATED,
        )
        txn = TransactionService._transition(
            transaction=txn,
            new_status=TransactionStatus.PENDING,
            actor_context=initiator_context,
        )

        AuditService.log(
            action=AuditLog.Action.TRANSACTION_CREATED,
            actor=_resolve_actor(initiator_context),
            resource=txn,
            request=request,
            details={
                "transaction_type": transaction_type,
                "mode": "invitation",
                "target_id": str(target_user_id),
            },
        )

        db_transaction.on_commit(
            lambda: TransactionService._notify_safe("invitation_created", txn),
        )
        return txn

    @staticmethod
    @db_transaction.atomic
    def create_request(
        *,
        transaction_type: str,
        user_id: UUID,
        target_account_type: str = None,
        target_account_id: UUID = None,
        target_user_id: UUID = None,
        payload: Dict[str, Any] | None = None,
        form_response_id: UUID | None = None,
        request: HttpRequest | None = None,
    ) -> Transaction:
        """Create request. Transitions CREATED -> PENDING atomically.

        For account-targeted requests (membership, follow, verification):
            Pass target_account_type + target_account_id.
        For user-targeted requests (connection):
            Pass target_user_id.
        """
        config = get_transaction_type(transaction_type)

        if config.mode != TransactionMode.REQUEST:
            raise ValidationError(
                message=f"{transaction_type} is not a request type",
                field="transaction_type",
            )
        if not config.enabled:
            raise ValidationError(
                message=f"Transaction type {transaction_type} is disabled",
                field="transaction_type",
            )

        user = User.objects.filter(id=user_id).first()
        if not user:
            raise NotFound(resource="User", resource_id=str(user_id))

        # Determine target type and ID from config
        if PartyType.USER in config.target_types:
            if not target_user_id:
                raise ValidationError(
                    message="target_user_id is required for user-targeted requests",
                    field="target_user_id",
                )
            target_type = PartyType.USER
            target_id = target_user_id
        else:
            if not target_account_id:
                raise ValidationError(
                    message="target_account_id is required for account-targeted requests",
                    field="target_account_id",
                )
            target_type = PartyType.ACCOUNT
            target_id = target_account_id

        if TransactionSelector.exists_active(
            transaction_type=transaction_type,
            initiator_id=user_id,
            target_id=target_id,
        ):
            raise ConflictError(
                message="You already have an active request",
                resource="Transaction",
                conflict_type="duplicate",
            )

        # Cross-type conflict check (e.g., pending invitation blocks request)
        if (
            config.conflict_group
            and target_type == PartyType.ACCOUNT
            and target_account_id
        ):
            conflicting = TransactionSelector.has_active_in_conflict_group(
                conflict_group=config.conflict_group,
                user_id=user_id,
                context_type=config.context_type,
                context_id=target_account_id,
            )
            if conflicting:
                raise ConflictError(
                    message=(
                        f"A conflicting active transaction already exists: "
                        f"{conflicting.transaction_type} ({conflicting.status})"
                    ),
                    resource="Transaction",
                    conflict_type="cross_type_duplicate",
                )

        cooldown_end = TransactionSelector.get_resubmission_cooldown(
            transaction_type=transaction_type,
            initiator_id=user_id,
            target_id=target_id,
        )
        if cooldown_end:
            raise ValidationError(
                message=f"Cannot resubmit until {cooldown_end.isoformat()}",
                field="transaction_type",
            )

        # Pre-checks for membership requests
        is_membership_request = "MembershipOutcomeHandler.handle_request_approved" in (
            config.outcome_handler or ""
        )
        if is_membership_request and config.context_type not in ("user", None):
            context_id = target_account_id if config.context_type != "user" else None
            if context_id:
                TransactionService._check_open_member_request(
                    account_type=config.context_type,
                    account_id=context_id,
                )
                TransactionService._check_member_quota(
                    account_type=config.context_type,
                    account_id=context_id,
                )

        TransactionService._validate_payload(config, payload or {})
        TransactionService._validate_form_requirement(
            config=config,
            form_response_id=form_response_id,
        )

        # Check dynamic form mapping (TransactionFormMapping per account)
        if target_type == PartyType.ACCOUNT and target_account_id:
            TransactionService._validate_form_mapping_requirement(
                transaction_type=transaction_type,
                account_type=config.context_type,
                account_id=target_account_id,
                form_response_id=form_response_id,
            )

        actor_context = ActorContext.for_user_context(user, request)

        txn = Transaction.objects.create_transaction(
            transaction_type=transaction_type,
            mode=TransactionMode.REQUEST,
            initiator_type=PartyType.USER,
            initiator_id=user_id,
            initiator_context=actor_context.to_dict(),
            target_type=target_type,
            target_id=target_id,
            context_type=config.context_type,
            context_id=target_id if config.context_type != "user" else None,
            payload=payload or {},
            form_response_id=form_response_id,
            expires_at=timezone.now() + timedelta(days=config.expiration_days),
            created_by=user,
        )

        # Bidirectional form linking
        if form_response_id:
            TransactionService._link_form_response(
                form_response_id=form_response_id,
                transaction_id=txn.id,
            )

        TransactionService._log_event(
            transaction=txn,
            event_type="created",
            actor_context=actor_context,
            new_status=TransactionStatus.CREATED,
        )
        txn = TransactionService._transition(
            transaction=txn,
            new_status=TransactionStatus.PENDING,
            actor_context=actor_context,
        )

        # Dispatch on_create_handler (e.g., set verification_status to PENDING)
        TransactionService._execute_on_create(
            transaction=txn,
            actor_context=actor_context,
        )

        # AUTO_APPROVAL: auto-accept immediately (e.g., business_follow_request)
        if config.approver_policy == ApproverPolicy.AUTO_APPROVAL:
            system_context = ActorContext.for_system()
            txn = TransactionService._transition(
                transaction=txn,
                new_status=TransactionStatus.ACCEPTED,
                actor_context=system_context,
            )
            TransactionService._execute_outcome(
                transaction=txn,
                actor_context=system_context,
            )

        AuditService.log(
            action=AuditLog.Action.TRANSACTION_CREATED,
            actor=user,
            resource=txn,
            request=request,
            details={
                "transaction_type": transaction_type,
                "mode": "request",
                "target_id": str(target_id),
            },
        )

        db_transaction.on_commit(
            lambda: TransactionService._notify_safe("request_created", txn),
        )
        return txn

    # =========================================================================
    # STATE TRANSITIONS
    # =========================================================================

    @staticmethod
    @db_transaction.atomic
    def accept(
        *,
        transaction_id: UUID,
        actor_context: ActorContext,
        acceptance_payload: Dict[str, Any] | None = None,
        request: HttpRequest | None = None,
    ) -> Transaction:
        try:
            txn = Transaction.objects.select_for_update().get(id=transaction_id)
        except Transaction.DoesNotExist:
            raise NotFound(resource="Transaction", resource_id=str(transaction_id))
        config = get_transaction_type(txn.transaction_type)
        TransactionPolicy.can_accept(
            transaction=txn,
            actor_context=actor_context,
            config=config,
        )

        if txn.mode == TransactionMode.INVITATION:
            TransactionService._validate_creator_authority(txn)

        # Role level validation for membership approvals with acceptance-time role_id
        ap = acceptance_payload or {}
        is_membership = "MembershipOutcomeHandler" in (config.outcome_handler or "")
        if is_membership and ap.get("role_id") and actor_context.role_level is not None:
            TransactionService._validate_role_level_for_membership(
                actor_context=actor_context,
                role_id_str=str(ap["role_id"]),
                account_type=txn.context_type,
                account_id=txn.context_id,
            )

        # Link form response if provided at accept time
        form_response_id = ap.get("form_response_id")
        if form_response_id and not txn.form_response_id:
            txn.form_response_id = form_response_id
            txn.save(update_fields=["form_response_id", "updated_at"])

        # Validate form requirement from TransactionFormMapping
        mapping = TransactionSelector.get_form_mapping_for_transaction(
            transaction=txn,
        )
        if mapping and mapping.is_required and not txn.form_response_id:
            raise ValidationError(
                message="A form response is required before accepting this transaction",
                field="form_response_id",
            )

        # Check if this invitation needs form review before finalizing
        needs_form_review = (
            txn.mode == TransactionMode.INVITATION
            and is_membership
            and txn.form_response_id is not None
            and mapping is not None
        )

        if needs_form_review:
            # Phase 1: User accepted invitation — needs business review
            txn = TransactionService._transition(
                transaction=txn,
                new_status=TransactionStatus.PENDING_REVIEW,
                actor_context=actor_context,
            )

            # Create provisional PENDING_APPROVAL membership
            TransactionService._create_pending_approval_membership(
                transaction=txn,
                actor_context=actor_context,
            )

            AuditService.log(
                action=AuditLog.Action.TRANSACTION_PENDING_REVIEW,
                actor=_resolve_actor(actor_context),
                resource=txn,
                request=request,
            )
            db_transaction.on_commit(
                lambda: TransactionService._notify_safe("pending_review", txn),
            )
            return txn

        # Standard flow: PENDING -> ACCEPTED
        txn = TransactionService._transition(
            transaction=txn,
            new_status=TransactionStatus.ACCEPTED,
            actor_context=actor_context,
            resolved_by_id=actor_context.user_id,
        )
        AuditService.log(
            action=AuditLog.Action.TRANSACTION_ACCEPTED,
            actor=_resolve_actor(actor_context),
            resource=txn,
            request=request,
        )
        TransactionService._execute_outcome(
            transaction=txn,
            actor_context=actor_context,
            acceptance_payload=acceptance_payload,
        )
        db_transaction.on_commit(
            lambda: TransactionService._notify_safe("accepted", txn),
        )
        return txn

    @staticmethod
    @db_transaction.atomic
    def approve_pending_review(
        *,
        transaction_id: UUID,
        actor_context: ActorContext,
        request: HttpRequest | None = None,
    ) -> Transaction:
        """Business approves form submission. PENDING_REVIEW -> ACCEPTED."""
        try:
            txn = Transaction.objects.select_for_update().get(id=transaction_id)
        except Transaction.DoesNotExist:
            raise NotFound(resource="Transaction", resource_id=str(transaction_id))
        config = get_transaction_type(txn.transaction_type)

        TransactionPolicy.can_approve_pending_review(
            transaction=txn,
            actor_context=actor_context,
            config=config,
        )

        # Transition to ACCEPTED
        txn = TransactionService._transition(
            transaction=txn,
            new_status=TransactionStatus.ACCEPTED,
            actor_context=actor_context,
            resolved_by_id=actor_context.user_id,
        )

        # Activate the PENDING_APPROVAL membership
        TransactionService._activate_pending_membership(
            transaction=txn,
            actor_context=actor_context,
        )

        # Mark outcome as executed
        txn.outcome_executed = True
        txn.outcome_executed_at = timezone.now()
        txn.save(update_fields=["outcome_executed", "outcome_executed_at"])

        AuditService.log(
            action=AuditLog.Action.TRANSACTION_REVIEW_APPROVED,
            actor=_resolve_actor(actor_context),
            resource=txn,
            request=request,
        )

        db_transaction.on_commit(
            lambda: TransactionService._notify_safe("accepted", txn),
        )
        return txn

    @staticmethod
    @db_transaction.atomic
    def deny(
        *,
        transaction_id: UUID,
        actor_context: ActorContext,
        reason: str = "",
        request: HttpRequest | None = None,
    ) -> Transaction:
        try:
            txn = Transaction.objects.select_for_update().get(id=transaction_id)
        except Transaction.DoesNotExist:
            raise NotFound(resource="Transaction", resource_id=str(transaction_id))
        config = get_transaction_type(txn.transaction_type)
        was_pending_review = txn.status == TransactionStatus.PENDING_REVIEW
        TransactionPolicy.can_deny(
            transaction=txn,
            actor_context=actor_context,
            config=config,
        )

        txn = TransactionService._transition(
            transaction=txn,
            new_status=TransactionStatus.DENIED,
            actor_context=actor_context,
            resolved_by_id=actor_context.user_id,
            resolution_reason=reason,
        )

        # Clean up PENDING_APPROVAL membership if denying from PENDING_REVIEW
        if was_pending_review:
            TransactionService._revoke_pending_membership(transaction=txn)

        # Dispatch on_close_handler (e.g., revert verification_status)
        TransactionService._execute_on_close(
            transaction=txn,
            actor_context=actor_context,
            terminal_status=TransactionStatus.DENIED,
        )

        AuditService.log(
            action=AuditLog.Action.TRANSACTION_DENIED,
            actor=_resolve_actor(actor_context),
            resource=txn,
            request=request,
            details={"reason": reason},
        )
        db_transaction.on_commit(
            lambda: TransactionService._notify_safe("denied", txn),
        )
        return txn

    @staticmethod
    @db_transaction.atomic
    def dismiss(
        *,
        transaction_id: UUID,
        actor_context: ActorContext,
        request: HttpRequest | None = None,
    ) -> Transaction:
        try:
            txn = Transaction.objects.select_for_update().get(id=transaction_id)
        except Transaction.DoesNotExist:
            raise NotFound(resource="Transaction", resource_id=str(transaction_id))
        if txn.mode != TransactionMode.REQUEST:
            raise ValidationError(
                message="Only requests can be dismissed",
                field="transaction_id",
            )
        if txn.status not in (
            TransactionStatus.ACCEPTED,
            TransactionStatus.DENIED,
        ):
            raise ValidationError(
                message=f"Cannot dismiss transaction in status: {txn.status}",
                field="status",
            )
        config = get_transaction_type(txn.transaction_type)
        TransactionPolicy.can_dismiss(
            transaction=txn,
            actor_context=actor_context,
            config=config,
        )

        txn = TransactionService._transition(
            transaction=txn,
            new_status=TransactionStatus.DISMISSED,
            actor_context=actor_context,
            resolved_by_id=actor_context.user_id,
        )
        AuditService.log(
            action=AuditLog.Action.TRANSACTION_DISMISSED,
            actor=_resolve_actor(actor_context),
            resource=txn,
            request=request,
        )
        return txn

    @staticmethod
    @db_transaction.atomic
    def cancel(
        *,
        transaction_id: UUID,
        actor_context: ActorContext,
        request: HttpRequest | None = None,
    ) -> Transaction:
        try:
            txn = Transaction.objects.select_for_update().get(id=transaction_id)
        except Transaction.DoesNotExist:
            raise NotFound(resource="Transaction", resource_id=str(transaction_id))
        was_pending_review = txn.status == TransactionStatus.PENDING_REVIEW

        # For PENDING_REVIEW invitations, either initiator or target can cancel
        if was_pending_review and txn.mode == TransactionMode.INVITATION:
            initiator_ctx = ActorContext.from_dict(txn.initiator_context)
            is_initiator = actor_context.user_id == initiator_ctx.user_id
            is_target = actor_context.user_id == txn.target_id
            if not is_initiator and not is_target:
                from apps.core.exceptions import PermissionDenied

                raise PermissionDenied(
                    message="Only the initiator or target can cancel this transaction",
                    action="cancel",
                    resource="Transaction",
                )
        else:
            TransactionPolicy.is_initiator(
                transaction=txn,
                actor_context=actor_context,
            )

        if txn.status not in (
            TransactionStatus.PENDING,
            TransactionStatus.PENDING_REVIEW,
        ):
            raise ValidationError(
                message="Can only cancel pending transactions",
                field="status",
            )

        txn = TransactionService._transition(
            transaction=txn,
            new_status=TransactionStatus.CANCELLED,
            actor_context=actor_context,
            resolved_by_id=actor_context.user_id,
        )

        # Clean up PENDING_APPROVAL membership if cancelling from PENDING_REVIEW
        if was_pending_review:
            TransactionService._revoke_pending_membership(transaction=txn)

        # Dispatch on_close_handler (e.g., revert verification_status)
        TransactionService._execute_on_close(
            transaction=txn,
            actor_context=actor_context,
            terminal_status=TransactionStatus.CANCELLED,
        )

        AuditService.log(
            action=AuditLog.Action.TRANSACTION_CANCELLED,
            actor=_resolve_actor(actor_context),
            resource=txn,
            request=request,
        )
        db_transaction.on_commit(
            lambda: TransactionService._notify_safe("cancelled", txn),
        )
        return txn

    @staticmethod
    @db_transaction.atomic
    def expire(*, transaction_id: UUID) -> Transaction:
        try:
            txn = Transaction.objects.select_for_update().get(id=transaction_id)
        except Transaction.DoesNotExist:
            raise NotFound(resource="Transaction", resource_id=str(transaction_id))
        if txn.is_terminal:
            return txn
        system_context = ActorContext.for_system()
        txn = TransactionService._transition(
            transaction=txn,
            new_status=TransactionStatus.EXPIRED,
            actor_context=system_context,
        )
        db_transaction.on_commit(
            lambda: TransactionService._notify_safe("expired", txn),
        )
        return txn

    @staticmethod
    @db_transaction.atomic
    def invalidate(*, transaction_id: UUID, reason: str) -> Transaction:
        try:
            txn = Transaction.objects.select_for_update().get(id=transaction_id)
        except Transaction.DoesNotExist:
            raise NotFound(resource="Transaction", resource_id=str(transaction_id))
        if txn.is_terminal:
            return txn
        system_context = ActorContext.for_system()
        txn = TransactionService._transition(
            transaction=txn,
            new_status=TransactionStatus.INVALIDATED,
            actor_context=system_context,
            resolution_reason=reason,
        )
        logger.warning(
            "transaction.invalidated",
            transaction_id=str(txn.id),
            reason=reason,
        )
        return txn

    # =========================================================================
    # INFO REQUEST FLOW
    # =========================================================================

    @staticmethod
    @db_transaction.atomic
    def request_info(
        *,
        transaction_id: UUID,
        message: str,
        requested_fields: list | None = None,
        actor_context: ActorContext,
        request: HttpRequest | None = None,
    ) -> Transaction:
        """Request additional info. PENDING/PENDING_REVIEW -> INFO_REQUESTED."""
        try:
            txn = Transaction.objects.select_for_update().get(id=transaction_id)
        except Transaction.DoesNotExist:
            raise NotFound(resource="Transaction", resource_id=str(transaction_id))
        config = get_transaction_type(txn.transaction_type)

        if txn.status not in (
            TransactionStatus.PENDING,
            TransactionStatus.PENDING_REVIEW,
        ):
            raise ValidationError(
                message=f"Cannot request info on transaction in {txn.status} status",
                field="status",
            )

        if not txn.form_response_id:
            raise ValidationError(
                message="Cannot request info on transaction without form response",
                field="form_response_id",
            )

        # For PENDING_REVIEW, use approve policy (ACCOUNT_AUTHORITY)
        if txn.status == TransactionStatus.PENDING_REVIEW:
            TransactionPolicy.can_approve_pending_review(
                transaction=txn,
                actor_context=actor_context,
                config=config,
            )
        else:
            TransactionPolicy.can_accept(
                transaction=txn,
                actor_context=actor_context,
                config=config,
            )

        # Validate requested fields exist in form template
        if requested_fields:
            from apps.forms.selectors import FormResponseSelector

            form_response = FormResponseSelector.get_by_id(
                response_id=txn.form_response_id,
            )
            valid_keys = set(
                form_response.form_template.fields.values_list("field_key", flat=True)
            )
            invalid_keys = set(requested_fields) - valid_keys
            if invalid_keys:
                raise ValidationError(
                    message=f"Invalid field keys: {invalid_keys}",
                    field="requested_fields",
                )

        # Set info request fields before transition (save() will persist all)
        actor = _resolve_actor(actor_context)
        txn.info_requested_at = timezone.now()
        txn.info_requested_by = actor
        txn.info_requested_message = message
        txn.info_requested_fields = requested_fields or []

        txn = TransactionService._transition(
            transaction=txn,
            new_status=TransactionStatus.INFO_REQUESTED,
            actor_context=actor_context,
        )

        # Update FormResponse
        from apps.forms.services import FormResponseService

        FormResponseService.mark_info_requested(
            response_id=txn.form_response_id,
            actor=actor,
        )

        AuditService.log(
            action=AuditLog.Action.TRANSACTION_INFO_REQUESTED,
            actor=actor,
            resource=txn,
            request=request,
            details={
                "message": message,
                "requested_fields": requested_fields or [],
            },
        )

        db_transaction.on_commit(
            lambda: TransactionService._notify_safe("info_requested", txn),
        )

        logger.info(
            "transaction.info_requested",
            transaction_id=str(txn.id),
        )
        return txn

    @staticmethod
    @db_transaction.atomic
    def resubmit_after_info_request(
        *,
        transaction_id: UUID,
        actor_context: ActorContext,
        request: HttpRequest | None = None,
    ) -> Transaction:
        """Resubmit transaction after updating form response.

        INFO_REQUESTED -> PENDING (requests) or PENDING_REVIEW (invitations with form).
        """
        try:
            txn = Transaction.objects.select_for_update().get(id=transaction_id)
        except Transaction.DoesNotExist:
            raise NotFound(resource="Transaction", resource_id=str(transaction_id))

        if txn.status != TransactionStatus.INFO_REQUESTED:
            raise ValidationError(
                message=f"Cannot resubmit transaction in {txn.status} status",
                field="status",
            )

        # For invitations, target user resubmits (they're the form filler)
        if txn.mode == TransactionMode.INVITATION:
            if actor_context.user_id != txn.target_id:
                from apps.core.exceptions import PermissionDenied

                raise PermissionDenied(
                    message="Only the target user can resubmit",
                    action="resubmit",
                    resource="Transaction",
                )
        else:
            TransactionPolicy.is_initiator(
                transaction=txn,
                actor_context=actor_context,
            )

        # Invitations with form go back to PENDING_REVIEW, requests go to PENDING
        mapping = TransactionSelector.get_form_mapping_for_transaction(transaction=txn)
        if txn.mode == TransactionMode.INVITATION and mapping and txn.form_response_id:
            new_status = TransactionStatus.PENDING_REVIEW
        else:
            new_status = TransactionStatus.PENDING

        txn = TransactionService._transition(
            transaction=txn,
            new_status=new_status,
            actor_context=actor_context,
        )

        AuditService.log(
            action=AuditLog.Action.TRANSACTION_RESUBMITTED,
            actor=_resolve_actor(actor_context),
            resource=txn,
            request=request,
        )

        db_transaction.on_commit(
            lambda: TransactionService._notify_safe("resubmitted", txn),
        )

        logger.info(
            "transaction.resubmitted",
            transaction_id=str(txn.id),
        )
        return txn

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    @staticmethod
    def _check_member_quota(*, account_type: str, account_id: UUID):
        """Pre-check: raise if account is at member capacity.

        Counts active members PLUS pending membership transactions
        (invitations and requests that haven't been resolved yet).
        The hard gate lives in RBACService.create_membership().
        """
        from apps.rbac.selectors import MembershipSelector

        active_count = MembershipSelector.count_active_members(
            account_type=account_type,
            account_id=account_id,
        )

        # Count pending membership transactions (invitations + requests)
        pending_count = (
            Transaction.objects.filter(
                context_type=account_type,
                context_id=account_id,
                transaction_type__contains="membership",
            )
            .exclude(
                status__in=TERMINAL_STATES,
            )
            .count()
        )

        total_committed = active_count + pending_count

        if account_type == "business":
            from apps.organization.business.models import BusinessAccount

            try:
                max_members = BusinessAccount.objects.values_list(
                    "max_members",
                    flat=True,
                ).get(id=account_id)
            except BusinessAccount.DoesNotExist:
                return
        elif account_type == "platform":
            from apps.organization.platform.models import PlatformAccount

            try:
                max_members = PlatformAccount.objects.values_list(
                    "max_members",
                    flat=True,
                ).get(id=account_id)
            except PlatformAccount.DoesNotExist:
                return
        else:
            return

        if max_members > 0 and total_committed >= max_members:
            raise BusinessRuleViolation(
                message=(
                    f"Account has reached its maximum member limit ({max_members}). "
                    f"Active members: {active_count}, pending invitations/requests: {pending_count}."
                ),
                rule="member_quota_exceeded",
            )

    @staticmethod
    def _check_open_member_request(*, account_type: str, account_id: UUID):
        """Pre-check: raise if account does not accept membership requests."""
        if account_type == "business":
            from apps.organization.business.models import BusinessAccount

            try:
                is_open = BusinessAccount.objects.values_list(
                    "open_member_request",
                    flat=True,
                ).get(id=account_id)
            except BusinessAccount.DoesNotExist:
                return
        elif account_type == "platform":
            from apps.organization.platform.models import PlatformAccount

            try:
                is_open = PlatformAccount.objects.values_list(
                    "open_member_request",
                    flat=True,
                ).get(id=account_id)
            except PlatformAccount.DoesNotExist:
                return
        else:
            return

        if not is_open:
            raise BusinessRuleViolation(
                message="This organization is not accepting membership requests.",
                rule="member_requests_closed",
            )

    @staticmethod
    def _validate_role_level_for_membership(
        *,
        actor_context: ActorContext,
        role_id_str: str,
        account_type: str,
        account_id: UUID,
    ):
        """Validate that actor outranks the role being assigned.

        Used for membership invitations (create-time) and membership
        request approvals (accept-time).
        """
        from apps.rbac.models import Role

        try:
            role = Role.objects.get(id=role_id_str)
        except (Role.DoesNotExist, ValueError):
            raise ValidationError(
                message=f"Role not found: {role_id_str}",
                field="role_id",
            )

        if role.level == 0:
            raise BusinessRuleViolation(
                message="Owner role cannot be assigned via transactions. "
                "Use ownership transfer instead.",
                rule="owner_role_not_assignable",
            )

        if str(role.account_id) != str(account_id) or role.account_type != account_type:
            raise ValidationError(
                message="Role does not belong to this account",
                field="role_id",
            )

        if (
            actor_context.role_level is not None
            and actor_context.role_level >= role.level
        ):
            raise BusinessRuleViolation(
                message="Cannot assign a role with equal or higher authority than your own",
                rule="insufficient_role_level",
            )

    @staticmethod
    def _transition(
        *,
        transaction,
        new_status,
        actor_context,
        resolved_by_id=None,
        resolution_reason="",
    ):
        if not transaction.can_transition_to(new_status):
            raise ValidationError(
                message=f"Invalid transition from {transaction.status} to {new_status}",
                field="status",
            )
        previous_status = transaction.status
        transaction.status = new_status
        if new_status in TERMINAL_STATES:
            transaction.resolved_at = timezone.now()
            if resolved_by_id:
                transaction.resolved_by_id = resolved_by_id
            if resolution_reason:
                transaction.resolution_reason = resolution_reason
        transaction.save()
        TransactionService._log_event(
            transaction=transaction,
            event_type="state_changed",
            actor_context=actor_context,
            previous_status=previous_status,
            new_status=new_status,
        )
        return transaction

    @staticmethod
    def _log_event(
        *,
        transaction,
        event_type,
        actor_context,
        previous_status="",
        new_status,
        metadata=None,
    ):
        return TransactionLog.objects.create(
            transaction=transaction,
            event_type=event_type,
            actor_context=actor_context.to_dict(),
            previous_status=previous_status,
            new_status=new_status,
            metadata=metadata or {},
        )

    @staticmethod
    def _validate_payload(config, payload):
        for field_name, rules in config.payload_schema.items():
            value = payload.get(field_name)
            if rules.get("required") and value is None:
                raise ValidationError(
                    message=f"Field '{field_name}' is required",
                    field=field_name,
                )
            if value is not None:
                if rules.get("type") == "string" and not isinstance(value, str):
                    raise ValidationError(
                        message=f"Field '{field_name}' must be a string",
                        field=field_name,
                    )
                max_len = rules.get("max_length")
                if max_len and isinstance(value, str) and len(value) > max_len:
                    raise ValidationError(
                        message=f"Field '{field_name}' exceeds max length {max_len}",
                        field=field_name,
                    )

    @staticmethod
    def _validate_form_requirement(*, config, form_response_id):
        """Validate form requirement for a transaction type."""
        requires = (
            config.required_form_template_slug or config.required_form_template_id
        )
        if requires and not form_response_id:
            raise ValidationError(
                message="This transaction type requires a form response",
                field="form_response_id",
            )
        if form_response_id and config.required_form_template_slug:
            from apps.forms.selectors import FormResponseSelector

            response = FormResponseSelector.get_by_id(response_id=form_response_id)
            if response.form_template.slug != config.required_form_template_slug:
                raise ValidationError(
                    message=f"Form response must use template '{config.required_form_template_slug}'",
                    field="form_response_id",
                )

    @staticmethod
    def _validate_form_mapping_requirement(
        *,
        transaction_type,
        account_type,
        account_id,
        form_response_id,
    ):
        """Validate dynamic form mapping requirement (TransactionFormMapping per account).

        If the account has configured a required form mapping for this transaction type,
        the form_response_id must be provided at request creation time.
        """
        from apps.transaction.models import TransactionFormMapping

        mapping = TransactionFormMapping.objects.filter(
            account_type=account_type,
            account_id=account_id,
            transaction_type=transaction_type,
            is_deleted=False,
        ).first()
        if mapping and mapping.is_required and not form_response_id:
            raise BusinessRuleViolation(
                message="This organization requires a form to be filled before submitting a request.",
                rule="form_response_required",
            )

    @staticmethod
    def _link_form_response(*, form_response_id, transaction_id):
        """Set bidirectional link from FormResponse to Transaction."""
        from apps.forms.services import FormResponseService

        FormResponseService.link_to_transaction(
            response_id=form_response_id,
            transaction_id=transaction_id,
        )

    @staticmethod
    def _create_pending_approval_membership(*, transaction, actor_context):
        """Create a PENDING_APPROVAL membership for invitation acceptance with form."""
        from apps.rbac.services import RBACService

        user = User.objects.get(id=actor_context.user_id)
        initiator_ctx = ActorContext.from_dict(transaction.initiator_context)
        created_by = User.objects.filter(id=initiator_ctx.user_id).first()

        RBACService.create_membership(
            user=user,
            account_type=AccountType(transaction.context_type),
            account_id=transaction.context_id,
            role_id=transaction.payload.get("role_id"),
            created_by=created_by,
            status=MembershipStatus.PENDING_APPROVAL,
        )
        logger.info(
            "transaction.pending_approval_membership_created",
            transaction_id=str(transaction.id),
            user_id=str(actor_context.user_id),
        )

    @staticmethod
    def _activate_pending_membership(*, transaction, actor_context):
        """Activate a PENDING_APPROVAL membership when form is approved."""
        from apps.rbac.models import Membership

        user_id = transaction.target_id

        membership = Membership.objects.filter(
            user_id=user_id,
            account_type=transaction.context_type,
            account_id=transaction.context_id,
            status=MembershipStatus.PENDING_APPROVAL,
            is_deleted=False,
        ).first()

        if membership:
            membership.status = MembershipStatus.ACTIVE
            membership.status_changed_at = timezone.now()
            membership.status_changed_by = _resolve_actor(actor_context)
            membership.save(
                update_fields=[
                    "status",
                    "status_changed_at",
                    "status_changed_by",
                    "updated_at",
                ]
            )
            logger.info(
                "transaction.pending_membership_activated",
                transaction_id=str(transaction.id),
                membership_id=str(membership.id),
            )

    @staticmethod
    def _revoke_pending_membership(*, transaction):
        """Remove PENDING_APPROVAL membership when transaction is denied/cancelled."""
        from apps.rbac.models import Membership

        user_id = transaction.target_id

        membership = Membership.objects.filter(
            user_id=user_id,
            account_type=transaction.context_type,
            account_id=transaction.context_id,
            status=MembershipStatus.PENDING_APPROVAL,
            is_deleted=False,
        ).first()

        if membership:
            membership.soft_delete()
            logger.info(
                "transaction.pending_membership_revoked",
                transaction_id=str(transaction.id),
                membership_id=str(membership.id),
            )

    @staticmethod
    def _validate_creator_authority(transaction):
        """Re-validate creator still has authority at acceptance time."""
        from apps.rbac.selectors import MembershipSelector, PermissionSelector

        initiator_context = ActorContext.from_dict(transaction.initiator_context)
        config = get_transaction_type(transaction.transaction_type)

        if config.context_type == "user" or not initiator_context.membership_id:
            return

        try:
            membership = MembershipSelector.get_membership_by_id(
                membership_id=initiator_context.membership_id,
            )
        except NotFound:
            TransactionService.invalidate(
                transaction_id=transaction.id,
                reason="Creator membership no longer exists",
            )
            raise ValidationError(
                message="This invitation is no longer valid",
                field="transaction_id",
            )

        if membership.status != "active":
            TransactionService.invalidate(
                transaction_id=transaction.id,
                reason="Creator membership no longer active",
            )
            raise ValidationError(
                message="This invitation is no longer valid",
                field="transaction_id",
            )

        if config.required_permissions:
            current_perms = PermissionSelector.get_permissions_for_membership(
                membership_id=initiator_context.membership_id,
            )
            # get_permissions_for_membership returns List[Tuple[str, str]] (code, scope)
            current_codes = {code for code, scope in current_perms}
            for perm_code in config.required_permissions:
                if perm_code not in current_codes:
                    TransactionService.invalidate(
                        transaction_id=transaction.id,
                        reason=f"Creator lost permission: {perm_code}",
                    )
                    raise ValidationError(
                        message="This invitation is no longer valid",
                        field="transaction_id",
                    )

    @staticmethod
    def _execute_outcome(*, transaction, actor_context, acceptance_payload=None):
        config = get_transaction_type(transaction.transaction_type)
        if not config.outcome_handler:
            transaction.outcome_executed = True
            transaction.outcome_executed_at = timezone.now()
            transaction.save(
                update_fields=["outcome_executed", "outcome_executed_at"],
            )
            return
        try:
            OutcomeHandlerRegistry.execute(
                transaction=transaction,
                actor_context=actor_context,
                acceptance_payload=acceptance_payload,
            )
            transaction.outcome_executed = True
            transaction.outcome_executed_at = timezone.now()
            transaction.save(
                update_fields=["outcome_executed", "outcome_executed_at"],
            )
        except Exception as e:
            transaction.outcome_error = str(e)
            transaction.save(update_fields=["outcome_error"])
            logger.error(
                "transaction.outcome.failed",
                transaction_id=str(transaction.id),
                error=str(e),
            )
            raise

    @staticmethod
    def _execute_on_create(*, transaction, actor_context):
        """Dispatch on_create_handler if configured for this transaction type."""
        config = get_transaction_type(transaction.transaction_type)
        if not config.on_create_handler:
            return
        try:
            module_path, method_name = config.on_create_handler.rsplit(".", 1)
            class_path, class_name = module_path.rsplit(".", 1)
            import importlib

            mod = importlib.import_module(class_path)
            cls = getattr(mod, class_name)
            handler = getattr(cls, method_name)
            handler(transaction=transaction, actor_context=actor_context)
        except Exception as e:
            logger.error(
                "transaction.on_create_handler.failed",
                transaction_id=str(transaction.id),
                handler=config.on_create_handler,
                error=str(e),
            )

    @staticmethod
    def _execute_on_close(*, transaction, actor_context, terminal_status):
        """Dispatch on_close_handler if configured for this transaction type."""
        config = get_transaction_type(transaction.transaction_type)
        if not config.on_close_handler:
            return
        try:
            module_path, method_name = config.on_close_handler.rsplit(".", 1)
            class_path, class_name = module_path.rsplit(".", 1)
            import importlib

            mod = importlib.import_module(class_path)
            cls = getattr(mod, class_name)
            handler = getattr(cls, method_name)
            handler(
                transaction=transaction,
                actor_context=actor_context,
                terminal_status=terminal_status,
            )
        except Exception as e:
            logger.error(
                "transaction.on_close_handler.failed",
                transaction_id=str(transaction.id),
                handler=config.on_close_handler,
                error=str(e),
            )

    # =========================================================================
    # NOTIFICATIONS (graceful degradation)
    # =========================================================================

    @staticmethod
    def _notify_safe(event_type, transaction):
        try:
            from apps.notifications.services import NotificationService
        except ImportError:
            return
        try:
            handler = getattr(
                TransactionService,
                f"_notify_{event_type}",
                None,
            )
            if handler:
                handler(transaction, NotificationService)
        except Exception as e:
            logger.warning(
                "transaction.notification.failed",
                event_type=event_type,
                error=str(e),
            )

    @staticmethod
    def _notify_invitation_created(txn, NS):
        target = User.objects.filter(id=txn.target_id).first()
        if target:
            NS.send(
                user=target,
                notification_type="transaction_invitation_received",
                context={
                    "transaction_id": str(txn.id),
                    "transaction_type": txn.transaction_type,
                },
            )

    @staticmethod
    def _notify_request_created(txn, NS):
        """Notify approvers that a new request needs review."""
        from apps.organization.platform.models import PlatformAccount
        from apps.rbac.selectors import MembershipSelector
        from apps.transaction.constants import ApproverPolicy
        from apps.transaction.types import get_transaction_type

        config = get_transaction_type(txn.transaction_type)
        if not config.approval_permission:
            return

        users = []
        if config.approver_policy == ApproverPolicy.PLATFORM_AUTHORITY:
            platform = PlatformAccount.objects.first()
            if platform:
                users = MembershipSelector.get_users_with_permission(
                    account_type="platform",
                    account_id=platform.id,
                    permission_code=config.approval_permission,
                )
        elif config.approver_policy == ApproverPolicy.ACCOUNT_AUTHORITY:
            if txn.context_id:
                users = MembershipSelector.get_users_with_permission(
                    account_type=txn.context_type,
                    account_id=txn.context_id,
                    permission_code=config.approval_permission,
                )

        for user in users:
            NS.send(
                user=user,
                notification_type="transaction_pending_approval",
                context={
                    "transaction_id": str(txn.id),
                    "transaction_type": txn.transaction_type,
                },
            )

    @staticmethod
    def _notify_accepted(txn, NS):
        ctx = ActorContext.from_dict(txn.initiator_context)
        initiator = User.objects.filter(id=ctx.user_id).first()
        if initiator:
            NS.send(
                user=initiator,
                notification_type="transaction_accepted",
                context={
                    "transaction_id": str(txn.id),
                    "transaction_type": txn.transaction_type,
                },
            )

    @staticmethod
    def _notify_denied(txn, NS):
        ctx = ActorContext.from_dict(txn.initiator_context)
        initiator = User.objects.filter(id=ctx.user_id).first()
        if initiator:
            NS.send(
                user=initiator,
                notification_type="transaction_denied",
                context={
                    "transaction_id": str(txn.id),
                    "reason": txn.resolution_reason or "",
                },
            )

    @staticmethod
    def _notify_cancelled(txn, NS):
        if txn.target_type == PartyType.USER:
            target = User.objects.filter(id=txn.target_id).first()
            if target:
                NS.send(
                    user=target,
                    notification_type="transaction_cancelled",
                    context={
                        "transaction_id": str(txn.id),
                        "transaction_type": txn.transaction_type,
                    },
                )

    @staticmethod
    def _notify_expired(txn, NS):
        ctx = ActorContext.from_dict(txn.initiator_context)
        initiator = User.objects.filter(id=ctx.user_id).first()
        if initiator:
            NS.send(
                user=initiator,
                notification_type="transaction_expired",
                context={
                    "transaction_id": str(txn.id),
                    "transaction_type": txn.transaction_type,
                },
            )

    @staticmethod
    def _notify_info_requested(txn, NS):
        ctx = ActorContext.from_dict(txn.initiator_context)
        initiator = User.objects.filter(id=ctx.user_id).first()
        if initiator:
            NS.send(
                user=initiator,
                notification_type="transaction_info_requested",
                context={
                    "transaction_id": str(txn.id),
                    "message": txn.info_requested_message or "",
                },
            )

    @staticmethod
    def _notify_pending_review(txn, NS):
        """Notify business that a form needs review after invitation acceptance."""
        TransactionService._notify_request_created(txn, NS)

    @staticmethod
    def _notify_resubmitted(txn, NS):
        """Notify approvers that a request/form has been resubmitted."""
        TransactionService._notify_request_created(txn, NS)
