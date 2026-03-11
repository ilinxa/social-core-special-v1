# Transaction System — Phase 2: Business Logic

**Implements:** Selectors, policies, services, outcome handlers, RBAC permissions.  
**Depends on:** Phase 1 complete. `apps.rbac` services/selectors.  
**Deliverable:** All service methods work. Unit tests pass.

---

## 1. Selectors

```python
# apps/transaction/selectors.py
from typing import Optional
from uuid import UUID
from django.db.models import QuerySet
from django.utils import timezone

from apps.core.exceptions import NotFound
from apps.transaction.models import Transaction, TransactionLog
from apps.transaction.constants import TransactionStatus


class TransactionSelector:

    @staticmethod
    def get_by_id(*, transaction_id: UUID) -> Transaction:
        txn = Transaction.objects.filter(id=transaction_id).first()
        if not txn:
            raise NotFound(resource="Transaction", resource_id=str(transaction_id))
        return txn

    @staticmethod
    def get_by_id_or_none(*, transaction_id: UUID) -> Optional[Transaction]:
        return Transaction.objects.filter(id=transaction_id).first()

    @staticmethod
    def get_by_id_with_logs(*, transaction_id: UUID) -> Transaction:
        txn = Transaction.objects.with_logs().filter(id=transaction_id).first()
        if not txn:
            raise NotFound(resource="Transaction", resource_id=str(transaction_id))
        return txn

    @staticmethod
    def exists_active(*, transaction_type: str, initiator_id: UUID, target_id: UUID) -> bool:
        return Transaction.objects.filter(
            transaction_type=transaction_type, initiator_id=initiator_id, target_id=target_id,
        ).active().exists()

    @staticmethod
    def list_for_user_as_initiator(*, user_id: UUID, include_terminal: bool = False) -> QuerySet:
        qs = Transaction.objects.for_initiator(initiator_type="user", initiator_id=user_id)
        if not include_terminal:
            qs = qs.active()
        return qs.order_by("-created_at")

    @staticmethod
    def list_for_user_as_target(*, user_id: UUID, include_terminal: bool = False) -> QuerySet:
        qs = Transaction.objects.for_target(target_type="user", target_id=user_id)
        if not include_terminal:
            qs = qs.active()
        return qs.order_by("-created_at")

    @staticmethod
    def list_pending_for_context(*, context_type: str, context_id: UUID,
                                  transaction_type: Optional[str] = None) -> QuerySet:
        qs = Transaction.objects.for_context(context_type=context_type, context_id=context_id).pending()
        if transaction_type:
            qs = qs.of_type(transaction_type)
        return qs.order_by("-created_at")

    @staticmethod
    def list_expired_needing_update() -> QuerySet:
        return Transaction.objects.expired_needing_update()

    @staticmethod
    def get_resubmission_cooldown(*, transaction_type: str, initiator_id: UUID,
                                    target_id: UUID) -> Optional[timezone.datetime]:
        from apps.transaction.types import get_transaction_type
        config = get_transaction_type(transaction_type)
        if config.resubmission_cooldown_days == 0:
            return None

        last_denied = Transaction.objects.filter(
            transaction_type=transaction_type, initiator_id=initiator_id,
            target_id=target_id, status=TransactionStatus.DENIED,
        ).order_by("-resolved_at").first()

        if not last_denied or not last_denied.resolved_at:
            return None

        cooldown_end = last_denied.resolved_at + timezone.timedelta(days=config.resubmission_cooldown_days)
        return cooldown_end if timezone.now() < cooldown_end else None


class TransactionLogSelector:

    @staticmethod
    def list_for_transaction(*, transaction_id: UUID) -> QuerySet:
        return TransactionLog.objects.filter(transaction_id=transaction_id).order_by("-timestamp")
```

---

## 2. Policies

**Key rule:** All permission checks use `ActorContext.has_permission()` / `has_global_permission()`. Never check `in permissions_snapshot` directly — it's `List[Tuple[str, str]]`, not flat strings.

