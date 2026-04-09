# Chat System — Frontend High-Level Description

**Version:** v2
**Date:** 2026-03-25
**Status:** Pre-Planning
**Backend Reference:** `docs/implementations/backend/chat-system.md`
**Frontend Features List:** `docs/descriptions/frontend/chat-system-frontend-features.md`

---

## 1. Vision

The Chat System provides real-time messaging across the entire platform. It appears in three distinct contexts — personal, business console, and platform console — each with different capabilities, scopes, and permissions. The same reusable chat engine (components, hooks, state, WebSocket) powers all three contexts; only the **scope filter** and **available features** change.

**UI Reference:** Instagram Direct (web and mobile) — but extended with organizational scoping, entity participation, chat requests, and dual-tab console layouts.

---

## 2. The Three Chat Contexts

The platform has three authenticated route groups. Chat integrates into each one differently:

```
Route Group            Chat Route                Scope          Behavior
─────────────────────  ────────────────────────  ─────────────  ─────────────────────
(user) personal        /chat/                    global         Personal DMs & groups
bconsole/[slug]        /bconsole/{slug}/chat/    dual           Entity tab + Internal tab
pconsole               /pconsole/chat/           dual           Entity tab + Internal tab
```

### 2.1 Personal Chat — Global Scope

**Route:** `/(app)/(user)/chat/`
**Scope:** `scope_type=global`, `scope_id=null`
**Who sees it:** Every authenticated user

This is the user's personal messaging inbox — equivalent to Instagram DMs. It contains:

- **Direct messages** between users (user-to-user)
- **Group conversations** created by users
- **Entity DMs** where a business or platform has messaged the user (the user sees these here; the entity manages them from their console)

The personal chat is **always global scope**. It has nothing to do with any business or platform the user belongs to. Even if a user is a member of 5 businesses, their personal chat is one unified inbox.

**Key behaviors:**
- Chat requests flow applies here (strangers must request, connections auto-accept)
- User can block participants from this context
- User sees all their global conversations regardless of who initiated them
- Unread badge on the sidebar "Chat" navigation item

### 2.2 Business Console Chat — Dual Tab

**Route:** `/(app)/bconsole/[slug]/chat/`
**Who sees it:** Active members of that business (BusinessGuard)
**Layout:** Two tabs within a single chat page

#### Tab 1: Entity Inbox (Business as a Person)

**Scope:** `scope_type=global` (entity conversations live in global scope)
**Backend endpoint:** `GET /api/v1/chat/entity/<account_type>/<account_id>/inbox/` (e.g., `/entity/business/{business_id}/inbox/`)
**Permission:** Tier 1.5 — only visible to members with `can_manage_chat` RBAC permission

This tab shows conversations where **the business itself is a participant** in the global chat world. The business acts as a "person" — it can:
- Send DMs to individual users
- Send DMs to other businesses
- Send DMs to the platform entity
- Participate in group conversations

The human operator behind the business sees these conversations and sends messages "as the business." Every message is attributed to the business entity (`sender_type=business`, `sender_id={business_id}`) with the operator's identity recorded in `acting_user_id` for audit.

**Key behaviors:**
- Messages show the business name and logo, not the operator's personal identity
- Multiple team members with `can_manage_chat` can access the same inbox
- No chat request flow for entity-to-entity or entity-to-user DMs (entities are trusted)
- The user recipient of an entity DM sees it in their personal chat inbox (Section 2.1)
- Conversations here are **not scoped to the business** — they are global conversations that happen to involve the business entity

**UX Pattern:** Like a shared business inbox (think: Facebook Page inbox, or a company support chat dashboard). The operator is a steward of the business's conversations, not a personal participant.

#### Tab 2: Internal Chat (Business Members)

**Scope:** `scope_type=business`, `scope_id={business_id}`
**Permission:** All active members can see and participate. Only members with `can_manage_chat` RBAC permission can create groups. Group management (add/remove participants, delete messages) is controlled by the **conversation-level admin role** (see Section 4.4).

This tab is the **internal communication channel** for all members of a specific business. Think of it as a team Slack/Discord — but scoped entirely to this one business.

**Key behaviors:**
- Only active members of this business can see or participate
- No chat requests — all members are trusted (scope=business bypasses request flow)
- DMs between two members within the business context
- Group chats within the business (project teams, departments, etc.)
- Members with `can_manage_chat` RBAC permission can:
  - Create group conversations
- Conversation group admins (conversation-level role) can:
  - Add/remove participants in their group
  - Delete messages in their group (moderation)
  - Promote/demote other members to admin within the group
- Regular members can:
  - Send DMs to other members
  - Participate in groups they're added to
  - Create DMs (but not groups, unless they have `can_manage_chat` permission)
