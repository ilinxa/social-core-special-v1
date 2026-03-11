# Chat System — Description

**Status:** Draft
**Date:** 2026-03-09
**Workspace:** cross-cutting (backend + frontend + mobile)

---

## 1. What Is This?

The Chat System is a **scope-isolated, reusable messaging engine** that provides real-time person-to-person and group chat across every layer of the platform. Rather than building separate chat systems for each organizational context, the platform uses a single engine where every conversation belongs to a **scope** — a boundary that controls who can participate, who can be discovered, and which conversations are visible.

The system supports four participant contexts through one unified architecture:

| Scope | Isolation | Participants |
|-------|-----------|-------------|
| **Global** (`scope=null`) | No isolation — platform-wide | All users + entity accounts (businesses, platform, teams) |
| **Business** (`scope=business-id`) | Business-internal only | Members of that business (chatting as themselves) |
| **Platform** (`scope=platform-id`) | Platform-internal only | Members of the platform (chatting as themselves) |
| **Team** (`scope=team-id`) | Team-internal only | Members of that team (chatting as themselves) — *future* |

The core design principle is **one codebase, one set of models, one API surface**. Scope is a filter parameter, not a separate system. Adding a new scope type (e.g., team) requires zero changes to the chat engine — just a new `scope_type` value.

---

## 2. Core Concepts

### 2.1 Scope Isolation Model

Every conversation belongs to **exactly one scope**. A scope is defined by two fields:

- `scope_type`: `global` | `business` | `platform` | `team` (extensible enum)
- `scope_id`: UUID of the owning entity, or `null` for global scope

**Isolation rules:**
- Queries **always** filter by scope. A user listing their conversations in the business console sees only `scope_type=business, scope_id=<that business>`.
- There is **no cross-scope visibility**. If Alice and Bob chat in global scope, and they are also both members of Acme Corp, the business-internal chat between them is a **completely separate conversation**. Messages do not merge or bleed across scopes.
- Scope determines **participant eligibility**: the chat engine validates that every participant in a conversation is authorized within that scope before allowing any action (join, send message, create conversation).

```
Scope Isolation:

  Global (scope_id=null)           Business: Acme (scope_id=abc-123)
  ┌─────────────────────┐         ┌─────────────────────┐
  │                     │         │                     │
  │  Alice ↔ Bob (DM)   │         │  Alice ↔ Bob (DM)   │  ← separate conversation
  │  Alice ↔ Acme (DM)  │         │  Alice ↔ Carol (DM) │
  │  Acme ↔ Beta (DM)   │         │  Team Chat (group)  │
  │  Public Group        │         │                     │
  │                     │         │  (Bob, Carol, Dave   │
  └─────────────────────┘         │   are Acme members)  │
                                  └─────────────────────┘
  These are different worlds. No shared messages.
```

### 2.2 Account Types & Participation

The platform has four account types. Each participates in chat differently depending on the scope:

#### User Account
- Every person on the platform has a User account.
- Users participate in chat **as themselves** in all scopes.
- In global scope, users can DM any other user or entity.
- In org scopes (business/platform/team), users can only chat with other members of that org.

#### Business Account
- An organizational account with RBAC-controlled membership.
- In **global scope**: the Business account itself is a **first-class chat participant** (entity account). It has its own inbox, can be in group chats, can DM and be DM'd.
- In **business scope** (its own internal scope): the business account is NOT a participant — members chat as themselves.
- Entity actions (sending messages as the business) are performed by members who hold the appropriate RBAC permission (e.g., `can_manage_chat`).

#### Platform Account
- The single platform-level organizational account.
- In **global scope**: the Platform account is a **first-class chat participant**, same as business entities.
- In **platform scope** (internal): members chat as themselves, platform entity is not a participant.
- Controlled by members with the appropriate RBAC permission.

#### Team Account (Future)
- A shared account type — a group of users forming a team.
- Teams can exist at any scope level:
  - `inherit=null` → global team (independent)
  - `inherit=business-id` → business-internal team
  - `inherit=platform-id` → platform-internal team
- In **global scope**: the Team account is a first-class entity participant.
- In **team scope** (its own internal scope): members chat as themselves.
- Teams are an **organizational unit**, not a chat feature. They use chat like any other account type.

### 2.3 Entity Participation Rules

Entity participation (an org account acting as a "person" in chat) follows strict rules:

