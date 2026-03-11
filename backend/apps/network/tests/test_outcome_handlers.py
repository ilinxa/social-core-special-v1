# apps/network/tests/test_outcome_handlers.py
import uuid

import pytest
from unittest.mock import MagicMock

from apps.core.types import ActorContext
from apps.network.models import Follow, FollowStatus, Connection, ConnectionStatus
from apps.network.outcome_handlers import FollowOutcomeHandler, ConnectionOutcomeHandler
from apps.users.tests.factories import UserFactory


def _make_transaction_mock(**kwargs):
    """Create a mock Transaction with given attributes."""
    txn = MagicMock()
    txn.id = kwargs.get("id", uuid.uuid4())
    txn.transaction_type = kwargs.get("transaction_type", "business_follow_request")
    txn.initiator_id = kwargs.get("initiator_id", uuid.uuid4())
    txn.target_id = kwargs.get("target_id", uuid.uuid4())
    txn.context_type = kwargs.get("context_type", "business")
    txn.context_id = kwargs.get("context_id", uuid.uuid4())
    txn.payload = kwargs.get("payload", {})
    txn.mode = kwargs.get("mode", "request")
    txn.status = kwargs.get("status", "accepted")
    return txn


@pytest.mark.django_db
class TestFollowOutcomeHandler:

    def test_handle_accepted_creates_follow(self):
        user = UserFactory()
        business_id = uuid.uuid4()

        txn = _make_transaction_mock(
            initiator_id=user.id,
            context_type="business",
            context_id=business_id,
        )
        actor_context = ActorContext.for_user_context(user)

        FollowOutcomeHandler.handle_accepted(
            transaction=txn,
            actor_context=actor_context,
        )

        follow = Follow.objects.get(follower=user)
        assert follow.followee_type == "business"
        assert follow.followee_id == business_id
        assert follow.status == FollowStatus.ACTIVE

    def test_handle_accepted_platform_follow(self):
        user = UserFactory()
        platform_id = uuid.uuid4()

        txn = _make_transaction_mock(
            transaction_type="platform_follow_request",
            initiator_id=user.id,
            context_type="platform",
            context_id=platform_id,
        )
        actor_context = ActorContext.for_user_context(user)

        FollowOutcomeHandler.handle_accepted(
            transaction=txn,
            actor_context=actor_context,
        )

        follow = Follow.objects.get(follower=user)
        assert follow.followee_type == "platform"
        assert follow.followee_id == platform_id


@pytest.mark.django_db
class TestConnectionOutcomeHandler:

    def test_handle_user_accepted_creates_connection(self):
        user_a = UserFactory()
        user_b = UserFactory()

        txn = _make_transaction_mock(
            transaction_type="user_connection_request",
            initiator_id=user_a.id,
            target_id=user_b.id,
            payload={"note": "Let's connect!"},
        )
        actor_context = ActorContext.for_user_context(user_b)

        ConnectionOutcomeHandler.handle_user_accepted(
            transaction=txn,
            actor_context=actor_context,
        )

        conn = Connection.objects.first()
        assert conn is not None
        assert conn.status == ConnectionStatus.ACTIVE
        assert conn.note == "Let's connect!"
        assert conn.initiated_by_id == user_a.id

    def test_handle_account_accepted_creates_connection(self):
        initiator = UserFactory()
        biz_a_id = uuid.uuid4()
        biz_b_id = uuid.uuid4()

        txn = _make_transaction_mock(
            transaction_type="business_connection_request",
            initiator_id=initiator.id,
            context_type="business",
            context_id=biz_b_id,
            payload={
                "initiator_account_type": "business",
                "initiator_account_id": str(biz_a_id),
                "note": "Partnership",
            },
        )
        actor_context = ActorContext.for_user_context(initiator)

        ConnectionOutcomeHandler.handle_account_accepted(
            transaction=txn,
            actor_context=actor_context,
        )

        conn = Connection.objects.first()
        assert conn is not None
        assert conn.connection_type == "account_account"
        assert conn.status == ConnectionStatus.ACTIVE
        assert conn.note == "Partnership"