- Conversations are **completely invisible** outside this business — different business = different scope
- A user who is a member of Business A and Business B has separate internal chats for each

**UX Pattern:** Like a team messaging tool embedded within the business dashboard.

### 2.3 Platform Console Chat — Dual Tab

**Route:** `/(app)/pconsole/chat/`
**Who sees it:** Active platform members (PlatformGuard)
**Layout:** Same dual-tab pattern as business

#### Tab 1: Entity Inbox (Platform as a Person)

Identical pattern to Business Entity Tab, but for the platform account:
- `scope_type=global`, entity is `participant_type=platform`
- Backend: `GET /api/v1/chat/entity/platform/{platform_id}/inbox/`
- Permission: `can_manage_chat` on platform membership
- Platform sends messages as itself globally

#### Tab 2: Internal Chat (Platform Members)

- `scope_type=platform`, `scope_id={platform_id}`
- All platform members can see and participate
- Same management rules as business internal chat
- Used for platform team coordination

---

## 3. Chat Requests — Detailed Concept

Chat requests are a **privacy protection mechanism** for global-scope user-to-user DMs. They prevent strangers from flooding a user's inbox.

### 3.1 When Requests Apply

| Sender | Recipient | Scope | Connected? | Result |
|--------|-----------|-------|-----------|--------|
| User | User | Global | Yes (network connection) | **Auto-accept** — no request |
| User | User | Global | No (strangers) | **Chat request** — pending until accepted |
| User | User | Business | N/A | **No request** — org members are trusted |
| User | User | Platform | N/A | **No request** — org members are trusted |
| Entity | User | Global | N/A | **No request** — entities are trusted |
| Entity | Entity | Global | N/A | **No request** — entities are trusted |

### 3.2 The Request Flow

```
1. User A (stranger) sends DM to User B in global scope
   → Conversation created
   → User A's participant: request_status = NONE (sender)
   → User B's participant: request_status = PENDING (recipient)

2. User A can send up to 3 messages (per sender) before acceptance
   → 4th message attempt: "Cannot send more than 3 messages before the request is accepted"
   → Note: limit is per-sender, not per-conversation total

3. User B sees the request in their Chat Requests section
   → Shows: requester info + up to 3 preview messages + accept/ignore buttons

4a. User B accepts → request_status = ACCEPTED → conversation appears in User B's main inbox
4b. User B ignores → request_status = IGNORED → request disappears from list
4c. 30 days pass → request_status reset to NONE by Celery task (auto-expired, can re-initiate)
```

### 3.3 Request Status Enum

| Status | Meaning |
|--------|---------|
| `NONE` | No request context (sender side, or expired) |
| `PENDING` | Awaiting recipient decision |
| `ACCEPTED` | Recipient accepted — full messaging unlocked |
| `IGNORED` | Recipient dismissed — removed from request list |
| `BLOCKED` | Recipient blocked the sender via chat blocks (set when block is created against a pending requester) |

### 3.4 UI Implications

**For the recipient (User B):**
- Chat requests are a **separate section** from the main conversation list — not mixed in
- Badge count on "Requests" tab/section shows pending count
- Each request card shows: requester avatar, name, preview of messages, timestamp
- Accept button moves conversation to main inbox
- Ignore button removes from requests (does NOT block)
- If viewing a conversation with pending status: banner at top with Accept/Ignore

**For the sender (User A):**
- After sending to a stranger, the conversation appears in their main inbox normally
- A subtle indicator shows "Request pending" status on the conversation
- Message composer shows "X of 3 messages remaining" when limit approaching
- At 3 messages: composer disabled with explanation text
- When recipient accepts: indicator disappears, full messaging unlocked
- When recipient ignores: no notification (silent)

**Important navigation note:**
- Requests only appear in **personal chat** (global scope)
- Business/platform internal chat never has requests (org members are trusted)
- Entity tab conversations never have requests (entities are trusted)

---

## 4. Permission Model Summary

### 4.1 Two Permission Layers

The chat system uses **two separate permission mechanisms** that must not be confused:

1. **RBAC `can_manage_chat` permission** — An org-level permission granted to business/platform members via their role. Controls:
   - Access to the entity inbox tab
   - Ability to send messages as the entity
   - Ability to create group conversations in org-scoped chat

2. **Conversation-level `role=admin`** — A per-conversation role on the `ConversationParticipant` record. Controls:
   - Adding/removing participants in that specific group
   - Deleting any message in that group (moderation)
   - Promoting/demoting other members to admin within that group
   - Editing group name/description

The conversation creator is automatically assigned `role=admin`. Other participants start as `role=member` and can be promoted by existing admins.

### 4.2 Personal Chat Permissions