```python
# apps/transaction/policies.py
from apps.core.exceptions import PermissionDenied, ValidationError
from apps.core.types import ActorContext
from apps.transaction.models import Transaction
from apps.transaction.types import TransactionTypeConfig
from apps.transaction.constants import TransactionStatus, ApproverPolicy, PartyType


class TransactionPolicy:

    @staticmethod
    def can_create_invitation(*, actor_context: ActorContext, config: TransactionTypeConfig) -> None:
        for perm_code in config.required_permissions:
            if not actor_context.has_permission(perm_code):
                raise PermissionDenied(
                    message=f"Missing required permission: {perm_code}",
                    action="create_invitation", resource="Transaction",
                )
        if config.owner_only and not actor_context.is_owner:
            raise PermissionDenied(
                message="Only the account owner can initiate this transaction",
                action="create_invitation", resource="Transaction",
            )

    @staticmethod
    def can_accept(*, transaction: Transaction, actor_context: ActorContext,
                   config: TransactionTypeConfig) -> None:
        if transaction.status != TransactionStatus.PENDING:
            raise ValidationError(
                message=f"Transaction is not pending (status: {transaction.status})",
                field="status",
            )

        policy = config.approver_policy

        if policy == ApproverPolicy.TARGET_ACCEPTANCE:
            if transaction.target_type != PartyType.USER:
                raise PermissionDenied(message="Invalid target type", action="accept", resource="Transaction")
            if actor_context.user_id != transaction.target_id:
                raise PermissionDenied(
                    message="Only the target user can accept this invitation",
                    action="accept", resource="Transaction",
                )

        elif policy == ApproverPolicy.ACCOUNT_AUTHORITY:
            if actor_context.account_id != transaction.context_id:
                raise PermissionDenied(
                    message="Not a member of the account this transaction belongs to",
                    action="accept", resource="Transaction",
                )
            if config.approval_permission and not actor_context.has_permission(config.approval_permission):
                raise PermissionDenied(
                    message=f"Missing permission: {config.approval_permission}",
                    action="accept", resource="Transaction",
                )

        elif policy == ApproverPolicy.PLATFORM_AUTHORITY:
            if actor_context.account_type != "platform":
                raise PermissionDenied(message="Platform authority required", action="accept", resource="Transaction")
            if config.approval_permission and not actor_context.has_permission(config.approval_permission):
                raise PermissionDenied(
                    message=f"Missing permission: {config.approval_permission}",
                    action="accept", resource="Transaction",
                )

        elif policy == ApproverPolicy.AUTO_APPROVAL:
            raise ValidationError(
                message="Auto-approval transactions don't require manual acceptance",
                field="transaction_type",
            )

    @staticmethod
    def can_deny(*, transaction: Transaction, actor_context: ActorContext,
                 config: TransactionTypeConfig) -> None:
        TransactionPolicy.can_accept(transaction=transaction, actor_context=actor_context, config=config)

    @staticmethod
    def is_initiator(*, transaction: Transaction, actor_context: ActorContext) -> None:
        initiator_context = ActorContext.from_dict(transaction.initiator_context)
        if actor_context.user_id != initiator_context.user_id:
            raise PermissionDenied(
                message="Only the initiator can perform this action",
                action="modify", resource="Transaction",
            )

    @staticmethod
    def can_view(*, transaction: Transaction, actor_context: ActorContext) -> None:
        initiator_context = ActorContext.from_dict(transaction.initiator_context)

        if actor_context.user_id == initiator_context.user_id:
            return
        if transaction.target_type == PartyType.USER and actor_context.user_id == transaction.target_id:
            return
        if (actor_context.account_id == transaction.context_id
                and actor_context.account_type == transaction.context_type):
            if actor_context.is_owner:
                return
            if actor_context.has_permission("can_view_transactions"):
                return
        if actor_context.account_type == "platform":
            if actor_context.has_global_permission("can_view_all_transactions"):
                return

        raise PermissionDenied(
            message="Not authorized to view this transaction",
            action="view", resource="Transaction",
        )
```

---

## 3. Services

