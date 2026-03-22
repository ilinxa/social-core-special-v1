# Chat System — Implementation Plan

**Status:** Implemented (v1)
**Date:** 2026-03-19 (written), 2026-03-20 (updated post-implementation)
**Description Doc:** `docs/descriptions/backend/chat_system/chat_system_description.md`
**App Location:** `backend/apps/chat/`

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js)                                             │
│  ┌────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │ Chat UI (React)│  │ WebSocket Client │  │ REST API Client│  │
│  └───────┬────────┘  └────────┬─────────┘  └───────┬────────┘  │
│          │                    │                     │           │
└──────────┼────────────────────┼─────────────────────┼───────────┘
           │                    │                     │
    ┌──────┼────────────────────┼─────────────────────┼──────┐
    │      │            WebSocket (Daphne)       REST (DRF)  │
    │      │                    │                     │      │
    │  ┌───▼────────────────────▼───┐  ┌──────────────▼───┐  │
    │  │      ChatConsumer          │  │   Chat Views     │  │
    │  │  (AsyncJsonWebsocket)      │  │   (APIView)      │  │
    │  │  extends AuthenticatedCons │  │                   │  │
    │  └────────────┬───────────────┘  └────────┬──────────┘  │
    │               │                           │             │
    │  ┌────────────▼───────────────────────────▼──────────┐  │
    │  │              ChatService (sync)                    │  │
    │  │  create_conversation · send_message · edit_msg     │  │
    │  │  accept_request · block · update_watermark         │  │
    │  └─────────────────────┬─────────────────────────────┘  │
    │                        │                                │
    │  ┌─────────────────────▼─────────────────────────────┐  │
    │  │              ChatSelector (read-only)              │  │
    │  │  get_conversations · get_messages · unread_count   │  │
    │  │  get_requests · is_blocked · get_participants      │  │
    │  └─────────────────────┬─────────────────────────────┘  │
    │                        │                                │
    │  ┌─────────────────────▼─────────────────────────────┐  │
    │  │              ChatPolicy (auth/perms)               │  │
    │  │  validate_scope_eligibility · can_send_message     │  │
    │  │  can_manage_entity_chat · get_viewer_permissions   │  │
    │  └─────────────────────┬─────────────────────────────┘  │
    │                        │                                │
    │  ┌─────────────────────▼─────────────────────────────┐  │
    │  │                   Models                          │  │
    │  │  Conversation · Message · ConversationParticipant │  │
    │  │  ChatBlock · ChatRequest (status on participant)   │  │
    │  └───────────────────────────────────────────────────┘  │
    │                                                         │
    │  Cross-system reads:                                    │
    │  ├── RBAC: MembershipSelector, PermissionSelector       │
    │  ├── Network: ConnectionSelector.is_connected()         │
    │  ├── Organization: BusinessAccount, PlatformAccount     │
    │  └── Users: User, UserProfile                           │
    │                                                         │
    │  Cross-system writes:                                   │
    │  ├── Audit: AuditService.log() (entity actions)         │
    │  └── Notifications: NotificationService.send()          │
    │                                                         │
    │  New RBAC:                                              │
    │  └── can_manage_chat (business + platform_only)         │
    │                                                         │
    │  Infrastructure:                                        │
    │  ├── Redis Channel Layer (pub/sub for WebSocket)        │
    │  └── PostgreSQL (persistent storage)                    │
    └─────────────────────────────────────────────────────────┘
```

**Dual-interface architecture:** The chat system exposes functionality through **two interfaces** serving different use cases:

| Interface | Purpose | Transport | When Used |
|-----------|---------|-----------|-----------|
| **REST API** | CRUD operations, history, search, lists | HTTP | Initial page load, pagination, search, management |
| **WebSocket** | Real-time events (messages, typing, seen, presence) | WS | Active chat session, live updates |

Both interfaces call the same `ChatService` and `ChatSelector` — no duplicated business logic.

---

## 2. Open Question Resolutions

All open questions from the description document are resolved here for the plan:

| OQ | Question | Resolution | Rationale |
|----|----------|------------|-----------|
| OQ-1 | Message search engine | **PostgreSQL FTS** (same as explore system) | Consistency. `SearchVector` on `Message.content` with `ts_rank`. No external dependency. Sufficient for v1 scale. Can add Elasticsearch later if needed. |
| OQ-4 | Media messages | **Reuse existing media infrastructure** | CMS system already has media upload (`cms/services.py` `upload_file()`). Chat messages reference media by URL. No chat-specific upload needed in v1 — text + URL/link content types only. File/image attachments deferred to v2. |
| OQ-5 | Rate limiting | **Per-user in-memory rate limiter** | 30 messages/minute per user per conversation. 5 conversations created/hour. Enforced in `ChatService` via Redis counter with TTL. No per-entity limits for v1 (entity operators are trusted RBAC members). |
| OQ-7 | Conversation archival | **No archival policy for v1** | Messages persist indefinitely. Old conversations naturally paginate. Archival is a v2 concern when storage costs matter. |
| OQ-9 | Admin moderation | **Platform admins can moderate within their scope only** | Platform admins (with `can_manage_chat` + global scope) can view/moderate platform-scope conversations and global-scope conversations involving platform entities. They CANNOT view business-internal conversations. Business-scope moderation is for business admins only. This preserves scope isolation. |
| OQ-10 | Offline message queue | **No special queue — messages persist in DB** | Offline users miss WebSocket delivery but messages are always in PostgreSQL. When they reconnect, the client fetches missed messages via REST API (cursor pagination from last known message). `delivered` watermark updates on reconnect. Push notifications deferred to mobile phase. |
| OQ-11 | Group chat invitations | **Require acceptance in global scope** | In global scope, adding someone to a group creates a `group_invitation` notification. The invitee must accept before becoming a participant. In org scopes, adding a member is instant (membership = trust). This prevents strangers from force-adding users to groups. |
| OQ-12 | Chat request accumulation | **Allow up to 3 messages** | Sender can send up to 3 messages before the request is accepted. After 3, further sends are rejected with "Request pending" error. This gives the sender enough context to introduce themselves without enabling spam. All pending messages are visible to the recipient in the request preview. |
| OQ-13 | Chat request expiration | **30 days** | Pending chat requests expire after 30 days. A Celery periodic task runs daily to expire stale requests. Expired requests allow the sender to re-send. |
| OQ-14 | Chat notifications | **Yes, via existing Notification System** | 4 new notification types in `CHAT` category: `chat_message_received`, `chat_request_received`, `chat_request_accepted`, `chat_group_invitation`. Only `chat_message_received` is rate-limited (max 1 notification per conversation per 5 minutes to avoid spam). |
| OQ-15 | Group chat administration | **Creator is admin, can promote others** | Group creator gets `admin` role. Admins can add/remove participants and promote other participants to admin. Admin rights are transferable. If all admins leave, the oldest remaining participant auto-promotes. No standalone group admin role model — stored as `role` field on `ConversationParticipant`. |

---

## 3. Core Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D-1 | Base model classes | `UUIDModel + TimeStampedModel` | Chat records need UUID PKs for cross-reference and chronological ordering. No soft-delete on messages (status field instead) — consistent with Network system pattern. |
| D-2 | Scope enforcement layer | **Data layer** (model constraints + selector filters) | Every query passes through `ChatSelector` which ALWAYS filters by `scope_type + scope_id`. DB-level partial unique constraints prevent cross-scope duplicates. |
| D-3 | Participant polymorphism | `participant_type + participant_id` (CharField + UUIDField) | Matches existing `PartyType` pattern in transaction system. No GenericForeignKey — explicit resolution in serializers. |
| D-4 | Message ordering | `created_at` + `sequence_number` (per-conversation auto-increment) | `created_at` for display, `sequence_number` for gap-free ordering and cursor pagination. Avoids clock skew issues between servers. |
| D-5 | Watermark pattern | Two UUIDField pointers on `ConversationParticipant` | `last_delivered_message_id` + `last_seen_message_id`. No per-message status table. O(1) write per status update instead of O(N). |
| D-6 | Chat request state | Field on `ConversationParticipant` (`request_status`) | Not a separate model. A DM conversation is created immediately but the recipient's participant record has `request_status=pending`. This keeps the conversation model clean and avoids a separate "request" entity. |
| D-7 | Block model | Separate `ChatBlock` model | Per-user block list, not per-conversation. Queried at message send time and conversation list time. Indexed by `(blocker_id, blocked_type, blocked_id)`. |
| D-8 | WebSocket consumer | Single `ChatConsumer` per user connection | One WebSocket per authenticated session. Consumer joins channel groups for all active conversations. Messages routed via Redis channel layer `group_send()`. |
| D-9 | Typing indicators | Redis-only (no DB persistence) | Typing state stored in Redis with 5s TTL. Broadcast via channel layer. No model, no migration, no DB write. |
| D-10 | Online presence | Redis-only with channel layer | User online status stored in Redis set. Updated on connect/disconnect. Broadcast to relevant channel groups. No DB persistence. |
| D-11 | Message content types | `content_type` enum field on Message | v1: `text` only. Extensible to `image`, `file`, `link`, `system` in v2. Content stored in `content` TextField. Metadata in `metadata` JSONField. |
| D-12 | Conversation `last_message` denormalization | Denormalized fields on `Conversation` | `last_message_id`, `last_message_at`, `last_message_preview` updated on every new message. Avoids N+1 join when listing conversations. |
| D-13 | No transaction types for chat | Chat requests are NOT transactions | Chat requests are too lightweight and high-frequency for the transaction system (which has state machines, expiration tasks, audit trails). Chat manages its own request lifecycle on `ConversationParticipant.request_status`. |

---

## 4. Data Model

### 4.1 Enums

```python
# apps/chat/constants.py