| Action | Who Can |
|--------|---------|
| View chat | Any authenticated user |
| Start DM with connected user | Any authenticated user |
| Start DM with stranger | Any authenticated user (creates request) |
| Create group | Any authenticated user |
| Manage group (add/remove/rename) | Conversation-level group admin |
| Delete own message | Message author (any time) |
| Delete any message in group | Conversation-level group admin |
| Edit own message | Message author (within 15-minute window) |
| Leave group | Any group participant |
| Block participant | Any authenticated user |
| View/manage chat requests | Any authenticated user (own requests) |

### 4.3 Business Console Chat Permissions

| Action | Tab | Who Can |
|--------|-----|---------|
| **See Entity tab** | Entity | Members with `can_manage_chat` (RBAC) |
| Send as business entity | Entity | Members with `can_manage_chat` (RBAC) |
| View business entity inbox | Entity | Members with `can_manage_chat` (RBAC) |
| **See Internal tab** | Internal | All active members |
| Send internal DM | Internal | All active members |
| Create internal group | Internal | Members with `can_manage_chat` (RBAC) |
| Manage group participants | Internal | Conversation-level group admins |
| Delete messages (moderation) | Internal | Conversation-level group admins |
| Edit group name/description | Internal | Conversation-level group admins |

### 4.4 Platform Console Chat Permissions

Same as business console, but for platform membership and `can_manage_chat` on platform.

### 4.5 Conversation Detail `_permissions` (Tier 1.5)

The `GET /conversations/{id}/` detail endpoint returns `_permissions` for UI gating:

```json
{
  "can_send_message": true,
  "can_view_messages": true,
  "can_leave": true,
  "can_manage_group": false,
  "can_add_participant": false,
  "can_remove_participant": false,
  "can_edit_group": false
}
```

The frontend should use these to conditionally show/hide UI elements (add participant button, delete message option, group settings panel, etc.).

---

## 5. Conversation List Behavior by Context

### 5.1 Personal Chat List

- Shows all global-scope conversations where `participant_type=user, participant_id=current_user`
- Excludes conversations with `request_status=PENDING` (those go to requests section)
- Sorted by `last_message_at` descending (secondary: `created_at` descending)
- Each row shows: other participant(s) avatar/name, last message preview, timestamp, unread badge
- For DMs: show other person's name
- For groups: show group name
- For entity DMs: show entity name + badge (e.g., "Acme Corp [Business]")
- Muted conversations show a mute icon

### 5.2 Business Entity Tab List

- Shows all global-scope conversations where `participant_type=business, participant_id=business_id`
- Same visual format but with different header ("Business Messages")
- Each row shows the OTHER participant's info (since the business is always "you" in this tab)

### 5.3 Business Internal Tab List

- Shows all business-scoped conversations where `participant_type=user, participant_id=current_user` AND `scope_type=business, scope_id=business_id`
- Members see their own DMs and groups within this business
- Sorted by last_message_at

### 5.4 Platform Tabs

Mirror business tabs but with `platform` scope and entity type.

---

## 6. Unread Counts & Badge Hierarchy

### 6.1 Backend API

Backend provides aggregated unread counts via `GET /api/v1/chat/unread/`:
```json
{
  "global": 12,
  "business": { "biz-uuid-1": 3, "biz-uuid-2": 0 },
  "platform": 1,
  "entity": {
    "business": { "biz-uuid-1": 5 },
    "platform": { "plat-uuid": 2 }
  }
}
```

- `global` — personal DMs and groups where the user is a direct participant (scope=global)
- `business.{id}` — internal business-scoped conversations (scope=business)
- `platform` — platform-scoped conversations (scope=platform)
- `entity.business.{id}` — entity inbox unread for businesses the user can manage (`can_manage_chat` RBAC)
- `entity.platform.{id}` — entity inbox unread for platform (same permission check)

### 6.2 Badge Placement

```
Sidebar Navigation
├── Chat [12]                     ← global (personal DMs + groups)
│
├── bconsole / Business A
│   └── Chat [8]                  ← entity + internal combined
│       ├── Entity [5]            ← entity.business.{biz-uuid-1}
│       └── Internal [3]          ← business.{biz-uuid-1}
│
├── bconsole / Business B
│   └── Chat [0]                  ← no unread
│
└── pconsole
    └── Chat [3]                  ← entity + internal combined
        ├── Entity [2]            ← entity.platform.{plat-uuid}
        └── Internal [1]          ← platform
```

### 6.3 Real-Time Updates

- WS `message.new` increments the relevant scope badge
- Opening a conversation and marking seen decrements
- Tab-level badges update when switching between entity/internal tabs

---

## 7. WebSocket Strategy

### 7.1 Single Connection Per User

One WebSocket connection handles ALL chat contexts:
```
ws://{host}/ws/chat/?token={jwt_access_token}
```