```python
# apps/transaction/services.py
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import timedelta
from django.db import transaction as db_transaction
from django.utils import timezone
from django.http import HttpRequest
from django.contrib.auth import get_user_model

from apps.core.observability import get_logger, AuditService, AuditLog
from apps.core.exceptions import NotFound, ConflictError, ValidationError
from apps.core.types import ActorContext
from apps.transaction.models import Transaction, TransactionLog
from apps.transaction.selectors import TransactionSelector
from apps.transaction.policies import TransactionPolicy
from apps.transaction.types import get_transaction_type, TransactionTypeConfig
from apps.transaction.constants import TransactionMode, TransactionStatus, PartyType, TERMINAL_STATES
from apps.transaction.outcome_handlers import OutcomeHandlerRegistry

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
        *, transaction_type: str, initiator_context: ActorContext,
        target_user_id: UUID, payload: Optional[Dict[str, Any]] = None,
        form_response_id: Optional[UUID] = None, request: Optional[HttpRequest] = None,
    ) -> Transaction:
        """Create invitation. Transitions CREATED → PENDING atomically."""
        config = get_transaction_type(transaction_type)

        if config.mode != TransactionMode.INVITATION:
            raise ValidationError(message=f"{transaction_type} is not an invitation type", field="transaction_type")
        if not config.enabled:
            raise ValidationError(message=f"Transaction type {transaction_type} is disabled", field="transaction_type")

        TransactionPolicy.can_create_invitation(actor_context=initiator_context, config=config)

        if TransactionSelector.exists_active(
            transaction_type=transaction_type,
            initiator_id=initiator_context.membership_id or initiator_context.user_id,
            target_id=target_user_id,
        ):
            raise ConflictError(message="An active transaction already exists for this target",
                                resource="Transaction", conflict_type="duplicate")

        TransactionService._validate_payload(config, payload or {})
        if config.required_form_template_id and not form_response_id:
            raise ValidationError(message="This transaction type requires a form response", field="form_response_id")

        context_id = initiator_context.account_id if config.context_type != "user" else None

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

        TransactionService._log_event(transaction=txn, event_type="created",
                                       actor_context=initiator_context, new_status=TransactionStatus.CREATED)
        txn = TransactionService._transition(transaction=txn, new_status=TransactionStatus.PENDING,
                                              actor_context=initiator_context)

        AuditService.log(
            action=AuditLog.Action.TRANSACTION_CREATED,
            actor=_resolve_actor(initiator_context), resource=txn, request=request,
            details={"transaction_type": transaction_type, "mode": "invitation", "target_id": str(target_user_id)},
        )

        db_transaction.on_commit(lambda: TransactionService._notify_safe("invitation_created", txn))
        return txn

    @staticmethod
    @db_transaction.atomic
    def create_request(
        *, transaction_type: str, user_id: UUID, target_account_type: str = None,
        target_account_id: UUID = None, target_user_id: UUID = None,
        payload: Optional[Dict[str, Any]] = None,
        form_response_id: Optional[UUID] = None, request: Optional[HttpRequest] = None,
    ) -> Transaction:
        """Create request. Transitions CREATED → PENDING atomically.

        For account-targeted requests (membership, follow, verification):
            Pass target_account_type + target_account_id.
        For user-targeted requests (connection):
            Pass target_user_id.
        """
        config = get_transaction_type(transaction_type)

        if config.mode != TransactionMode.REQUEST:
            raise ValidationError(message=f"{transaction_type} is not a request type", field="transaction_type")
        if not config.enabled:
            raise ValidationError(message=f"Transaction type {transaction_type} is disabled", field="transaction_type")

        user = User.objects.filter(id=user_id).first()
        if not user:
            raise NotFound(resource="User", resource_id=str(user_id))

        # Determine target type and ID from config
        if PartyType.USER in config.target_types:
            if not target_user_id:
                raise ValidationError(message="target_user_id is required for user-targeted requests", field="target_user_id")
            target_type = PartyType.USER
            target_id = target_user_id
        else:
            if not target_account_id:
                raise ValidationError(message="target_account_id is required for account-targeted requests", field="target_account_id")
            target_type = PartyType.ACCOUNT
            target_id = target_account_id

        if TransactionSelector.exists_active(
            transaction_type=transaction_type, initiator_id=user_id, target_id=target_id,
        ):
            raise ConflictError(message="You already have an active request", resource="Transaction", conflict_type="duplicate")

        cooldown_end = TransactionSelector.get_resubmission_cooldown(
            transaction_type=transaction_type, initiator_id=user_id, target_id=target_id,
        )
        if cooldown_end:
            raise ValidationError(message=f"Cannot resubmit until {cooldown_end.isoformat()}", field="transaction_type")

        TransactionService._validate_payload(config, payload or {})
        if config.required_form_template_id and not form_response_id:
            raise ValidationError(message="This transaction type requires a form response", field="form_response_id")

        actor_context = ActorContext.for_user_context(user, request)

        txn = Transaction.objects.create_transaction(
            transaction_type=transaction_type, mode=TransactionMode.REQUEST,
            initiator_type=PartyType.USER, initiator_id=user_id,
            initiator_context=actor_context.to_dict(),
            target_type=target_type, target_id=target_id,
            context_type=config.context_type,
            context_id=target_id if config.context_type != "user" else None,
            payload=payload or {}, form_response_id=form_response_id,
            expires_at=timezone.now() + timedelta(days=config.expiration_days),
            created_by=user,
        )

        TransactionService._log_event(transaction=txn, event_type="created",
                                       actor_context=actor_context, new_status=TransactionStatus.CREATED)
        txn = TransactionService._transition(transaction=txn, new_status=TransactionStatus.PENDING,
                                              actor_context=actor_context)

        # AUTO_APPROVAL: auto-accept immediately (e.g., business_follow_request)
        if config.approver_policy == ApproverPolicy.AUTO_APPROVAL:
            system_context = ActorContext.for_system()
            txn = TransactionService._transition(
                transaction=txn, new_status=TransactionStatus.ACCEPTED,
                actor_context=system_context,
            )
            TransactionService._execute_outcome(transaction=txn, actor_context=system_context)

        AuditService.log(
            action=AuditLog.Action.TRANSACTION_CREATED, actor=user, resource=txn, request=request,
            details={"transaction_type": transaction_type, "mode": "request", "target_id": str(target_id)},
        )

        db_transaction.on_commit(lambda: TransactionService._notify_safe("request_created", txn))
        return txn

    # =========================================================================
    # STATE TRANSITIONS
    # =========================================================================

    @staticmethod
    @db_transaction.atomic
    def accept(*, transaction_id: UUID, actor_context: ActorContext,
               request: Optional[HttpRequest] = None) -> Transaction:
        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        config = get_transaction_type(txn.transaction_type)
        TransactionPolicy.can_accept(transaction=txn, actor_context=actor_context, config=config)

        if txn.mode == TransactionMode.INVITATION:
            TransactionService._validate_creator_authority(txn)

        txn = TransactionService._transition(
            transaction=txn, new_status=TransactionStatus.ACCEPTED,
            actor_context=actor_context, resolved_by_id=actor_context.user_id,
        )
        AuditService.log(action=AuditLog.Action.TRANSACTION_ACCEPTED,
                         actor=_resolve_actor(actor_context), resource=txn, request=request)
        TransactionService._execute_outcome(transaction=txn, actor_context=actor_context)
        db_transaction.on_commit(lambda: TransactionService._notify_safe("accepted", txn))
        return txn

    @staticmethod
    @db_transaction.atomic
    def deny(*, transaction_id: UUID, actor_context: ActorContext,
             reason: str = "", request: Optional[HttpRequest] = None) -> Transaction:
        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        config = get_transaction_type(txn.transaction_type)
        TransactionPolicy.can_deny(transaction=txn, actor_context=actor_context, config=config)

        txn = TransactionService._transition(
            transaction=txn, new_status=TransactionStatus.DENIED,
            actor_context=actor_context, resolved_by_id=actor_context.user_id, resolution_reason=reason,
        )
        AuditService.log(action=AuditLog.Action.TRANSACTION_DENIED,
                         actor=_resolve_actor(actor_context), resource=txn, request=request, details={"reason": reason})
        db_transaction.on_commit(lambda: TransactionService._notify_safe("denied", txn))
        return txn

    @staticmethod
    @db_transaction.atomic
    def dismiss(*, transaction_id: UUID, actor_context: ActorContext,
                request: Optional[HttpRequest] = None) -> Transaction:
        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        if txn.mode != TransactionMode.REQUEST:
            raise ValidationError(message="Only requests can be dismissed", field="transaction_id")
        config = get_transaction_type(txn.transaction_type)
        TransactionPolicy.can_deny(transaction=txn, actor_context=actor_context, config=config)

        txn = TransactionService._transition(
            transaction=txn, new_status=TransactionStatus.DISMISSED,
            actor_context=actor_context, resolved_by_id=actor_context.user_id,
        )
        AuditService.log(action=AuditLog.Action.TRANSACTION_DISMISSED,
                         actor=_resolve_actor(actor_context), resource=txn, request=request)
        return txn

    @staticmethod
    @db_transaction.atomic
    def cancel(*, transaction_id: UUID, actor_context: ActorContext,
               request: Optional[HttpRequest] = None) -> Transaction:
        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        TransactionPolicy.is_initiator(transaction=txn, actor_context=actor_context)
        if txn.status != TransactionStatus.PENDING:
            raise ValidationError(message="Can only cancel pending transactions", field="status")

        txn = TransactionService._transition(
            transaction=txn, new_status=TransactionStatus.CANCELLED,
            actor_context=actor_context, resolved_by_id=actor_context.user_id,
        )
        AuditService.log(action=AuditLog.Action.TRANSACTION_CANCELLED,
                         actor=_resolve_actor(actor_context), resource=txn, request=request)
        db_transaction.on_commit(lambda: TransactionService._notify_safe("cancelled", txn))
        return txn

    @staticmethod
    @db_transaction.atomic
    def expire(*, transaction_id: UUID) -> Transaction:
        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        if txn.is_terminal:
            return txn
        system_context = ActorContext.for_system()
        txn = TransactionService._transition(transaction=txn, new_status=TransactionStatus.EXPIRED,
                                              actor_context=system_context)
        db_transaction.on_commit(lambda: TransactionService._notify_safe("expired", txn))
        return txn

    @staticmethod
    @db_transaction.atomic
    def invalidate(*, transaction_id: UUID, reason: str) -> Transaction:
        txn = TransactionSelector.get_by_id(transaction_id=transaction_id)
        if txn.is_terminal:
            return txn
        system_context = ActorContext.for_system()
        txn = TransactionService._transition(
            transaction=txn, new_status=TransactionStatus.INVALIDATED,
            actor_context=system_context, resolution_reason=reason,
        )
        logger.warning("transaction.invalidated", transaction_id=str(txn.id), reason=reason)
        return txn

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    @staticmethod
    def _transition(*, transaction, new_status, actor_context, resolved_by_id=None, resolution_reason=""):
        if not transaction.can_transition_to(new_status):
            raise ValidationError(message=f"Invalid transition from {transaction.status} to {new_status}", field="status")
        previous_status = transaction.status
        transaction.status = new_status
        if new_status in TERMINAL_STATES:
            transaction.resolved_at = timezone.now()
            if resolved_by_id:
                transaction.resolved_by_id = resolved_by_id
            if resolution_reason:
                transaction.resolution_reason = resolution_reason
        transaction.save()
        TransactionService._log_event(transaction=transaction, event_type="state_changed",
                                       actor_context=actor_context, previous_status=previous_status, new_status=new_status)
        return transaction

    @staticmethod
    def _log_event(*, transaction, event_type, actor_context, previous_status="", new_status, metadata=None):
        return TransactionLog.objects.create(
            transaction=transaction, event_type=event_type, actor_context=actor_context.to_dict(),
            previous_status=previous_status, new_status=new_status, metadata=metadata or {},
        )

    @staticmethod
    def _validate_payload(config, payload):
        for field_name, rules in config.payload_schema.items():
            value = payload.get(field_name)
            if rules.get("required") and value is None:
                raise ValidationError(message=f"Field '{field_name}' is required", field=field_name)
            if value is not None:
                if rules.get("type") == "string" and not isinstance(value, str):
                    raise ValidationError(message=f"Field '{field_name}' must be a string", field=field_name)
                max_len = rules.get("max_length")
                if max_len and isinstance(value, str) and len(value) > max_len:
                    raise ValidationError(message=f"Field '{field_name}' exceeds max length {max_len}", field=field_name)

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
                membership_id=initiator_context.membership_id
            )
        except NotFound:
            TransactionService.invalidate(transaction_id=transaction.id, reason="Creator membership no longer exists")
            raise ValidationError(message="This invitation is no longer valid", field="transaction_id")

        if membership.status != "active":
            TransactionService.invalidate(transaction_id=transaction.id, reason="Creator membership no longer active")
            raise ValidationError(message="This invitation is no longer valid", field="transaction_id")

        if config.required_permissions:
            current_perms = PermissionSelector.get_permissions_for_membership(
                membership_id=initiator_context.membership_id
            )
            # get_permissions_for_membership returns List[Tuple[str, str]] (code, scope)
            current_codes = {code for code, scope in current_perms}
            for perm_code in config.required_permissions:
                if perm_code not in current_codes:
                    TransactionService.invalidate(transaction_id=transaction.id, reason=f"Creator lost permission: {perm_code}")
                    raise ValidationError(message="This invitation is no longer valid", field="transaction_id")

    @staticmethod
    def _execute_outcome(*, transaction, actor_context):
        config = get_transaction_type(transaction.transaction_type)
        if not config.outcome_handler:
            transaction.outcome_executed = True
            transaction.outcome_executed_at = timezone.now()
            transaction.save(update_fields=["outcome_executed", "outcome_executed_at"])
            return
        try:
            OutcomeHandlerRegistry.execute(transaction=transaction, actor_context=actor_context)
            transaction.outcome_executed = True
            transaction.outcome_executed_at = timezone.now()
            transaction.save(update_fields=["outcome_executed", "outcome_executed_at"])
        except Exception as e:
            transaction.outcome_error = str(e)
            transaction.save(update_fields=["outcome_error"])
            logger.error("transaction.outcome.failed", transaction_id=str(transaction.id), error=str(e))
            raise

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
            handler = getattr(TransactionService, f"_notify_{event_type}", None)
            if handler:
                handler(transaction, NotificationService)
        except Exception as e:
            logger.warning("transaction.notification.failed", event_type=event_type, error=str(e))

    @staticmethod
    def _notify_invitation_created(txn, NS):
        target = User.objects.filter(id=txn.target_id).first()
        if target:
            NS.send(user=target, notification_type="transaction_invitation_received",
                    context={"transaction_id": str(txn.id), "transaction_type": txn.transaction_type})

    @staticmethod
    def _notify_request_created(txn, NS):
        pass  # TODO: notify approvers based on policy

    @staticmethod
    def _notify_accepted(txn, NS):
        ctx = ActorContext.from_dict(txn.initiator_context)
        initiator = User.objects.filter(id=ctx.user_id).first()
        if initiator:
            NS.send(user=initiator, notification_type="transaction_accepted",
                    context={"transaction_id": str(txn.id), "transaction_type": txn.transaction_type})

    @staticmethod
    def _notify_denied(txn, NS):
        ctx = ActorContext.from_dict(txn.initiator_context)
        initiator = User.objects.filter(id=ctx.user_id).first()
        if initiator:
            NS.send(user=initiator, notification_type="transaction_denied",
                    context={"transaction_id": str(txn.id), "reason": txn.resolution_reason or ""})

    @staticmethod
    def _notify_cancelled(txn, NS):
        if txn.target_type == PartyType.USER:
            target = User.objects.filter(id=txn.target_id).first()
            if target:
                NS.send(user=target, notification_type="transaction_cancelled",
                        context={"transaction_id": str(txn.id), "transaction_type": txn.transaction_type})

    @staticmethod
    def _notify_expired(txn, NS):
        ctx = ActorContext.from_dict(txn.initiator_context)
        initiator = User.objects.filter(id=ctx.user_id).first()
        if initiator:
            NS.send(user=initiator, notification_type="transaction_expired",
                    context={"transaction_id": str(txn.id), "transaction_type": txn.transaction_type})
```

