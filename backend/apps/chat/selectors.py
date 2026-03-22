"""
Chat Selectors
===============
Read-only query layer for the chat system.
All methods are @staticmethod, read-only.
"""

from uuid import UUID

from django.db import connection
from django.db.models import Count, Q, QuerySet, Subquery

from apps.chat.constants import (
    MessageStatus,
    ParticipantType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import (
    ChatBlock,
    Conversation,
    ConversationParticipant,
    Message,
    MessageAttachment,
    MessageReaction,
)
from apps.core.exceptions import NotFound


class ChatSelector:
    """Read-only queries for the chat system."""

    # =========================================================================
    # CONVERSATIONS
    # =========================================================================

    @staticmethod
    def get_conversation_by_id(*, conversation_id: UUID) -> Conversation:
        """Get a conversation by ID. Raises NotFound if not found."""
        conversation = Conversation.objects.filter(
            id=conversation_id, is_active=True
        ).first()
        if not conversation:
            raise NotFound(resource="Conversation", resource_id=str(conversation_id))
        return conversation

    @staticmethod
    def get_conversations_for_participant(
        *,
        participant_type: str,
        participant_id: UUID,
        scope_type: str,
        scope_id: UUID | None = None,
        exclude_requests: bool = True,
    ) -> QuerySet[Conversation]:
        """
        Get all active conversations for a participant in a given scope.

        Returns conversations ordered by last_message_at (most recent first).
        Excludes conversations where the participant has a pending chat request
        by default (use exclude_requests=False to include them).
        """
        participant_filter = Q(
            participants__participant_type=participant_type,
            participants__participant_id=participant_id,
            participants__is_active=True,
        )

        if exclude_requests:
            participant_filter &= ~Q(
                participants__request_status=RequestStatus.PENDING,
            )

        scope_filter = Q(scope_type=scope_type)
        if scope_type == ScopeType.GLOBAL:
            scope_filter &= Q(scope_id__isnull=True)
        else:
            scope_filter &= Q(scope_id=scope_id)

        return (
            Conversation.objects.filter(
                participant_filter,
                scope_filter,
                is_active=True,
            )
            .distinct()
            .order_by("-last_message_at", "-created_at")
        )

    @staticmethod
    def get_dm_conversation(
        *,
        scope_type: str,
        scope_id: UUID | None,
        participant_a_type: str,
        participant_a_id: UUID,
        participant_b_type: str,
        participant_b_id: UUID,
    ) -> Conversation | None:
        """
        Find an existing DM conversation between two participants in a scope.

        Returns None if no DM exists.
        """
        scope_filter = Q(scope_type=scope_type)
        if scope_type == ScopeType.GLOBAL:
            scope_filter &= Q(scope_id__isnull=True)
        else:
            scope_filter &= Q(scope_id=scope_id)

        # Find conversations where both participants are active
        conversations = (
            Conversation.objects.filter(
                scope_filter,
                conversation_type="direct",
                is_active=True,
            )
            .filter(
                participants__participant_type=participant_a_type,
                participants__participant_id=participant_a_id,
                participants__is_active=True,
            )
            .filter(
                id__in=Subquery(
                    ConversationParticipant.objects.filter(
                        participant_type=participant_b_type,
                        participant_id=participant_b_id,
                        is_active=True,
                    ).values("conversation_id")
                )
            )
        )
        return conversations.first()

    # =========================================================================
    # MESSAGES
    # =========================================================================

    @staticmethod
    def get_messages(
        *,
        conversation_id: UUID,
        cursor: int | None = None,
        page_size: int = 50,
        direction: str = "older",
    ) -> QuerySet[Message]:
        """
        Get messages for a conversation with cursor-based pagination.

        Args:
            conversation_id: The conversation to get messages from
            cursor: sequence_number to paginate from (None = latest)
            page_size: Number of messages to return
            direction: "older" (before cursor) or "newer" (after cursor)
        """
        qs = Message.objects.filter(conversation_id=conversation_id)

        if cursor is not None:
            if direction == "older":
                qs = qs.filter(sequence_number__lt=cursor).order_by(
                    "-sequence_number"
                )
            else:
                qs = qs.filter(sequence_number__gt=cursor).order_by(
                    "sequence_number"
                )
        else:
            # No cursor = latest messages
            qs = qs.order_by("-sequence_number")

        return qs[:page_size]

    @staticmethod
    def get_message_by_id(*, message_id: UUID) -> Message:
        """Get a message by ID. Raises NotFound if not found."""
        message = Message.objects.filter(id=message_id).first()
        if not message:
            raise NotFound(resource="Message", resource_id=str(message_id))
        return message

    # =========================================================================
    # PARTICIPANTS
    # =========================================================================

    @staticmethod
    def get_participants(
        *, conversation_id: UUID
    ) -> QuerySet[ConversationParticipant]:
        """Get all active participants for a conversation."""
        return ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            is_active=True,
        ).order_by("created_at")

    @staticmethod
    def get_participant(
        *,
        conversation_id: UUID,
        participant_type: str,
        participant_id: UUID,
    ) -> ConversationParticipant | None:
        """Get a specific active participant in a conversation."""
        return ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            participant_type=participant_type,
            participant_id=participant_id,
            is_active=True,
        ).first()

    @staticmethod
    def is_participant(
        *,
        conversation_id: UUID,
        participant_type: str,
        participant_id: UUID,
    ) -> bool:
        """Check if a participant is active in a conversation."""
        return ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            participant_type=participant_type,
            participant_id=participant_id,
            is_active=True,
        ).exists()

    # =========================================================================
    # CHAT REQUESTS
    # =========================================================================

    @staticmethod
    def get_pending_requests(
        *, recipient_type: str, recipient_id: UUID
    ) -> QuerySet[ConversationParticipant]:
        """Get pending chat requests for a recipient."""
        return (
            ConversationParticipant.objects.filter(
                participant_type=recipient_type,
                participant_id=recipient_id,
                request_status=RequestStatus.PENDING,
                is_active=True,
            )
            .select_related("conversation")
            .order_by("-created_at")
        )

    @staticmethod
    def count_pending_requests(
        *, recipient_type: str, recipient_id: UUID
    ) -> int:
        """Count pending chat requests for a recipient."""
        return ConversationParticipant.objects.filter(
            participant_type=recipient_type,
            participant_id=recipient_id,
            request_status=RequestStatus.PENDING,
            is_active=True,
        ).count()

    # =========================================================================
    # BLOCKS
    # =========================================================================

    @staticmethod
    def is_blocked(
        *, blocker_id: UUID, blocked_type: str, blocked_id: UUID
    ) -> bool:
        """Check if blocker has blocked the specified participant."""
        return ChatBlock.objects.filter(
            blocker_id=blocker_id,
            blocked_type=blocked_type,
            blocked_id=blocked_id,
        ).exists()

    @staticmethod
    def get_blocks_for_user(*, user_id: UUID) -> QuerySet[ChatBlock]:
        """Get all blocks for a user."""
        return ChatBlock.objects.filter(blocker_id=user_id).order_by("-created_at")

    # =========================================================================
    # UNREAD COUNTS
    # =========================================================================

    @staticmethod
    def get_unread_count(
        *,
        conversation_id: UUID,
        participant_type: str,
        participant_id: UUID,
    ) -> int:
        """
        Get unread message count for a participant in a conversation.

        Count messages after the participant's last_seen_message_id.
        """
        participant = ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            participant_type=participant_type,
            participant_id=participant_id,
            is_active=True,
        ).first()

        if not participant:
            return 0

        qs = Message.objects.filter(
            conversation_id=conversation_id,
            status__in=[MessageStatus.ACTIVE, MessageStatus.EDITED],
        ).exclude(
            sender_type=participant_type,
            sender_id=participant_id,
        )

        if participant.last_seen_message_id:
            # Get the sequence number of the last seen message
            last_seen = Message.objects.filter(
                id=participant.last_seen_message_id
            ).values_list("sequence_number", flat=True).first()
            if last_seen is not None:
                qs = qs.filter(sequence_number__gt=last_seen)

        return qs.count()

    @staticmethod
    def get_unread_counts_by_scope(*, user_id: UUID) -> dict:
        """
        Get unread counts aggregated by scope for a user.

        Returns: {"global": N, "business": {id: N}, "platform": N}
        """
        # Get all conversations the user participates in
        participant_records = ConversationParticipant.objects.filter(
            participant_type=ParticipantType.USER,
            participant_id=user_id,
            is_active=True,
        ).select_related("conversation").exclude(
            request_status=RequestStatus.PENDING,
        )

        result = {"global": 0, "business": {}, "platform": 0}

        for pr in participant_records:
            count = ChatSelector.get_unread_count(
                conversation_id=pr.conversation_id,
                participant_type=ParticipantType.USER,
                participant_id=user_id,
            )
            if count == 0:
                continue

            conv = pr.conversation
            if conv.scope_type == ScopeType.GLOBAL:
                result["global"] += count
            elif conv.scope_type == ScopeType.BUSINESS:
                scope_key = str(conv.scope_id)
                result["business"][scope_key] = (
                    result["business"].get(scope_key, 0) + count
                )
            elif conv.scope_type == ScopeType.PLATFORM:
                result["platform"] += count

        return result

    # =========================================================================
    # ATTACHMENTS
    # =========================================================================

    @staticmethod
    def get_attachments_for_messages(
        *, message_ids: list[UUID]
    ) -> dict[UUID, list[MessageAttachment]]:
        """
        Batch-fetch attachments for a list of messages.

        Returns {message_id: [attachment, ...]}. Used by views to prevent N+1.
        """
        if not message_ids:
            return {}
        attachments = MessageAttachment.objects.filter(
            message_id__in=message_ids
        ).order_by("created_at")
        result: dict[UUID, list[MessageAttachment]] = {}
        for att in attachments:
            result.setdefault(att.message_id, []).append(att)
        return result

    @staticmethod
    def get_media_gallery(
        *,
        conversation_id: UUID,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> QuerySet[MessageAttachment]:
        """
        Get all image attachments in a conversation (for media gallery).

        Only linked attachments (not orphans). Cursor-based pagination by created_at.
        """
        qs = MessageAttachment.objects.filter(
            conversation_id=conversation_id,
            message__isnull=False,
        ).order_by("-created_at")

        if cursor:
            qs = qs.filter(created_at__lt=cursor)

        return qs[:page_size]

    # =========================================================================
    # REACTIONS
    # =========================================================================

    @staticmethod
    def get_reactions_for_messages(
        *, message_ids: list[UUID], user_id: UUID | None = None
    ) -> dict[UUID, dict]:
        """
        Batch-fetch reaction counts + user's own reactions for messages.

        Returns {message_id: {"counts": {"like": 3, ...}, "my_reactions": ["like"]}}.
        Used by views to prevent N+1.
        """
        if not message_ids:
            return {}

        # Aggregate counts per message per reaction type
        counts_qs = (
            MessageReaction.objects.filter(message_id__in=message_ids)
            .values("message_id", "reaction")
            .annotate(count=Count("id"))
        )

        result: dict[UUID, dict] = {}
        for row in counts_qs:
            mid = row["message_id"]
            if mid not in result:
                result[mid] = {"counts": {}, "my_reactions": []}
            result[mid]["counts"][row["reaction"]] = row["count"]

        # Get current user's reactions
        if user_id:
            user_reactions = MessageReaction.objects.filter(
                message_id__in=message_ids, user_id=user_id
            ).values_list("message_id", "reaction")
            for mid, reaction in user_reactions:
                if mid not in result:
                    result[mid] = {"counts": {}, "my_reactions": []}
                result[mid]["my_reactions"].append(reaction)

        return result

    # =========================================================================
    # MESSAGE SEARCH
    # =========================================================================

    @staticmethod
    def search_messages(
        *,
        query: str,
        participant_type: str,
        participant_id: UUID,
        scope_type: str,
        scope_id: UUID | None = None,
        conversation_id: UUID | None = None,
    ) -> QuerySet[Message]:
        """
        Full-text search across messages in conversations the user participates in.

        Uses PostgreSQL FTS (SearchVector + SearchQuery) with trigram fallback
        for typo tolerance. Falls back to simple icontains on SQLite.

        Args:
            query: Search text
            participant_type: Searcher's participant type
            participant_id: Searcher's participant ID
            scope_type: Filter to this scope
            scope_id: Filter to this scope ID (None for global)
            conversation_id: Optional — restrict to a single conversation
        """
        # Build base queryset: only messages in conversations the user participates in
        conversation_ids = ConversationParticipant.objects.filter(
            participant_type=participant_type,
            participant_id=participant_id,
            is_active=True,
        ).values_list("conversation_id", flat=True)

        qs = Message.objects.filter(
            conversation_id__in=conversation_ids,
            conversation__scope_type=scope_type,
            status__in=[MessageStatus.ACTIVE, MessageStatus.EDITED],
        )

        if scope_type == ScopeType.GLOBAL:
            qs = qs.filter(conversation__scope_id__isnull=True)
        elif scope_id:
            qs = qs.filter(conversation__scope_id=scope_id)

        if conversation_id:
            qs = qs.filter(conversation_id=conversation_id)

        # PostgreSQL: FTS + trigram. SQLite: simple icontains fallback.
        if connection.vendor == "postgresql":
            from django.contrib.postgres.search import (
                SearchQuery,
                SearchRank,
                SearchVector,
                TrigramSimilarity,
            )
            from django.db.models.functions import Greatest

            vector = SearchVector("content", weight="A")
            search_query = SearchQuery(query, search_type="websearch")
            fts_rank = SearchRank(vector, search_query)
            trigram_rank = TrigramSimilarity("content", query) * 0.5
            combined_rank = Greatest(fts_rank, trigram_rank)

            qs = (
                qs.annotate(search_rank=combined_rank)
                .filter(search_rank__gt=0.01)
                .order_by("-search_rank")
                .select_related("conversation")
            )
        else:
            # Fallback for SQLite: simple icontains
            qs = (
                qs.filter(content__icontains=query)
                .order_by("-created_at")
                .select_related("conversation")
            )

        return qs
