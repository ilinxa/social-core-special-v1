# Chat System — Backend Implementation Reference

**Version:** v1
**Last Updated:** 2026-03-20
**Status:** Implemented (All 5 phases)
**Plan:** `docs/plans/backend/chat_system/chat_system_plan.md`
**Description:** `docs/descriptions/backend/chat_system/chat_system_description.md`

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           API Layer (views.py)                           │
│  ConversationListCreateView  ConversationDetailView                      │
│  MessageListCreateView       MessageEditDeleteView    MarkSeenView       │
│  ParticipantListAddView      ParticipantRemoveView    LeaveConversation  │
│  ChatRequestListView         AcceptChatRequestView    IgnoreChatRequest  │
│  BlockListCreateView         UnblockView              UnreadCountsView   │
│  MuteConversationView        UnmuteConversationView                      │
│  AttachmentUploadView        ReactionView                                │
│  EntityInboxView             MessageSearchView                           │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                      Serializers (serializers.py)                        │
│  INPUT: ConversationCreate  MessageCreate  MessageEdit  Reaction  Block  │
│  OUTPUT: ConversationList  ConversationDetail  Message  Participant      │
│          ChatRequest  ChatBlock  Attachment  MessageSearch               │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
    ┌──────────────────────────┼──────────────────────────┐
    ▼                          ▼                          ▼
┌──────────────┐   ┌───────────────────┐   ┌───────────────────────┐
│  Services    │   │    Selectors      │   │    Policies           │
│ ChatService  │   │ ChatSelector      │   │ ChatPolicy            │
│ (19 methods, │   │ (18 methods,      │   │ (scope eligibility,   │
│  all writes) │   │  all reads)       │   │  entity chat,         │
│              │   │                   │   │  group admin,         │
│              │   │                   │   │  message perms)       │
└──────┬───────┘   └────────┬──────────┘   └───────────────────────┘
       │                    │
┌──────▼────────────────────▼─────────────────────────────────────────┐
│                        Models (models.py)                            │
│  Conversation  ConversationParticipant  Message  ChatBlock           │
│  MessageAttachment  MessageReaction                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
    ┌──────────────────────────┼──────────────────────────┐
    ▼                          ▼                          ▼
