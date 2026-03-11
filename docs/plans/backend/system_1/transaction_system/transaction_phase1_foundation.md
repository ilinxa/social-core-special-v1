# Transaction System — Phase 1: Foundation

**Implements:** App structure, constants, type registry, models, managers, audit actions, migrations.  
**Depends on:** `apps.core`, `apps.organization` (for `ContextType`)  
**Deliverable:** `makemigrations transaction` succeeds. Models exist in DB.

---

## 1. App Configuration

```python
# apps/transaction/__init__.py
# (empty)
```

```python
# apps/transaction/apps.py
from django.apps import AppConfig


class TransactionConfig(AppConfig):
    name = "apps.transaction"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "Transaction System"

    def ready(self):
        import apps.transaction.signals  # noqa: F401
        from apps.transaction.outcome_handlers import register_all_handlers
        register_all_handlers()
```

```python
# apps/transaction/signals.py
# Placeholder — populated in Phase 2 if needed
```

```python
# apps/transaction/outcome_handlers.py
# Placeholder — Phase 1 only needs the import to not crash in apps.py ready()
def register_all_handlers():
    pass
```

Add `"apps.transaction"` to `INSTALLED_APPS` in settings.

---

## 2. Constants & Enums

```python
# apps/transaction/constants.py
from django.db import models


class TransactionMode(models.TextChoices):
    INVITATION = "invitation", "Invitation"
    REQUEST = "request", "Request"


class TransactionStatus(models.TextChoices):
    CREATED = "created", "Created"
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    DENIED = "denied", "Denied"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"
    DISMISSED = "dismissed", "Dismissed"
    INVALIDATED = "invalidated", "Invalidated"


class PartyType(models.TextChoices):
    USER = "user", "User"
    ACCOUNT = "account", "Account"
    MEMBERSHIP_ACTOR = "membership_actor", "Membership Actor"
    SYSTEM = "system", "System"


class ApproverPolicy(models.TextChoices):
    TARGET_ACCEPTANCE = "target_acceptance", "Target Acceptance"
    ACCOUNT_AUTHORITY = "account_authority", "Account Authority"
    PLATFORM_AUTHORITY = "platform_authority", "Platform Authority"
    AUTO_APPROVAL = "auto_approval", "Auto Approval"


TERMINAL_STATES = frozenset([
    TransactionStatus.ACCEPTED,
    TransactionStatus.DENIED,
    TransactionStatus.CANCELLED,
    TransactionStatus.EXPIRED,
    TransactionStatus.DISMISSED,
    TransactionStatus.INVALIDATED,
])

VALID_TRANSITIONS = {
    TransactionStatus.CREATED: [
        TransactionStatus.PENDING,
        TransactionStatus.EXPIRED,
        TransactionStatus.INVALIDATED,
    ],
    TransactionStatus.PENDING: [
        TransactionStatus.ACCEPTED,
        TransactionStatus.DENIED,
        TransactionStatus.CANCELLED,
        TransactionStatus.DISMISSED,
        TransactionStatus.EXPIRED,
        TransactionStatus.INVALIDATED,
    ],
}
```

---

## 3. Transaction Type Registry