class ScopeType(models.TextChoices):
    GLOBAL = "global", "Global"
    BUSINESS = "business", "Business"
    PLATFORM = "platform", "Platform"
    # TEAM = "team", "Team"  # Future

class ConversationType(models.TextChoices):
    DIRECT = "direct", "Direct Message"
    GROUP = "group", "Group Chat"

class ParticipantType(models.TextChoices):
    USER = "user", "User"
    BUSINESS = "business", "Business"
    PLATFORM = "platform", "Platform"
    # TEAM = "team", "Team"  # Future

class ParticipantRole(models.TextChoices):
    MEMBER = "member", "Member"
    ADMIN = "admin", "Admin"

class RequestStatus(models.TextChoices):
    NONE = "none", "None"           # No request (direct delivery)
    PENDING = "pending", "Pending"   # Awaiting acceptance
    ACCEPTED = "accepted", "Accepted"
    IGNORED = "ignored", "Ignored"
    BLOCKED = "blocked", "Blocked"

class MessageContentType(models.TextChoices):
    TEXT = "text", "Text"
    SYSTEM = "system", "System"      # Join/leave/rename notifications
    # IMAGE = "image", "Image"       # v2
    # FILE = "file", "File"          # v2
    # LINK = "link", "Link"          # v2

class MessageStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    EDITED = "edited", "Edited"
    DELETED = "deleted", "Deleted"
```

### 4.2 Models

#### Conversation

```python
class Conversation(UUIDModel, TimeStampedModel):
    """
    A DM or group chat, scoped to exactly one isolation boundary.
    """
    # Scope isolation (immutable after creation)
    scope_type = CharField(max_length=20, choices=ScopeType.choices, db_index=True)
    scope_id = UUIDField(null=True, blank=True, db_index=True)  # null = global

    # Conversation metadata
    conversation_type = CharField(max_length=20, choices=ConversationType.choices)
    name = CharField(max_length=255, blank=True, default="")      # Group only
    description = TextField(blank=True, default="")                # Group only

    # Creator tracking
    created_by_type = CharField(max_length=20, choices=ParticipantType.choices)
    created_by_id = UUIDField()

    # Denormalized last message (avoids N+1 on conversation list)
    last_message_id = UUIDField(null=True, blank=True)
    last_message_at = DateTimeField(null=True, blank=True, db_index=True)
    last_message_preview = CharField(max_length=200, blank=True, default="")
    last_message_sender_type = CharField(max_length=20, blank=True, default="")
    last_message_sender_id = UUIDField(null=True, blank=True)

    # Active state
    is_active = BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "chat_conversation"
        ordering = ["-last_message_at", "-created_at"]
        indexes = [
            Index(fields=["scope_type", "scope_id", "is_active"]),
            Index(fields=["scope_type", "scope_id", "last_message_at"]),
            Index(fields=["conversation_type", "scope_type", "scope_id"]),
        ]
```

#### ConversationParticipant

```python
class ConversationParticipant(UUIDModel, TimeStampedModel):
    """
    Links a participant (user or entity) to a conversation.
    Also stores per-participant state: watermarks, request status, mute, role.
    """
    conversation = ForeignKey(Conversation, on_delete=CASCADE, related_name="participants")

    # Polymorphic participant identity
    participant_type = CharField(max_length=20, choices=ParticipantType.choices)
    participant_id = UUIDField()

    # Group chat role (ignored for DMs)
    role = CharField(max_length=20, choices=ParticipantRole.choices, default=ParticipantRole.MEMBER)

    # Chat request state (DMs in global scope only)
    request_status = CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.NONE)

    # Delivery watermarks
    last_delivered_message_id = UUIDField(null=True, blank=True)
    last_seen_message_id = UUIDField(null=True, blank=True)
    last_seen_at = DateTimeField(null=True, blank=True)

    # Notification control
    is_muted = BooleanField(default=False)

    # Participation lifecycle
    is_active = BooleanField(default=True, db_index=True)
    left_at = DateTimeField(null=True, blank=True)
    removed_at = DateTimeField(null=True, blank=True)
    removed_by = ForeignKey(User, on_delete=SET_NULL, null=True, blank=True,
                            related_name="removed_chat_participants")

    # Entity delegation (who added this participant — for audit)
    added_by = ForeignKey(User, on_delete=SET_NULL, null=True, blank=True,
                          related_name="added_chat_participants")

    class Meta:
        db_table = "chat_conversation_participant"
        constraints = [
            UniqueConstraint(
                fields=["conversation", "participant_type", "participant_id"],
                condition=Q(is_active=True),
                name="unique_active_participant",
            ),
        ]
        indexes = [
            Index(fields=["participant_type", "participant_id", "is_active"]),
            Index(fields=["conversation", "is_active"]),
            Index(fields=["participant_type", "participant_id", "request_status"]),
        ]
```

#### Message

```python
class Message(UUIDModel, TimeStampedModel):
    """
    A single message in a conversation. Immutable except for edit/delete.
    """
    conversation = ForeignKey(Conversation, on_delete=CASCADE, related_name="messages")

    # Sender identity (polymorphic — user or entity)
    sender_type = CharField(max_length=20, choices=ParticipantType.choices)
    sender_id = UUIDField()

    # Entity delegation audit
    acting_user_id = UUIDField(null=True, blank=True)  # The human behind an entity message

    # Content
    content_type = CharField(max_length=20, choices=MessageContentType.choices, default=MessageContentType.TEXT)
    content = TextField()
    metadata = JSONField(default=dict, blank=True)  # For rich content types (url preview, file info, etc.)

    # Ordering (gap-free within conversation)
    sequence_number = PositiveIntegerField(db_index=True)

    # Edit/delete lifecycle
    status = CharField(max_length=20, choices=MessageStatus.choices, default=MessageStatus.ACTIVE)
    edited_at = DateTimeField(null=True, blank=True)
    original_content = TextField(blank=True, default="")  # Preserved on edit

    class Meta:
        db_table = "chat_message"
        ordering = ["sequence_number"]
        constraints = [
            UniqueConstraint(
                fields=["conversation", "sequence_number"],
                name="unique_message_sequence",
            ),
        ]
        indexes = [
            Index(fields=["conversation", "created_at"]),
            Index(fields=["conversation", "sequence_number"]),
            Index(fields=["sender_type", "sender_id"]),
        ]
```

#### ChatBlock

```python
class ChatBlock(UUIDModel, TimeStampedModel):
    """
    Per-user block list. Global scope only.
    Prevents blocked participant from sending DMs to the blocker.
    """
    blocker = ForeignKey(User, on_delete=CASCADE, related_name="chat_blocks")
    blocked_type = CharField(max_length=20, choices=ParticipantType.choices)
    blocked_id = UUIDField()

    class Meta:
        db_table = "chat_block"
        constraints = [
            UniqueConstraint(
                fields=["blocker", "blocked_type", "blocked_id"],
                name="unique_chat_block",
            ),
        ]
        indexes = [
            Index(fields=["blocker", "blocked_type", "blocked_id"]),
            Index(fields=["blocked_type", "blocked_id"]),
        ]