┌──────────────┐   ┌───────────────────┐   ┌───────────────────────┐
│  WebSocket   │   │    RBAC           │   │    Notifications      │
│ ChatConsumer │   │ can_manage_chat   │   │ 5 social types        │
│ 12 event     │   │ (entity chat)     │   │ (presence-aware,      │
│ types,       │   │                   │   │  rate-limited)        │
│ presence,    │   │                   │   │                       │
│ broadcast    │   │                   │   │                       │
└──────────────┘   └───────────────────┘   └───────────────────────┘
```

The Chat system is a **scope-isolated, reusable messaging engine** built as a single Django app (`apps/chat/`). The same codebase, models, and API surface serve all scopes — scope is just a filter parameter. It provides both REST API (20 views, 20 URL patterns) and WebSocket (12 client→server event types, 10 server→client event types) interfaces.

### Dual-Interface Pattern

| Interface | Purpose | State Changes | Real-Time |
|-----------|---------|---------------|-----------|
| **REST** | Full CRUD, pagination, search, uploads | All writes go through `ChatService` | Broadcasts to WS via `broadcast.py` |
| **WebSocket** | Real-time messaging, typing, presence | Calls same `ChatService` methods | Native `channel_layer.group_send` |

Both REST and WS write paths converge on `ChatService` — a single write layer with atomic transactions, policy checks, and audit logging.

---

## 2. Core Concepts & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Base models | `UUIDModel + TimeStampedModel` (NOT SoftDeleteModel) | Chat uses explicit `status` field (active/edited/deleted) and `is_active` flags; soft-delete semantics don't map cleanly |
| Scope isolation | `scope_type` + `scope_id` on Conversation | Every query filters by scope. Adding a new scope type (e.g., team) requires zero chat engine changes — just a new `ScopeType` value |
| Polymorphic participants | `participant_type` (CharField) + `participant_id` (UUID) | Matches Transaction system's `initiator_type/target_type` pattern. Supports User, Business, Platform |
| Entity participation | Global scope only, requires `can_manage_chat` RBAC permission | Entities are organizational accounts — only global scope makes sense. RBAC controls which members can act as the entity |
| Message ordering | Gap-free `sequence_number` per conversation | Reliable cursor-based pagination. Avoids clock-skew issues with `created_at`. Unique constraint prevents duplicates |
| Watermark pattern | `last_seen_message_id` + `last_delivered_message_id` on `ConversationParticipant` | O(1) per watermark update vs O(N) per-message read receipts |
| Chat request state | `request_status` field on `ConversationParticipant` (not separate model) | Simpler schema, no join required. States: NONE/PENDING/ACCEPTED/IGNORED |
| Denormalized last message | 5 fields on Conversation (`last_message_id/at/preview/sender_type/sender_id`) | Avoids N+1 on conversation list — the most frequent query |
| Single WS consumer | One `ChatConsumer` per user session | Joins all conversation groups on connect. Simpler than per-conversation connections |
| Typing/Presence | Redis-only (no DB) | Ephemeral data — 5s typing TTL, 30s presence TTL. Broadcast-only, not persisted |
| Image attachments | Two-step upload (upload orphan → link on send) | Decouples file upload from message creation. Orphan cleanup via Celery task |
| Preset reactions | 6 fixed `ReactionType` enum values | Simpler than custom emoji. Unique constraint per (message, user, reaction) |

---

## 3. Data Layer

### 3.1 Conversation

Location: `apps/chat/models.py`

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | From `UUIDModel` |
| `scope_type` | CharField(20) | Choices: `global`, `business`, `platform`. Indexed |
| `scope_id` | UUIDField | Nullable. NULL = global scope |
| `conversation_type` | CharField(20) | Choices: `direct`, `group` |
| `name` | CharField(255) | Empty for DMs, required for groups |
| `description` | TextField | Group description |
| `created_by_type` | CharField(20) | ParticipantType choices |
| `created_by_id` | UUIDField | Creator reference |
| `last_message_id` | UUIDField | Nullable. Denormalized |
| `last_message_at` | DateTimeField | Nullable. Denormalized. Indexed |
| `last_message_preview` | CharField(200) | Truncated content |
| `last_message_sender_type` | CharField(20) | Nullable |
| `last_message_sender_id` | UUIDField | Nullable |
| `is_active` | BooleanField | Default True. Indexed |
| `created_at` / `updated_at` | DateTimeField | From `TimeStampedModel` |

**Indexes:**
- `(scope_type, scope_id, is_active)` — scope-filtered listing
- `(scope_type, scope_id, last_message_at)` — scope-filtered ordering
- `(conversation_type, scope_type, scope_id)` — DM lookup

### 3.2 ConversationParticipant

Location: `apps/chat/models.py`

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | From `UUIDModel` |
| `conversation` | FK(Conversation, CASCADE) | `related_name='participants'` |
| `participant_type` | CharField(20) | `user`, `business`, `platform` |
| `participant_id` | UUIDField | Polymorphic reference |
| `role` | CharField(20) | `member` (default), `admin` |
| `request_status` | CharField(20) | `none`, `pending`, `accepted`, `ignored`, `blocked` |
| `last_delivered_message_id` | UUIDField | Nullable. Watermark |
| `last_seen_message_id` | UUIDField | Nullable. Watermark |
| `last_seen_at` | DateTimeField | Nullable |
| `is_muted` | BooleanField | Default False |
| `is_active` | BooleanField | Default True |
| `left_at` | DateTimeField | Nullable |
| `removed_at` | DateTimeField | Nullable |
| `removed_by` | FK(User, SET_NULL) | Nullable |
| `added_by` | FK(User, SET_NULL) | Nullable |

**Constraints:**
- `unique_active_participant`: UNIQUE(`conversation`, `participant_type`, `participant_id`) WHERE `is_active=True`

**Indexes:**
- `(participant_type, participant_id, is_active)` — "my conversations" lookup
- `(conversation, is_active)` — participant list
- `(participant_type, participant_id, request_status)` — pending requests

### 3.3 Message

Location: `apps/chat/models.py`

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | From `UUIDModel` |
| `conversation` | FK(Conversation, CASCADE) | `related_name='messages'` |
| `sender_type` | CharField(20) | ParticipantType choices |
| `sender_id` | UUIDField | Polymorphic reference |
| `acting_user_id` | UUIDField | Nullable. Audit trail for entity messages |
| `content_type` | CharField(20) | `text`, `system`, `image` |
| `content` | TextField | Message body. Cleared on delete |
| `metadata` | JSONField | Extensible data (default `{}`) |
| `status` | CharField(20) | `active`, `edited`, `deleted` |
| `sequence_number` | PositiveIntegerField | Gap-free per conversation. Indexed |
| `edited_at` | DateTimeField | Nullable |
| `original_content` | TextField | Preserved on edit/delete for audit |

**Constraints:**
- `unique_conversation_sequence`: UNIQUE(`conversation`, `sequence_number`)

**Indexes:**
- `(conversation, created_at)` — time-based queries
- `(conversation, sequence_number)` — cursor pagination
- `(sender_type, sender_id)` — messages by sender

**PostgreSQL-only (migration `0004`):**
- GIN index on `to_tsvector('english', content)` — full-text search
- GIN index on `content gin_trgm_ops` — trigram similarity

### 3.4 ChatBlock

Location: `apps/chat/models.py`

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | From `UUIDModel` |
| `blocker` | FK(User, CASCADE) | `related_name='chat_blocks'` |
| `blocked_type` | CharField(20) | ParticipantType choices |
| `blocked_id` | UUIDField | Polymorphic reference |

**Constraints:**
- `unique_chat_block`: UNIQUE(`blocker`, `blocked_type`, `blocked_id`)

### 3.5 MessageAttachment

Location: `apps/chat/models.py`

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | From `UUIDModel` |
| `message` | FK(Message, CASCADE) | Nullable. NULL = orphan (uploaded but not linked) |
| `conversation` | FK(Conversation, CASCADE) | Required. For scope validation |
| `uploaded_by` | FK(User, CASCADE) | `related_name='chat_attachments'` |
| `file_type` | CharField(20) | Currently only `image` |
| `storage_key` | CharField(500) | `chat/{conversation_id}/attachments/{uuid}.{ext}` |
| `original_filename` | CharField(255) | User's original filename |
| `mime_type` | CharField(100) | Validated against whitelist |
| `file_size` | PositiveIntegerField | Bytes. Max 10MB |
| `width` | PositiveIntegerField | Nullable. Pillow extraction |
| `height` | PositiveIntegerField | Nullable. Pillow extraction |

**Indexes:**
- `(message)` — attachments for a message
- `(conversation)` — media gallery
- Partial index: `(message) WHERE message IS NULL` — orphan detection

### 3.6 MessageReaction

Location: `apps/chat/models.py`

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | From `UUIDModel` |
| `message` | FK(Message, CASCADE) | `related_name='reactions'` |
| `user` | FK(User, CASCADE) | `related_name='chat_reactions'` |
| `reaction` | CharField(20) | Choices: `like`, `heart`, `laugh`, `wow`, `sad`, `angry` |

**Constraints:**
- `unique_message_user_reaction`: UNIQUE(`message`, `user`, `reaction`)

### 3.7 Migrations

| Migration | Purpose |
|-----------|---------|
| `0001_initial` | 4 core models (Conversation, Participant, Message, ChatBlock) |
| `0002_seed_chat_permissions` | Seeds `can_manage_chat` into RBAC Permission table |
| `0003_messageattachment_messagereaction` | 2 new models (attachments + reactions) |
| `0004_message_fts_index` | PostgreSQL GIN indexes (FTS + trigram). No-op on SQLite |

---

## 4. Service Layer

### 4.1 ChatService

Location: `apps/chat/services.py`

All methods are `@staticmethod` with `@transaction.atomic`. Notifications and broadcasts fire via `transaction.on_commit()`.

#### Conversation Operations

| Method | Signature | Purpose |
|--------|-----------|---------|
| `create_conversation` | `(*, scope_type, scope_id, conversation_type, participant_ids, name, creator_type, creator_id, acting_user, request)` → `Conversation` | Creates conversation + participants. DM: checks uniqueness, blocks, determines request_status. Group: validates admin role, size limit |
| `update_group` | `(*, conversation_id, name, description, user, request)` → `Conversation` | Admin-only group name/description update |

#### Message Operations

| Method | Signature | Purpose |
|--------|-----------|---------|
| `send_message` | `(*, conversation_id, sender_type, sender_id, acting_user_id, content, content_type, metadata, attachment_ids, request)` → `Message` | Validates participant, request limit (3 msgs before acceptance), links attachments, updates denormalized fields, audits entity msgs, broadcasts |
| `edit_message` | `(*, message_id, new_content, user, request)` → `Message` | Author/acting-user only. 15-min window. Preserves `original_content` |
| `delete_message` | `(*, message_id, user, request)` → `None` | Author, group admin, or staff. Soft-delete: clears content, preserves `original_content` |

#### Watermark Operations

| Method | Signature | Purpose |
|--------|-----------|---------|
| `update_seen_watermark` | `(*, conversation_id, participant_type, participant_id, last_seen_message_id)` | Updates `last_seen_message_id` + `last_seen_at` |
| `update_delivered_watermark` | `(*, conversation_id, participant_type, participant_id, last_delivered_message_id)` | Updates `last_delivered_message_id` |

#### Chat Request Operations

| Method | Signature | Purpose |
|--------|-----------|---------|
| `accept_request` | `(*, conversation_id, user)` → `None` | Sets `request_status=ACCEPTED`. Notifies requester |
| `ignore_request` | `(*, conversation_id, user)` → `None` | Sets `request_status=IGNORED` |

#### Participant Management

| Method | Signature | Purpose |
|--------|-----------|---------|
| `add_participant` | `(*, conversation_id, participant_type, participant_id, added_by, request)` → `ConversationParticipant` | Group-only, admin-only. Respects max size (100). Reactivates if previously left |
| `remove_participant` | `(*, conversation_id, participant_type, participant_id, removed_by, request)` → `None` | Group-only, admin-only. Sends system message |
| `leave_conversation` | `(*, conversation_id, user)` → `None` | Group-only. Auto-promotes oldest member if last admin leaves. Deactivates conversation if empty |
| `promote_to_admin` | `(*, conversation_id, participant_id, user)` → `None` | Admin-only, idempotent |
| `demote_from_admin` | `(*, conversation_id, participant_id, user)` → `None` | Admin-only. Prevents last-admin demotion |

#### Block Operations

| Method | Signature | Purpose |
|--------|-----------|---------|
| `block_participant` | `(*, blocker, blocked_type, blocked_id, request)` → `ChatBlock` | Self-block prevented, idempotent |
| `unblock_participant` | `(*, blocker, block_id, request)` → `None` | Deletes block record |

#### Attachment & Reaction Operations

| Method | Signature | Purpose |
|--------|-----------|---------|
| `upload_attachment` | `(*, conversation_id, user, file)` → `MessageAttachment` | Validates participant, extension, MIME, size. Creates orphan (message=None) |
| `add_reaction` | `(*, message_id, user, reaction)` → `MessageReaction` | Validates type, participant, not-deleted. Broadcasts + notifies |
| `remove_reaction` | `(*, message_id, user, reaction)` → `None` | Deletes and broadcasts |

#### Internal Helpers

| Method | Purpose |
|--------|---------|
| `_check_block_status(sender_type, sender_id, recipient_type, recipient_id)` | Raises if either party has blocked the other |
| `_determine_request_status(sender_type, sender_id, recipient_type, recipient_id, scope_type)` | Returns `NONE` (trusted) or `PENDING` (stranger DM) based on network connection status |
| `_check_dm_request_limit(conversation, sender_type, sender_id)` | Enforces 3-message limit before acceptance |
| `_get_next_sequence_number(conversation_id)` | Gap-free increment using `Max()` + 1 |
| `_update_conversation_last_message(conversation, message)` | Denormalize last message fields |
| `_send_system_message(*, conversation, content)` | System-type message (joins, leaves, promotions) |
| `_link_attachments_to_message(*, message, attachment_ids, conversation_id, uploaded_by_id)` | Links orphan attachments. Validates ownership, count, orphan status |
| `_is_rate_limited(user_id, conversation_id)` | Redis counter, 1 notification per conversation per 5 min |

#### Notification Helpers (Best-Effort)

All wrapped in `_notify_safe()` — never raise, log warnings on failure.

| Method | Notification Type | Trigger |
|--------|-------------------|---------|
| `_notify_new_message` | `chat_message_received` | Message sent (offline recipients only, rate-limited) |
| `_notify_request_received` | `chat_request_received` | DM created with `request_status=PENDING` |
| `_notify_request_accepted` | `chat_request_accepted` | Recipient accepts pending request |
| `_notify_group_added` | `chat_group_added` | User added to group |
| `_notify_reaction_received` | `chat_reaction_received` | Reaction on another user's message |

### 4.2 ChatSelector

Location: `apps/chat/selectors.py`

All methods are `@staticmethod`, read-only.

| Method | Returns | Purpose |
|--------|---------|---------|
| `get_conversation_by_id(*, conversation_id)` | `Conversation` | Raises `NotFound` if not found or inactive |
| `get_conversations_for_participant(*, participant_type, participant_id, scope_type, scope_id, exclude_requests)` | `QuerySet[Conversation]` | Ordered by `last_message_at`. Excludes pending requests by default |
| `get_dm_conversation(*, scope_type, scope_id, participant_a_*, participant_b_*)` | `Conversation \| None` | DM dedup lookup using subquery |
| `get_messages(*, conversation_id, cursor, page_size, direction)` | `QuerySet[Message]` | Cursor-based (sequence_number). Bidirectional |
| `get_message_by_id(*, message_id)` | `Message` | Raises `NotFound` |
| `get_participants(*, conversation_id)` | `QuerySet[ConversationParticipant]` | Active participants only |
| `get_participant(*, conversation_id, participant_type, participant_id)` | `ConversationParticipant \| None` | Single active participant |
| `is_participant(*, conversation_id, participant_type, participant_id)` | `bool` | Existence check |
| `get_pending_requests(*, recipient_type, recipient_id)` | `QuerySet[ConversationParticipant]` | For chat request inbox |
| `count_pending_requests(*, recipient_type, recipient_id)` | `int` | Badge count |
| `is_blocked(*, blocker_id, blocked_type, blocked_id)` | `bool` | Block check |
| `get_blocks_for_user(*, user_id)` | `QuerySet[ChatBlock]` | Block list |
| `get_unread_count(*, conversation_id, participant_type, participant_id)` | `int` | Messages after `last_seen_message_id` |
| `get_unread_counts_by_scope(*, user_id)` | `dict` | `{global: N, business: {id: N}, platform: N}` |
| `get_attachments_for_messages(*, message_ids)` | `dict[UUID, list]` | Batch-fetch for N+1 prevention |
| `get_media_gallery(*, conversation_id, cursor, page_size)` | `QuerySet[MessageAttachment]` | Linked attachments, cursor by `created_at` |
| `get_reactions_for_messages(*, message_ids, user_id)` | `dict[UUID, dict]` | `{msg_id: {counts: {...}, my_reactions: [...]}}` |
| `search_messages(*, query, participant_type, participant_id, scope_type, scope_id, conversation_id)` | `QuerySet[Message]` | PostgreSQL: FTS + trigram. SQLite: icontains fallback |

---

## 5. API Layer

### 5.1 REST Endpoints

All under `/api/v1/chat/`. All require `IsAuthenticated` unless noted.

| # | Method | URL | View | Purpose |
|---|--------|-----|------|---------|
| 1 | GET | `conversations/` | `ConversationListCreateView` | List conversations (paginated) |
| 2 | POST | `conversations/` | `ConversationListCreateView` | Create conversation |
| 3 | GET | `conversations/{id}/` | `ConversationDetailView` | Conversation detail |
| 4 | PATCH | `conversations/{id}/` | `ConversationDetailView` | Update group name/description |
| 5 | GET | `conversations/{id}/participants/` | `ParticipantListAddView` | List participants |
| 6 | POST | `conversations/{id}/participants/` | `ParticipantListAddView` | Add participant to group |
| 7 | DELETE | `conversations/{id}/participants/{pid}/` | `ParticipantRemoveView` | Remove participant from group |
| 8 | POST | `conversations/{id}/leave/` | `LeaveConversationView` | Leave group |
| 9 | GET | `conversations/{id}/messages/` | `MessageListCreateView` | Messages (cursor pagination) |
| 10 | POST | `conversations/{id}/messages/` | `MessageListCreateView` | Send message |
| 11 | PATCH | `conversations/{id}/messages/{mid}/` | `MessageEditDeleteView` | Edit message |
| 12 | DELETE | `conversations/{id}/messages/{mid}/` | `MessageEditDeleteView` | Delete message |
| 13 | POST | `conversations/{id}/seen/` | `MarkSeenView` | Update seen watermark |
| 14 | POST | `conversations/{id}/mute/` | `MuteConversationView` | Mute notifications |
| 15 | POST | `conversations/{id}/unmute/` | `UnmuteConversationView` | Unmute notifications |
| 16 | GET | `requests/` | `ChatRequestListView` | List pending chat requests |
| 17 | POST | `requests/{id}/accept/` | `AcceptChatRequestView` | Accept request |
| 18 | POST | `requests/{id}/ignore/` | `IgnoreChatRequestView` | Ignore request |
| 19 | GET | `blocks/` | `BlockListCreateView` | List blocks |
| 20 | POST | `blocks/` | `BlockListCreateView` | Create block |
| 21 | DELETE | `blocks/{id}/` | `UnblockView` | Remove block |
| 22 | GET | `unread/` | `UnreadCountsView` | Unread counts by scope |
| 23 | POST | `conversations/{id}/upload/` | `AttachmentUploadView` | Upload image (multipart) |
| 24 | POST | `conversations/{cid}/messages/{mid}/reactions/` | `ReactionView` | Add reaction |
| 25 | DELETE | `conversations/{cid}/messages/{mid}/reactions/` | `ReactionView` | Remove reaction |
| 26 | GET | `entity/{type}/{id}/inbox/` | `EntityInboxView` | Entity conversation list |
| 27 | GET | `messages/search/` | `MessageSearchView` | Full-text message search |

### 5.2 WebSocket Protocol

**Connection:** `ws://host/ws/chat/` (requires JWT auth via `AuthenticatedConsumer`)