```python
# apps/transaction/types.py
from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID
from apps.core.constants import ContextType
from apps.transaction.constants import TransactionMode, PartyType, ApproverPolicy


@dataclass
class TransactionTypeConfig:
    id: str
    name: str
    mode: TransactionMode
    initiator_types: List[PartyType]
    target_types: List[PartyType]
    context_type: ContextType
    approver_policy: ApproverPolicy
    required_permissions: List[str] = field(default_factory=list)
    approval_permission: Optional[str] = None
    owner_only: bool = False
    required_form_template_id: Optional[UUID] = None
    optional_form_template_id: Optional[UUID] = None
    payload_schema: dict = field(default_factory=dict)
    expiration_days: int = 7
    resubmission_cooldown_days: int = 0
    outcome_handler: str = ""
    user_configurable: bool = True
    enabled: bool = True


TRANSACTION_TYPES = {
    # --- PLATFORM ---
    "platform_membership_invitation": TransactionTypeConfig(
        id="platform_membership_invitation",
        name="Platform Membership Invitation",
        mode=TransactionMode.INVITATION,
        initiator_types=[PartyType.MEMBERSHIP_ACTOR],
        target_types=[PartyType.USER],
        context_type=ContextType.PLATFORM,
        approver_policy=ApproverPolicy.TARGET_ACCEPTANCE,
        required_permissions=["can_invite_member"],
        expiration_days=14,
        outcome_handler="apps.transaction.outcome_handlers.MembershipOutcomeHandler.handle_invitation_accepted",
    ),
    "platform_membership_request": TransactionTypeConfig(
        id="platform_membership_request",
        name="Platform Membership Request",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.USER],
        target_types=[PartyType.ACCOUNT],
        context_type=ContextType.PLATFORM,
        approver_policy=ApproverPolicy.PLATFORM_AUTHORITY,
        approval_permission="can_approve_membership_request",
        expiration_days=30,
        resubmission_cooldown_days=7,
        outcome_handler="apps.transaction.outcome_handlers.MembershipOutcomeHandler.handle_request_approved",
    ),
    "platform_ownership_transfer": TransactionTypeConfig(
        id="platform_ownership_transfer",
        name="Platform Ownership Transfer",
        mode=TransactionMode.INVITATION,
        initiator_types=[PartyType.MEMBERSHIP_ACTOR],
        target_types=[PartyType.USER],
        context_type=ContextType.PLATFORM,
        approver_policy=ApproverPolicy.TARGET_ACCEPTANCE,
        owner_only=True,
        expiration_days=7,
        outcome_handler="apps.transaction.outcome_handlers.OwnershipOutcomeHandler.handle_accepted",
    ),

    # --- BUSINESS ---
    "business_membership_invitation": TransactionTypeConfig(
        id="business_membership_invitation",
        name="Business Membership Invitation",
        mode=TransactionMode.INVITATION,
        initiator_types=[PartyType.MEMBERSHIP_ACTOR],
        target_types=[PartyType.USER],
        context_type=ContextType.BUSINESS,
        approver_policy=ApproverPolicy.TARGET_ACCEPTANCE,
        required_permissions=["can_invite_member"],
        payload_schema={
            "role_id": {"type": "string", "format": "uuid", "required": True},
            "message": {"type": "string", "max_length": 500, "required": False},
        },
        expiration_days=7,
        outcome_handler="apps.transaction.outcome_handlers.MembershipOutcomeHandler.handle_invitation_accepted",
    ),
    "business_membership_request": TransactionTypeConfig(
        id="business_membership_request",
        name="Business Membership Request",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.USER],
        target_types=[PartyType.ACCOUNT],
        context_type=ContextType.BUSINESS,
        approver_policy=ApproverPolicy.ACCOUNT_AUTHORITY,
        approval_permission="can_approve_membership_request",
        payload_schema={
            "message": {"type": "string", "max_length": 1000, "required": False},
            "referral_code": {"type": "string", "required": False},
        },
        expiration_days=30,
        resubmission_cooldown_days=7,
        outcome_handler="apps.transaction.outcome_handlers.MembershipOutcomeHandler.handle_request_approved",
    ),
    "business_verification_request": TransactionTypeConfig(
        id="business_verification_request",
        name="Business Verification Request",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.MEMBERSHIP_ACTOR],
        target_types=[PartyType.ACCOUNT],
        context_type=ContextType.PLATFORM,
        approver_policy=ApproverPolicy.PLATFORM_AUTHORITY,
        approval_permission="can_approve_verification_request",
        payload_schema={
            "form_response_id": {"type": "string", "format": "uuid", "required": True},
            "documents": {"type": "array", "required": False},
        },
        expiration_days=90,
        resubmission_cooldown_days=30,
        outcome_handler="apps.transaction.outcome_handlers.VerificationOutcomeHandler.handle_accepted",
    ),
    "business_follow_request": TransactionTypeConfig(
        id="business_follow_request",
        name="Business Follow Request",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.USER],
        target_types=[PartyType.ACCOUNT],
        context_type=ContextType.BUSINESS,
        approver_policy=ApproverPolicy.AUTO_APPROVAL,
        expiration_days=30,
        outcome_handler="apps.transaction.outcome_handlers.FollowOutcomeHandler.handle_accepted",
    ),
    "business_ownership_transfer": TransactionTypeConfig(
        id="business_ownership_transfer",
        name="Business Ownership Transfer",
        mode=TransactionMode.INVITATION,
        initiator_types=[PartyType.MEMBERSHIP_ACTOR],
        target_types=[PartyType.USER],
        context_type=ContextType.BUSINESS,
        approver_policy=ApproverPolicy.TARGET_ACCEPTANCE,
        owner_only=True,
        payload_schema={
            "message": {"type": "string", "required": False},
        },
        expiration_days=7,
        outcome_handler="apps.transaction.outcome_handlers.OwnershipOutcomeHandler.handle_accepted",
    ),
    "business_creation_permission_request": TransactionTypeConfig(
        id="business_creation_permission_request",
        name="Business Creation Permission Request",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.USER],
        target_types=[PartyType.ACCOUNT],
        context_type=ContextType.PLATFORM,
        approver_policy=ApproverPolicy.PLATFORM_AUTHORITY,
        approval_permission="can_approve_business_creation",
        expiration_days=30,
        resubmission_cooldown_days=30,
        outcome_handler="apps.transaction.outcome_handlers.PermissionOutcomeHandler.handle_business_creation_approved",
    ),

    # --- USER-TO-USER ---
    "user_connection_request": TransactionTypeConfig(
        id="user_connection_request",
        name="User Connection Request",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.USER],
        target_types=[PartyType.USER],
        context_type=ContextType.USER,
        approver_policy=ApproverPolicy.TARGET_ACCEPTANCE,
        expiration_days=30,
        resubmission_cooldown_days=3,
        outcome_handler="apps.transaction.outcome_handlers.ConnectionOutcomeHandler.handle_accepted",
    ),
}


def get_transaction_type(type_id: str) -> TransactionTypeConfig:
    from apps.core.exceptions import NotFound
    config = TRANSACTION_TYPES.get(type_id)
    if not config:
        raise NotFound(message=f"Unknown transaction type: {type_id}",
                       resource="TransactionType", resource_id=type_id)
    return config
```

