"""
Chat WebSocket Serializers
==========================
Lightweight dict-based serializers for WebSocket event payloads.

Plain functions returning dicts — NOT DRF serializers (no overhead).
Output shapes match REST serializer shapes for frontend consistency.
"""

from apps.chat.serializers import _resolve_participant_display


def serialize_attachment(attachment) -> dict:
    """Serialize a MessageAttachment for WS broadcast."""
    from django.core.files.storage import default_storage

    return {
        "id": str(attachment.id),
        "file_type": attachment.file_type,
        "original_filename": attachment.original_filename,
        "mime_type": attachment.mime_type,
        "file_size": attachment.file_size,
        "width": attachment.width,
        "height": attachment.height,
        "url": default_storage.url(attachment.storage_key),
    }


def serialize_message(message) -> dict:
    """
    Serialize a Message instance for WS broadcast.

    Matches REST MessageOutputSerializer fields:
    id, conversation_id, sender_type, sender_id, sender_name,
    sender_avatar_url, content_type, content, status,
    sequence_number, edited_at, created_at, attachments
    """
    from apps.chat.models import MessageAttachment

    sender_name, sender_avatar_url = _resolve_participant_display(
        message.sender_type, message.sender_id
    )

    attachments = MessageAttachment.objects.filter(message=message).order_by(
        "created_at"
    )

    return {
        "id": str(message.id),
        "conversation_id": str(message.conversation_id),
        "sender_type": message.sender_type,
        "sender_id": str(message.sender_id),
        "sender_name": sender_name,
        "sender_avatar_url": sender_avatar_url,
        "content_type": message.content_type,
        "content": message.content,
        "status": message.status,
        "sequence_number": message.sequence_number,
        "edited_at": (message.edited_at.isoformat() if message.edited_at else None),
        "created_at": message.created_at.isoformat(),
        "attachments": [serialize_attachment(att) for att in attachments],
    }


def serialize_message_edited(message) -> dict:
    """Serialize an edited message for WS broadcast."""
    return {
        "conversation_id": str(message.conversation_id),
        "message_id": str(message.id),
        "content": message.content,
        "edited_at": (message.edited_at.isoformat() if message.edited_at else None),
    }


def serialize_message_deleted(message) -> dict:
    """Serialize a deleted message for WS broadcast."""
    return {
        "conversation_id": str(message.conversation_id),
        "message_id": str(message.id),
    }


def serialize_typing(conversation_id, user_id, is_typing: bool) -> dict:
    """Serialize a typing indicator for WS broadcast."""
    return {
        "conversation_id": str(conversation_id),
        "user_id": str(user_id),
        "is_typing": is_typing,
    }


def serialize_seen_update(
    conversation_id, participant_id, last_seen_message_id
) -> dict:
    """Serialize a seen watermark update for WS broadcast."""
    return {
        "conversation_id": str(conversation_id),
        "participant_id": str(participant_id),
        "last_seen_message_id": str(last_seen_message_id),
    }


def serialize_delivered_update(
    conversation_id, participant_id, last_delivered_message_id
) -> dict:
    """Serialize a delivered watermark update for WS broadcast."""
    return {
        "conversation_id": str(conversation_id),
        "participant_id": str(participant_id),
        "last_delivered_message_id": str(last_delivered_message_id),
    }


def serialize_presence(user_id, is_online: bool) -> dict:
    """Serialize a presence update for WS broadcast."""
    return {
        "user_id": str(user_id),
        "is_online": is_online,
    }


def serialize_reaction_update(
    conversation_id, message_id, user_id, reaction, action
) -> dict:
    """Serialize a reaction add/remove event for WS broadcast."""
    return {
        "conversation_id": str(conversation_id),
        "message_id": str(message_id),
        "user_id": str(user_id),
        "reaction": reaction,
        "action": action,
    }