#### Client → Server Events

| Event Type | Payload | Handler |
|------------|---------|---------|
| `message.send` | `{conversation_id, content, content_type?, sender_type?, sender_id?, attachment_ids?}` | Creates message via ChatService |
| `message.edit` | `{message_id, content}` | Edits message |
| `message.delete` | `{message_id}` | Deletes message |
| `typing.start` | `{conversation_id}` | Broadcasts typing indicator |
| `typing.stop` | `{conversation_id}` | Broadcasts typing stop |
| `seen` | `{conversation_id, last_seen_message_id}` | Updates + broadcasts watermark |
| `delivered` | `{conversation_id, last_delivered_message_id}` | Updates + broadcasts watermark |
| `presence.subscribe` | `{user_ids: [...]}` | Subscribes to online status (max 50) |
| `conversation.join` | `{conversation_id}` | Joins channel group for real-time |
| `conversation.leave` | `{conversation_id}` | Leaves channel group |
| `reaction.add` | `{message_id, reaction}` | Adds reaction + broadcasts |
| `reaction.remove` | `{message_id, reaction}` | Removes reaction + broadcasts |

#### Server → Client Events

| Event Type | Payload | Trigger |
|------------|---------|---------|
| `message.new` | Full message object (same shape as REST) | Message sent |
| `message.edited` | `{conversation_id, message_id, content, edited_at}` | Message edited |
| `message.deleted` | `{conversation_id, message_id}` | Message deleted |
| `typing` | `{conversation_id, user_id, is_typing}` | Typing indicator |
| `seen.update` | `{conversation_id, participant_id, last_seen_message_id}` | Read receipt |
| `delivered.update` | `{conversation_id, participant_id, last_delivered_message_id}` | Delivery receipt |
| `presence` | `{user_id, is_online}` | Presence change |
| `conversation.new` | Full conversation object | Added to conversation |
| `reaction.update` | `{conversation_id, message_id, user_id, reaction, action}` | Reaction add/remove |
| `error` | `{code, message}` | Validation/permission errors |

