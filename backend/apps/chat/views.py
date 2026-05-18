"""
Chat Views
==========
REST API views for the chat system.

All endpoints require authentication (IsAuthenticated) unless noted.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.policies import ChatPolicy
from apps.core.observability import get_logger
from apps.core.permissions import IsAuthenticated
from apps.core.views import PermissionInjectMixin

logger = get_logger(__name__)

# =============================================================================
# CONVERSATION VIEWS
# =============================================================================


class ConversationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.chat.selectors import ChatSelector
        from apps.chat.serializers import ConversationListOutputSerializer

        scope_type = request.query_params.get("scope_type", "global")
        scope_id = request.query_params.get("scope_id")

        conversations = ChatSelector.get_conversations_for_participant(
            participant_type="user",
            participant_id=request.user.id,
            scope_type=scope_type,
            scope_id=scope_id,
        )

        from apps.core.pagination import StandardPagination

        paginator = StandardPagination()
        page = paginator.paginate_queryset(conversations, request, view=self)
        serializer = ConversationListOutputSerializer(
            page, many=True, context={"request": request}
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        from apps.chat.serializers import ConversationCreateInputSerializer
        from apps.chat.services import ChatService

        serializer = ConversationCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        conversation = ChatService.create_conversation(
            scope_type=data["scope_type"],
            scope_id=data.get("scope_id"),
            conversation_type=data["conversation_type"],
            participant_ids=data["participant_ids"],
            name=data.get("name", ""),
            creator_type="user",
            creator_id=request.user.id,
            acting_user=request.user,
            request=request,
        )

        from apps.chat.serializers import ConversationDetailOutputSerializer

        output = ConversationDetailOutputSerializer(
            conversation, context={"request": request}
        )

        try:
            from apps.chat.broadcast import broadcast_new_conversation

            uids = [str(p["participant_id"]) for p in data["participant_ids"]]
            broadcast_new_conversation(conversation, uids)
        except Exception as e:
            logger.warning(
                "chat.broadcast.failed",
                broadcast_kind="new_conversation",
                conversation_id=str(conversation.id),
                error=str(e),
            )

        return Response(output.data, status=status.HTTP_201_CREATED)


class ConversationDetailView(PermissionInjectMixin, APIView):
    permission_classes = [IsAuthenticated]
    policy_class = ChatPolicy

    def _build_policy_kwargs(self) -> dict:
        return {"user": self.request.user, "conversation": self._conversation}

    def get(self, request, conversation_id):
        from apps.chat.selectors import ChatSelector
        from apps.chat.serializers import ConversationDetailOutputSerializer

        conversation = ChatSelector.get_conversation_by_id(
            conversation_id=conversation_id
        )
        self._conversation = conversation
        self._inject_permissions = True

        serializer = ConversationDetailOutputSerializer(
            conversation, context={"request": request}
        )
        return Response(serializer.data)

    def patch(self, request, conversation_id):
        from apps.chat.serializers import ConversationUpdateInputSerializer
        from apps.chat.services import ChatService

        serializer = ConversationUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        conversation = ChatService.update_group(
            conversation_id=conversation_id,
            name=data.get("name"),
            description=data.get("description"),
            user=request.user,
            request=request,
        )

        from apps.chat.serializers import ConversationDetailOutputSerializer

        output = ConversationDetailOutputSerializer(
            conversation, context={"request": request}
        )
        return Response(output.data)


# =============================================================================
# PARTICIPANT VIEWS
# =============================================================================


class ParticipantListAddView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        from apps.chat.selectors import ChatSelector
        from apps.chat.serializers import ParticipantOutputSerializer

        participants = ChatSelector.get_participants(
            conversation_id=conversation_id,
        )
        serializer = ParticipantOutputSerializer(
            participants, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request, conversation_id):
        from apps.chat.serializers import AddParticipantInputSerializer
        from apps.chat.services import ChatService

        serializer = AddParticipantInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        participant = ChatService.add_participant(
            conversation_id=conversation_id,
            participant_type=data["participant_type"],
            participant_id=data["participant_id"],
            added_by=request.user,
            request=request,
        )

        from apps.chat.serializers import ParticipantOutputSerializer

        output = ParticipantOutputSerializer(participant, context={"request": request})

        try:
            from apps.chat.broadcast import broadcast_new_conversation
            from apps.chat.selectors import ChatSelector

            conversation = ChatSelector.get_conversation_by_id(
                conversation_id=conversation_id
            )
            broadcast_new_conversation(conversation, [str(data["participant_id"])])
        except Exception as e:
            logger.warning(
                "chat.broadcast.failed",
                broadcast_kind="participant_added",
                conversation_id=str(conversation_id),
                error=str(e),
            )

        return Response(output.data, status=status.HTTP_201_CREATED)


class ParticipantRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, conversation_id, participant_id):
        from apps.chat.services import ChatService

        # `participant_id` is the ConversationParticipant.id (row PK).
        # The service reads participant_type from the row itself; we no
        # longer accept it via the request body (DELETE-with-body antipattern).
        ChatService.remove_participant(
            conversation_id=conversation_id,
            participant_pk=participant_id,
            removed_by=request.user,
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeaveConversationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        from apps.chat.services import ChatService

        ChatService.leave_conversation(
            conversation_id=conversation_id,
            user=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# MESSAGE VIEWS
# =============================================================================


class MessageListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        from apps.chat.selectors import ChatSelector
        from apps.chat.serializers import MessageOutputSerializer

        cursor = request.query_params.get("cursor")
        page_size = int(request.query_params.get("page_size", 50))
        direction = request.query_params.get("direction", "older")

        messages = list(
            ChatSelector.get_messages(
                conversation_id=conversation_id,
                cursor=cursor,
                page_size=min(page_size, 100),
                direction=direction,
            )
        )

        # Batch-fetch attachments + reactions to prevent N+1
        if messages:
            msg_ids = [m.id for m in messages]
            att_map = ChatSelector.get_attachments_for_messages(message_ids=msg_ids)
            user_id = request.user.id if request.user else None
            react_map = ChatSelector.get_reactions_for_messages(
                message_ids=msg_ids, user_id=user_id
            )
            for msg in messages:
                msg._prefetched_attachments = att_map.get(msg.id, [])
                msg._prefetched_reactions = react_map.get(
                    msg.id, {"counts": {}, "my_reactions": []}
                )

        serializer = MessageOutputSerializer(
            messages, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request, conversation_id):
        from apps.chat.serializers import MessageCreateInputSerializer
        from apps.chat.services import ChatService

        serializer = MessageCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        attachment_ids = data.get("attachment_ids") or None

        message = ChatService.send_message(
            conversation_id=conversation_id,
            sender_type=data.get("sender_type", "user"),
            sender_id=data.get("sender_id", request.user.id),
            acting_user_id=request.user.id,
            content=data["content"],
            content_type=data.get("content_type", "text"),
            attachment_ids=attachment_ids,
            request=request,
        )

        from apps.chat.serializers import MessageOutputSerializer

        output = MessageOutputSerializer(message, context={"request": request})

        try:
            from apps.chat.broadcast import broadcast_message_new

            broadcast_message_new(message)
        except Exception as e:
            logger.warning(
                "chat.broadcast.failed",
                broadcast_kind="message_new",
                conversation_id=str(message.conversation_id),
                message_id=str(message.id),
                error=str(e),
            )

        return Response(output.data, status=status.HTTP_201_CREATED)


class MessageEditDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, conversation_id, message_id):
        from apps.chat.serializers import MessageEditInputSerializer
        from apps.chat.services import ChatService

        serializer = MessageEditInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = ChatService.edit_message(
            message_id=message_id,
            new_content=serializer.validated_data["content"],
            user=request.user,
            request=request,
        )

        from apps.chat.serializers import MessageOutputSerializer

        output = MessageOutputSerializer(message, context={"request": request})

        try:
            from apps.chat.broadcast import broadcast_message_edited

            broadcast_message_edited(message)
        except Exception as e:
            logger.warning(
                "chat.broadcast.failed",
                broadcast_kind="message_edited",
                conversation_id=str(message.conversation_id),
                message_id=str(message.id),
                error=str(e),
            )

        return Response(output.data)

    def delete(self, request, conversation_id, message_id):
        from apps.chat.services import ChatService

        ChatService.delete_message(
            message_id=message_id,
            user=request.user,
            request=request,
        )

        try:
            from apps.chat.broadcast import broadcast_message_deleted_by_ids

            broadcast_message_deleted_by_ids(conversation_id, message_id)
        except Exception as e:
            logger.warning(
                "chat.broadcast.failed",
                broadcast_kind="message_deleted",
                conversation_id=str(conversation_id),
                message_id=str(message_id),
                error=str(e),
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# WATERMARK / MUTE VIEWS
# =============================================================================


class MarkSeenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        from apps.chat.services import ChatService

        last_seen_message_id = request.data.get("last_seen_message_id")
        if not last_seen_message_id:
            return Response(
                {"message": "last_seen_message_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ChatService.update_seen_watermark(
            conversation_id=conversation_id,
            participant_type="user",
            participant_id=request.user.id,
            last_seen_message_id=last_seen_message_id,
        )

        try:
            from apps.chat.broadcast import broadcast_seen_update

            broadcast_seen_update(
                conversation_id, request.user.id, last_seen_message_id
            )
        except Exception as e:
            logger.warning(
                "chat.broadcast.failed",
                broadcast_kind="seen_update",
                conversation_id=str(conversation_id),
                user_id=str(request.user.id),
                error=str(e),
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class MuteConversationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        from apps.chat.selectors import ChatSelector

        participant = ChatSelector.get_participant(
            conversation_id=conversation_id,
            participant_type="user",
            participant_id=request.user.id,
        )
        if not participant:
            from apps.core.exceptions import NotFound

            raise NotFound(resource="ConversationParticipant")

        participant.is_muted = True
        participant.save(update_fields=["is_muted", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class UnmuteConversationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        from apps.chat.selectors import ChatSelector

        participant = ChatSelector.get_participant(
            conversation_id=conversation_id,
            participant_type="user",
            participant_id=request.user.id,
        )
        if not participant:
            from apps.core.exceptions import NotFound

            raise NotFound(resource="ConversationParticipant")

        participant.is_muted = False
        participant.save(update_fields=["is_muted", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# CHAT REQUEST VIEWS
# =============================================================================


class ChatRequestListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.chat.selectors import ChatSelector
        from apps.chat.serializers import ChatRequestOutputSerializer

        requests_qs = ChatSelector.get_pending_requests(
            recipient_type="user",
            recipient_id=request.user.id,
        )

        from apps.core.pagination import StandardPagination

        paginator = StandardPagination()
        page = paginator.paginate_queryset(requests_qs, request, view=self)
        serializer = ChatRequestOutputSerializer(
            page, many=True, context={"request": request}
        )
        return paginator.get_paginated_response(serializer.data)


class AcceptChatRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        from apps.chat.services import ChatService

        ChatService.accept_request(
            conversation_id=conversation_id,
            user=request.user,
        )
        return Response(status=status.HTTP_200_OK)


class IgnoreChatRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        from apps.chat.services import ChatService

        ChatService.ignore_request(
            conversation_id=conversation_id,
            user=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# BLOCK VIEWS
# =============================================================================


class BlockListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.chat.selectors import ChatSelector
        from apps.chat.serializers import ChatBlockOutputSerializer

        blocks = ChatSelector.get_blocks_for_user(user_id=request.user.id)

        from apps.core.pagination import StandardPagination

        paginator = StandardPagination()
        page = paginator.paginate_queryset(blocks, request, view=self)
        serializer = ChatBlockOutputSerializer(
            page, many=True, context={"request": request}
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        from apps.chat.serializers import BlockCreateInputSerializer
        from apps.chat.services import ChatService

        serializer = BlockCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        block = ChatService.block_participant(
            blocker=request.user,
            blocked_type=data["blocked_type"],
            blocked_id=data["blocked_id"],
            request=request,
        )

        from apps.chat.serializers import ChatBlockOutputSerializer

        output = ChatBlockOutputSerializer(block, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class UnblockView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, block_id):
        from apps.chat.services import ChatService

        ChatService.unblock_participant(
            blocker=request.user,
            block_id=block_id,
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# UNREAD COUNTS VIEW
# =============================================================================


class UnreadCountsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.chat.selectors import ChatSelector

        counts = ChatSelector.get_unread_counts_by_scope(user_id=request.user.id)
        return Response(counts)


# =============================================================================
# GROUP ADMIN MANAGEMENT VIEWS
# =============================================================================


class PromoteToAdminView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id, participant_id):
        from apps.chat.services import ChatService

        ChatService.promote_to_admin(
            conversation_id=conversation_id,
            participant_id=participant_id,
            user=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class DemoteFromAdminView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id, participant_id):
        from apps.chat.services import ChatService

        ChatService.demote_from_admin(
            conversation_id=conversation_id,
            participant_id=participant_id,
            user=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# ATTACHMENT VIEWS
# =============================================================================


class AttachmentUploadView(APIView):
    permission_classes = [IsAuthenticated]

    # Override global JSONParser — upload needs multipart
    from rest_framework.parsers import FormParser, MultiPartParser

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, conversation_id):
        from apps.chat.serializers import AttachmentOutputSerializer
        from apps.chat.services import ChatService

        file = request.FILES.get("file")
        if not file:
            from apps.core.exceptions import ValidationError

            raise ValidationError(message="No file provided", field="file")

        attachment = ChatService.upload_attachment(
            conversation_id=conversation_id,
            user=request.user,
            file=file,
        )

        output = AttachmentOutputSerializer(attachment, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)


# =============================================================================
# REACTION VIEWS
# =============================================================================


class ReactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id, message_id):
        """Add a reaction to a message."""
        from apps.chat.serializers import ReactionInputSerializer
        from apps.chat.services import ChatService

        serializer = ReactionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reaction_obj = ChatService.add_reaction(
            message_id=message_id,
            user=request.user,
            reaction=serializer.validated_data["reaction"],
        )

        return Response(
            {"id": str(reaction_obj.id), "reaction": reaction_obj.reaction},
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, conversation_id, message_id):
        """Remove a reaction from a message."""
        from apps.chat.serializers import ReactionInputSerializer
        from apps.chat.services import ChatService

        serializer = ReactionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ChatService.remove_reaction(
            message_id=message_id,
            user=request.user,
            reaction=serializer.validated_data["reaction"],
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# MEDIA GALLERY VIEW
# =============================================================================


class MediaGalleryView(APIView):
    """
    List all image attachments in a conversation (for media gallery).

    Cursor-based pagination by created_at. Only returns linked attachments.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        from apps.chat.selectors import ChatSelector
        from apps.chat.serializers import AttachmentOutputSerializer

        # Verify user is participant
        participant = ChatSelector.get_participant(
            conversation_id=conversation_id,
            participant_type="user",
            participant_id=request.user.id,
        )
        if not participant:
            from apps.core.exceptions import PermissionDenied

            raise PermissionDenied(
                message="You are not a participant in this conversation",
                action="view_media",
                resource="Conversation",
            )

        cursor = request.query_params.get("cursor")
        page_size = min(int(request.query_params.get("page_size", 50)), 100)

        attachments = ChatSelector.get_media_gallery(
            conversation_id=conversation_id,
            cursor=cursor,
            page_size=page_size + 1,  # Fetch one extra to detect has_next
        )
        items = list(attachments)
        has_next = len(items) > page_size
        if has_next:
            items = items[:page_size]

        serializer = AttachmentOutputSerializer(
            items, many=True, context={"request": request}
        )

        next_cursor = None
        if has_next and items:
            next_cursor = items[-1].created_at.isoformat()

        return Response(
            {
                "results": serializer.data,
                "next_cursor": next_cursor,
            }
        )


