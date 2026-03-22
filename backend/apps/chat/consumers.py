"""
Chat Consumer
=============
WebSocket consumer for real-time chat.

Single connection per user at ws/chat/?token=<jwt>.
Multiplexes all conversations over one pipe.
Calls existing ChatService/ChatSelector via database_sync_to_async.
"""

import asyncio
import json
from uuid import UUID

from channels.db import database_sync_to_async
from django.core.serializers.json import DjangoJSONEncoder

from apps.auth.consumers import AuthenticatedConsumer
from apps.chat.constants import (
    ParticipantType,
    WS_HEARTBEAT_INTERVAL_SECONDS,
    WS_MAX_PRESENCE_SUBSCRIPTIONS,
)
from apps.core.observability import get_logger

logger = get_logger(__name__)


class ChatConsumer(AuthenticatedConsumer):
    """
    Real-time chat consumer.

    Lifecycle:
        on_authenticated() → join user + conversation groups, start presence
        receive_authenticated() → dispatch event → call service → broadcast
        on_disconnect() → leave groups, stop presence
    """

    EVENT_HANDLERS = {
        "message.send": "_handle_message_send",
        "message.edit": "_handle_message_edit",
        "message.delete": "_handle_message_delete",
        "typing.start": "_handle_typing_start",
        "typing.stop": "_handle_typing_stop",
        "seen": "_handle_seen",
        "delivered": "_handle_delivered",
        "presence.subscribe": "_handle_presence_subscribe",
        "conversation.join": "_handle_conversation_join",
        "conversation.leave": "_handle_conversation_leave",
        "reaction.add": "_handle_reaction_add",
        "reaction.remove": "_handle_reaction_remove",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._heartbeat_task = None
        self._joined_conversations = set()
        self._presence_subscriptions = set()

    @classmethod
    async def encode_json(cls, content):
        """Override to handle UUID serialization."""
        return json.dumps(content, cls=DjangoJSONEncoder)

    # =========================================================================
    # LIFECYCLE HOOKS
    # =========================================================================

    async def on_authenticated(self):
        """Join channel groups and start presence heartbeat."""
        user = self.scope["user"]
        user_id = str(user.id)

        # Join personal user group
        await self.channel_layer.group_add(
            f"user_{user_id}", self.channel_name
        )

        # Join all conversation groups
        conversation_ids = await self._get_user_conversation_ids(user.id)
        for conv_id in conversation_ids:
            group_name = f"conversation_{conv_id}"
            await self.channel_layer.group_add(group_name, self.channel_name)
            self._joined_conversations.add(str(conv_id))

        # Set presence online and start heartbeat
        await self._set_presence_online(user.id)
        self._heartbeat_task = asyncio.ensure_future(
            self._heartbeat_loop(user.id)
        )

        logger.info(
            "chat.ws.connected",
            user_id=user_id,
            conversations=len(conversation_ids),
        )

    async def on_disconnect(self):
        """Leave groups and clear presence."""
        user = self.scope["user"]
        user_id = str(user.id)

        # Cancel heartbeat
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Leave all conversation groups
        for conv_id in self._joined_conversations:
            await self.channel_layer.group_discard(
                f"conversation_{conv_id}", self.channel_name
            )
        self._joined_conversations.clear()

        # Leave presence subscription groups
        for uid in self._presence_subscriptions:
            await self.channel_layer.group_discard(
                f"presence_{uid}", self.channel_name
            )
        self._presence_subscriptions.clear()

        # Leave personal group
        await self.channel_layer.group_discard(
            f"user_{user_id}", self.channel_name
        )

        # Set offline and broadcast
        await self._set_presence_offline(user.id)
        await self._broadcast_presence(user_id, is_online=False)

        logger.info("chat.ws.disconnected", user_id=user_id)

    # =========================================================================
    # EVENT DISPATCH
    # =========================================================================

    async def receive_authenticated(self, content):
        """Dispatch incoming events to handlers."""
        event_type = content.get("type")

        if not event_type:
            await self._send_error("missing_type", "Event type is required")
            return

        handler_name = self.EVENT_HANDLERS.get(event_type)
        if not handler_name:
            await self._send_error(
                "unknown_event", f"Unknown event type: {event_type}"
            )
            return

        handler = getattr(self, handler_name)
        try:
            await handler(content)
        except Exception as e:
            error_payload = self._format_error(e)
            await self.send_json({"type": "error", **error_payload})

    # =========================================================================
    # MESSAGE HANDLERS
    # =========================================================================

    async def _handle_message_send(self, content):
        """Handle message.send event."""
        conversation_id = content.get("conversation_id")
        text_content = content.get("content", "")
        attachment_ids_raw = content.get("attachment_ids", [])

        if not conversation_id or (not text_content and not attachment_ids_raw):
            await self._send_error(
                "invalid_payload",
                "conversation_id and (content or attachment_ids) are required",
            )
            return

        user = self.scope["user"]
        sender_type = content.get("sender_type", ParticipantType.USER)
        sender_id = content.get("sender_id", str(user.id))
        content_type = content.get("content_type", "text")

        # Convert attachment_ids from strings to UUIDs
        attachment_ids = None
        if attachment_ids_raw:
            try:
                attachment_ids = [UUID(str(aid)) for aid in attachment_ids_raw]
            except (ValueError, AttributeError):
                await self._send_error(
                    "invalid_payload", "attachment_ids must be valid UUIDs"
                )
                return

        # For entity senders, acting_user_id is the authenticated user
        # For user senders, the service auto-sets it to None (services.py:306)
        acting_user_id = user.id

        message = await self._db_send_message(
            conversation_id=UUID(conversation_id),
            sender_type=sender_type,
            sender_id=UUID(str(sender_id)),
            acting_user_id=acting_user_id,
            content=text_content,
            content_type=content_type,
            attachment_ids=attachment_ids,
        )

        # Serialize and broadcast to conversation group
        from apps.chat.ws_serializers import serialize_message

        payload = await database_sync_to_async(serialize_message)(message)

        await self.channel_layer.group_send(
            f"conversation_{conversation_id}",
            {"type": "chat.message.new", "payload": payload},
        )

    async def _handle_message_edit(self, content):
        """Handle message.edit event."""
        message_id = content.get("message_id")
        new_content = content.get("content")

        if not message_id or not new_content:
            await self._send_error(
                "invalid_payload",
                "message_id and content are required",
            )
            return

        user = self.scope["user"]
        message = await self._db_edit_message(
            message_id=UUID(message_id),
            new_content=new_content,
            user=user,
        )

        from apps.chat.ws_serializers import serialize_message_edited

        payload = serialize_message_edited(message)

        await self.channel_layer.group_send(
            f"conversation_{payload['conversation_id']}",
            {"type": "chat.message.edited", "payload": payload},
        )

    async def _handle_message_delete(self, content):
        """Handle message.delete event."""
        message_id = content.get("message_id")

        if not message_id:
            await self._send_error(
                "invalid_payload", "message_id is required"
            )
            return

        user = self.scope["user"]

        # Get message before deletion to know conversation_id
        message = await self._db_get_message(UUID(message_id))
        conversation_id = str(message.conversation_id)

        await self._db_delete_message(message_id=UUID(message_id), user=user)

        from apps.chat.ws_serializers import serialize_message_deleted

        payload = serialize_message_deleted(message)

        await self.channel_layer.group_send(
            f"conversation_{conversation_id}",
            {"type": "chat.message.deleted", "payload": payload},
        )

    # =========================================================================
    # REACTION HANDLERS
    # =========================================================================

    async def _handle_reaction_add(self, content):
        """Handle reaction.add — add reaction and broadcast to conversation."""
        message_id = content.get("message_id")
        reaction = content.get("reaction")

        if not message_id or not reaction:
            await self._send_error(
                "invalid_payload", "message_id and reaction are required"
            )
            return

        user = self.scope["user"]
        reaction_obj = await self._db_add_reaction(
            message_id=UUID(message_id),
            user=user,
            reaction=reaction,
        )

        # Get conversation_id for broadcast group
        message = await self._db_get_message(UUID(message_id))

        from apps.chat.ws_serializers import serialize_reaction_update

        payload = serialize_reaction_update(
            message.conversation_id, message_id, user.id, reaction, "add"
        )

        await self.channel_layer.group_send(
            f"conversation_{message.conversation_id}",
            {"type": "chat.reaction.update", "payload": payload},
        )

    async def _handle_reaction_remove(self, content):
        """Handle reaction.remove — remove reaction and broadcast to conversation."""
        message_id = content.get("message_id")
        reaction = content.get("reaction")

        if not message_id or not reaction:
            await self._send_error(
                "invalid_payload", "message_id and reaction are required"
            )
            return

        user = self.scope["user"]

        # Get conversation_id before deletion
        message = await self._db_get_message(UUID(message_id))

        await self._db_remove_reaction(
            message_id=UUID(message_id),
            user=user,
            reaction=reaction,
        )

        from apps.chat.ws_serializers import serialize_reaction_update

        payload = serialize_reaction_update(
            message.conversation_id, message_id, user.id, reaction, "remove"
        )

        await self.channel_layer.group_send(
            f"conversation_{message.conversation_id}",
            {"type": "chat.reaction.update", "payload": payload},
        )

    # =========================================================================
    # TYPING HANDLERS
    # =========================================================================

    async def _handle_typing_start(self, content):
        """Handle typing.start event — no DB, broadcast only."""
        await self._broadcast_typing(content, is_typing=True)

    async def _handle_typing_stop(self, content):
        """Handle typing.stop event — no DB, broadcast only."""
        await self._broadcast_typing(content, is_typing=False)

    async def _broadcast_typing(self, content, is_typing: bool):
        """Broadcast typing indicator to conversation group (no self-echo)."""
        conversation_id = content.get("conversation_id")
        if not conversation_id:
            await self._send_error(
                "invalid_payload", "conversation_id is required"
            )
            return

        user = self.scope["user"]

        from apps.chat.ws_serializers import serialize_typing

        payload = serialize_typing(conversation_id, user.id, is_typing)

        await self.channel_layer.group_send(
            f"conversation_{conversation_id}",
            {
                "type": "chat.typing",
                "payload": payload,
                "exclude_channel": self.channel_name,
            },
        )

    # =========================================================================
    # WATERMARK HANDLERS
    # =========================================================================

    async def _handle_seen(self, content):
        """Handle seen event — update watermark and broadcast."""
        conversation_id = content.get("conversation_id")
        last_seen_message_id = content.get("last_seen_message_id")

        if not conversation_id or not last_seen_message_id:
            await self._send_error(
                "invalid_payload",
                "conversation_id and last_seen_message_id are required",
            )
            return

        user = self.scope["user"]
        await self._db_update_seen(
            conversation_id=UUID(conversation_id),
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            last_seen_message_id=UUID(last_seen_message_id),
        )

        from apps.chat.ws_serializers import serialize_seen_update

        payload = serialize_seen_update(
            conversation_id, user.id, last_seen_message_id
        )
        await self.channel_layer.group_send(
            f"conversation_{conversation_id}",
            {"type": "chat.seen.update", "payload": payload},
        )

    async def _handle_delivered(self, content):
        """Handle delivered event — update watermark and broadcast."""
        conversation_id = content.get("conversation_id")
        last_delivered_message_id = content.get("last_delivered_message_id")

        if not conversation_id or not last_delivered_message_id:
            await self._send_error(
                "invalid_payload",
                "conversation_id and last_delivered_message_id are required",
            )
            return

        user = self.scope["user"]
        await self._db_update_delivered(
            conversation_id=UUID(conversation_id),
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            last_delivered_message_id=UUID(last_delivered_message_id),
        )

        from apps.chat.ws_serializers import serialize_delivered_update

        payload = serialize_delivered_update(
            conversation_id, user.id, last_delivered_message_id
        )
        await self.channel_layer.group_send(
            f"conversation_{conversation_id}",
            {"type": "chat.delivered.update", "payload": payload},
        )

    # =========================================================================
    # PRESENCE HANDLER
    # =========================================================================

    async def _handle_presence_subscribe(self, content):
        """Subscribe to presence updates for specified users."""
        user_ids = content.get("user_ids", [])

        if not isinstance(user_ids, list):
            await self._send_error(
                "invalid_payload", "user_ids must be a list"
            )
            return

        if len(user_ids) > WS_MAX_PRESENCE_SUBSCRIPTIONS:
            await self._send_error(
                "too_many_subscriptions",
                f"Max {WS_MAX_PRESENCE_SUBSCRIPTIONS} presence subscriptions",
            )
            return

        # Leave old subscriptions
        for uid in self._presence_subscriptions:
            await self.channel_layer.group_discard(
                f"presence_{uid}", self.channel_name
            )
        self._presence_subscriptions.clear()

        # Join new subscriptions
        for uid in user_ids:
            uid_str = str(uid)
            await self.channel_layer.group_add(
                f"presence_{uid_str}", self.channel_name
            )
            self._presence_subscriptions.add(uid_str)

        # Send current status for all subscribed users
        statuses = await self._get_online_users(user_ids)
        from apps.chat.ws_serializers import serialize_presence

        for uid, is_online in statuses.items():
            await self.send_json({
                "type": "presence",
                **serialize_presence(uid, is_online),
            })

    # =========================================================================
    # CONVERSATION GROUP MANAGEMENT
    # =========================================================================

    async def _handle_conversation_join(self, content):
        """Join a specific conversation group dynamically."""
        conversation_id = content.get("conversation_id")
        if not conversation_id:
            await self._send_error(
                "invalid_payload", "conversation_id is required"
            )
            return

        user = self.scope["user"]
        is_participant = await self._db_is_participant(
            conversation_id=UUID(conversation_id),
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )

        if not is_participant:
            await self._send_error(
                "not_participant",
                "You are not a participant in this conversation",
            )
            return

        group_name = f"conversation_{conversation_id}"
        await self.channel_layer.group_add(group_name, self.channel_name)
        self._joined_conversations.add(conversation_id)

    async def _handle_conversation_leave(self, content):
        """Leave a conversation group."""
        conversation_id = content.get("conversation_id")
        if not conversation_id:
            await self._send_error(
                "invalid_payload", "conversation_id is required"
            )
            return

        group_name = f"conversation_{conversation_id}"
        await self.channel_layer.group_discard(group_name, self.channel_name)
        self._joined_conversations.discard(conversation_id)

    # =========================================================================
    # CHANNEL LAYER EVENT RECEIVERS (group_send → these methods)
    # =========================================================================

    async def chat_message_new(self, event):
        """Receive message.new from channel layer and send to client."""
        await self.send_json({
            "type": "message.new",
            **event["payload"],
        })

    async def chat_message_edited(self, event):
        """Receive message.edited from channel layer and send to client."""
        await self.send_json({
            "type": "message.edited",
            **event["payload"],
        })

    async def chat_message_deleted(self, event):
        """Receive message.deleted from channel layer and send to client."""
        await self.send_json({
            "type": "message.deleted",
            **event["payload"],
        })

    async def chat_typing(self, event):
        """Receive typing from channel layer — skip if sender."""
        if event.get("exclude_channel") == self.channel_name:
            return
        await self.send_json({
            "type": "typing",
            **event["payload"],
        })

    async def chat_seen_update(self, event):
        """Receive seen.update from channel layer and send to client."""
        await self.send_json({
            "type": "seen.update",
            **event["payload"],
        })

    async def chat_delivered_update(self, event):
        """Receive delivered.update from channel layer and send to client."""
        await self.send_json({
            "type": "delivered.update",
            **event["payload"],
        })

    async def chat_presence(self, event):
        """Receive presence from channel layer and send to client."""
        await self.send_json({
            "type": "presence",
            **event["payload"],
        })

    async def chat_reaction_update(self, event):
        """Receive reaction.update from channel layer and send to client."""
        await self.send_json({
            "type": "reaction.update",
            **event["payload"],
        })

    async def chat_conversation_new(self, event):
        """Receive new conversation notification and send to client."""
        await self.send_json({
            "type": "conversation.new",
            **event["payload"],
        })

    # =========================================================================
    # HEARTBEAT
    # =========================================================================

    async def _heartbeat_loop(self, user_id):
        """Refresh presence TTL periodically."""
        try:
            while True:
                await asyncio.sleep(WS_HEARTBEAT_INTERVAL_SECONDS)
                await self._set_presence_online(user_id)
        except asyncio.CancelledError:
            pass

    # =========================================================================
    # DATABASE ASYNC WRAPPERS
    # =========================================================================

    @database_sync_to_async
    def _get_user_conversation_ids(self, user_id):
        """Get all conversation IDs for a user (all scopes)."""
        from apps.chat.constants import ParticipantType
        from apps.chat.models import ConversationParticipant

        return list(
            ConversationParticipant.objects.filter(
                participant_type=ParticipantType.USER,
                participant_id=user_id,
                is_active=True,
            ).values_list("conversation_id", flat=True)
        )

    @database_sync_to_async
    def _db_send_message(self, **kwargs):
        from apps.chat.services import ChatService

        return ChatService.send_message(**kwargs)

    @database_sync_to_async
    def _db_edit_message(self, **kwargs):
        from apps.chat.services import ChatService

        return ChatService.edit_message(**kwargs)

    @database_sync_to_async
    def _db_delete_message(self, **kwargs):
        from apps.chat.services import ChatService

        return ChatService.delete_message(**kwargs)

    @database_sync_to_async
    def _db_get_message(self, message_id):
        from apps.chat.selectors import ChatSelector

        return ChatSelector.get_message_by_id(message_id=message_id)

    @database_sync_to_async
    def _db_update_seen(self, **kwargs):
        from apps.chat.services import ChatService

        return ChatService.update_seen_watermark(**kwargs)

    @database_sync_to_async
    def _db_update_delivered(self, **kwargs):
        from apps.chat.services import ChatService

        return ChatService.update_delivered_watermark(**kwargs)

    @database_sync_to_async
    def _db_is_participant(self, **kwargs):
        from apps.chat.selectors import ChatSelector

        return ChatSelector.is_participant(**kwargs)

    @database_sync_to_async
    def _db_add_reaction(self, **kwargs):
        from apps.chat.services import ChatService

        return ChatService.add_reaction(**kwargs)

    @database_sync_to_async
    def _db_remove_reaction(self, **kwargs):
        from apps.chat.services import ChatService

        return ChatService.remove_reaction(**kwargs)

    @staticmethod
    async def _set_presence_online(user_id):
        """Set user as online in presence manager (sync call, fast)."""
        from apps.chat.presence import PresenceManager

        PresenceManager.set_online(user_id)

    @staticmethod
    async def _set_presence_offline(user_id):
        """Set user as offline in presence manager (sync call, fast)."""
        from apps.chat.presence import PresenceManager

        PresenceManager.set_offline(user_id)

    @staticmethod
    async def _get_online_users(user_ids):
        """Batch check online status (sync call, fast pipeline)."""
        from apps.chat.presence import PresenceManager

        return PresenceManager.get_online_users(user_ids)

    async def _broadcast_presence(self, user_id, is_online: bool):
        """Broadcast presence change to all subscribers."""
        from apps.chat.ws_serializers import serialize_presence

        payload = serialize_presence(user_id, is_online)
        await self.channel_layer.group_send(
            f"presence_{user_id}",
            {"type": "chat.presence", "payload": payload},
        )

    # =========================================================================
    # ERROR HELPERS
    # =========================================================================

    async def _send_error(self, code: str, message: str):
        """Send error event to client."""
        await self.send_json({
            "type": "error",
            "code": code,
            "message": message,
        })

    @staticmethod
    def _format_error(exc) -> dict:
        """Map domain exceptions to WS error payloads."""
        from apps.core.exceptions import (
            BusinessRuleViolation,
            ConflictError,
            NotFound,
            PermissionDenied,
            ValidationError,
        )

        if isinstance(exc, ValidationError):
            return {"code": "validation_error", "message": str(exc)}
        elif isinstance(exc, PermissionDenied):
            return {"code": "permission_denied", "message": str(exc)}
        elif isinstance(exc, NotFound):
            return {"code": "not_found", "message": str(exc)}
        elif isinstance(exc, BusinessRuleViolation):
            return {"code": "business_rule_violation", "message": str(exc)}
        elif isinstance(exc, ConflictError):
            return {"code": "conflict", "message": str(exc)}
        else:
            logger.error(
                "chat.ws.unhandled_error",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return {
                "code": "internal_error",
                "message": "An unexpected error occurred",
            }