---

## 4. Models

```python
# apps/transaction/models.py
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.core.models import UUIDModel, AuditModel
from apps.core.constants import ContextType
from apps.transaction.constants import (
    TransactionMode, TransactionStatus, PartyType,
    TERMINAL_STATES, VALID_TRANSITIONS,
)
from apps.transaction.managers import TransactionManager


class Transaction(UUIDModel, AuditModel):
    """
    Inherits: UUIDModel (UUID pk), AuditModel (created_at, updated_at,
    created_by, updated_by, is_deleted, deleted_at, deleted_by + SoftDeleteManager).
    """

    # Type
    transaction_type = models.CharField(max_length=100, db_index=True)
    mode = models.CharField(max_length=20, choices=TransactionMode.choices)

    # Initiator
    initiator_type = models.CharField(max_length=20, choices=PartyType.choices)
    initiator_id = models.UUIDField(help_text="User UUID or Membership UUID")
    initiator_context = models.JSONField(default=dict,
                                          help_text="ActorContext.to_dict() snapshot at creation")

    # Target
    target_type = models.CharField(max_length=20, choices=PartyType.choices)
    target_id = models.UUIDField(help_text="User UUID or Account UUID")

    # Context
    context_type = models.CharField(max_length=20, choices=ContextType.choices, db_index=True)
    context_id = models.UUIDField(null=True, blank=True, db_index=True,
                                   help_text="Account UUID. NULL for user context.")

    # State
    status = models.CharField(max_length=20, choices=TransactionStatus.choices,
                               default=TransactionStatus.CREATED, db_index=True)

    # Payload
    payload = models.JSONField(default=dict)
    form_response_id = models.UUIDField(null=True, blank=True)

    # Timing
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Resolution
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name="resolved_transactions")
    resolution_reason = models.TextField(blank=True)

    # Outcome
    outcome_executed = models.BooleanField(default=False)
    outcome_executed_at = models.DateTimeField(null=True, blank=True)
    outcome_error = models.TextField(blank=True)

    # Override manager
    objects = TransactionManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "transaction_transaction"
        indexes = [
            models.Index(fields=["transaction_type", "status"]),
            models.Index(fields=["context_type", "context_id", "status"]),
            models.Index(fields=["initiator_type", "initiator_id"]),
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["status", "outcome_executed"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(context_type="user") | models.Q(context_id__isnull=False),
                name="txn_context_id_required_for_account_contexts",
            ),
        ]

    def __str__(self):
        return f"{self.transaction_type} ({self.status})"

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATES

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and timezone.now() > self.expires_at

    def can_transition_to(self, new_status: str) -> bool:
        if self.is_terminal:
            return False
        return new_status in VALID_TRANSITIONS.get(self.status, [])


class TransactionLog(models.Model):
    """
    Immutable audit log for transaction state changes.
    Does NOT inherit from base models.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name="logs")
    event_type = models.CharField(max_length=50, db_index=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    actor_context = models.JSONField(default=dict)
    previous_status = models.CharField(max_length=20, choices=TransactionStatus.choices, blank=True)
    new_status = models.CharField(max_length=20, choices=TransactionStatus.choices)
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = "transaction_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["transaction", "timestamp"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk and TransactionLog.objects.filter(pk=self.pk).exists():
            raise ValueError("TransactionLog entries cannot be modified")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("TransactionLog entries cannot be deleted")
```