```

### 4.3 Migration Plan

| Migration | Description |
|-----------|-------------|
| `0001_initial` | All 4 models: Conversation, ConversationParticipant, Message, ChatBlock |
| `0002_seed_chat_permissions` | Seed `can_manage_chat` permission into RBAC Permission table |
| `0003_message_fts_index` | GIN index on `Message.content` for FTS (requires PostgreSQL) |

### 4.4 Model Relationships Diagram

```
┌──────────────┐       ┌─────────────────────────┐
│ Conversation │──1:N──│ ConversationParticipant  │
│              │       │                         │
│ scope_type   │       │ participant_type/id     │
│ scope_id     │       │ request_status          │
│ conv_type    │       │ last_seen_message_id    │
│ last_msg_*   │       │ last_delivered_msg_id   │
│              │       │ role (group admin)      │
└──────┬───────┘       └─────────────────────────┘
       │
       │ 1:N
       ▼
┌──────────────┐       ┌──────────────┐
│   Message    │       │  ChatBlock   │
│              │       │              │
│ sender_type  │       │ blocker (FK) │
│ sender_id    │       │ blocked_type │
│ acting_user  │       │ blocked_id   │
│ content      │       │              │
│ seq_number   │       └──────────────┘
│ status       │
└──────────────┘
```

---

## 5. RBAC Integration

### 5.1 New Permission

| Code | Name | Description | Category | Applicable Scopes |
|------|------|-------------|----------|--------------------|
| `can_manage_chat` | Manage Chat | Send/receive messages as entity, access entity inbox | `chat` | `["business", "platform_only"]` |

### 5.2 Permission Seed Migration

File: `apps/chat/migrations/0002_seed_chat_permissions.py`

Pattern: Same as `apps/rbac/migrations/0002_seed_permissions.py` — uses `get_or_create` with defaults tuple.

```python
PERMISSIONS = [
    (
        "can_manage_chat",
        "Manage Chat",
        "Send and receive messages as the entity account, access entity inbox",
        "chat",
        ["business", "platform_only"],
    ),
]
```

### 5.3 Policy Design

```python
class ChatPolicy:
    """Authorization for all chat actions."""

    @staticmethod
    def validate_scope_eligibility(
        *, user, participant_type, participant_id,
        scope_type, scope_id
    ) -> None:
        """
        Validates that a participant can act in the given scope.
        Raises PermissionDenied if not eligible.

        Rules:
        - Global scope: any authenticated user, or entity with can_manage_chat
        - Business scope: must be ACTIVE member of that business
        - Platform scope: must be ACTIVE platform member
        - Entity participants: global scope only, acting_user must have can_manage_chat
        """

    @staticmethod
    def can_send_message(*, user, conversation, sender_type, sender_id) -> bool:
        """Check if user can send a message to this conversation."""

    @staticmethod
    def can_manage_entity_chat(*, user, account_type, account_id) -> bool:
        """Check if user has can_manage_chat permission for this entity."""

    @staticmethod
    def can_manage_group(*, user, conversation) -> bool:
        """Check if user is admin of this group conversation."""

    @staticmethod
    def get_viewer_permissions(*, user, conversation) -> dict:
        """Tier 1.5 permissions for conversation detail view."""
```

---

## 6. Audit Integration

### 6.1 New AuditLog Actions

| Action | When | Details |
|--------|------|---------|
| `chat.conversation.created` | New conversation | `{scope_type, scope_id, conversation_type, participant_ids}` |
| `chat.message.sent` | Entity sends message | `{conversation_id, sender_type, sender_id, acting_user_id}` — **entity messages only** (user messages are too high-volume for audit) |
| `chat.message.edited` | Message edited | `{conversation_id, message_id, acting_user_id}` |
| `chat.message.deleted` | Message deleted by moderator/admin | `{conversation_id, message_id, acting_user_id, reason}` |
| `chat.participant.added` | Added to group | `{conversation_id, participant_type, participant_id, added_by}` |
| `chat.participant.removed` | Removed from group | `{conversation_id, participant_type, participant_id, removed_by}` |
| `chat.request.accepted` | Chat request accepted | `{conversation_id, requester_type, requester_id}` |
| `chat.block.created` | User blocked someone | `{blocker_id, blocked_type, blocked_id}` |
| `chat.block.removed` | User unblocked someone | `{blocker_id, blocked_type, blocked_id}` |

**Audit policy:** Only entity actions and moderation actions are audited. Regular user-to-user messages are NOT audited (too high-volume, privacy concerns). Block/unblock are audited for abuse detection.

---

## 7. Notification Integration

### 7.1 New Notification Types

| Type | Category | Channels | Required Context | Configurable | Rate Limit |
|------|----------|----------|-----------------|-------------|------------|
| `chat_message_received` | `chat` | `push` | `conversation_id, sender_name, preview` | Yes | 1 per conversation per 5 min |
| `chat_request_received` | `chat` | `push, email` | `conversation_id, requester_name, preview` | Yes | None |
| `chat_request_accepted` | `chat` | `push` | `conversation_id, accepter_name` | Yes | None |
| `chat_group_invitation` | `chat` | `push` | `conversation_id, group_name, inviter_name` | Yes | None |

**New enum value required:** `Category.CHAT = "chat"` must be added to `apps/notifications/types.py` `Category` enum (currently has: AUTH, SECURITY, TRANSACTIONAL, MARKETING, SYSTEM, SOCIAL).

### 7.2 Notification Delivery Logic

`NotificationService.send()` has **no built-in rate-limiting or presence awareness**. All delivery logic must be implemented in `ChatService` before calling `NotificationService.send()`:

```python
# In ChatService.send_message() — after persisting the message:

def _send_message_notifications(message, conversation, sender_type, sender_id):
    """Send notifications to offline, unmuted recipients."""
    for participant in offline_unmuted_participants:
        # 1. Presence check — skip online users (they get WebSocket delivery)
        if PresenceManager.is_online(participant.participant_id):
            continue

        # 2. Rate-limit check — max 1 notification per conversation per 5 min
        rate_key = f"chat:rate:notif:{participant.participant_id}:{conversation.id}"
        if redis_client.get(rate_key):
            continue  # Already notified recently
        redis_client.setex(rate_key, 300, "1")  # 5 min TTL

        # 3. Send via NotificationService
        NotificationService.send(
            user=participant_user,  # User object, resolved from participant
            notification_type="chat_message_received",
            context={...},
        )
```

### 7.3 Entity Notification Routing

When a user sends a DM to a business/platform entity, the notification must reach the **humans** who manage that entity's chat:

```python
# Use existing RBAC selector to find all members with can_manage_chat:
from apps.rbac.selectors import MembershipSelector

users = MembershipSelector.get_users_with_permission(
    account_type=entity_account_type,  # "business" or "platform"
    account_id=entity_account_id,
    permission_code="can_manage_chat",
)

# Send notification to each (with same presence + rate-limit checks)
for user in users:
    if not PresenceManager.is_online(user.id):
        NotificationService.send(user=user, notification_type="chat_message_received", ...)