#### Channel Groups

| Group Name | Members | Events |
|------------|---------|--------|
| `user_{user_id}` | Single user's connections | `conversation.new` |
| `conversation_{conversation_id}` | All connected participants | `message.*`, `typing`, `seen.*`, `delivered.*`, `reaction.*` |
| `presence_{user_id}` | Users subscribed to this user's presence | `presence` |

### 5.3 Key Serializer Shapes

**ConversationListOutputSerializer** (GET list):
```json
{
  "id": "uuid",
  "scope_type": "global",
  "scope_id": null,
  "conversation_type": "direct",
  "name": "",
  "last_message": {
    "id": "uuid",
    "sender_type": "user",
    "sender_id": "uuid",
    "sender_name": "Alice",
    "content_preview": "Hello there...",
    "created_at": "2026-03-20T..."
  },
  "unread_count": 3,
  "is_muted": false,
  "created_at": "2026-03-20T..."
}
```

**MessageOutputSerializer** (GET messages):
```json
{
  "id": "uuid",
  "conversation_id": "uuid",
  "sender_type": "user",
  "sender_id": "uuid",
  "sender_name": "Alice",
  "sender_avatar_url": "/media/avatars/...",
  "content_type": "text",
  "content": "Hello there",
  "status": "active",
  "sequence_number": 42,
  "edited_at": null,
  "created_at": "2026-03-20T...",
  "attachments": [
    {
      "id": "uuid",
      "file_type": "image",
      "original_filename": "photo.jpg",
      "mime_type": "image/jpeg",
      "file_size": 512000,
      "width": 1920,
      "height": 1080,
      "url": "/media/chat/{conv_id}/attachments/{uuid}.jpg"
    }
  ],
  "reactions": {"like": 3, "heart": 1},
  "my_reactions": ["like"]
}
```