On connect, the consumer auto-joins channel groups for ALL conversations the user participates in (across all scopes). This means:
- Personal DMs: joined
- Business entity conversations: joined (if user has permission)
- Business internal conversations: joined
- Platform conversations: joined

The frontend receives ALL events through one pipe and routes them to the correct context based on `conversation_id` → scope lookup.

### 7.2 Event Routing

When a WS event arrives (e.g., `message.new`), the frontend must:
1. Look up which conversation it belongs to (from `conversation_id`)
2. Determine which scope/context it belongs to
3. Update the correct part of the UI (personal inbox, business entity tab, etc.)
4. Update the correct unread badge

This means the **message store** should be conversation-keyed, not context-keyed. The context (personal/entity/internal) is derived from the conversation's `scope_type` + `scope_id`.

### 7.3 Client → Server Events

| Event | Payload | Purpose |
|-------|---------|---------|
| `message.send` | `conversation_id`, `content`, `sender_type?`, `sender_id?`, `attachment_ids?` | Send a message |
| `message.edit` | `message_id`, `content` | Edit own message |
| `message.delete` | `message_id` | Delete a message |
| `typing.start` | `conversation_id` | Notify typing started |
| `typing.stop` | `conversation_id` | Notify typing stopped |
| `seen` | `conversation_id`, `last_seen_message_id` | Mark messages as seen |
| `delivered` | `conversation_id`, `last_delivered_message_id` | Mark messages as delivered |
| `presence.subscribe` | `user_ids: [...]` | Subscribe to presence updates (max 50) |
| `reaction.add` | `message_id`, `reaction` | Add emoji reaction |
| `reaction.remove` | `message_id`, `reaction` | Remove emoji reaction |
| `conversation.join` | `conversation_id` | Dynamically join a conversation group |
| `conversation.leave` | `conversation_id` | Leave a conversation group |

### 7.4 Server → Client Events

| Event | Payload | Purpose |
|-------|---------|---------|
| `message.new` | Full message object (with attachments) | New message received |
| `message.edited` | `conversation_id`, `message_id`, `content`, `edited_at` | Message was edited |
| `message.deleted` | `conversation_id`, `message_id` | Message was deleted |
| `typing` | `conversation_id`, `user_id`, `is_typing` | Typing indicator |
| `seen.update` | `conversation_id`, `participant_id`, `last_seen_message_id` | Seen watermark updated |
| `delivered.update` | `conversation_id`, `participant_id`, `last_delivered_message_id` | Delivery watermark updated |
| `presence` | `user_id`, `is_online` | User presence changed |
| `reaction.update` | `conversation_id`, `message_id`, `user_id`, `reaction`, `action` | Reaction added/removed |
| `conversation.new` | Conversation object | New conversation created involving user |
| `error` | `code`, `message` | Error response from server |

### 7.5 Reconnection & Token Refresh

JWT access tokens expire (typically 15 minutes). The WebSocket connection stays alive after token expiry (authentication is on-connect only), but if the connection drops:
- Frontend must detect disconnection
- Refresh the JWT access token via the refresh token endpoint
- Reconnect with the new token
- Re-fetch missed messages (query messages since last known `sequence_number`)

---

## 8. Component Independence Principle

### 8.1 Architecture Goal

The chat system must be built as a **self-contained feature module** with maximum internal independence. No chat component should depend on business-specific or platform-specific imports. The context (scope, permissions, entity) is injected from outside.

```
features/chat/                    ← Self-contained chat engine
├── api/                          ← API client + types
├── components/                   ← UI building blocks
│   ├── conversation-list/        ← Reusable conversation list
│   ├── chat-window/              ← Reusable chat window
│   ├── message/                  ← Message bubble + variants (text, system, deleted)
│   ├── composer/                 ← Message input + attachments
│   ├── requests/                 ← Chat request cards + actions
│   ├── participants/             ← Participant list + management
│   ├── reactions/                ← Reaction picker + display
│   ├── group-settings/           ← Group rename, description, admin management
│   ├── typing-indicator/         ← "User is typing..." display
│   ├── media-gallery/            ← Grid view of shared images (future, backend ready)
│   └── ...                       ← Other atomic components
├── hooks/                        ← TQ queries, mutations, WS hooks
├── stores/                       ← Zustand stores (chat + presence)
├── providers/                    ← Chat context provider (scope injection)
├── layouts/                      ← Chat page layouts (single/dual-tab)
├── constants/                    ← Enums, limits mirrored from backend
├── utils/                        ← Helpers (time formatting, etc.)
└── types/                        ← All chat TypeScript types
```

### 8.2 Context Injection Pattern