```
                        Global Scope    Own Internal Scope
                        ────────────    ──────────────────
User                    ✓ as self       ✓ as self
Business Entity         ✓ as entity     ✗ (members chat as selves)
Platform Entity         ✓ as entity     ✗ (members chat as selves)
Team Entity (future)    ✓ as entity     ✗ (members chat as selves)
```

**Entity-to-entity chat** is allowed in global scope:
- Business ↔ Business
- Business ↔ Platform
- Business ↔ User
- Platform ↔ User
- Team ↔ any (future)

**Who controls an entity?** Any member with the correct RBAC permission can act on behalf of the entity. When they send a message, it appears as coming from the entity (e.g., "Acme Corp"), not from the individual user. However, an internal audit trail records which user performed the action.

### 2.4 Conversation Types

Two conversation types exist, uniform across all scopes:

#### Direct Message (1:1)
- Exactly two participants.
- Can be: user ↔ user, user ↔ entity, entity ↔ entity (global scope only for entity involvement).
- Either participant can initiate.

#### Group Chat
- 3 or more participants (like Instagram group chats).
- Created by any eligible participant within the scope.
- Has a name, optional avatar/description.
- Participants can be added/removed by the group creator or members with appropriate rights.
- In global scope: group can contain a mix of users and entities.
- In org scopes: group contains only members of that org (as themselves).

**Key distinction: Group Chat ≠ Team.** A group chat is a conversation inside the chat system with no identity outside of chat. A team is an organizational account type with its own RBAC, features, and lifecycle — it uses the chat system but is not defined by it.

### 2.5 Chat Requests (First-Message Gating)

When a user sends the **first message** to someone they have no prior relationship with (no follow, no connection), the message is not delivered directly. Instead, it arrives as a **chat request** that the recipient must accept, ignore, or block.

**Relationship check (via Network system):**
- `ConnectionSelector.is_connected()` — are sender and recipient connected? (user↔user connections)
- `FollowSelector.is_following()` — does user follow the entity? (user→business/platform follows only — the Network system does not support user-to-user follows)

**Decision matrix for DMs in global scope:**

```
Scenario                               First message behavior
─────────────────────────────────────  ─────────────────────
User → User (connected)                Direct delivery (no request)
User → User (not connected)            → Chat Request (pending acceptance)
User → User (blocked)                  → Silently rejected (sender sees "sent")
User → Entity (any relationship)       Direct delivery (entities are public-facing)
Entity → User (any relationship)       Direct delivery (entity bypass)
Entity → Entity                        Direct delivery (entity bypass)
```

**Note:** The Network system's Follow model is one-way User → Business/Platform only. There are no user-to-user follows. For user↔user DMs, only the Connection relationship determines whether chat requests are triggered. Entity participants always bypass chat requests regardless of follow/connection status.

**Chat request lifecycle:**

```
User A sends first message to User B (no relationship)
  │
  ▼
Chat Request created (status: pending)
  │
  ├── User B sees it in "Message Requests" section (separate from main inbox)
  │   ├── Preview: sender identity + first message text (optionally truncated)
  │   └── Actions: [Accept] [Ignore] [Block]
  │
  ├── Accept → conversation moves to main inbox, all future messages direct
  ├── Ignore → request disappears from UI, can be re-surfaced later
  └── Block  → sender added to block list, all future messages silently rejected
```

**Rules:**
- Chat requests apply to **DMs only** (not group chats — group invitations are a separate flow).
- Chat requests apply in **global scope only**. In org scopes (business/platform), all members can message each other directly — membership itself is the trust signal.
- Only the **first message** triggers the request. Once accepted, the conversation is permanent (until blocked).
- Entity accounts (businesses/platforms) bypass chat requests — messages from entities are always delivered directly (entities are public-facing by nature).
- If User A sends a chat request to User B, and before B responds, B sends a message to A — this auto-accepts the request (mutual intent established).

### 2.6 Block System

Users can block other participants from messaging them. Blocking is **per-participant**, not per-conversation.

**Block actions:**
- **Block**: Adds participant to the blocker's block list. Silently prevents all future messages from the blocked participant. The blocked user is **not notified** — their messages appear "sent" from their perspective but are never delivered.
- **Unblock**: Removes participant from block list. Does not restore previous conversations or re-send blocked messages.

**Block scope:**
- Blocking a **user** prevents that user from sending DMs to the blocker in **global scope**. Does not affect org-scope messaging (org admins may still need to communicate with all members).
- Blocking an **entity** (business/platform) prevents that entity from initiating DMs with the blocker in global scope.
- In org scopes, blocking is **not available** — org membership implies communication ability. Org admins can use suspension/removal for problematic members instead.