**Participant display resolution** (`_resolve_participant_display` in serializers.py):
- **User**: `User.profile.display_name`, `User.profile.avatar.url`
- **Business**: `BusinessProfile.display_name`, `BusinessProfile.logo.url`
- **Platform**: `PlatformProfile.name`, `PlatformProfile.logo.url`

---

## 6. Constants & Enums

Location: `apps/chat/constants.py`

### Enums

| Enum | Values | Purpose |
|------|--------|---------|
| `ScopeType` | `global`, `business`, `platform` | Conversation isolation |
| `ConversationType` | `direct`, `group` | 1:1 vs N-participant |
| `ParticipantType` | `user`, `business`, `platform` | Polymorphic participant identity |
| `ParticipantRole` | `member`, `admin` | Group role (admins manage group) |
| `RequestStatus` | `none`, `pending`, `accepted`, `ignored`, `blocked` | DM request lifecycle |
| `MessageContentType` | `text`, `system`, `image` | Message type discriminator |
| `MessageStatus` | `active`, `edited`, `deleted` | Message lifecycle |
| `ReactionType` | `like`, `heart`, `laugh`, `wow`, `sad`, `angry` | 6 preset emoji reactions |
| `AttachmentType` | `image` | Currently images only |

### Limits & Settings

| Constant | Value | Purpose |
|----------|-------|---------|
| `CHAT_MESSAGE_MAX_LENGTH` | 5000 | Max message content chars |
| `CHAT_MESSAGE_EDIT_WINDOW_MINUTES` | 15 | Edit time limit |
| `CHAT_MESSAGE_PREVIEW_LENGTH` | 200 | Denormalized preview truncation |
| `CHAT_REQUEST_MAX_MESSAGES` | 3 | Messages before acceptance required |
| `CHAT_REQUEST_EXPIRY_DAYS` | 30 | Auto-expire pending requests |
| `CHAT_GROUP_MAX_PARTICIPANTS` | 100 | Group size limit |
| `CHAT_RATE_LIMIT_MESSAGES_PER_MINUTE` | 30 | Per-conversation rate limit |
| `CHAT_RATE_LIMIT_CONVERSATIONS_PER_HOUR` | 5 | Creation rate limit |
| `CHAT_RATE_LIMIT_REQUESTS_PER_HOUR` | 10 | DM request rate limit |
| `CHAT_ALLOWED_IMAGE_TYPES` | jpeg, png, gif, webp | Accepted MIME types |
| `CHAT_MAX_IMAGE_SIZE` | 10 MB | Max upload size |
| `CHAT_MAX_ATTACHMENTS_PER_MESSAGE` | 10 | Max files per message |
| `CHAT_ATTACHMENT_ORPHAN_TTL_HOURS` | 24 | Orphan cleanup threshold |
| `WS_PRESENCE_TTL_SECONDS` | 30 | Redis presence key TTL |
| `WS_HEARTBEAT_INTERVAL_SECONDS` | 20 | Consumer heartbeat interval |
| `WS_MAX_PRESENCE_SUBSCRIPTIONS` | 50 | Max presence subscriptions per user |

---

## 7. Key Flows

### 7.1 DM Creation (Stranger → Chat Request)

```
1. User A calls POST /chat/conversations/ with {participant_ids: [User B], conversation_type: "direct"}
2. ChatPolicy.validate_scope_eligibility() — passes (both are users in global scope)
3. ChatSelector.get_dm_conversation() — checks for existing DM (dedup)
4. ChatService._check_block_status() — verifies neither has blocked the other
5. ChatService._determine_request_status() — checks Network Connection:
   - Connected → request_status=NONE (trusted)
   - NOT connected → request_status=PENDING (stranger)
6. Creates Conversation + 2 ConversationParticipants
7. on_commit: _notify_safe("request_received", ...) for PENDING DMs
8. on_commit: broadcast_new_conversation() to both users' WS groups
```

### 7.2 Message Send (with Attachment)

```
1. Client uploads via POST /chat/conversations/{id}/upload/ (multipart)
   → Returns orphan MessageAttachment with id
2. Client sends POST /chat/conversations/{id}/messages/ with {content: "Check this out", attachment_ids: [uuid]}
3. ChatService.send_message():
   a. Validates participant status
   b. Checks DM request limit (3 messages before acceptance)
   c. Creates Message with next sequence_number
   d. Calls _link_attachments_to_message() — validates ownership, orphan status, count
   e. Updates Conversation denormalized fields (last_message_*)
   f. Audits entity messages (non-user senders only)
   g. on_commit: broadcast_message_new() to conversation WS group
   h. on_commit: _notify_safe("new_message", ...) for offline participants
```

### 7.3 Entity Chat (Business Sends Message)

```
1. Business member (with can_manage_chat) sends message as business:
   POST /chat/conversations/{id}/messages/ with {sender_type: "business", sender_id: biz_id}
2. ChatPolicy.can_send_message():
   a. Checks business is active participant in conversation
   b. Calls can_manage_entity_chat() → checks RBAC membership + can_manage_chat permission
3. ChatService.send_message() with acting_user_id = request.user.id
4. AuditService.log(action=CHAT_MESSAGE_SENT) — entity messages always audited
5. Message has sender_type="business", sender_id=biz_id, acting_user_id=member_id
```

### 7.4 Chat Request Lifecycle

```
DM Created → Participant B has request_status=PENDING
  ├── B sees request in GET /chat/requests/ (with preview_messages and requester info)
  ├── A can send up to 3 messages (then blocked with "Request pending" error)
  │
  ├── B accepts: POST /chat/requests/{conv_id}/accept/
  │   → request_status=ACCEPTED, A can send unlimited messages
  │   → Notifies A: "B accepted your chat request"
  │
  ├── B ignores: POST /chat/requests/{conv_id}/ignore/
  │   → request_status=IGNORED, conversation hidden from B's inbox
  │
  └── Auto-expire: Celery task after 30 days
      → request_status reverted to NONE
```

### 7.5 Group Admin Succession

```
1. Admin A leaves group (POST /chat/conversations/{id}/leave/)
2. ChatService.leave_conversation():
   a. Deactivates A's participant record (is_active=False, left_at=now)
   b. If A was admin and other active participants exist:
      - Check if any other admins remain
      - If NO other admins: promote oldest active member → admin
   c. If NO active participants remain: deactivate conversation (is_active=False)
   d. Sends system message: "Alice left the group"
```

### 7.6 Full-Text Message Search