```

This uses `MembershipSelector.get_users_with_permission()` which joins Membership → Role → RolePermission → Permission to find all active users with the specified permission in the account.

---

## 8. API Design

### 8.1 REST Endpoints

All under `/api/v1/chat/`. All require authentication (`IsAuthenticated`) unless noted.

#### Conversations

| Endpoint | Method | Description | Request Body | Response |
|----------|--------|-------------|-------------|----------|
| `/conversations/` | GET | List conversations for current scope | Query: `scope_type`, `scope_id`, `page`, `page_size` | Paginated list with last_message, unread_count |
| `/conversations/` | POST | Create new conversation (DM or group) | `{scope_type, scope_id, conversation_type, participant_ids[], name?}` | `{id, ...}` 201 |
| `/conversations/<id>/` | GET | Get conversation detail | — | Conversation with participants, `_permissions` |
| `/conversations/<id>/` | PATCH | Update group metadata | `{name?, description?}` | Updated conversation |
| `/conversations/<id>/participants/` | GET | List participants | — | Participant list with display info |
| `/conversations/<id>/participants/` | POST | Add participant to group | `{participant_type, participant_id}` | 201 |
| `/conversations/<id>/participants/<pid>/` | DELETE | Remove participant | — | 204 |
| `/conversations/<id>/leave/` | POST | Leave group conversation | — | 204 |
| `/conversations/<id>/messages/` | GET | Message history (cursor paginated) | Query: `cursor`, `page_size`, `direction` | Cursor-paginated messages |
| `/conversations/<id>/messages/` | POST | Send message (REST fallback) | `{content, content_type?, sender_type?, sender_id?}` | `{id, ...}` 201 |
| `/conversations/<id>/messages/<mid>/` | PATCH | Edit message | `{content}` | Updated message |
| `/conversations/<id>/messages/<mid>/` | DELETE | Delete message | — | 204 |
| `/conversations/<id>/seen/` | POST | Mark seen (watermark update) | `{last_seen_message_id}` | 204 |
| `/conversations/<id>/mute/` | POST | Mute conversation | — | 204 |
| `/conversations/<id>/unmute/` | POST | Unmute conversation | — | 204 |

#### Chat Requests

| Endpoint | Method | Description | Request Body | Response |
|----------|--------|-------------|-------------|----------|
| `/requests/` | GET | List pending chat requests | Query: `page`, `page_size` | Paginated requests with preview |
| `/requests/<conversation_id>/accept/` | POST | Accept chat request | — | 200 |
| `/requests/<conversation_id>/ignore/` | POST | Ignore chat request | — | 204 |
| `/requests/<conversation_id>/block/` | POST | Block from chat request | — | 204 |

#### Blocks

| Endpoint | Method | Description | Request Body | Response |
|----------|--------|-------------|-------------|----------|
| `/blocks/` | GET | List blocked participants | Query: `page`, `page_size` | Paginated block list |
| `/blocks/` | POST | Block a participant | `{blocked_type, blocked_id}` | 201 |
| `/blocks/<block_id>/` | DELETE | Unblock | — | 204 |

#### Entity Inbox

| Endpoint | Method | Description | Request Body | Response |
|----------|--------|-------------|-------------|----------|
| `/entity/<account_type>/<account_id>/conversations/` | GET | Entity inbox (global scope) | Query: `page`, `page_size` | Paginated entity conversations |

#### Search

| Endpoint | Method | Description | Request Body | Response |
|----------|--------|-------------|-------------|----------|
| `/search/` | GET | Search conversations/messages | Query: `q`, `scope_type`, `scope_id`, `page` | Paginated search results |

#### Unread Counts

| Endpoint | Method | Description | Request Body | Response |
|----------|--------|-------------|-------------|----------|
| `/unread/` | GET | Unread counts per scope | — | `{global: N, business: {id: N}, platform: N}` |

### 8.2 WebSocket Protocol

**Connection:** `ws://host/ws/chat/?token=<jwt_access_token>`

#### Client → Server Events

| Event Type | Payload | Description |
|------------|---------|-------------|
| `message.send` | `{conversation_id, content, content_type?, sender_type?, sender_id?}` | Send a message |
| `message.edit` | `{message_id, content}` | Edit own message |
| `message.delete` | `{message_id}` | Delete own message |
| `typing.start` | `{conversation_id, sender_type?, sender_id?}` | Start typing indicator |
| `typing.stop` | `{conversation_id, sender_type?, sender_id?}` | Stop typing indicator |
| `seen` | `{conversation_id, last_seen_message_id}` | Mark messages as seen (watermark) |
| `delivered` | `{conversation_id, last_delivered_message_id}` | Acknowledge delivery (watermark) |
| `conversation.join` | `{conversation_id}` | Subscribe to conversation updates |
| `conversation.leave` | `{conversation_id}` | Unsubscribe from conversation updates |

#### Server → Client Events

| Event Type | Payload | Description |
|------------|---------|-------------|
| `message.new` | `{conversation_id, message: {...}}` | New message received |
| `message.edited` | `{conversation_id, message_id, content, edited_at}` | Message was edited |
| `message.deleted` | `{conversation_id, message_id}` | Message was deleted |
| `typing` | `{conversation_id, participant_type, participant_id, is_typing}` | Typing indicator |
| `seen.update` | `{conversation_id, participant_type, participant_id, last_seen_message_id}` | Someone read messages |
| `delivered.update` | `{conversation_id, participant_type, participant_id, last_delivered_message_id}` | Delivery confirmed |
| `participant.joined` | `{conversation_id, participant: {...}}` | Someone joined group |
| `participant.left` | `{conversation_id, participant_type, participant_id}` | Someone left/removed |
| `conversation.updated` | `{conversation_id, name?, description?}` | Group metadata changed |
| `request.received` | `{conversation_id, requester: {...}, preview}` | New chat request |
| `request.accepted` | `{conversation_id}` | Your chat request was accepted |
| `presence` | `{user_id, is_online}` | Presence update |
| `error` | `{code, message, details?}` | Error response |

#### WebSocket Error Codes

| Code | Meaning |
|------|---------|
| `not_authenticated` | Token invalid or expired |
| `not_participant` | Not a participant in conversation |
| `scope_denied` | Not eligible for this scope |
| `blocked` | Blocked by recipient |
| `request_pending` | Chat request already pending |
| `rate_limited` | Too many messages |
| `message_too_long` | Content exceeds max length |
| `edit_window_expired` | Edit time window passed |

---

## 9. Service Layer Design

### 9.1 ChatService Methods

All methods are `@staticmethod` with `@db_transaction.atomic` for writes.

```
ChatService:
  # Conversations
  create_conversation(*, scope_type, scope_id, conversation_type, participant_ids,
                      name="", creator_type, creator_id, acting_user, request=None)
                      → Conversation

  # Messages
  send_message(*, conversation_id, sender_type, sender_id, acting_user_id,
               content, content_type="text", metadata=None, request=None)
               → Message

  edit_message(*, message_id, new_content, user, request=None) → Message

  delete_message(*, message_id, user, request=None) → None

  # Watermarks
  update_seen_watermark(*, conversation_id, participant_type, participant_id,
                        last_seen_message_id) → None

  update_delivered_watermark(*, conversation_id, participant_type, participant_id,
                            last_delivered_message_id) → None

  # Chat requests
  accept_request(*, conversation_id, user) → None
  ignore_request(*, conversation_id, user) → None

  # Participants
  add_participant(*, conversation_id, participant_type, participant_id,
                  added_by, request=None) → ConversationParticipant

  remove_participant(*, conversation_id, participant_type, participant_id,
                     removed_by, request=None) → None

  leave_conversation(*, conversation_id, user) → None

  # Blocks
  block_participant(*, blocker, blocked_type, blocked_id, request=None) → ChatBlock
  unblock_participant(*, blocker, block_id, request=None) → None

  # Group management
  update_group(*, conversation_id, name=None, description=None, user, request=None) → Conversation
  promote_to_admin(*, conversation_id, participant_id, user) → None
  demote_from_admin(*, conversation_id, participant_id, user) → None

  # Internal helpers
  _validate_scope_eligibility(user, participant_type, participant_id, scope_type, scope_id)
  _check_block_status(sender_type, sender_id, recipient_type, recipient_id)
  _determine_request_status(sender_type, sender_id, recipient_type, recipient_id, scope_type)
  _update_conversation_last_message(conversation, message)
  _get_next_sequence_number(conversation_id)
  _check_rate_limit(user_id, conversation_id)
```

### 9.2 ChatSelector Methods

All methods are `@staticmethod`, read-only.

```
ChatSelector:
  # Conversations
  get_conversation_by_id(*, conversation_id) → Conversation
  get_conversations_for_participant(*, participant_type, participant_id,
                                    scope_type, scope_id=None,
                                    exclude_requests=True) → QuerySet

  get_dm_conversation(*, scope_type, scope_id, participant_a_type,
                      participant_a_id, participant_b_type, participant_b_id)
                      → Conversation | None

  # Messages
  get_messages(*, conversation_id, cursor=None, page_size=50,
               direction="older") → QuerySet

  get_message_by_id(*, message_id) → Message

  search_messages(*, query, participant_type, participant_id,
                  scope_type, scope_id=None) → QuerySet

  # Participants
  get_participants(*, conversation_id) → QuerySet[ConversationParticipant]
  get_participant(*, conversation_id, participant_type, participant_id) → CP | None
  is_participant(*, conversation_id, participant_type, participant_id) → bool

  # Chat requests
  get_pending_requests(*, recipient_type, recipient_id) → QuerySet
  count_pending_requests(*, recipient_type, recipient_id) → int

  # Blocks
  is_blocked(*, blocker_id, blocked_type, blocked_id) → bool
  get_blocks_for_user(*, user_id) → QuerySet[ChatBlock]

  # Unread
  get_unread_count(*, conversation_id, participant_type, participant_id) → int
  get_unread_counts_by_scope(*, user_id) → dict

  # Presence (Redis)
  get_online_users(*, user_ids) → set[UUID]
```