---

## 5. Managers

```python
# apps/transaction/managers.py
from django.db import models
from django.utils import timezone
from apps.core.models import SoftDeleteManager
from apps.transaction.constants import TransactionStatus, TERMINAL_STATES


class TransactionQuerySet(models.QuerySet):

    def active(self):
        return self.exclude(status__in=TERMINAL_STATES)

    def pending(self):
        return self.filter(status=TransactionStatus.PENDING)

    def expired_needing_update(self):
        return self.filter(expires_at__lt=timezone.now()).exclude(status__in=TERMINAL_STATES)

    def for_context(self, context_type, context_id=None):
        qs = self.filter(context_type=context_type)
        if context_id:
            qs = qs.filter(context_id=context_id)
        return qs

    def for_initiator(self, initiator_type, initiator_id):
        return self.filter(initiator_type=initiator_type, initiator_id=initiator_id)

    def for_target(self, target_type, target_id):
        return self.filter(target_type=target_type, target_id=target_id)

    def of_type(self, transaction_type):
        return self.filter(transaction_type=transaction_type)

    def needing_outcome_execution(self):
        return self.filter(status=TransactionStatus.ACCEPTED, outcome_executed=False)

    def with_logs(self):
        return self.prefetch_related("logs")


class TransactionManager(SoftDeleteManager):

    def get_queryset(self):
        return TransactionQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def create_transaction(self, **kwargs):
        kwargs.setdefault("status", TransactionStatus.CREATED)
        kwargs.setdefault("payload", {})
        return self.create(**kwargs)
```

---

## 6. New Audit Actions

Add to `AuditLog.Action` in `apps/core/observability/audit/models.py`:

```python
# Transaction System
TRANSACTION_CREATED = "txn.created", "Transaction Created"
TRANSACTION_ACCEPTED = "txn.accepted", "Transaction Accepted"
TRANSACTION_DENIED = "txn.denied", "Transaction Denied"
TRANSACTION_DISMISSED = "txn.dismissed", "Transaction Dismissed"
TRANSACTION_CANCELLED = "txn.cancelled", "Transaction Cancelled"
TRANSACTION_EXPIRED = "txn.expired", "Transaction Expired"
TRANSACTION_INVALIDATED = "txn.invalidated", "Transaction Invalidated"
```

Then run: `python manage.py makemigrations core`

---

## 7. Phase 1 Verification

After implementing all files above:

```bash
python manage.py makemigrations transaction
python manage.py migrate
python manage.py shell -c "from apps.transaction.models import Transaction, TransactionLog; print('Models OK')"
python manage.py shell -c "from apps.transaction.types import TRANSACTION_TYPES; print(f'{len(TRANSACTION_TYPES)} types registered')"
python manage.py shell -c "from apps.transaction.constants import VALID_TRANSITIONS; print('Constants OK')"
```

All 5 commands must succeed before moving to Phase 2.