```
1. GET /chat/messages/search/?q=payment&scope_type=global&conversation_id={optional}
2. ChatSelector.search_messages():
   a. Gets conversation IDs where user participates
   b. Filters messages: conversation_id IN (...), scope_type match, status IN (active, edited)
   c. PostgreSQL: SearchVector + SearchQuery(websearch) + TrigramSimilarity → combined rank
   d. SQLite: simple content__icontains fallback
   e. Returns QuerySet ordered by relevance (PG) or created_at (SQLite)
3. View paginates and serializes via MessageSearchOutputSerializer
```

---

## 8. Permissions & Authorization

### 8.1 ChatPolicy Methods

| Method | Purpose | Who Passes |
|--------|---------|------------|
| `validate_scope_eligibility` | Can this participant act in this scope? | Users: global=any, org=member. Entities: global only + `can_manage_chat` |
| `can_manage_entity_chat` | Can user act as this business/platform? | Staff/superuser, or member with `can_manage_chat` permission |
| `can_manage_group` | Can user manage this group? | Active admin participant |
| `can_send_message` | Can user send to this conversation? | Active participant (+ entity permission for entity senders) |
| `can_delete_message` | Can user delete this message? | Author, entity acting_user, group admin, staff/superuser |
| `get_viewer_permissions` | Tier 1.5 permission dict | Returns `{can_send_message, can_view_messages, can_leave, can_manage_group, can_add_participant, can_remove_participant, can_edit_group}` |

### 8.2 RBAC Permission

| Code | Scope | Description |
|------|-------|-------------|
| `can_manage_chat` | `business`, `platform_only` | Send/receive messages as entity, access entity inbox |

Seeded in migration `0002_seed_chat_permissions`. Assigned to Owner role by `RBACService.initialize_business_account()` (all business-scope permissions).

### 8.3 Audit Actions

9 actions logged via `AuditService.log()`:

| Action | Trigger | Policy |
|--------|---------|--------|
| `CHAT_CONVERSATION_CREATED` | `create_conversation()` | All conversations |
| `CHAT_MESSAGE_SENT` | `send_message()` | Entity messages only (user-to-user too high-volume) |
| `CHAT_MESSAGE_EDITED` | `edit_message()` | All edits |
| `CHAT_MESSAGE_DELETED` | `delete_message()` | All deletes |
| `CHAT_PARTICIPANT_ADDED` | `add_participant()` | Group adds |
| `CHAT_PARTICIPANT_REMOVED` | `remove_participant()` | Group removes |
| `CHAT_REQUEST_ACCEPTED` | `accept_request()` | All accepts |
| `CHAT_BLOCK_CREATED` | `block_participant()` | All blocks |
| `CHAT_BLOCK_REMOVED` | `unblock_participant()` | All unblocks |

---

## 9. Real-Time Infrastructure

### 9.1 Broadcast Bridge (REST → WS)

Location: `apps/chat/broadcast.py`

All functions use `async_to_sync(channel_layer.group_send)` and are best-effort (fail silently).

| Function | Target Group | Trigger |
|----------|-------------|---------|
| `broadcast_message_new(message)` | `conversation_{id}` | Message sent via REST |
| `broadcast_message_edited(message)` | `conversation_{id}` | Message edited via REST |
| `broadcast_message_deleted(message)` | `conversation_{id}` | Message deleted via REST |
| `broadcast_message_deleted_by_ids(conversation_id, message_id)` | `conversation_{id}` | Delete by IDs (when message object unavailable) |
| `broadcast_new_conversation(conversation, participant_ids)` | `user_{id}` (each) | Conversation created |
| `broadcast_seen_update(...)` | `conversation_{id}` | Seen watermark via REST |
| `broadcast_delivered_update(...)` | `conversation_{id}` | Delivered watermark via REST |
| `broadcast_reaction_update(...)` | `conversation_{id}` | Reaction add/remove via REST |

### 9.2 Presence Manager

Location: `apps/chat/presence.py`

| Method | Purpose |
|--------|---------|
| `set_online(user_id, ttl=30)` | Redis SETEX `chat:presence:{user_id}` |
| `set_offline(user_id)` | Redis DELETE key |
| `is_online(user_id)` | Redis EXISTS check |
| `get_online_users(user_ids)` | Pipeline batch check |

**Fail-open**: Redis unavailable → everyone shows offline. Heartbeat (20s) < TTL (30s) ensures online status persists across heartbeats.

### 9.3 WS Serializers

Location: `apps/chat/ws_serializers.py`

Pure functions returning dicts (no DRF overhead). All UUID fields are stringified. All shapes match REST serializer output for frontend consistency.

---

## 10. Celery Tasks

Location: `apps/chat/tasks.py`

| Task | Schedule | Purpose |
|------|----------|---------|
| `expire_stale_chat_requests` | Celery beat (daily) | Resets `PENDING` requests older than 30 days to `NONE` |
| `cleanup_orphan_attachments` | Celery beat (daily at 3am) | Deletes files + DB records for unlinked attachments older than 24h |

Both tasks have `soft_time_limit=120`, `time_limit=180`.

---

## 11. Notification Types

5 chat notifications registered in `apps/notifications/types.py`:

| Type | Category | Channels | Trigger | Special Logic |
|------|----------|----------|---------|---------------|
| `chat_message_received` | SOCIAL | PUSH | New message | Offline-only, rate-limited (1/conv/5min) |
| `chat_request_received` | SOCIAL | PUSH, EMAIL | DM request created | Sent to pending recipient |
| `chat_request_accepted` | SOCIAL | PUSH | Request accepted | Sent to original sender |
| `chat_group_added` | SOCIAL | PUSH | Added to group | Sent to added user |
| `chat_reaction_received` | SOCIAL | PUSH | Reaction on message | Skip self-reaction, skip entity messages |

All are user-configurable and delivered via `NotificationService.send()`.

---

## 12. Testing

**387 tests total**, all passing on SQLite (unit tests).

| Module | File | Count | Scope |
|--------|------|-------|-------|
| Phase 1: Models | `test_models.py` | 24 | Conversation, Participant, Message, Block model logic |
| Phase 1: Selectors | `test_selectors.py` | 37 | All ChatSelector methods |
| Phase 1: Services | `test_services.py` | 80 | All ChatService write methods |
| Phase 1: Policies | `test_policies.py` | 33 | Scope eligibility, entity chat, group admin, message perms |
| Phase 1: Views | `test_views.py` | 25 | REST endpoints, HTTP methods, pagination |
| Phase 2: Consumers | `test_consumers.py` | 38 | All WS event types, lifecycle |
| Phase 2: WS Serializers | `test_ws_serializers.py` | 8 | All serialize_* functions |
| Phase 2: Presence | `test_presence.py` | 14 | Redis presence manager |
| Phase 3: Broadcast | `test_broadcast_wiring.py` | 13 | REST→WS bridge functions |
| Phase 3: Notifications | `test_notifications.py` | 26 | Notification type registration, rate limiting |
| Phase 3: Tasks | `test_tasks.py` | 5 | Celery task logic (request expiry + orphan cleanup) |
| Phase 4: Attachments | `test_attachments.py` | 25 | Upload, link, orphan cleanup |
| Phase 4: Reactions | `test_reactions.py` | 26 | Add, remove, counts, broadcasts |
| Phase 5: Audit | `test_audit.py` | 11 | All 9 audit actions |
| Phase 5: Entity Inbox | `test_entity_inbox.py` | 7 | Entity inbox endpoint |
| Phase 5: Search | `test_search.py` | 15 | Selector + view search tests |