Instead of the chat engine "knowing" about business or platform logic, the **page-level component** injects context:

```
// In (user)/chat/page.tsx
<ChatProvider scope={{ type: "global" }}>
  <PersonalChatLayout />           ← Single-panel chat
</ChatProvider>

// In bconsole/[slug]/chat/page.tsx
<ChatProvider scope={{ type: "dual", entity: "business", entityId: business.id }}>
  <DualTabChatLayout                ← Two-tab layout
    entityTab={<EntityInbox />}
    internalTab={<InternalChat scope="business" scopeId={business.id} />}
    permissions={businessPermissions}
  />
</ChatProvider>

// In pconsole/chat/page.tsx
<ChatProvider scope={{ type: "dual", entity: "platform", entityId: platform.id }}>
  <DualTabChatLayout
    entityTab={<EntityInbox />}
    internalTab={<InternalChat scope="platform" scopeId={platform.id} />}
    permissions={platformPermissions}
  />
</ChatProvider>
```

The `ChatProvider` establishes the WebSocket connection, configures stores, and exposes scope context to all child components via React context.

### 8.3 Layout Variants

| Layout | Used By | Structure |
|--------|---------|-----------|
| `PersonalChatLayout` | Personal chat | Instagram-like: conversation list (left) + chat window (right) |
| `DualTabChatLayout` | bconsole, pconsole | Tab bar (Entity \| Internal) + conversation list (left) + chat window (right) |

Both layouts compose the same underlying components — they just arrange them differently and pass different scope props.

---

## 9. Entity Participation — UX Clarification

### 9.1 What "Entity as a Person" Means

When a business or platform "acts as a person" in global chat:

**From the entity operator's perspective (in bconsole/pconsole Entity tab):**
- "I am speaking as Acme Corp, not as myself"
- The conversation list shows conversations Acme Corp is involved in
- When composing a message, the sender is automatically Acme Corp
- The operator's personal identity is hidden from the recipient
- Multiple team members can manage the same inbox (shared access)

**From the recipient's perspective (in personal chat):**
- "Acme Corp sent me a message"
- They see the business name + logo as the sender
- They see a "Business" badge next to the name
- They can reply normally — their reply goes to Acme Corp's entity inbox
- They can block the business entity from DMs

**From the system's perspective:**
- `sender_type=business, sender_id={business_uuid}` on messages
- `acting_user_id={operator_uuid}` for audit trail (invisible to recipient)
- `participant_type=business, participant_id={business_uuid}` on participant record
- The conversation's `scope_type=global` (entity conversations always live in global scope)

### 9.2 Entity Cannot Participate in Scoped Chat

Entity participation is **global scope only**. A business entity cannot be a participant in another business's internal chat or in platform internal chat. Internal chat is always user-to-user within that org's scope.

### 9.3 Entity-Personal Inbox Overlap

When a business sends a DM to a user, that conversation appears in:
1. The business's Entity Inbox tab (in bconsole)
2. The user's Personal Chat inbox

If the user also has `can_manage_chat` on that same business, they could see the conversation in **both** their personal inbox (as the recipient) and the entity inbox (as the business operator). The frontend should be aware of this overlap but does NOT need to deduplicate — the two views serve different roles.

---

## 10. Typing Indicators

### 10.1 How They Work

Typing indicators are real-time, broadcast-only (no database storage):

1. User starts typing → frontend sends WS `typing.start` with `conversation_id`
2. Backend broadcasts `typing` event to all conversation participants (excluding sender)
3. User stops typing (or timeout) → frontend sends WS `typing.stop`
4. Recipients show/hide "User is typing..." indicator

### 10.2 Frontend Implementation

- Send `typing.start` on first keystroke in composer
- Send `typing.stop` after 3 seconds of inactivity (debounce)
- Display typing indicator below the last message in chat window
- Show up to 3 names: "Alice is typing...", "Alice and Bob are typing...", "Alice, Bob, and 2 others are typing..."
- Auto-expire typing indicator after 5 seconds without a refresh (safety net if `typing.stop` is lost)

---

## 11. Message Display States

### 11.1 Message Status

Every message has a `status` field:

| Status | Display |
|--------|---------|
| `active` | Normal message bubble |
| `edited` | Normal bubble + "(edited)" label. `edited_at` timestamp available on hover |
| `deleted` | Gray bubble with "This message was deleted" text. Content is cleared |

### 11.2 System Messages

The backend sends messages with `content_type=system` for lifecycle events:
- "Alice was added to the group"
- "Bob left the group"
- "Charlie was promoted to admin"
- "Diana was removed from the group"
- "Eve was demoted from admin"

System messages render differently from user messages:
- Centered text (not in a bubble)
- Gray/muted color
- No sender avatar or name
- No reaction support
- Not editable or deletable