**Block effects on existing conversations:**
- DM with blocked user: blocker no longer sees new messages from blocked user. Conversation moves to a hidden state for the blocker.
- Group chat: blocked user's messages are hidden for the blocker, but the group continues normally for other participants. Neither party is removed from the group.

**Block list management:**
- Users can view their block list and unblock participants.
- Block list is private — blocked users cannot see that they've been blocked.

### 2.7 Message Delivery & Read Status

Every message tracks its delivery lifecycle through three states:

```
Message States:
  SENT        → Server received and persisted the message
  DELIVERED   → Message reached the recipient's device (client acknowledgment)
  SEEN        → Recipient viewed the message (read receipt)
```

**How each state is triggered:**

| State | Trigger | Mechanism |
|-------|---------|-----------|
| **Sent** | Server persists message to database | Synchronous — sender gets confirmation immediately |
| **Delivered** | Recipient's client receives the message via WebSocket | Client sends `ack` event back to server. For offline users, delivered is set when they next connect and receive pending messages |
| **Seen** | Recipient opens/views the conversation containing the message | Client sends `seen` event with conversation_id + last_seen_message_id (watermark pattern) |

**Design: Watermark, not per-message tracking.**

Rather than storing a `seen_at` timestamp on every individual message (expensive at scale), the system uses a **watermark** approach:

```
ConversationParticipant:
  conversation_id: <conv>
  participant_type: "user"
  participant_id: <user-uuid>
  last_seen_message_id: <message-uuid>     ← all messages up to this are "seen"
  last_delivered_message_id: <message-uuid> ← all messages up to this are "delivered"
  last_seen_at: timestamp
```

- Messages are chronologically ordered. If the watermark points to message #47, all messages #1–#47 are considered seen.
- The sender's UI shows: double-check for "delivered", blue/filled double-check for "seen" (like WhatsApp/Telegram).
- In **group chats**, the watermark is per-participant. A message is "seen" when all (or a threshold of) participants have seen it. The UI can show "Seen by 3 of 5" or similar.

**Real-time delivery of status updates:**
- `delivered` and `seen` events are broadcast via WebSocket to the message sender.
- Status updates are **batched** — if a user reads 20 messages at once, one `seen` event is sent with the latest message ID, not 20 separate events.

---

## 3. Requirements

### Functional Requirements

#### Conversations
- FR-1: Users can create direct message conversations with any eligible participant in their current scope.
- FR-2: Users can create group chat conversations with multiple participants in their current scope.
- FR-3: Conversations are strictly isolated by scope — no cross-scope visibility or message leakage.
- FR-4: Each conversation tracks its scope (`scope_type` + `scope_id`) immutably after creation.
- FR-5: Conversations have metadata: type (direct/group), name (group only), created_by, created_at.

#### Messages
- FR-6: Participants can send text messages to conversations they belong to.
- FR-7: Messages support rich content types: text, images, files, links (extensible).
- FR-8: Messages are ordered chronologically within a conversation.
- FR-9: Messages can be edited by their sender within a configurable time window.
- FR-10: Messages can be deleted (soft delete) by their sender or by a moderator/admin.
- FR-11: Message delivery status is tracked: sent, delivered, seen (see FR-27 through FR-31 for detailed requirements).

#### Participants
- FR-12: Participant eligibility is validated against the conversation's scope on every action.
- FR-13: In global scope, entity accounts (business/platform/team) can participate as first-class entities.
- FR-14: Entity actions are performed by RBAC-authorized members; the entity is the visible sender.
- FR-15: An internal audit trail records which user performed actions on behalf of an entity.
- FR-16: Group chat creators can add/remove participants (within scope eligibility).

#### Chat Requests
- FR-17: The first DM to a non-connected user in global scope is delivered as a chat request (pending acceptance).
- FR-18: Recipients see chat requests in a separate "Message Requests" section with Accept, Ignore, and Block actions.
- FR-19: Accepting a chat request moves the conversation to the main inbox; all future messages are delivered directly.
- FR-20: If the recipient sends a message to the requester before responding, the request is auto-accepted (mutual intent).
- FR-21: Chat requests do not apply in org scopes (membership = trust) or for entity-to-anyone messages.