---

## 13. Configuration & Gotchas

### Critical Gotchas

| # | Gotcha | Solution |
|---|--------|----------|
| 1 | `connection.vendor` for FTS, NOT `try/except ImportError` | `django.contrib.postgres.search` imports fine on SQLite — it fails at query time. Use `if connection.vendor == "postgresql":` explicitly |
| 2 | `PermissionSelector.get_permissions_for_membership()` returns `List[Tuple[str, str]]` | Check with `any(code == "can_manage_chat" for code, scope in permissions)`, NOT `"perm" in permissions` |
| 3 | `transaction.on_commit()` doesn't fire in tests | Use `immediate_on_commit` fixture (monkeypatches to call func immediately) |
| 4 | `_notify_safe` inside `immediate_on_commit` + `@transaction.atomic` | If notification handler raises, the atomic block rolls back. Mock the handler, not `_notify_safe` |
| 5 | Lazy imports in services/views | Mock at source module (`apps.chat.services.ChatService`), NOT consumer module |
| 6 | DummyCache in test settings | `cache.set()` is a no-op. Rate limiting tests need `LocMemCache` fixture |
| 7 | `AttachmentUploadView` needs explicit `parser_classes` | Global `DEFAULT_PARSER_CLASSES = [JSONParser]`. Upload view must set `parser_classes = [MultiPartParser, FormParser]` |
| 8 | `default_storage.url()` in tests | Returns `/media/key` with FileSystemStorage. Tests should assert URL contains storage_key |
| 9 | Orphan attachment validation | `_link_attachments_to_message()` must check: same conversation, same uploader, message=None, count limit |
| 10 | Message edit window | 15 minutes from creation. `message.created_at + timedelta(minutes=15) < now()` → raises |
| 11 | Group admin succession | `leave_conversation()` auto-promotes oldest active member. Tests must account for this |
| 12 | WS consumer `_db_send_message` vs REST `send_message` | Same `ChatService.send_message()` method — WS wraps in `@database_sync_to_async` |

### Settings

| Setting | Value | Location |
|---------|-------|----------|
| `CHANNEL_LAYERS` | Redis backend (`channels_redis`) | `settings/base.py` |
| `WS_PRESENCE_TTL_SECONDS` | 30 | `chat/constants.py` |
| `CELERY_BEAT_SCHEDULE` | `expire_stale_chat_requests`, `cleanup_orphan_attachments` | `settings/base.py` |
| `CHAT_*` constants | See Section 6 | `chat/constants.py` |

---

## 14. File Summary

### New Files

| File | Lines | Purpose |
|------|-------|---------|
| `apps/chat/__init__.py` | — | App init |
| `apps/chat/apps.py` | — | AppConfig |
| `apps/chat/models.py` | ~457 | 6 models |
| `apps/chat/constants.py` | ~104 | 9 enums + 17 scalar constants |
| `apps/chat/services.py` | ~1713 | 19 public + 14 internal methods |
| `apps/chat/selectors.py` | ~528 | 18 selector methods |
| `apps/chat/serializers.py` | ~430 | 8 input + 9 output serializers |
| `apps/chat/views.py` | ~720 | 20 view classes |
| `apps/chat/urls.py` | ~113 | 20 URL patterns |
| `apps/chat/policies.py` | ~243 | 6 policy methods |
| `apps/chat/consumers.py` | ~761 | ChatConsumer (12 client→server event types) |
| `apps/chat/ws_serializers.py` | ~120 | 9 serializer functions |
| `apps/chat/broadcast.py` | ~130 | 8 broadcast functions + 1 helper |
| `apps/chat/presence.py` | ~80 | PresenceManager |
| `apps/chat/tasks.py` | ~60 | 2 Celery tasks |
| `apps/chat/migrations/` | 4 files | DB schema + seeds |
| `apps/chat/tests/` | 16 files | 387 tests |

### Modified Files

| File | Change |
|------|--------|
| `apps/notifications/types.py` | Added 5 chat notification types |
| `backend_core/settings/base.py` | Celery beat schedule, task routes |
| `backend_core/urls.py` | Included `apps.chat.urls` at `/api/v1/chat/` |
| `apps/core/observability/audit/models.py` | 9 new `AuditLog.Action` enum values |

---

## 15. Frontend Integration Guide

### REST API Consumption

**Key endpoints for frontend:**

1. **Conversation list**: `GET /api/v1/chat/conversations/?scope_type=global` — paginated, use `last_message` for preview
2. **Message thread**: `GET /api/v1/chat/conversations/{id}/messages/?page_size=50&direction=older&cursor={seq}` — cursor-based
3. **Send message**: `POST /api/v1/chat/conversations/{id}/messages/` — `{content, attachment_ids?}`
4. **Upload image**: `POST /api/v1/chat/conversations/{id}/upload/` — multipart/form-data, returns `{id, url, ...}`
5. **Reactions**: `POST/DELETE /api/v1/chat/conversations/{cid}/messages/{mid}/reactions/` — `{reaction: "like"}`
6. **Chat requests**: `GET /requests/`, `POST /requests/{id}/accept/`, `POST /requests/{id}/ignore/`
7. **Unread counts**: `GET /api/v1/chat/unread/` — returns `{global: N, business: {id: N}, platform: N}`
8. **Search**: `GET /api/v1/chat/messages/search/?q=term&scope_type=global`

### WebSocket Integration

```typescript
// Connect
const ws = new WebSocket(`ws://host/ws/chat/?token=${jwt}`);

// Send message
ws.send(JSON.stringify({
  type: "message.send",
  conversation_id: "uuid",
  content: "Hello!",
  attachment_ids: ["uuid"]  // optional, upload via REST first
}));

// Add reaction
ws.send(JSON.stringify({
  type: "reaction.add",
  message_id: "uuid",
  reaction: "like"
}));

// Subscribe to presence
ws.send(JSON.stringify({
  type: "presence.subscribe",
  user_ids: ["uuid1", "uuid2"]
}));

