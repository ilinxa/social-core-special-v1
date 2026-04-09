"""
Chat Broadcast Utilities
========================
REST-to-WS bridge for broadcasting chat events from sync views.

Uses async_to_sync(channel_layer.group_send) to send events
from synchronous Django REST views to WebSocket consumers.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.chat.ws_serializers import (
    serialize_delivered_update,
    serialize_message,
    serialize_message_deleted,
    serialize_message_edited,
)
from apps.chat.ws_serializers import (
    serialize_reaction_update as _serialize_reaction_update,
)
from apps.chat.ws_serializers import serialize_seen_update
from apps.core.observability import get_logger

logger = get_logger(__name__)


def _get_layer():
    """Get the default channel layer."""
    return get_channel_layer()


def broadcast_message_new(message) -> None:
    """Broadcast a new message to the conversation group."""
    layer = _get_layer()
    if not layer:
        return

    payload = serialize_message(message)
    async_to_sync(layer.group_send)(
        f"conversation_{message.conversation_id}",
        {"type": "chat.message.new", "payload": payload},
    )


def broadcast_message_edited(message) -> None:
    """Broadcast an edited message to the conversation group."""
    layer = _get_layer()
    if not layer:
        return

    payload = serialize_message_edited(message)
    async_to_sync(layer.group_send)(
        f"conversation_{payload['conversation_id']}",
        {"type": "chat.message.edited", "payload": payload},
    )


def broadcast_message_deleted(message) -> None:
    """Broadcast a deleted message to the conversation group."""
    layer = _get_layer()
    if not layer:
        return

    payload = serialize_message_deleted(message)
    async_to_sync(layer.group_send)(
        f"conversation_{payload['conversation_id']}",
        {"type": "chat.message.deleted", "payload": payload},
    )


def broadcast_new_conversation(conversation, participant_ids: list) -> None:
    """
    Notify users when they're added to a new conversation.

    Sends to each participant's personal user_{id} group.
    """
    layer = _get_layer()
    if not layer:
        return

    payload = {
        "conversation_id": str(conversation.id),
        "conversation_type": conversation.conversation_type,
        "name": conversation.name,
        "scope_type": conversation.scope_type,
    }

    for uid in participant_ids:
        async_to_sync(layer.group_send)(
            f"user_{uid}",
            {"type": "chat.conversation.new", "payload": payload},
        )


def broadcast_message_deleted_by_ids(conversation_id, message_id) -> None:
    """Broadcast a deleted message using raw IDs (no message object needed)."""
    layer = _get_layer()
    if not layer:
        return

    payload = {
        "conversation_id": str(conversation_id),
        "message_id": str(message_id),
    }
    async_to_sync(layer.group_send)(
        f"conversation_{conversation_id}",
        {"type": "chat.message.deleted", "payload": payload},
    )


def broadcast_seen_update(
    conversation_id, participant_id, last_seen_message_id
) -> None:
    """Broadcast a seen watermark update to the conversation group."""
    layer = _get_layer()
    if not layer:
        return

    payload = serialize_seen_update(
        conversation_id, participant_id, last_seen_message_id
    )
    async_to_sync(layer.group_send)(
        f"conversation_{conversation_id}",
        {"type": "chat.seen.update", "payload": payload},
    )


def broadcast_delivered_update(
    conversation_id, participant_id, last_delivered_message_id
) -> None:
    """Broadcast a delivered watermark update to the conversation group."""
    layer = _get_layer()
    if not layer:
        return

    payload = serialize_delivered_update(
        conversation_id, participant_id, last_delivered_message_id
    )
    async_to_sync(layer.group_send)(
        f"conversation_{conversation_id}",
        {"type": "chat.delivered.update", "payload": payload},
    )


def broadcast_reaction_update(
    conversation_id, message_id, user_id, reaction, action
) -> None:
    """Broadcast a reaction add/remove event to the conversation group."""
    layer = _get_layer()
    if not layer:
        return

    payload = _serialize_reaction_update(
        conversation_id, message_id, user_id, reaction, action
    )
    async_to_sync(layer.group_send)(
        f"conversation_{conversation_id}",
        {"type": "chat.reaction.update", "payload": payload},
    )
