from datetime import timedelta
from uuid import uuid4

import factory
from django.utils import timezone

from apps.core.constants import ContextType
from apps.transaction.constants import PartyType, TransactionMode, TransactionStatus
from apps.transaction.models import Transaction, TransactionLog


class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction

    transaction_type = "business_membership_invitation"
    mode = TransactionMode.INVITATION
    initiator_type = PartyType.MEMBERSHIP_ACTOR
    initiator_id = factory.LazyFunction(uuid4)
    initiator_context = factory.LazyFunction(dict)
    target_type = PartyType.USER
    target_id = factory.LazyFunction(uuid4)
    context_type = ContextType.BUSINESS
    context_id = factory.LazyFunction(uuid4)
    status = TransactionStatus.PENDING
    payload = factory.LazyFunction(dict)
    expires_at = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=7),
    )


class TransactionLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TransactionLog

    transaction = factory.SubFactory(TransactionFactory)
    event_type = "state_changed"
    actor_context = factory.LazyFunction(dict)
    previous_status = TransactionStatus.CREATED
    new_status = TransactionStatus.PENDING
    metadata = factory.LazyFunction(dict)


class PendingInvitationFactory(TransactionFactory):
    """Shortcut for a PENDING invitation."""

    mode = TransactionMode.INVITATION
    status = TransactionStatus.PENDING
    initiator_type = PartyType.MEMBERSHIP_ACTOR


class PendingRequestFactory(TransactionFactory):
    """Shortcut for a PENDING request."""

    transaction_type = "business_membership_request"
    mode = TransactionMode.REQUEST
    status = TransactionStatus.PENDING
    initiator_type = PartyType.USER