#### Block System
- FR-22: Users can block any participant to silently prevent all future DMs from them in global scope.
- FR-23: Blocked users are not notified — their messages appear "sent" but are never delivered.
- FR-24: Users can view their block list and unblock participants to restore messaging ability.
- FR-25: Blocking hides the blocked user's messages in existing DMs and group chats for the blocker.
- FR-26: Blocking is not available in org scopes — org membership implies communication ability.

#### Delivery & Read Status
- FR-27: Every message tracks three states: sent (server persisted), delivered (client received), seen (recipient viewed).
- FR-28: Delivery status uses a watermark pattern — `last_delivered_message_id` and `last_seen_message_id` per participant per conversation.
- FR-29: Status updates (delivered, seen) are broadcast in real-time to the message sender via WebSocket.
- FR-30: Status updates are batched — reading 20 messages sends one `seen` event with the latest message ID.
- FR-31: In group chats, seen status is per-participant with aggregate display (e.g., "Seen by 3 of 5").

#### Real-Time
- FR-32: New messages are delivered in real-time to all online conversation participants.
- FR-33: Typing indicators show when a participant is composing a message.
- FR-34: Online/offline presence is visible for users within the current scope.
- FR-35: Delivered and seen status changes are pushed in real-time.

#### Discovery & Lists
- FR-36: Users can list their conversations per scope, ordered by last activity.
- FR-37: Users can search conversations by participant name or message content within a scope.
- FR-38: Unread message count is available per conversation and as a total badge.
- FR-39: In global scope, users can discover other users/entities to start new conversations.
- FR-40: Chat requests are listed separately from accepted conversations (dedicated "Message Requests" section).

#### Entity Chat Management
- FR-41: Members with `can_manage_chat` permission can access the entity's inbox.
- FR-42: Multiple members with the permission can manage the same entity inbox concurrently.
- FR-43: Entity inbox shows all conversations the entity is part of in global scope.

### Non-Functional Requirements

- NFR-1: Message delivery latency < 200ms for online recipients (WebSocket).
- NFR-2: Conversation list API response < 300ms for users with up to 500 conversations.
- NFR-3: Message history pagination must handle conversations with 100K+ messages efficiently.
- NFR-4: The system must handle 10K+ concurrent WebSocket connections per server instance.
- NFR-5: Messages must be persisted durably before acknowledging delivery.
- NFR-6: Scope isolation must be enforced at the data layer (not just API layer) to prevent leakage.
- NFR-7: Entity chat operations must be auditable (who acted on behalf of which entity).

---

## 4. Scope

### In Scope

- Chat engine with scope-based isolation (global, business, platform)
- Direct message and group chat conversation types
- Text messages with extensible content types
- Real-time delivery via WebSocket
- Typing indicators, online presence
- Message delivery status (sent → delivered → seen) with watermark pattern
- Chat request system (first-message gating for non-connected/non-following users)
- Block/unblock system (global scope, silent rejection, block list management)
- Entity participation in global scope (business/platform act as chat participants)
- RBAC-gated entity chat management
- Conversation list, search, unread counts
- Message edit and soft-delete
- Audit trail for entity actions
- Backend API + WebSocket layer
- Frontend chat UI (responsive, works in all console contexts)

### Out of Scope

- Voice/video calls (may be added later as separate feature)
- End-to-end encryption (server-side encryption at rest is sufficient for v1)
- Message reactions/emoji responses (may be added in a later phase)
- Bots/automated messages (future feature)
- Chat analytics/reporting dashboard
- File storage service (uses existing media/file upload infrastructure)
- Team account type implementation (team scope is designed for but not built in v1)
- Chat backup/export functionality
- Push notifications for mobile (will use existing notification system when mobile is built)
- Message threading/replies (may be added later — v1 is flat message list)

---

## 5. User Stories

### Global Scope

| ID | As a... | I want to... | So that... |
|----|---------|--------------|------------|
| US-1 | User | Send a direct message to another user | I can communicate privately with anyone on the platform |
| US-2 | User | Create a group chat with multiple users | We can have a shared conversation |
| US-3 | User | Send a message to a business account | I can inquire about their services |
| US-4 | Business member (with chat permission) | Read and reply to messages sent to my business | Our business can communicate with customers/partners |
| US-5 | Business member (with chat permission) | Start a conversation as my business with another business | We can establish B2B communication |
| US-6 | Platform member (with chat permission) | Send messages as the platform to any user or business | We can communicate official announcements or support |

### Business Internal Scope

