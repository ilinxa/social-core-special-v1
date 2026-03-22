from django.db import models
from django.utils import timezone

from apps.core.models import SoftDeleteManager
from apps.transaction.constants import TERMINAL_STATES, TransactionStatus


class TransactionQuerySet(models.QuerySet):

    def active(self):
        return self.exclude(status__in=TERMINAL_STATES)

    def pending(self):
        return self.filter(status=TransactionStatus.PENDING)

    def expired_needing_update(self):
        return self.filter(
            expires_at__lt=timezone.now(),
        ).exclude(status__in=TERMINAL_STATES)

    def for_context(self, context_type, context_id=None):
        qs = self.filter(context_type=context_type)
        if context_id:
            qs = qs.filter(context_id=context_id)
        return qs

    def for_initiator(self, initiator_type, initiator_id):
        return self.filter(
            initiator_type=initiator_type,
            initiator_id=initiator_id,
        )

    def for_target(self, target_type, target_id):
        return self.filter(
            target_type=target_type,
            target_id=target_id,
        )

    def of_type(self, transaction_type):
        return self.filter(transaction_type=transaction_type)

    def needing_outcome_execution(self):
        return self.filter(
            status=TransactionStatus.ACCEPTED,
            outcome_executed=False,
        )

    def with_logs(self):
        return self.prefetch_related("logs")


class TransactionManager(SoftDeleteManager):

    def get_queryset(self):
        return TransactionQuerySet(self.model, using=self._db).filter(
            is_deleted=False,
        )

    # Delegate custom QuerySet methods to the underlying TransactionQuerySet
    # so they are accessible directly from Transaction.objects.<method>().
    def active(self):
        return self.get_queryset().active()

    def pending(self):
        return self.get_queryset().pending()

    def expired_needing_update(self):
        return self.get_queryset().expired_needing_update()

    def for_context(self, context_type, context_id=None):
        return self.get_queryset().for_context(context_type, context_id)

    def for_initiator(self, initiator_type, initiator_id):
        return self.get_queryset().for_initiator(initiator_type, initiator_id)

    def for_target(self, target_type, target_id):
        return self.get_queryset().for_target(target_type, target_id)

    def of_type(self, transaction_type):
        return self.get_queryset().of_type(transaction_type)

    def needing_outcome_execution(self):
        return self.get_queryset().needing_outcome_execution()

    def with_logs(self):
        return self.get_queryset().with_logs()

    def create_transaction(self, **kwargs):
        kwargs.setdefault("status", TransactionStatus.CREATED)
        kwargs.setdefault("payload", {})
        return self.create(**kwargs)