### 11.3 Delivery & Read Receipts

The backend tracks two separate watermarks per participant:

| Watermark | Meaning | WS Event |
|-----------|---------|----------|
| `last_delivered_message_id` | Message reached the client | `delivered.update` |
| `last_seen_message_id` | User opened the conversation and viewed the message | `seen.update` |

**Frontend display (DMs only):**
- Single checkmark: delivered
- Double checkmark (or blue): seen
- No checkmarks: sent but not yet delivered

**For groups:** Show "Seen by X" count instead of individual checkmarks.

---

## 12. Muting & Notification Behavior

### 12.1 Mute

Each participant has an `is_muted` flag per conversation. Muting:
- Does NOT hide the conversation from the list
- Does NOT stop unread count updates
- Shows a mute icon on the conversation row
- Mute/unmute is per-conversation, per-user
- Endpoints: `POST /conversations/{id}/mute/` and `POST /conversations/{id}/unmute/`

> **Note:** The `is_muted` flag is fully functional. Muted participants are skipped in the notification loop (`_notify_new_message`) — they will not receive push notifications for new messages in muted conversations.

### 12.2 Notifications

5 notification types, all configurable in user notification preferences:

| Event | When | Who Receives |
|-------|------|-------------|
| `chat_message_received` | New message in conversation | Offline participants (presence-checked) |
| `chat_request_received` | Stranger initiates DM | Recipient of the request |
| `chat_request_accepted` | Recipient accepts request | Original sender |
| `chat_group_added` | Admin adds user to group | Added user |
| `chat_reaction_received` | Someone reacts to your message | Message author (not self) |

**Rate limiting:** 1 notification per conversation per 5 minutes (backend enforced via Redis).
**Presence-aware:** Online users don't get push notifications for messages (backend checks presence before notifying).

---

## 13. Group Management

### 13.1 Group Lifecycle

- **Create:** User creates group via `POST /conversations/` with `conversation_type=group` and participant list. Creator becomes `role=admin`.
- **Update:** Admin can rename group and edit description via `PATCH /conversations/{id}/`.
- **Add participant:** Admin adds via `POST /conversations/{id}/participants/`.
- **Remove participant:** Admin removes via `DELETE /conversations/{id}/participants/{participant_id}/`.
- **Leave:** Any participant can leave via `POST /conversations/{id}/leave/`.
- **Auto-deactivation:** When the last participant leaves, the conversation's `is_active` flag is set to `false`. Inactive conversations are excluded from all queries.

### 13.2 Admin Succession

When the last admin leaves a group, the **oldest remaining member** (by `created_at` on participant record) is automatically promoted to admin. A system message is sent to announce this.

### 13.3 Admin Promotion/Demotion

REST endpoints for admin management:
- `POST /api/v1/chat/conversations/{id}/participants/{participant_id}/promote/` → 204
- `POST /api/v1/chat/conversations/{id}/participants/{participant_id}/demote/` → 204

Only group admins can call these. Demoting the last admin returns 400 (`business_rule_violation`, rule `last_admin`). Promote is idempotent (promoting an existing admin returns 204 silently). Demoting a member returns 204 silently.

---

## 14. Search Behavior

### 14.1 Search Scope

Message search is scoped to conversations the user participates in, within the current scope context:

| Context | Search Scope |
|---------|-------------|
| Personal chat | All global conversations the user is in |
| Business entity tab | All global conversations the business entity is in |
| Business internal tab | All business-scoped conversations the user is in |
| Platform entity tab | All global conversations the platform entity is in |
| Platform internal tab | All platform-scoped conversations the user is in |

**Important:** The search endpoint (`GET /api/v1/chat/messages/search/`) accepts `scope_type`, `scope_id`, and optional `conversation_id` query params. The frontend **must** pass the correct scope params to restrict search results to the current context. Omitting scope params returns results across ALL the user's conversations, which would leak business-internal messages into personal search results.

### 14.2 Search UX

- Search bar within the chat interface
- Debounced input (300ms)
- Results show: message content (highlighted), sender name, conversation name, timestamp
- Click result → navigate to that conversation, scroll to that message
- PostgreSQL FTS with trigram fallback for typo tolerance

---

## 15. Key Business Rules & Constraints