| ID | As a... | I want to... | So that... |
|----|---------|--------------|------------|
| US-7 | Business member | DM a colleague within my business | We can discuss work privately |
| US-8 | Business member | Create a group chat with my team | We can coordinate on projects |
| US-9 | Business member | See only business-internal conversations in the business console | I'm not distracted by global chat |

### Platform Internal Scope

| ID | As a... | I want to... | So that... |
|----|---------|--------------|------------|
| US-10 | Platform member | DM another platform member | We can coordinate on platform operations |
| US-11 | Platform admin | Create a group chat with moderators | We can discuss moderation decisions |

### Chat Requests & Blocking

| ID | As a... | I want to... | So that... |
|----|---------|--------------|------------|
| US-12 | User | Have unknown users' first messages appear as requests | I'm not spammed by strangers |
| US-13 | User | Accept a message request to start chatting | I can connect with people I choose |
| US-14 | User | Ignore a message request | It disappears without blocking the sender |
| US-15 | User | Block a user from a message request | They can never message me again |
| US-16 | User | View and manage my block list | I can unblock people if I change my mind |
| US-17 | User | Message my connections directly without requests | Existing relationships have frictionless chat |

### Delivery & Read Status

| ID | As a... | I want to... | So that... |
|----|---------|--------------|------------|
| US-18 | User | See when my message was delivered to the recipient | I know it reached their device |
| US-19 | User | See when the recipient has read my message | I know they've seen it |
| US-20 | User | See "Seen by 3 of 5" in group chats | I know who has read my message |

### Cross-Cutting

| ID | As a... | I want to... | So that... |
|----|---------|--------------|------------|
| US-21 | User | See my unread count per scope | I know where I have pending messages |
| US-22 | User | Search my conversations by name or content | I can find past discussions quickly |
| US-23 | User | See typing indicators in real-time | I know when someone is responding |
| US-24 | Admin/Moderator | See audit trail of entity chat actions | I can track who communicated on behalf of the org |

---

## 6. Participant Model

### 6.1 Participant Identity

Every participant in a conversation has a polymorphic identity:

| Participant Type | Identity Source | Display Name | Avatar |
|-----------------|----------------|--------------|--------|
| `user` | `User.id` | User's display_name | User's avatar |
| `business` | `BusinessAccount.id` | Business display_name | Business logo |
| `platform` | `PlatformAccount.id` | Platform display_name | Platform logo |
| `team` | `TeamAccount.id` (future) | Team display_name | Team avatar |

This is modeled as `participant_type` + `participant_id` (polymorphic FK pattern, consistent with how the transaction system models `initiator_type`/`target_type`).

### 6.2 Entity Delegation Model

When a user acts on behalf of an entity:

```
Message Record:
  conversation_id: <conv>
  participant_type: "business"       ← visible sender
  participant_id: <business-uuid>    ← visible sender identity
  acting_user_id: <user-uuid>       ← internal audit field (who actually typed this)
  content: "Thank you for your inquiry"
  created_at: 2026-03-09T12:00:00Z
```

- **Public view**: "Acme Corp" sent this message.
- **Audit view**: User alice@example.com sent this on behalf of Acme Corp.
- **Permission check**: Alice must have `can_manage_chat` on the Acme Corp business account.

### 6.3 Scope Eligibility Matrix

Before any chat action, the engine validates participant eligibility:

| Action | Global Scope | Business Scope | Platform Scope |
|--------|-------------|----------------|----------------|
| User starts DM with user | Any user on platform (subject to chat request gating if not connected, and block list check) | Both must be active members of the business (no chat request, no blocking) | Both must be active platform members (no chat request, no blocking) |
| User starts DM with entity | Entity must exist (no chat request — entities are public-facing) | N/A (no entity participation) | N/A |
| Entity starts DM with user | Acting user has chat perm (no chat request — entity bypass) | N/A | N/A |
| Entity starts DM with entity | Both acting users have chat perm | N/A | N/A |
| Create group chat | All participants meet above rules (no chat request for group invitations — see OQ-11) | All are active business members | All are active platform members |
| Send message | Is participant in conversation + not blocked by recipient | Is participant + still an active member | Is participant + still an active member |

### 6.4 Membership Lifecycle Impact

When a user's membership in an org changes, it affects their chat participation:

| Membership Change | Chat Impact |
|-------------------|-------------|
| Member **removed/leaves** business | Cannot send new messages in business scope. Existing conversations remain visible (read-only) or are hidden based on policy. |
| Member **suspended** | Cannot send messages. Conversations hidden until reactivation. |
| Member **reactivated** | Chat access restored. Can see conversation history from before suspension. |
| Member **banned** | All business-scope conversations permanently inaccessible. |
| Entity **deleted** (business closed) | All conversations in that business scope become archived/read-only. Entity's global conversations remain but entity cannot send new messages. |

