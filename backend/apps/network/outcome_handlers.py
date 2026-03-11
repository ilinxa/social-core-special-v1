# apps/network/outcome_handlers.py
"""
Network Outcome Handlers — Called by the Transaction system when
follow/connection transactions reach terminal states.
"""

from django.db import transaction as db_transaction

from apps.core.observability import get_logger
from apps.core.types import ActorContext
from apps.transaction.models import Transaction

logger = get_logger(__name__)


class FollowOutcomeHandler:

    @staticmethod
    @db_transaction.atomic
    def handle_accepted(
        *, transaction: Transaction, actor_context: ActorContext,
        acceptance_payload: dict = None,
    ):
        """
        Follow transaction accepted → create Follow record.

        Works for all follow types:
        - business_follow_request (AUTO_APPROVAL — actor is the follower)
        - business_follow_approval_request (ACCOUNT_AUTHORITY — target accepted)
        - platform_follow_request (AUTO_APPROVAL)
        """
        from django.contrib.auth import get_user_model
        from apps.network.services import FollowService

        User = get_user_model()
        follower = User.objects.get(id=transaction.initiator_id)

        FollowService.create_follow(
            follower=follower,
            followee_type=transaction.context_type,
            followee_id=transaction.context_id,
            transaction_id=transaction.id,
        )
        logger.info(
            "outcome.follow.accepted",
            transaction_id=str(transaction.id),
            follower_id=str(follower.id),
        )


class ConnectionOutcomeHandler:

    @staticmethod
    @db_transaction.atomic
    def handle_user_accepted(
        *, transaction: Transaction, actor_context: ActorContext,
        acceptance_payload: dict = None,
    ):
        """
        User connection request accepted → create Connection record.

        initiator = requester (user_a or user_b after canonical ordering)
        target = accepter
        """
        from apps.network.services import ConnectionService

        note = (transaction.payload or {}).get("note", "")

        ConnectionService.create_user_connection(
            user_a_id=transaction.initiator_id,
            user_b_id=transaction.target_id,
            note=note,
            initiated_by_id=transaction.initiator_id,
            transaction_id=transaction.id,
        )
        logger.info(
            "outcome.connection.user_accepted",
            transaction_id=str(transaction.id),
        )

    @staticmethod
    @db_transaction.atomic
    def handle_account_accepted(
        *, transaction: Transaction, actor_context: ActorContext,
        acceptance_payload: dict = None,
    ):
        """
        Account connection request accepted → create Connection record.

        The initiating business identity is stored in the transaction payload
        (because create_request() uses USER as initiator, not MEMBERSHIP_ACTOR).
        """
        from apps.network.services import ConnectionService

        payload = transaction.payload or {}
        initiator_account_type = payload["initiator_account_type"]
        initiator_account_id = payload["initiator_account_id"]
        note = payload.get("note", "")

        # Target account is the transaction target
        target_account_type = transaction.context_type
        target_account_id = transaction.context_id

        ConnectionService.create_account_connection(
            a_type=initiator_account_type,
            a_id=initiator_account_id,
            b_type=target_account_type,
            b_id=target_account_id,
            initiated_by_id=transaction.initiator_id,
            note=note,
            transaction_id=transaction.id,
        )
        logger.info(
            "outcome.connection.account_accepted",
            transaction_id=str(transaction.id),
        )
