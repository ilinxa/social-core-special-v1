import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.constants import ContextType
from apps.core.models import AuditModel, UUIDModel
from apps.transaction.constants import (
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    PartyType,
    TransactionMode,
    TransactionStatus,
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
    initiator_context = models.JSONField(
        default=dict,
        help_text="ActorContext.to_dict() snapshot at creation",
    )

    # Target
    target_type = models.CharField(max_length=20, choices=PartyType.choices)
    target_id = models.UUIDField(help_text="User UUID or Account UUID")

    # Context
    context_type = models.CharField(
        max_length=20,
        choices=ContextType.choices,
        db_index=True,
    )
    context_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Account UUID. NULL for user context.",
    )

    # State
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.CREATED,
        db_index=True,
    )

    # Payload
    payload = models.JSONField(default=dict)
    form_response_id = models.UUIDField(null=True, blank=True, db_index=True)

    # Info Request
    info_requested_at = models.DateTimeField(null=True, blank=True)
    info_requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="info_requested_transactions",
    )
    info_requested_message = models.TextField(blank=True, default="")
    info_requested_fields = models.JSONField(default=list)

    # Timing
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Resolution
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_transactions",
    )
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
        verbose_name = "transaction"
        verbose_name_plural = "transactions"
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
                check=models.Q(context_type="user")
                | models.Q(context_id__isnull=False),
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
        return new_status in VALID_TRANSITIONS.get(self.status, [])


class TransactionLog(models.Model):
    """
    Immutable audit log for transaction state changes.
    Does NOT inherit from base models — standalone with UUID PK.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    event_type = models.CharField(max_length=50, db_index=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    actor_context = models.JSONField(default=dict)
    previous_status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        blank=True,
    )
    new_status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
    )
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = "transaction_log"
        verbose_name = "transaction log"
        verbose_name_plural = "transaction logs"
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


class TransactionFormMapping(UUIDModel, AuditModel):
    """Maps a transaction type to a custom form template for an account."""

    account_type = models.CharField(max_length=20, choices=ContextType.choices)
    account_id = models.UUIDField(db_index=True)
    transaction_type = models.CharField(max_length=100, db_index=True)
    form_template = models.ForeignKey(
        "forms.FormTemplate",
        on_delete=models.CASCADE,
        related_name="transaction_mappings",
    )
    is_required = models.BooleanField(default=False)

    class Meta:
        db_table = "transaction_form_mapping"
        verbose_name = "transaction form mapping"
        verbose_name_plural = "transaction form mappings"
        constraints = [
            models.UniqueConstraint(
                fields=["account_type", "account_id", "transaction_type"],
                condition=models.Q(is_deleted=False),
                name="unique_active_form_mapping_per_type",
            ),
        ]

    def __str__(self):
        return f"{self.transaction_type} -> {self.form_template_id}"