---

## 7. Scope-Context Integration

### 7.1 How Scopes Map to Platform Contexts

The chat system integrates with the existing route/console structure:

| Platform Context | Chat Scope | Where User Sees It |
|-----------------|------------|-------------------|
| Personal (`/home`, `/activity`) | Global (`scope_type=global`) | User's personal chat section |
| Business Console (`/bconsole/[slug]/`) | Business (`scope_type=business`, `scope_id=<business_id>`) | Business console chat tab |
| Platform Console (`/pconsole/`) | Platform (`scope_type=platform`, `scope_id=<platform_id>`) | Platform console chat tab |
| Admin Console (`/admin/`) | N/A (no chat in admin) | — |

### 7.2 Entity Inbox Access

Entity inboxes (global-scope conversations where the entity is a participant) are accessible from:

| Entity Type | Where Inbox Lives | Who Can Access |
|-------------|------------------|----------------|
| Business | Business Console → Entity Inbox | Members with `can_manage_chat` |
| Platform | Platform Console → Entity Inbox | Members with `can_manage_chat` |
| Team (future) | Team Console → Entity Inbox | Members with appropriate permission |

The entity inbox is **separate from** the business/platform internal chat. It shows global-scope conversations where the entity is a participant.

```
Business Console Chat:
├── Internal Chat (scope=business)     ← members chatting as themselves
│   ├── DMs with colleagues
│   └── Team group chats
└── Entity Inbox (scope=global)        ← business entity's global conversations
    ├── Customer inquiries
    ├── B2B conversations
    └── Platform announcements
```

---

## 8. Key Design Distinctions

### 8.1 Chat Groups vs Teams

| Aspect | Chat Group | Team |
|--------|-----------|------|
| **What it is** | A conversation with 3+ participants | An organizational account type |
| **Lifecycle** | Created/deleted inside chat | Created via platform (like business), with RBAC |
| **Identity** | Name + participant list only | Has its own slug, profile, permissions, features |
| **RBAC** | No roles, just creator + members | Full role/permission hierarchy |
| **Scope** | Exists within a scope | Can OWN a scope (team members chat inside team scope) |
| **Features** | Messaging only | Chat + forms + transactions + whatever a team account supports |
| **Persistence** | Can be abandoned/deleted | Persists as a platform entity |

### 8.2 Scope Inheritance for Teams

Teams themselves have a parent scope (where the team was created):

```
Team "Design Squad":
  inherit = business-id (Acme Corp)
  → This team is internal to Acme Corp
  → Only Acme Corp members can be team members
  → Team's own internal chat scope is: scope_type=team, scope_id=<team-id>

Team "Open Source Contributors":
  inherit = null (global)
  → This team is platform-wide
  → Any platform user can be a team member
  → Team's own internal chat scope is: scope_type=team, scope_id=<team-id>
```

The team's parent scope (`inherit`) controls who can join the team. The team's own scope controls who can chat inside the team. These are distinct concepts.

### 8.3 Cross-Scope Conversation Independence

A critical design rule: **the same two people chatting in different scopes have entirely separate conversations.**

```
Alice and Bob:
  Global DM:    conversation_id=aaa, scope=global     → "Hey, nice meeting you at the conference!"
  Acme DM:      conversation_id=bbb, scope=business   → "Can you review the Q3 report?"
  Platform DM:  conversation_id=ccc, scope=platform    → "Moderator shift swap?"

Three separate conversations. Three separate histories. Three separate unread counts.
```

This is intentional — it preserves context boundaries. Work chat stays in the business console, personal chat stays in the personal section.

---

## 9. Dependencies

### Existing Systems Required
- **RBAC System**: Permission checks for entity chat management (`can_manage_chat`)
- **Organization System**: Business/Platform account resolution, membership validation
- **User System**: User identity, profile data (display_name, avatar)
- **Auth System**: JWT authentication for REST API, WebSocket token validation
- **Network System**: `ConnectionSelector.is_connected()` for user↔user chat request gating (connected = direct delivery, not connected = chat request). Note: `FollowSelector` is NOT used for chat request decisions — follows are User→Business/Platform only, and entities bypass chat requests entirely
- **Core Infrastructure**: Base models, exceptions, pagination, observability, audit logging
- **Notification System** (optional): Chat notifications can route through existing notification channels