| Rule | Value | Source |
|------|-------|--------|
| Max message length | 5,000 characters | `CHAT_MESSAGE_MAX_LENGTH` |
| Message edit window | 15 minutes | `CHAT_MESSAGE_EDIT_WINDOW_MINUTES` |
| Chat request message limit | 3 messages per sender | `CHAT_REQUEST_MAX_MESSAGES` |
| Chat request expiry | 30 days | `CHAT_REQUEST_EXPIRY_DAYS` |
| Max group participants | 100 | `CHAT_GROUP_MAX_PARTICIPANTS` |
| Max attachments per message | 10 | `CHAT_MAX_ATTACHMENTS_PER_MESSAGE` |
| Max image size | 10 MB | `CHAT_MAX_IMAGE_SIZE` |
| Allowed image types | JPEG, PNG, GIF, WebP | `CHAT_ALLOWED_IMAGE_TYPES` |
| Presence TTL | 30 seconds | `WS_PRESENCE_TTL_SECONDS` |
| Heartbeat interval | 20 seconds | `WS_HEARTBEAT_INTERVAL_SECONDS` |
| Max presence subscriptions | 50 | `WS_MAX_PRESENCE_SUBSCRIPTIONS` |
| Message rate limit | 30 per minute | `CHAT_RATE_LIMIT_MESSAGES_PER_MINUTE` |
| Conversation rate limit | 5 per hour | `CHAT_RATE_LIMIT_CONVERSATIONS_PER_HOUR` |
| Request rate limit | 10 per hour | `CHAT_RATE_LIMIT_REQUESTS_PER_HOUR` |

**Note:** Many of these are configurable via the Feature Gate system (`feature_config.get_value()`). The frontend should not hardcode these — fetch them from the backend or use the values from the initial config load.

---

## 16. Feature Gate Integration

The backend chat system has extensive feature gates. When a feature is disabled, the backend returns HTTP 403 with `code="feature_disabled"` and a `feature` field identifying what's disabled:

```json
{ "code": "feature_disabled", "feature": "chat.reactions", "message": "This feature is currently disabled" }
```

### 16.1 Gated Features

| Feature Gate | What It Controls |
|-------------|-----------------|
| `systems.chat` | Entire chat system (URL group not registered) |
| `user.chat.group` | Group conversation creation |
| `user.chat.file_sharing` | Image attachment upload |
| `user.chat.reactions` | Adding/removing reactions |
| `user.chat.search` | Message search endpoint |
| Entity participation gates | Business/platform entity chat |

### 16.2 Frontend Handling

- **System-level gate (`systems.chat`):** If chat is disabled, the chat route/nav item should be hidden entirely. Detect via initial config or 404 on first API call.
- **Feature-level gates:** When user attempts a gated action and gets `feature_disabled`, show an explanatory message instead of a generic error. Consider pre-fetching enabled features to hide disabled UI elements proactively.
- **Rate limit errors (HTTP 429):** Show "Slow down" toast message with the `Retry-After` header value.

---

## 17. Mobile / Responsive Behavior

### Desktop (md and above)
- **Personal chat:** Two-panel layout (conversation list left, chat window right) — like Instagram web DMs
- **Console chat:** Tab bar + two-panel layout within the console sidebar context

### Mobile (below md)
- **Personal chat:** Single-panel — conversation list OR chat window, not both. Tap a conversation to enter it, back button to return to list.
- **Console chat:** Same single-panel behavior, with tab bar above the active panel
- Bottom navigation bar shows chat icon with unread badge

---

## 18. Presence Strategy

### 18.1 Subscription Management

Backend caps presence subscriptions at 50 per WebSocket connection. In a system with many group conversations, the frontend needs a smart subscription strategy:

- **Subscribe on visibility:** Only subscribe to presence for users currently visible in the UI (conversation list, participant panel, active chat window)
- **Unsubscribe on navigation:** When switching tabs or conversations, re-issue `presence.subscribe` with only the currently relevant user IDs
- **DM priority:** Always subscribe to the other user's presence in active DM conversations
- **Group strategy:** Subscribe to presence of the N most recently active participants in the current group (not all members)

### 18.2 Presence Display

- Green dot on avatar for online users
- "Last seen X ago" for offline users (if the backend ever adds this — currently only online/offline boolean)

---

## 19. What This Description Does NOT Cover (Deferred)

The following are explicitly **out of scope** for this description and the initial implementation:

- **Voice/video calls** — Future enhancement
- **Message forwarding** — Not in backend
- **Message threading/replies** — Not in backend (flat message list)
- **Custom emoji reactions** — Backend supports 6 preset only
- **File attachments (non-image)** — Backend prepared but images only for now
- **Read receipts privacy settings** — Not in backend
- **Ephemeral/disappearing messages** — Not in backend
- **Message pinning** — Not in backend
- **Conversation archiving** — Not in backend
- **Rich text formatting (markdown/bold/italic)** — Messages are plain text
- **Media gallery view** — Backend endpoint ready (`GET /api/v1/chat/conversations/{id}/media/`, cursor-paginated, images only), frontend UI deferred

---

## 20. Backend Gaps & Issues (All Resolved)

All four gaps/bugs identified during the review have been fixed and tested (408 chat tests passing).