### 9.3 Membership Lifecycle Edge Cases

#### Member removed from organization → org-scope chat access revoked

When a membership transitions from ACTIVE to any non-active status (removed, suspended, left), the user loses access to all org-scope conversations. This is handled **lazily** (not eagerly cascaded):

**Strategy: Lazy access check (preferred over eager cascade)**
- Every chat query (`get_conversations_for_participant`, `send_message`, etc.) for org-scope conversations re-validates membership via `MembershipSelector.is_user_member_of_account(user=..., account_type=..., account_id=...)` which filters ACTIVE only.
- Removed members naturally cannot send messages (scope eligibility fails) or see conversations (selector excludes them).
- Their `ConversationParticipant` records are NOT eagerly deactivated — this avoids tight coupling between RBAC and chat systems.
- Historical messages authored by removed members remain visible to other participants (messages are authored by `sender_id`, not tied to active participation).

**Why lazy over eager:**
1. No cross-system signal/hook needed — chat doesn't subscribe to RBAC events
2. Membership status can be temporary (suspension → reinstatement)
3. Simpler to reason about — one source of truth (RBAC membership status)

#### Last participant leaves a group conversation

When the last active participant calls `leave_conversation()`:
1. Participant's `is_active = False`, `left_at = now()`
2. Check: `ConversationParticipant.objects.filter(conversation=conv, is_active=True).count() == 0`
3. If zero active participants → set `Conversation.is_active = False`
4. Inactive conversations are excluded from all list queries
5. Messages are preserved (no cascade delete) — they may be needed for moderation/audit

#### Admin succession in group chats

When the last admin leaves a group that still has active members:
1. `leave_conversation()` detects no remaining admins
2. Auto-promotes the oldest active participant (by `created_at`) to `role=admin`
3. Sends `system` message: "{user} was promoted to admin"
4. If no members remain, conversation becomes inactive (see above)

---

## 10. WebSocket Consumer Design

### 10.1 ChatConsumer

```python
class ChatConsumer(AuthenticatedConsumer):
    """
    Single WebSocket per authenticated user session.
    Extends AuthenticatedConsumer from apps.auth.consumers.
    """

    async def on_authenticated(self):
        """Join personal channel group and all active conversation groups."""
        self.user_group = f"user_{self.scope['user'].id}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        # Join all active conversation groups
        conversation_ids = await self._get_user_conversations()
        for conv_id in conversation_ids:
            await self.channel_layer.group_add(f"conv_{conv_id}", self.channel_name)

        # Set online presence in Redis
        await self._set_online(True)

    async def on_disconnect(self):
        """Leave all groups, clear presence."""
        await self._set_online(False)
        # Groups auto-cleaned by Channels on disconnect

    async def receive_authenticated(self, content):
        """Route incoming messages to handler methods."""
        event_type = content.get("type")
        handler = self._handlers.get(event_type)
        if handler:
            await handler(self, content)
        else:
            await self.send_json({"type": "error", "code": "unknown_event"})

    # Handler registry
    _handlers = {
        "message.send": handle_message_send,
        "message.edit": handle_message_edit,
        "message.delete": handle_message_delete,
        "typing.start": handle_typing,
        "typing.stop": handle_typing,
        "seen": handle_seen,
        "delivered": handle_delivered,
        "conversation.join": handle_join,
        "conversation.leave": handle_leave,
    }
```

### 10.2 Channel Group Strategy

| Group Name | Members | Events |
|------------|---------|--------|
| `user_{user_id}` | All WebSocket connections for a user | Personal notifications, request received, presence |
| `conv_{conversation_id}` | All online participants of a conversation | Messages, typing, seen, participant changes |

### 10.3 Message Flow

```
1. Client sends: {"type": "message.send", "conversation_id": "abc", "content": "Hello"}
2. ChatConsumer.handle_message_send():
   a. Validate user is participant (via ChatSelector)
   b. Validate scope eligibility (via ChatPolicy)
   c. Check block status
   d. Check chat request status (if DM + not connected → create/update request)
   e. Check rate limit
   f. Call ChatService.send_message() via database_sync_to_async
   g. Broadcast to conv_abc group: {"type": "message.new", "message": {...}}
   h. Send delivery confirmation to sender: {"type": "message.sent", "message_id": "..."}
3. Other participants' ChatConsumer.chat_message() handler receives group_send
4. Each participant's client gets the message via WebSocket
5. Client auto-sends "delivered" event → watermark update → broadcast to sender
```

---

## 11. Implementation Phases

### Phase 1: Foundation (Models + Migrations + Basic Service)

**Files to create:**
```
apps/chat/
├── __init__.py
├── apps.py
├── constants.py         (all enums)
├── models.py            (Conversation, ConversationParticipant, Message, ChatBlock)
├── admin.py             (ModelAdmin for all models)
├── selectors.py         (ChatSelector — all read methods)
├── services.py          (ChatService — all write methods)
├── policies.py          (ChatPolicy — scope validation, permissions)
├── serializers.py       (Input/Output serializers)
├── views.py             (REST API views)
├── urls.py              (URL routing)
├── migrations/
│   ├── __init__.py
│   ├── 0001_initial.py
│   └── 0002_seed_chat_permissions.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── factories.py
```

**Cross-system changes:**
- `backend_core/settings/base.py` — add `"apps.chat"` to INSTALLED_APPS
- `backend_core/urls.py` — add `path("api/v1/chat/", include("apps.chat.urls"))`
- `apps/core/observability/audit/models.py` — add 9 new AuditLog.Action values

**Steps:**
1. Create app structure (apps.py, __init__.py, constants.py)
2. Create models (Conversation, ConversationParticipant, Message, ChatBlock)
3. Create initial migration + permission seed migration
4. Register in settings + URLs
5. Create ChatSelector with core query methods
6. Create ChatPolicy with scope validation
7. Create ChatService with conversation/message CRUD
8. Create serializers (input + output)
9. Create REST API views
10. Write factories (ConversationFactory, MessageFactory, etc.)
11. Write unit tests for models, selectors, services, policies, views
12. Add AuditLog.Action entries for chat actions

**Test target:** ~200 unit tests

### Phase 2: WebSocket Real-Time Layer

**Files to create/modify:**
```
apps/chat/
├── consumers.py          (ChatConsumer)
├── ws_handlers.py        (Handler functions for each event type)
├── presence.py           (Redis-based presence manager)
├── tests/
│   ├── test_consumers.py
│   └── test_presence.py
```

**Cross-system changes:**
- `backend_core/routing.py` — add WebSocket URL pattern
- `backend_core/asgi.py` — switch to JWTAuthMiddleware (from AuthMiddlewareStack)

**Steps:**
1. Create ChatConsumer extending AuthenticatedConsumer
2. Implement handler functions (message.send, typing, seen, delivered)
3. Create presence manager (Redis-backed online status)
4. Wire up WebSocket routing
5. Implement channel group management (join/leave conversation groups)
6. Write WebSocket consumer tests
7. Integration test: REST create + WS message flow

**Test target:** ~50 WebSocket tests

### Phase 3: Chat Requests + Blocks + Notifications

**Files to modify:**
```
apps/chat/services.py     (add request/block logic)
apps/chat/selectors.py    (add request/block queries)
apps/chat/views.py        (add request/block endpoints)
apps/chat/serializers.py  (add request/block serializers)
apps/notifications/types.py  (add 4 chat notification types)
```

**Steps:**
1. Implement chat request lifecycle (pending → accepted/ignored/blocked)
2. Implement block system (block/unblock, silent rejection)
3. Integrate with ConnectionSelector.is_connected() for request gating
4. Add notification types to notifications system
5. Wire notifications to chat events (new message for offline users, request received)
6. Implement chat request expiration task (Celery periodic)
7. Write tests for request flows, block flows, notifications

