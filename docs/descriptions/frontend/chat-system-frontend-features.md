# Chat System — Frontend Features & UX Comprehensive Checklist

**Version:** v1
**Created:** 2026-03-20
**Backend Reference:** `docs/implementations/backend/chat-system.md`
**Backend Plan:** `docs/plans/backend/chat_system/chat_system_plan.md`

---

## Table of Contents

1. [Scope Context & Navigation](#1-scope-context--navigation)
2. [Conversation List](#2-conversation-list)
3. [Conversation Detail / Chat Window](#3-conversation-detail--chat-window)
4. [Message Composition & Sending](#4-message-composition--sending)
5. [Message Display & Formatting](#5-message-display--formatting)
6. [Message Actions (Edit / Delete)](#6-message-actions-edit--delete)
7. [Image Attachments](#7-image-attachments)
8. [Emoji Reactions](#8-emoji-reactions)
9. [Chat Requests (Global Scope DMs)](#9-chat-requests-global-scope-dms)
10. [Blocking](#10-blocking)
11. [Group Chat Management](#11-group-chat-management)
12. [Entity Chat (Business/Platform as Participants)](#12-entity-chat-businessplatform-as-participants)
13. [Typing Indicators](#13-typing-indicators)
14. [Read Receipts & Watermarks](#14-read-receipts--watermarks)
15. [Presence (Online/Offline Status)](#15-presence-onlineoffline-status)
16. [Unread Counts & Badges](#16-unread-counts--badges)
17. [Message Search](#17-message-search)
18. [Notifications](#18-notifications)
19. [WebSocket Connection Management](#19-websocket-connection-management)
20. [State Management Architecture](#20-state-management-architecture)
21. [TypeScript Types](#21-typescript-types)
22. [API Client Layer](#22-api-client-layer)
23. [Error Handling & Edge Cases](#23-error-handling--edge-cases)
24. [Performance & Optimization](#24-performance--optimization)
25. [Accessibility](#25-accessibility)
26. [Responsive / Mobile Considerations](#26-responsive--mobile-considerations)

---

## 1. Scope Context & Navigation

### Backend Support
- Conversations are scoped by `scope_type` (global | business | platform) + `scope_id`
- All list/query endpoints accept `scope_type` and `scope_id` query params
- Each scope is completely isolated — no cross-scope visibility

### Frontend Requirements

- [ ] **Scope context selector**: When user navigates to chat, determine scope from route context:
  - Global chat: `/chat/` — `scope_type=global`, `scope_id=null`
  - Business chat: `/business/{slug}/chat/` — `scope_type=business`, `scope_id={business_id}`
  - Platform chat: `/platform/chat/` — `scope_type=platform`, `scope_id={platform_id}`
- [ ] **Scope indicator badge**: Show current scope context in chat header (e.g., "Global", business name, platform name)
- [ ] **Cross-scope separation**: User may have DMs with same person in global AND in a business — these are different conversations
- [ ] **Scope-aware new chat flow**: When starting a new conversation, auto-fill scope from current context

### Business Rules
- Business scope: only visible to active members of that business
- Platform scope: only visible to active platform members
- Global scope: any authenticated user

---

## 2. Conversation List

### Endpoints
| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/api/v1/chat/conversations/?scope_type=X&scope_id=Y` | List conversations (paginated) |
| POST | `/api/v1/chat/conversations/` | Create new conversation |

### Response Shape (per conversation)
```typescript
{
  id: string;                    // UUID
  scope_type: "global" | "business" | "platform";
  scope_id: string | null;
  conversation_type: "direct" | "group";
  name: string;                  // Group name or empty for DMs
  last_message: {
    id: string;
    sender_type: string;
    sender_id: string;