---

## 4. Outcome Handlers

Replace the Phase 1 placeholder `outcome_handlers.py` with the full implementation:

```python
# apps/transaction/outcome_handlers.py
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
    def execute(cls, *, transaction: Transaction, actor_context: ActorContext):
        handler = cls._handlers.get(transaction.transaction_type)
        if handler:
            handler(transaction=transaction, actor_context=actor_context)


class MembershipOutcomeHandler:

    @staticmethod
    @db_transaction.atomic
    def handle_invitation_accepted(*, transaction: Transaction, actor_context: ActorContext):
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
        logger.info("outcome.membership.invitation_accepted", transaction_id=str(transaction.id))

    @staticmethod
    @db_transaction.atomic
    def handle_request_approved(*, transaction: Transaction, actor_context: ActorContext):
        from apps.rbac.services import RBACService
        from apps.rbac.selectors import RoleSelector
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user = User.objects.get(id=transaction.initiator_id)
        approver = User.objects.filter(id=actor_context.user_id).first()

        role_id = transaction.payload.get("role_id")
        if not role_id:
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
        logger.info("outcome.membership.request_approved", transaction_id=str(transaction.id))


class VerificationOutcomeHandler:
    @staticmethod
    @db_transaction.atomic
    def handle_accepted(*, transaction: Transaction, actor_context: ActorContext):
        from apps.organization.business.services import BusinessAccountService
        from apps.organization.business.selectors import BusinessAccountSelector
        from apps.core.constants import VerificationStatus
        from django.contrib.auth import get_user_model
        User = get_user_model()

        initiator_ctx = ActorContext.from_dict(transaction.initiator_context)
        business = BusinessAccountSelector.get_by_id(business_id=initiator_ctx.account_id)
        actor = User.objects.get(id=actor_context.user_id)

        BusinessAccountService.update_verification_status(
            business=business,
            status=VerificationStatus.VERIFIED,
            actor=actor,
        )


class OwnershipOutcomeHandler:
    @staticmethod
    @db_transaction.atomic
    def handle_accepted(*, transaction: Transaction, actor_context: ActorContext):
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


class ConnectionOutcomeHandler:
    """
    Stub: The Connection subsystem does not exist yet.
    Will be implemented when the Social/Connection system is built.
    For now, only logs the accepted event.
    """

    @staticmethod
    @db_transaction.atomic
    def handle_accepted(*, transaction: Transaction, actor_context: ActorContext):
        logger.info("outcome.connection.created", transaction_id=str(transaction.id))


class FollowOutcomeHandler:
    """
    Stub: The Follow subsystem does not exist yet.
    Will be implemented when the Social/Follow system is built.
    For now, only logs the accepted event.
    """

    @staticmethod
    @db_transaction.atomic
    def handle_accepted(*, transaction: Transaction, actor_context: ActorContext):
        logger.info("outcome.follow.created", transaction_id=str(transaction.id))


class PermissionOutcomeHandler:
    """
    Stub: The BusinessCreation permission subsystem does not exist yet.
    Will be implemented when platform-level permission grants are built.
    For now, only logs the accepted event.
    """

    @staticmethod
    @db_transaction.atomic
    def handle_business_creation_approved(*, transaction: Transaction, actor_context: ActorContext):
        logger.info("outcome.permission.business_creation_granted", transaction_id=str(transaction.id))


def register_all_handlers():
    r = OutcomeHandlerRegistry.register
    r("platform_membership_invitation", MembershipOutcomeHandler.handle_invitation_accepted)
    r("platform_membership_request", MembershipOutcomeHandler.handle_request_approved)
    r("business_membership_invitation", MembershipOutcomeHandler.handle_invitation_accepted)
    r("business_membership_request", MembershipOutcomeHandler.handle_request_approved)
    r("business_verification_request", VerificationOutcomeHandler.handle_accepted)
    r("platform_ownership_transfer", OwnershipOutcomeHandler.handle_accepted)
    r("business_ownership_transfer", OwnershipOutcomeHandler.handle_accepted)
    r("user_connection_request", ConnectionOutcomeHandler.handle_accepted)
    r("business_follow_request", FollowOutcomeHandler.handle_accepted)
    r("business_creation_permission_request", PermissionOutcomeHandler.handle_business_creation_approved)
```

---

## 5. New RBAC Permissions

Add to `apps/rbac/permissions/registry.py`:

```python
("can_view_transactions", "View Transactions", "View transactions within the account", "transaction", ["business", "platform_only"]),
("can_view_all_transactions", "View All Transactions", "View transactions across all accounts", "transaction", ["global_only", "platform_and_global"]),
```

Create migration: `apps/rbac/migrations/000X_seed_transaction_permissions.py` using the standard `get_or_create` + backfill pattern.

---

## 6. Phase 2 Verification

```bash
# Run unit tests
pytest apps/transaction/tests/test_services.py -v
pytest apps/transaction/tests/test_policies.py -v

# Quick smoke test
python manage.py shell -c "
from apps.transaction.services import TransactionService
from apps.transaction.selectors import TransactionSelector
from apps.transaction.policies import TransactionPolicy
print('Phase 2 imports OK')
"
```