# =============================================================================
# ENTITY INBOX VIEW
# =============================================================================


class EntityInboxView(APIView):
    """
    List conversations for a business or platform entity.

    The acting user must have `can_manage_chat` permission for the entity.
    Returns conversations where the entity is a participant, scoped to global.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, account_type, account_id):
        from apps.chat.policies import ChatPolicy
        from apps.chat.selectors import ChatSelector
        from apps.chat.serializers import ConversationListOutputSerializer

        if account_type not in ("business", "platform"):
            from apps.core.exceptions import ValidationError

            raise ValidationError(
                message="account_type must be 'business' or 'platform'",
                field="account_type",
            )

        if not ChatPolicy.can_manage_entity_chat(
            user=request.user,
            account_type=account_type,
            account_id=account_id,
        ):
            from apps.core.exceptions import PermissionDenied

            raise PermissionDenied(
                message="You do not have permission to manage chat for this entity",
                action="entity_inbox",
                resource="Conversation",
            )

        conversations = ChatSelector.get_conversations_for_participant(
            participant_type=account_type,
            participant_id=account_id,
            scope_type="global",
        )

        from apps.core.pagination import StandardPagination

        paginator = StandardPagination()
        page = paginator.paginate_queryset(conversations, request, view=self)
        serializer = ConversationListOutputSerializer(
            page, many=True, context={"request": request}
        )
        return paginator.get_paginated_response(serializer.data)


# =============================================================================
# MESSAGE SEARCH VIEW
# =============================================================================


class MessageSearchView(APIView):
    """
    Search messages across conversations the user participates in.

    Supports FTS (PostgreSQL) with trigram fallback for typo tolerance.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.chat.selectors import ChatSelector
        from apps.chat.serializers import MessageSearchOutputSerializer

        query = request.query_params.get("q", "").strip()
        if not query:
            return Response([])

        scope_type = request.query_params.get("scope_type", "global")
        scope_id = request.query_params.get("scope_id")
        conversation_id = request.query_params.get("conversation_id")

        messages = ChatSelector.search_messages(
            query=query,
            participant_type="user",
            participant_id=request.user.id,
            scope_type=scope_type,
            scope_id=scope_id,
            conversation_id=conversation_id,
        )

        from apps.core.pagination import StandardPagination

        paginator = StandardPagination()
        page = paginator.paginate_queryset(messages, request, view=self)
        serializer = MessageSearchOutputSerializer(
            page, many=True, context={"request": request}
        )
        return paginator.get_paginated_response(serializer.data)
