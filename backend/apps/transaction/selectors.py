from uuid import UUID

from django.db.models import QuerySet
from django.utils import timezone

from apps.core.exceptions import NotFound
from apps.transaction.constants import TransactionStatus
from apps.transaction.models import Transaction, TransactionLog


class TransactionSelector:

    @staticmethod
    def get_by_id(*, transaction_id: UUID) -> Transaction:
        txn = Transaction.objects.filter(id=transaction_id).first()
        if not txn:
            raise NotFound(
                resource="Transaction",
                resource_id=str(transaction_id),
            )
        return txn

    @staticmethod
    def get_by_id_or_none(*, transaction_id: UUID) -> Transaction | None:
        return Transaction.objects.filter(id=transaction_id).first()

    @staticmethod
    def get_by_id_with_logs(*, transaction_id: UUID) -> Transaction:
        txn = Transaction.objects.with_logs().filter(id=transaction_id).first()
        if not txn:
            raise NotFound(
                resource="Transaction",
                resource_id=str(transaction_id),
            )
        return txn

    @staticmethod
    def exists_active(
        *,
        transaction_type: str,
        initiator_id: UUID,
        target_id: UUID,
    ) -> bool:
        return (
            Transaction.objects.filter(
                transaction_type=transaction_type,
                initiator_id=initiator_id,
                target_id=target_id,
            )
            .active()
            .exists()
        )

    @staticmethod
    def has_active_in_conflict_group(
        *,
        conflict_group: str,
        user_id: UUID,
        context_type: str,
        context_id: UUID,
    ) -> Transaction | None:
        """Check for any active transaction in the same conflict group
        involving this user for this account context.

        Returns the conflicting Transaction if found, else None.
        """
        from django.db.models import Q

        from apps.transaction.types import get_conflict_group_types

        type_ids = get_conflict_group_types(conflict_group)
        if not type_ids:
            return None

        return (
            Transaction.objects.filter(
                transaction_type__in=type_ids,
                context_type=context_type,
                context_id=context_id,
            )
            .filter(
                Q(target_id=user_id, target_type="user")
                | TransactionSelector._user_as_initiator_q(user_id)
            )
            .active()
            .first()
        )

    @staticmethod
    def _user_as_initiator_q(user_id: UUID) -> "Q":
        """Q filter matching transactions where user is the initiator.

        Covers both direct user-type initiators AND membership_actor
        initiators (where user_id is stored in initiator_context JSON).
        """
        from django.db.models import Q

        return Q(initiator_id=user_id, initiator_type="user") | Q(
            initiator_type="membership_actor",
            initiator_context__user_id=str(user_id),
        )

    @staticmethod
    def list_for_user_as_initiator(
        *,
        user_id: UUID,
        include_terminal: bool = False,
    ) -> QuerySet:
        qs = Transaction.objects.filter(
            TransactionSelector._user_as_initiator_q(user_id),
        )
        if not include_terminal:
            qs = qs.active()
        return qs.order_by("-created_at")

    @staticmethod
    def list_for_user_as_target(
        *,
        user_id: UUID,
        include_terminal: bool = False,
    ) -> QuerySet:
        qs = Transaction.objects.for_target(
            target_type="user",
            target_id=user_id,
        )
        if not include_terminal:
            qs = qs.active()
        return qs.order_by("-created_at")

    @staticmethod
    def list_for_user(
        *,
        user_id: UUID,
        include_terminal: bool = False,
    ) -> QuerySet:
        """Combined initiator+target query using Q objects (supports .filter())."""
        from django.db.models import Q

        qs = Transaction.objects.filter(
            TransactionSelector._user_as_initiator_q(user_id)
            | Q(target_id=user_id, target_type="user")
        )
        if not include_terminal:
            qs = qs.active()
        return qs.order_by("-created_at")

    @staticmethod
    def list_for_context(
        *,
        context_type: str,
        context_id: UUID,
        include_terminal: bool = False,
    ) -> QuerySet:
        """All transactions for an account context (business/platform).

        Used by bconsole/pconsole to view all transactions within their account,
        regardless of whether the viewing user is personally the initiator or target.
        """
        qs = Transaction.objects.for_context(
            context_type=context_type,
            context_id=context_id,
        )
        if not include_terminal:
            qs = qs.active()
        return qs.order_by("-created_at")

    @staticmethod
    def apply_permission_filters(
        qs: "QuerySet[Transaction]",
        actor_context: "ActorContext",
    ) -> "QuerySet[Transaction]":
        """Exclude transaction types whose approval_permission the actor lacks.

        Used to hide permission-gated transaction types (e.g., business creation
        requests) from platform members who don't have the required permission.
        """
        from apps.transaction.types import TRANSACTION_TYPES

        excluded_types = [
            type_id
            for type_id, config in TRANSACTION_TYPES.items()
            if config.approval_permission
            and not actor_context.has_permission(config.approval_permission)
        ]
        if excluded_types:
            qs = qs.exclude(transaction_type__in=excluded_types)
        return qs

    @staticmethod
    def list_pending_for_context(
        *,
        context_type: str,
        context_id: UUID,
        transaction_type: str | None = None,
    ) -> QuerySet:
        qs = Transaction.objects.for_context(
            context_type=context_type,
            context_id=context_id,
        ).pending()
        if transaction_type:
            qs = qs.of_type(transaction_type)
        return qs.order_by("-created_at")

    @staticmethod
    def list_expired_needing_update() -> QuerySet:
        return Transaction.objects.expired_needing_update()

    @staticmethod
    def get_resubmission_cooldown(
        *,
        transaction_type: str,
        initiator_id: UUID,
        target_id: UUID,
    ) -> timezone.datetime | None:
        from apps.transaction.types import get_transaction_type

        config = get_transaction_type(transaction_type)
        if config.resubmission_cooldown_days == 0:
            return None

        last_denied = (
            Transaction.objects.filter(
                transaction_type=transaction_type,
                initiator_id=initiator_id,
                target_id=target_id,
                status=TransactionStatus.DENIED,
            )
            .order_by("-resolved_at")
            .first()
        )

        if not last_denied or not last_denied.resolved_at:
            return None

        from datetime import timedelta

        cooldown_end = last_denied.resolved_at + timedelta(
            days=config.resubmission_cooldown_days,
        )
        return cooldown_end if timezone.now() < cooldown_end else None

    @staticmethod
    def get_by_form_response_id(*, form_response_id: UUID) -> Transaction | None:
        return Transaction.objects.filter(
            form_response_id=form_response_id,
        ).first()

    @staticmethod
    def get_form_template_for_type(*, transaction_type: str):
        """Get the required form template for a transaction type."""
        from apps.core.constants import OwnerType
        from apps.forms.selectors import FormTemplateSelector
        from apps.transaction.types import get_transaction_type

        config = get_transaction_type(transaction_type)
        slug = config.required_form_template_slug or config.optional_form_template_slug
        if slug:
            return FormTemplateSelector.get_by_slug_or_none(
                owner_type=OwnerType.SYSTEM,
                owner_id=None,
                slug=slug,
            )
        return None

    @staticmethod
    def get_form_mapping_for_transaction(*, transaction: Transaction):
        """Get the custom form mapping for a transaction's type and context."""
        from apps.transaction.models import TransactionFormMapping

        return (
            TransactionFormMapping.objects.filter(
                account_type=transaction.context_type,
                account_id=transaction.context_id,
                transaction_type=transaction.transaction_type,
            )
            .select_related("form_template")
            .first()
        )

    @staticmethod
    def list_all_transactions(
        *,
        status: str | None = None,
        mode: str | None = None,
        transaction_type: str | None = None,
        context_type: str | None = None,
        include_terminal: bool = True,
    ) -> QuerySet:
        """Global transaction listing for governance. All accounts."""
        qs = Transaction.objects.all()

        if not include_terminal:
            qs = qs.active()

        if status:
            qs = qs.filter(status=status)
        if mode:
            qs = qs.filter(mode=mode)
        if transaction_type:
            qs = qs.filter(transaction_type=transaction_type)
        if context_type:
            qs = qs.filter(context_type=context_type)

        return qs.order_by("-created_at")


class TransactionLogSelector:

    @staticmethod
    def list_for_transaction(*, transaction_id: UUID) -> QuerySet:
        return TransactionLog.objects.filter(
            transaction_id=transaction_id,
        ).order_by("-timestamp")