**Test target:** ~100 tests

### Phase 4: Entity Chat + Audit

**Steps:**
1. Implement entity participation (acting_user_id delegation)
2. Add can_manage_chat permission checks for entity actions
3. Entity inbox endpoints
4. Audit logging for entity actions
5. Multiple concurrent entity operators
6. Tests for entity flows, permission checks, audit trail

**Test target:** ~80 tests

### Phase 5: Message Search + Unread Counts

**Steps:**
1. FTS index migration on Message.content (PostgreSQL GIN)
2. Implement message search in ChatSelector (SearchVector + SearchQuery)
3. Unread count aggregation (per-conversation, per-scope)
4. Search REST endpoint
5. Tests for search, unread counts

**Test target:** ~30 tests

**Total test target:** ~460 tests across all phases (actual: 387 — see Section 22 addendum for details)

---

## 12. Serializer Shapes

### 12.1 Participant Name & Avatar Resolution

Serializers must resolve `display_name` and `avatar_url` from the correct model path for each participant type. **This is a known gotcha** — the network system had real bugs from using non-existent field names (see `network-system.md` Section 11).

| Participant Type | `display_name` source | `avatar_url` source |
|-----------------|----------------------|---------------------|
| `user` | `User.profile.display_name` (property: first+last, or first, or email prefix) | `User.profile.avatar` (ImageField, nullable) |
| `business` | `BusinessProfile.display_name` (CharField) | `BusinessProfile.logo` (ImageField, nullable) |
| `platform` | `PlatformProfile.name` (CharField) | `PlatformProfile.logo` (ImageField, nullable) |

**Common mistakes to avoid:**
- `BusinessAccount.business_name` → does NOT exist. Use `BusinessProfile.display_name` (via `business.profile.display_name`)
- `BusinessAccount.name` → does NOT exist. `BusinessAccount.legal_name` is for legal/internal use only
- `User.full_name` → does NOT exist on User model. It's a property on `UserProfile` (via `user.profile.full_name`)
- `PlatformAccount.name` → does NOT exist. Use `PlatformProfile.name` (via `platform.profile.name`)