// Listen for events
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.type) {
    case "message.new":       // New message in a conversation
    case "message.edited":    // Message content updated
    case "message.deleted":   // Message removed
    case "typing":            // User typing indicator
    case "seen.update":       // Read receipt
    case "delivered.update":  // Delivery receipt
    case "presence":          // Online/offline status
    case "conversation.new":  // Added to new conversation
    case "reaction.update":   // Reaction added/removed
    case "error":             // Error from server
  }
};
```

### TypeScript Types (Suggested)

```typescript
// Scope types
type ScopeType = "global" | "business" | "platform";
type ConversationType = "direct" | "group";
type ParticipantType = "user" | "business" | "platform";
type MessageStatus = "active" | "edited" | "deleted";
type RequestStatus = "none" | "pending" | "accepted" | "ignored" | "blocked";
type ReactionType = "like" | "heart" | "laugh" | "wow" | "sad" | "angry";

// Conversation
interface Conversation {
  id: string;
  scope_type: ScopeType;
  scope_id: string | null;
  conversation_type: ConversationType;
  name: string;
  last_message: LastMessage | null;
  unread_count: number;
  is_muted: boolean;
  created_at: string;
}

interface ConversationDetail extends Conversation {
  description: string;
  participants: Participant[];
  is_active: boolean;
}

// Message
interface Message {
  id: string;
  conversation_id: string;
  sender_type: ParticipantType;
  sender_id: string;
  sender_name: string;
  sender_avatar_url: string | null;
  content_type: string;
  content: string;
  status: MessageStatus;
  sequence_number: number;
  edited_at: string | null;
  created_at: string;
  attachments: Attachment[];
  reactions: Record<ReactionType, number>;
  my_reactions: ReactionType[];
}

// Attachment
interface Attachment {
  id: string;
  file_type: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  width: number | null;
  height: number | null;
  url: string;
}

// Participant
interface Participant {
  id: string;
  participant_type: ParticipantType;
  participant_id: string;
  display_name: string;
  avatar_url: string | null;
  role: "member" | "admin";
  request_status: RequestStatus;
  is_muted: boolean;
  is_active: boolean;
  created_at: string;
}

// Chat Request (pending DM)
interface ChatRequest {
  conversation_id: string;
  requester: {
    participant_type: ParticipantType;
    participant_id: string;
    display_name: string;
    avatar_url: string | null;
  };
  preview_messages: { content: string; created_at: string }[];
  message_count: number;
  created_at: string;
}

// Unread counts
interface UnreadCounts {
  global: number;
  business: Record<string, number>;
  platform: number;
}

// Search result
interface MessageSearchResult {
  id: string;
  conversation_id: string;
  sender_type: ParticipantType;
  sender_id: string;
  sender_name: string;
  content: string;
  status: MessageStatus;
  sequence_number: number;
  created_at: string;
  conversation_name: string;
}
```

### Frontend State Management (Suggested Architecture)

```
┌─────────────────────────────────────────────────────────┐
│                  Zustand Stores                          │
│                                                         │
│  chatStore: {                                           │
│    conversations: Map<string, Conversation>              │
│    activeConversationId: string | null                   │
│    messages: Map<string, Message[]>                      │
│    unreadCounts: UnreadCounts                            │
│    pendingRequests: ChatRequest[]                        │
│  }                                                      │
│                                                         │
│  presenceStore: {                                        │
│    onlineUsers: Set<string>                              │
│  }                                                      │
└────────────────────────┬────────────────────────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    ▼                    ▼                    ▼
┌──────────┐   ┌─────────────────┐   ┌──────────────┐
│ TanStack │   │  WebSocket      │   │  REST API    │
│ Query    │   │  Connection     │   │  (uploads,   │
│ (list,   │   │  (real-time     │   │   search,    │
│  detail, │   │   events →      │   │   reactions)  │
│  search) │   │   store updates)│   │              │
└──────────┘   └─────────────────┘   └──────────────┘
```

**Key patterns:**
- **Conversation list**: TanStack Query for initial load + WS events update Zustand store
- **Message thread**: TanStack Query with cursor pagination (infinite scroll) + WS appends
- **Typing indicators**: WS only, short-lived state (clear after 5s timeout)
- **Presence**: WS `presence.subscribe` + presenceStore
- **Unread counts**: REST initial load + WS message events increment locally
- **Image upload**: REST multipart → get attachment ID → include in message send

### Scope Context for Frontend

| Frontend Context | `scope_type` | `scope_id` | Who Chats |
|-----------------|-------------|-----------|-----------|
| Personal / Global | `global` | `null` | Users + Entities (Business, Platform) |
| Business Console | `business` | `business.id` | Business members (as themselves) |
| Platform Console | `platform` | `platform.id` | Platform members (as themselves) |

---

## 16. Known Limitations

| Limitation | Detail | Mitigation |
|------------|--------|------------|
| No audio/video/file attachments | Only image uploads (jpg, png, gif, webp) | Extend `AttachmentType` + MIME whitelist |
| No link previews | No OG meta extraction | Deferred to future phase |
| No message threading/replies | Flat message list only | Add `reply_to_id` FK on Message |
| No read receipts per user | Only aggregate watermark | Per-message `MessageReadReceipt` model if needed |
| No message pinning | No pinned messages feature | Add `is_pinned` on Message |
| FTS only on PostgreSQL | SQLite uses simple `icontains` | Acceptable for dev/test; production uses PG |
| No archival | Messages persist indefinitely | Add archival policy in future |
| Group size limit | 100 participants hard-coded | Configurable via constants |
| Single admin model | No role hierarchy within groups | Extend `ParticipantRole` if needed |

---

## 17. vNext TODOs

| Priority | Feature | Notes |
|----------|---------|-------|
| P1 | Message threading/replies | Add `reply_to_id` FK, adjust WS + REST serializers |
| P1 | Link previews | Extract OG meta server-side, store in `metadata` JSONField |
| P2 | Audio/video attachments | Extend `AttachmentType`, add transcoding task |
| P2 | Message reactions analytics | Track reaction trends per conversation |
| P2 | Admin moderation dashboard | Cross-conversation search, bulk actions |
| P3 | Voice/video calls | WebRTC signaling via WS, separate service |
| P3 | Message scheduling | Deferred send via Celery |
| P3 | Bot/webhook participants | New `ParticipantType.BOT` |

---

## 18. Changelog

| Version | Date | Changes |
|---------|------|---------|
| v1 | 2026-03-20 | Initial implementation doc. All 5 phases complete: REST (20 views, 20 URL patterns), WebSocket (12 C→S + 10 S→C events), attachments, reactions, audit, entity inbox, FTS search. 387 tests across 16 files |