### Infrastructure (Already Available)
- **WebSocket Layer**: Django Channels 4.3 + Daphne ASGI server (installed, configured, routing scaffolded)
- **WebSocket Auth**: JWT middleware for WebSocket connections (`apps/auth/middleware.py`) + `AuthenticatedConsumer` base class (`apps/auth/consumers.py`)
- **Channel Layer**: Redis-backed channel layer (`channels-redis 4.2`, configured in `CHANNEL_LAYERS`)
- **Message Broker**: Redis 7 (shared with cache + Celery, already on Docker)
- **Message Storage**: PostgreSQL (consistent with the rest of the system, sufficient for current scale)

---

## 10. Architecture Decision Record

### ADR-1: Monolith (Django app) — not a separate microservice

**Decision:** Build the chat system as `apps/chat/` inside the existing Django monolith.

**Rationale:**
1. **RBAC coupling** — Every chat action requires scope validation via `MembershipSelector`, `RBACService`, and `policies`. Direct Python imports = zero latency, transactional, type-safe. A microservice would need HTTP round-trips, duplicated logic, or event-based sync for every permission check.
2. **Infrastructure already built** — Django Channels 4.3, Daphne, Redis channel layer, JWT WebSocket middleware, and `AuthenticatedConsumer` base class are all installed and configured. A separate service would rebuild this from scratch.
3. **Membership lifecycle events** — Member removal, suspension, ban, and reactivation directly affect chat access. In the monolith this is a service-layer call or Django signal (atomic). A microservice requires an event bus with eventual consistency.
4. **Operational simplicity** — Single deployment pipeline, single test suite, single monitoring stack. No service discovery, no distributed tracing, no API versioning between services.
5. **Scale is sufficient** — Django Channels handles 5K-20K concurrent WebSocket connections with multiple Daphne workers. This platform is not a messaging-first product; chat is a supporting feature.
6. **Future extraction preserved** — The layered architecture (selectors, services, policies) and scope-based data model make future extraction straightforward if scale demands it. The monolith decision is reversible; a premature microservice is not.

**Rejected alternative:** Separate FastAPI WebSocket service. Would provide marginally better async throughput but at the cost of duplicated auth/RBAC, distributed state management, and weeks of infrastructure rebuilding.

---

## 11. Open Questions

These are decisions to be resolved during the Plan phase:

- OQ-1: **Message search** — PostgreSQL FTS (like explore system) or dedicated search (Elasticsearch/Meilisearch) for searching within message content?
- OQ-4: **Media messages** — Reuse existing media upload infrastructure or build chat-specific media handling?
- OQ-5: **Rate limiting** — Per-user message rate limits? Per-entity rate limits? Anti-spam measures?
- ~~OQ-6: **Read receipt granularity** — Resolved: watermark pattern (see Section 2.7). Per-participant `last_seen_message_id` + `last_delivered_message_id`, not per-message status.~~
- OQ-7: **Conversation archival** — How long are messages retained? Is there an archival policy?
- ~~OQ-8: **Blocking** — Resolved: see Section 2.6. Block in global scope only, silent rejection, hidden messages in groups.~~
- OQ-9: **Admin moderation** — Can platform admins view/moderate any conversation in any scope? Or only within their scope?
- OQ-10: **Offline message queue** — How are messages handled for offline users? Push notification? Deferred delivery?
- OQ-11: **Group chat invitations** — Section 2.5 says "group invitations are a separate flow" but this flow is undefined. Can a stranger add you to a group chat in global scope (bypassing chat request protection)? Should group invitations require acceptance?
- OQ-12: **Chat request accumulation** — If a sender's chat request is pending/ignored, can they send additional messages that accumulate in the pending request? Or are they limited to one message until accepted?
- OQ-13: **Chat request expiration** — Do pending chat requests expire after a period? Or do they persist indefinitely?
- OQ-14: **Chat notifications** — Should new messages and chat requests trigger notifications via the existing Notification System? What notification types are needed (new_message, chat_request_received, message_request_accepted)?
- OQ-15: **Group chat administration** — Section 2.4 mentions "members with appropriate rights" can add/remove participants. Is there a group admin role, or only the creator? Can admin rights be transferred?

---

## 12. Acceptance Criteria