**Query pattern:** Use `select_related("profile")` when loading Business/Platform/User objects to avoid N+1 queries during name resolution. For participant lists, annotate names in the queryset if possible (see network system's N+1 TODO).

### 12.2 Conversation Output (list item)

```json
{
  "id": "uuid",
  "scope_type": "global",
  "scope_id": null,
  "conversation_type": "direct",
  "name": "",
  "participants": [
    {
      "participant_type": "user",
      "participant_id": "uuid",
      "display_name": "Alice",
      "avatar_url": "/media/...",
      "is_online": true
    }
  ],
  "last_message": {
    "id": "uuid",
    "sender_type": "user",
    "sender_id": "uuid",
    "sender_name": "Bob",
    "content_preview": "Hey, how are you?",
    "created_at": "2026-03-19T12:00:00Z"
  },
  "unread_count": 3,
  "is_muted": false,
  "created_at": "2026-03-19T10:00:00Z"
}
```

### Message Output

```json
{
  "id": "uuid",
  "conversation_id": "uuid",
  "sender_type": "business",
  "sender_id": "uuid",
  "sender_name": "Acme Corp",
  "sender_avatar_url": "/media/...",
  "content_type": "text",
  "content": "Thank you for your inquiry!",
  "status": "active",
  "sequence_number": 47,
  "edited_at": null,
  "created_at": "2026-03-19T12:05:00Z",
  "delivery_status": {
    "delivered_to": 2,
    "seen_by": 1,
    "total_recipients": 3
  }
}
```

### Chat Request Output

```json
{
  "conversation_id": "uuid",
  "requester": {
    "participant_type": "user",
    "participant_id": "uuid",
    "display_name": "Unknown User",
    "avatar_url": "/media/..."
  },
  "preview_messages": [
    {
      "content": "Hi! I saw your profile and...",
      "created_at": "2026-03-19T11:00:00Z"
    }
  ],
  "message_count": 2,
  "created_at": "2026-03-19T11:00:00Z"
}
```

---

## 13. Cursor Pagination for Messages

Messages use **cursor-based pagination** (not page-number) for efficient bi-directional scrolling.

**Important:** The existing `CursorResultsPagination` defaults to `ordering = "-created_at"`. Messages need a **custom subclass** that orders by `sequence_number` and supports bidirectional scrolling:

```python
class MessageCursorPagination(CursorPagination):
    """
    Custom cursor pagination for message history.

    Extends DRF's CursorPagination (NOT CursorResultsPagination) because
    we need custom ordering and bidirectional support.

    Ordering by sequence_number instead of created_at:
    - Gap-free: no clock skew issues
    - Deterministic: no ties between messages
    - Bidirectional: supports both "older" and "newer" directions
    """
    page_size = 50
    max_page_size = 100
    page_size_query_param = "page_size"
    cursor_query_param = "cursor"
    ordering = "-sequence_number"  # Most recent first (default load direction)

    # Custom: bidirectional support via `direction` query param
    # ?cursor=<sequence_number>&direction=older&page_size=50
    # ?cursor=<sequence_number>&direction=newer&page_size=50
    # No cursor = latest messages (first page load)
```

**Note:** Conversation lists use `StandardPagination` (page-number) since they're ordered by `last_message_at` and don't need cursor stability.

**Response shape:**
```json
{
  "messages": [...],
  "has_more": true,
  "next_cursor": 42,
  "prev_cursor": 92
}
```

---

## 14. Rate Limiting

Enforced via Redis counters with TTL:

| Action | Limit | Window | Key Pattern |
|--------|-------|--------|-------------|
| Send message | 30 per conversation | 1 minute | `chat:rate:msg:{user_id}:{conv_id}` |
| Create conversation | 5 total | 1 hour | `chat:rate:conv:{user_id}` |
| Send chat request | 10 total | 1 hour | `chat:rate:req:{user_id}` |

Exceeding raises `RateLimitExceeded` with `retry_after` seconds.

---

## 15. Edit & Delete Behavior

### 15.1 Edit Window

Messages can be edited within **15 minutes** of creation. After that, `edit_message()` raises `BusinessRuleViolation(rule="edit_window_expired")`.

Setting: `CHAT_MESSAGE_EDIT_WINDOW_MINUTES = 15` in settings.

On edit:
1. `original_content` = current `content` (preserved for moderation audit)
2. `content` = new text
3. `status` = `"edited"`
4. `edited_at` = now
5. Broadcast `message.edited` to conversation group

### 15.2 Delete Behavior

On delete (`ChatService.delete_message()`):
1. `original_content` = current `content` (preserved for moderation — consistent with edit pattern)
2. `content` = `""` (cleared for privacy — recipients see "This message was deleted")
3. `status` = `"deleted"`
4. Broadcast `message.deleted` to conversation group

**Who can delete:**
- Message author: can delete own messages (any time, no window restriction)
- Group admin: can delete any message in their group
- Business/Platform moderator (org scope): members with moderation permission can delete messages in org-scope conversations

**Why preserve in `original_content`:** Consistent with the edit pattern. Enables moderation review of deleted content for abuse reports. The `content` field is cleared so serializers never expose deleted text to regular participants.

---

## 16. Testing Strategy

### Unit Tests (SQLite-compatible)

| Module | Tests | Focus |
|--------|-------|-------|
| `test_models.py` | ~30 | Constraints, enums, field validation, str representations |
| `test_selectors.py` | ~60 | Query methods, filtering, scope isolation, cursor pagination |
| `test_services.py` | ~80 | CRUD operations, business rules, request lifecycle, block logic |
| `test_policies.py` | ~40 | Scope eligibility, permission checks, entity delegation |
| `test_views.py` | ~80 | REST API endpoints (mock service layer), response shapes |
| `test_serializers.py` | ~20 | Input validation, output shape |
| `test_consumers.py` | ~50 | WebSocket handlers, channel layer mock |
| `test_presence.py` | ~10 | Redis presence manager |
| **Total** | **~370** | |

### PostgreSQL-Required Tests

| Test | Marker | Focus |
|------|--------|-------|
| `test_fts_search.py` | `requires_postgres` | FTS SearchVector + SearchQuery on messages |
| `test_constraints.py` | `requires_postgres` | Partial unique constraints, CHECK constraints |

### Integration Tests (Docker)

| Test | Count | Focus |
|------|-------|-------|
| DM flow (create → send → receive → seen) | ~10 | End-to-end happy path |
| Chat request flow (send → accept/ignore/block) | ~8 | Request lifecycle |
| Entity chat flow (business DMs user) | ~6 | Entity delegation + audit |
| Scope isolation | ~5 | Cross-scope visibility prevention |
| Block flow | ~5 | Silent rejection verification |
| Group chat flow | ~8 | Create, add, remove, leave, admin transfer |
| **Total** | **~42** | |

### Key Edge Cases

- DM deduplication: creating a DM with the same two participants in the same scope returns existing conversation
- Chat request auto-accept: B sends to A while A's request to B is pending → auto-accept
- Race condition: two users send first message to each other simultaneously
- Entity operator switch: user A starts message as entity, user B continues — both see same inbox
- Member removal: user removed from business → can no longer send in business scope
- Block + group chat: blocked user's messages hidden, neither party removed
- Edit window: message edited at exactly 15 minutes
- Conversation with no messages (created but empty)
- Sequence number gap: message deleted, next message gets N+1 (no gaps)

---

## 17. Risks & Mitigations

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| R-1 | WebSocket connection scaling | High | Redis channel layer handles pub/sub. Multiple Daphne workers behind load balancer. Sticky sessions for WebSocket. |
| R-2 | Message delivery race conditions | Medium | `sequence_number` with DB unique constraint prevents ordering issues. `select_for_update()` on conversation for sequence allocation. |
| R-3 | Scope isolation leak | Critical | Every selector query includes `scope_type + scope_id` filter. DB-level constraints prevent cross-scope participants. Integration tests verify isolation. |
| R-4 | Entity permission caching | Low | `can_manage_chat` checked via PermissionSelector which has 5-min cache. Acceptable staleness for chat. |
| R-5 | Chat request spam | Medium | Rate limiting (10 requests/hour), 3-message cap per pending request, 30-day expiration. |
| R-6 | Database load from message writes | Medium | Denormalized `last_message_*` on Conversation avoids expensive joins on list. Cursor pagination on messages. Sequence number indexed. |
| R-7 | Redis channel layer failure | High | Messages are persisted to PostgreSQL first. Redis failure means real-time delivery fails but messages are not lost. Client falls back to polling REST API. |
| R-8 | Large group chat performance | Low | v1 group chats capped at 50 participants. Typing indicators suppressed for groups > 20. Seen status shows aggregate only. |

---

## 18. Configuration Settings

```python
# backend_core/settings/base.py (new chat settings)

CHAT_MESSAGE_EDIT_WINDOW_MINUTES = 15
CHAT_MESSAGE_MAX_LENGTH = 5000
CHAT_GROUP_MAX_PARTICIPANTS = 50
CHAT_REQUEST_MAX_PENDING_MESSAGES = 3
CHAT_REQUEST_EXPIRATION_DAYS = 30
CHAT_RATE_LIMIT_MESSAGES_PER_MINUTE = 30
CHAT_RATE_LIMIT_CONVERSATIONS_PER_HOUR = 5
CHAT_RATE_LIMIT_REQUESTS_PER_HOUR = 10
CHAT_NOTIFICATION_COOLDOWN_SECONDS = 300  # 5 min per conversation
CHAT_TYPING_INDICATOR_TTL_SECONDS = 5
```

---

## 19. File Summary

### New Files (apps/chat/)

| File | Description |
|------|-------------|
| `__init__.py` | Empty |
| `apps.py` | ChatConfig |
| `constants.py` | ScopeType, ConversationType, ParticipantType, ParticipantRole, RequestStatus, MessageContentType, MessageStatus |
| `models.py` | Conversation, ConversationParticipant, Message, ChatBlock |
| `admin.py` | ModelAdmin for all 4 models |
| `selectors.py` | ChatSelector (all read queries) |
| `services.py` | ChatService (all write operations) |
| `policies.py` | ChatPolicy (scope validation, permission checks) |
| `serializers.py` | Input/output serializers for all endpoints |
| `views.py` | REST API views (~15 endpoints) |
| `urls.py` | URL routing |
| `consumers.py` | ChatConsumer (WebSocket) |
| `ws_handlers.py` | WebSocket event handler functions |
| `presence.py` | Redis-backed online presence manager |
| `tasks.py` | Celery tasks (request expiration) |
| `migrations/0001_initial.py` | Schema migration |
| `migrations/0002_seed_chat_permissions.py` | Permission seed |
| `migrations/0003_message_fts_index.py` | FTS index (PostgreSQL) |
| `tests/conftest.py` | Test fixtures |
| `tests/factories.py` | Factory Boy factories |
| `tests/test_models.py` | Model tests |
| `tests/test_selectors.py` | Selector tests |
| `tests/test_services.py` | Service tests |
| `tests/test_policies.py` | Policy tests |
| `tests/test_views.py` | View tests |
| `tests/test_serializers.py` | Serializer tests |
| `tests/test_consumers.py` | WebSocket tests |
| `tests/test_presence.py` | Presence tests |

### Modified Files

| File | Change |
|------|--------|
| `backend_core/settings/base.py` | Add `"apps.chat"` to INSTALLED_APPS, add CHAT_* settings |
| `backend_core/urls.py` | Add `path("api/v1/chat/", include("apps.chat.urls"))` |
| `backend_core/routing.py` | Add `path("ws/chat/", ChatConsumer.as_asgi())` |
| `backend_core/asgi.py` | Switch to JWTAuthMiddleware |
| `apps/core/observability/audit/models.py` | Add 9 AuditLog.Action values |
| `apps/notifications/types.py` | Add `Category.CHAT` enum value + 4 CHAT notification type entries to `NOTIFICATION_TYPES` dict |

---

## 20. Dependency Graph

```
apps/chat/ READS FROM:
  ├── apps/core/models          (UUIDModel, TimeStampedModel)
  ├── apps/core/types           (ActorContext)
  ├── apps/core/constants       (AccountType, MembershipStatus)
  ├── apps/core/exceptions      (NotFound, PermissionDenied, ConflictError, etc.)
  ├── apps/core/pagination      (StandardPagination, CursorResultsPagination)
  ├── apps/core/views           (PermissionInjectMixin)
  ├── apps/core/permissions     (IsAuthenticated)
  ├── apps/rbac/selectors       (MembershipSelector.is_user_member_of_account,
  │                               MembershipSelector.get_users_with_permission,
  │                               PermissionSelector.get_permissions_for_membership)
  ├── apps/network/selectors    (ConnectionSelector.is_connected)
  ├── apps/users/models         (User, UserProfile — for display_name, avatar)
  ├── apps/organization/business/models    (BusinessAccount, BusinessProfile)
  ├── apps/organization/platform/models    (PlatformAccount, PlatformProfile)
  └── apps/auth/consumers       (AuthenticatedConsumer)

apps/chat/ WRITES TO:
  ├── apps/core/observability/audit  (AuditService.log — entity actions only)
  └── apps/notifications/services    (NotificationService.send — offline notifications)

apps/chat/ ADDS TO:
  ├── apps/rbac/permissions/registry.py  (can_manage_chat — optional, for documentation)
  └── apps/rbac Permission table         (via data migration)
```

---

## 21. Review Notes

*Updated 2026-03-19 — Deep review (development alignment + UX scenarios)*

### Review methodology

Verified the plan against all 8 dependent systems by reading actual source code:
- RBAC: `rbac/selectors.py`, `rbac/models.py`, `rbac/services.py`, 11 seed migrations
- Auth/WebSocket: `auth/middleware.py`, `auth/consumers.py`, `backend_core/asgi.py`, `routing.py`
- Notifications: `notifications/types.py`, `notifications/services/notification_service.py`
- Audit: `core/observability/audit/service.py`, `audit/models.py`
- Network: `network/selectors.py`, `network/models.py`
- Organization: `business/models.py`, `platform/models.py`
- Users: `users/models.py` (User, UserProfile)
- Core: `core/models/base.py`, `core/types.py`, `core/exceptions/domain.py`, `core/pagination/page.py`, `core/views.py`

Walked through 15 UX scenarios: stranger DM, connected DM, user→entity, entity→user, entity↔entity, business internal, platform internal, group creation, group in org scope, block/unblock, offline→online reconnect, entity operator switching, chat request auto-accept, typing indicators, message edit/delete, multi-scope separation.

### Findings (initial count: 15, re-validated to 9)

6 findings were **false alarms** (plan was already correct):
- F-1: `PermissionSelector.has_permission()` — plan uses `ChatPolicy.can_manage_entity_chat()`, dependency graph correctly references `get_permissions_for_membership`
- F-5: `AuditService.log(actor_context=)` — plan's Section 6 Details column correctly maps to `details` kwarg
- F-6: `is_user_member_of_account(user_id=)` — plan's policy takes `user` objects, which are correctly forwarded
- F-10: Permission seed migration dependency — `0002_seed_chat_permissions.py` only needs `("rbac", "0001_initial")` for Permission model

### Changes applied

| # | Finding | Section | Change |
|---|---------|---------|--------|
| F-2/3/4 | Name/avatar resolution undocumented (known gotcha from network-system.md) | 12 | Added Section 12.1 with exact model access paths for User, Business, Platform display names and avatars |
| F-7 | `CursorResultsPagination` defaults to `-created_at`, not `sequence_number` | 13 | Documented custom `MessageCursorPagination(CursorPagination)` subclass with `ordering = "-sequence_number"` |
| F-8 | `NotificationService` has no rate-limiting | 7 | Added Section 7.2 showing rate-limit check in ChatService before calling NotificationService |
| F-9 | `NotificationService` has no presence awareness | 7 | Added `PresenceManager.is_online()` check in Section 7.2 delivery logic |
| F-11 | `Category.CHAT` enum missing from modified files | 19 | Updated modified files entry for `notifications/types.py` |
| UX-1 | Entity DM notification target unclear | 7 | Added Section 7.3 using `MembershipSelector.get_users_with_permission("can_manage_chat")` |
| UX-2 | Member removal effect on org-scope chat | 9 | Added Section 9.3 — lazy access check strategy (re-validates membership on every query) |
| UX-3 | Last participant leaves group | 9 | Added to Section 9.3 — `Conversation.is_active = False` when zero active participants |
| UX-4 | Deleted message content handling | 15 | Added Section 15.2 — `original_content` preserved for moderation, `content` cleared for privacy |

### Additional improvements
- Dependency graph (Section 20): Added `MembershipSelector.get_users_with_permission` to RBAC reads
- Section 9.3: Added admin succession logic (oldest member auto-promoted when last admin leaves)
- Section 15: Expanded from edit-only to comprehensive edit + delete behavior with who-can-delete rules

---

## 22. Post-Implementation Addendum (2026-03-20)

*Added after all 5 phases were implemented. Documents deviations from the original plan.*

### Phase Reordering

The original plan's Phase 4 (Entity Chat + Audit) and Phase 5 (Message Search + Unread Counts) were **reorganized** during implementation:

| Original Plan | Actual Implementation |
|---------------|----------------------|
| Phase 1: Foundation | Phase 1: Foundation (as planned) — 199 tests |
| Phase 2: WebSocket | Phase 2: WebSocket (as planned) — 60 tests |
| Phase 3: Requests + Blocks + Notifications | Phase 3: Requests + Blocks + Notifications + REST→WS Broadcast — 44 tests |
| Phase 4: Entity Chat + Audit | **Phase 4: Image Attachments + Reactions** (new scope) — 51 tests |
| Phase 5: Message Search + Unread | **Phase 5: Audit + Entity Inbox + FTS Search** (merged from old 4+5) — 33 tests |

### New Scope: Phase 4 (Image Attachments + Reactions)

This phase was NOT in the original plan. It was planned separately via `C:\Users\AsiaData\.claude\plans\robust-swimming-harp.md` and added 2 new models + 4 new service methods + 3 new views + 3 new URL patterns.

**New models:**
- `MessageAttachment` — image file attached to a message (two-step upload: orphan → link)
- `MessageReaction` — emoji reaction on a message (6 preset types, unique per user+message+type)

**New service methods:**
- `upload_attachment(*, conversation_id, user, file)` → `MessageAttachment`
- `_link_attachments_to_message(*, message, attachment_ids, conversation_id, uploaded_by_id)` → None
- `add_reaction(*, message_id, user, reaction)` → `MessageReaction`
- `remove_reaction(*, message_id, user, reaction)` → None

**New selector methods:**
- `get_attachments_for_messages(*, message_ids)` → `dict[UUID, list]` (N+1 prevention)
- `get_media_gallery(*, conversation_id, cursor, page_size)` → `QuerySet`
- `get_reactions_for_messages(*, message_ids, user_id)` → `dict[UUID, dict]`
- `search_messages(*, query, ...)` → `QuerySet` (FTS + trigram)

**New constants/enums:**
- `ReactionType` (like, heart, laugh, wow, sad, angry)
- `AttachmentType` (image)
- `CHAT_ALLOWED_IMAGE_TYPES`, `CHAT_ALLOWED_IMAGE_EXTENSIONS`, `CHAT_MAX_IMAGE_SIZE`, `CHAT_MAX_ATTACHMENTS_PER_MESSAGE`, `CHAT_ATTACHMENT_ORPHAN_TTL_HOURS`

**New views:**
- `AttachmentUploadView` (POST, multipart parser)
- `ReactionView` (POST/DELETE)
- `EntityInboxView` (GET)
- `MessageSearchView` (GET)

**New URL patterns (4):**
- `conversations/{id}/upload/`
- `conversations/{id}/messages/{mid}/reactions/`
- `entity/{type}/{id}/inbox/`
- `messages/search/`

**New Celery task:**
- `cleanup_orphan_attachments` — daily at 3am, deletes unlinked attachments older than 24h

**New notification type:**
- `chat_reaction_received` (SOCIAL, PUSH, skip self-reaction + entity messages)

**Modified `send_message()`:** Accepts optional `attachment_ids`, allows empty content if attachments provided.

**Modified `MessageOutputSerializer`:** Added `attachments`, `reactions`, `my_reactions` fields with batch-fetch for N+1 prevention.

### Deviations from Original Plan

| Plan Said | Actual | Reason |
|-----------|--------|--------|
| 4 models | **6 models** | Added MessageAttachment + MessageReaction in Phase 4 |
| ChatService: 20 methods | **19 public + 14 internal** | _validate_scope_eligibility moved to ChatPolicy; added attachment/reaction/notification methods |
| ChatSelector: 14 methods | **18 methods** | Added attachment, reaction, media gallery, search selectors |
| `POST requests/{id}/block/` endpoint | **Not implemented** | Blocking is a separate action via `POST /blocks/`. No combined "block from request" endpoint |
| `entity/{type}/{id}/conversations/` | **`entity/{type}/{id}/inbox/`** | Renamed for clarity |
| `GET /chat/search/` | **`GET /chat/messages/search/`** | More specific URL for message-level search |
| 10 WS client→server events | **12** | Added `reaction.add`, `reaction.remove` |
| 12 WS server→client events | **10** | `participant.joined`, `participant.left`, `conversation.updated`, `request.received`, `request.accepted` are NOT sent as separate WS events (covered by REST response + broadcast) |
| 4 notification types | **5** | Added `chat_reaction_received` |
| ~460 total tests | **387 total tests** | Lower but sufficient — plan estimates were high on views/tasks/ws_serializers |
| `CHAT_GROUP_MAX_PARTICIPANTS = 50` | **100** | Increased to match Instagram group sizes |

### Final Counts (Actual)

| Component | Count |
|-----------|-------|
| Models | 6 |
| Enums | 9 |
| Scalar constants | 17 |
| Service methods (public) | 19 |
| Service methods (internal) | 14 |
| Selector methods | 18 |
| Policy methods | 6 |
| View classes | 20 |
| URL patterns | 20 |
| Input serializers | 8 |
| Output serializers | 9 |
| WS client→server events | 12 |
| WS server→client events | 10 (9 + error) |
| WS serializer functions | 9 |
| Broadcast functions | 8 + 1 helper |
| Celery tasks | 2 |
| Notification types | 5 |
| Audit actions | 9 |
| Test files | 16 |
| Test methods | 387 |
| Migrations | 4 |
| Lines: services.py | ~1713 |
| Lines: consumers.py | ~761 |
| Lines: models.py | ~457 |
| Lines: selectors.py | ~528 |