### 20.1 Unread Count API Now Includes Entity Counts (RESOLVED)

**Was:** `GET /api/v1/chat/unread/` returned only personal unread (`global`, `business`, `platform`). No way to get entity inbox unread counts.

**Fix:** Extended `ChatSelector.get_unread_counts_by_scope()` to query entity participants (business/platform) and check `ChatPolicy.can_manage_entity_chat()` per entity. Response now includes an `entity` key:

```json
{
  "global": 5,
  "business": { "biz-uuid": 2 },
  "platform": 0,
  "entity": {
    "business": { "biz-uuid": 3 },
    "platform": { "plat-uuid": 1 }
  }
}
```

**Frontend usage:** Use `data.entity.business[bizId]` for the Entity Inbox tab badge, `data.business[bizId]` for the Internal Chat tab badge.

### 20.2 `is_muted` Now Suppresses Notifications (RESOLVED)

**Was:** `_notify_new_message()` checked presence and rate limiting but never checked `is_muted`. Muted users still received push notifications.

**Fix:** Added `if p.is_muted: continue` to the notification loop in `services.py:1729`. Muted participants are now skipped before the presence and rate-limit checks.

### 20.3 Promote/Demote Admin REST Endpoints Added (RESOLVED)

**Was:** `promote_to_admin()` / `demote_from_admin()` service methods existed but had no API surface.

**Fix:** Added two REST endpoints:
- `POST /api/v1/chat/conversations/{id}/participants/{participant_id}/promote/` → 204
- `POST /api/v1/chat/conversations/{id}/participants/{participant_id}/demote/` → 204

Both require authentication. Only group admins can call them. Demoting the last admin returns 400 (`business_rule_violation`, rule `last_admin`).

### 20.4 Media Gallery REST Endpoint Added (RESOLVED)

**Was:** `ChatSelector.get_media_gallery()` existed but no view or URL exposed it.

**Fix:** Added `GET /api/v1/chat/conversations/{id}/media/` with cursor-based pagination:

```json
{
  "results": [
    {
      "id": "uuid",
      "file_type": "image",
      "original_filename": "photo.jpg",
      "mime_type": "image/jpeg",
      "file_size": 1024,
      "width": 800,
      "height": 600,
      "url": "/media/chat/..."
    }
  ],
  "next_cursor": "2026-03-25T12:00:00+00:00"
}
```

Query params: `cursor` (ISO datetime), `page_size` (default 50, max 100). Only participants can access. Excludes orphan (unlinked) attachments.

---

## 21. Summary: Route → Scope → Tab Mapping

```
┌─────────────────────────────────────────────────────────────────────┐
│ /(user)/chat/                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ PERSONAL CHAT                                                   │ │
│ │ scope_type = global                                             │ │
│ │ participant_type = user                                         │ │
│ │                                                                 │ │
│ │ ┌───────────────┐  ┌──────────────────────────────────────────┐│ │
│ │ │ Conversation  │  │ Chat Window                              ││ │
│ │ │ List          │  │                                          ││ │
│ │ │               │  │ Messages + Composer                      ││ │
│ │ │ [Requests]    │  │ (typing indicator below)                 ││ │
│ │ │ section/badge │  │                                          ││ │
│ │ └───────────────┘  └──────────────────────────────────────────┘│ │
│ └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ /bconsole/{slug}/chat/                                              │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ [Entity Inbox]  [Internal Chat]    ← Tab bar                   │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │ TAB 1: ENTITY INBOX                                             │ │
│ │ scope_type = global                                             │ │
│ │ participant_type = business                                     │ │
│ │ endpoint = /entity/business/{id}/inbox/                         │ │
│ │ permission = can_manage_chat (RBAC)                             │ │
│ │                                                                 │ │
│ │ ┌───────────────┐  ┌──────────────────────────────────────────┐│ │
│ │ │ Entity Convos │  │ Chat Window (sending as business)        ││ │
│ │ └───────────────┘  └──────────────────────────────────────────┘│ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │ TAB 2: INTERNAL CHAT                                            │ │
│ │ scope_type = business                                           │ │
│ │ scope_id = {business_id}                                        │ │
│ │ participant_type = user                                         │ │
│ │ group creation = can_manage_chat (RBAC)                         │ │
│ │ group management = conversation-level admin role                │ │
│ │                                                                 │ │
│ │ ┌───────────────┐  ┌──────────────────────────────────────────┐│ │
│ │ │ Internal      │  │ Chat Window (sending as user)            ││ │
│ │ │ Convos        │  │                                          ││ │
│ │ └───────────────┘  └──────────────────────────────────────────┘│ │
│ └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

pconsole/chat/ follows the identical dual-tab pattern with platform scope.
```