### Scope Isolation
- [ ] Conversations in business scope are invisible from global scope and vice versa
- [ ] Users can only participate in business-scope conversations if they are active members
- [ ] Users can only participate in platform-scope conversations if they are platform members
- [ ] Removing a member from a business prevents them from sending new messages in business scope
- [ ] No API endpoint returns conversations from a different scope than requested

### Conversation Management
- [ ] Users can create 1:1 DM conversations within their scope
- [ ] Users can create group conversations with 3+ participants within their scope
- [ ] Group chat supports add/remove participants (within scope eligibility)
- [ ] Conversation list returns conversations ordered by last activity
- [ ] Unread count is accurate per conversation and per scope

### Entity Participation (Global Scope)
- [ ] Business accounts can send/receive messages in global scope
- [ ] Only members with `can_manage_chat` can act on behalf of the entity
- [ ] Messages sent by entity show entity name/avatar (not the acting user)
- [ ] Audit trail records which user performed each entity action
- [ ] Entity-to-entity conversations work (business ↔ business, business ↔ platform)

### Real-Time
- [ ] New messages appear instantly for online participants (< 200ms)
- [ ] Typing indicators display correctly for active participants
- [ ] Read receipts update in real-time
- [ ] Online/offline presence is visible within scope

### Chat Requests
- [ ] First DM to a non-connected user creates a chat request (not direct delivery)
- [ ] Connected users bypass chat requests entirely
- [ ] Chat requests appear in a separate "Message Requests" section for the recipient
- [ ] Accepting a request moves the conversation to main inbox and enables direct messaging
- [ ] Ignoring a request hides it from the UI but does not block future requests
- [ ] Blocking from a request adds the sender to the block list
- [ ] Mutual intent (recipient messages requester first) auto-accepts the pending request
- [ ] Entity accounts (businesses/platforms) bypass chat requests — always direct delivery
- [ ] Chat requests do not apply in org scopes (business/platform internal)

### Block System
- [ ] Blocking a user silently prevents all future DMs from them in global scope
- [ ] Blocked user sees their messages as "sent" (no indication of being blocked)
- [ ] Block list is viewable and manageable (unblock restores messaging ability)
- [ ] Blocked user's messages are hidden in existing DMs and group chats for the blocker
- [ ] Blocking is not available in org scopes
- [ ] Unblocking does not re-deliver previously blocked messages

### Delivery & Read Status
- [ ] Messages transition through sent → delivered → seen states correctly
- [ ] Delivered status is set when recipient's client acknowledges receipt
- [ ] Seen status is set when recipient opens the conversation (watermark pattern)
- [ ] Status updates are pushed in real-time to the sender via WebSocket
- [ ] Status updates are batched (one event per conversation, not per message)
- [ ] Group chats show per-participant seen status with aggregate display
- [ ] Offline users receive delivered status when they reconnect and receive pending messages

### Messages
- [ ] Text messages send and display correctly
- [ ] Messages can be edited within the configured time window
- [ ] Deleted messages show "message deleted" placeholder
- [ ] Message history loads with cursor-based pagination
- [ ] Messages persist durably before delivery acknowledgment

---

## Appendix A: Terminology

| Term | Definition |
|------|-----------|
| **Scope** | An isolation boundary for conversations, defined by `scope_type` + `scope_id` |
| **Global scope** | Platform-wide scope (`scope_id=null`), where all users and entities can participate |
| **Org scope** | Business, platform, or team scope — limited to members of that organization |
| **Entity account** | A business, platform, or team account acting as a participant in global chat |
| **Entity delegation** | A user performing chat actions on behalf of an entity account |
| **Acting user** | The real human behind an entity action (recorded in audit trail) |
| **Chat group** | A conversation with 3+ participants (exists only within chat, not an org unit) |
| **Team** | An organizational account type (separate from chat groups) with its own scope, RBAC, and features |
| **Participant** | A user or entity that is part of a conversation |
| **Conversation** | A DM or group chat — the container for messages between participants |
| **Inbox** | The list of conversations for a participant (user or entity) within a scope |
| **Chat request** | A pending first message from a non-connected user, requiring recipient acceptance before conversation is established (user↔user DMs in global scope only) |
| **Message requests** | The UI section showing pending chat requests, separate from the main inbox |
| **Block list** | Per-user list of blocked participants; blocked users' messages are silently rejected |
| **Watermark** | Per-participant pointer to the last delivered/seen message in a conversation; avoids per-message status tracking |
| **Delivered** | Message reached the recipient's client (client acknowledgment via WebSocket) |
| **Seen** | Recipient opened/viewed the conversation containing the message |
