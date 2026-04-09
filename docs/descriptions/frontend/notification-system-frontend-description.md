# Notification System — Frontend High-Level Description

**Version:** v2
**Date:** 2026-03-29
**Status:** Pre-Planning
**Backend Reference:** `backend/apps/notifications/CLAUDE.md`
**Backend Implementation:** 27 notification types, 5 API endpoints, org scope, RBAC, Tier 1.5, Feature Gate (SG/FG/VG)

---

## 1. Vision

The Notification System provides a centralized notification center for the entire platform. Users see notifications from all contexts — personal account activity, business operations, platform events — in one unified experience with scope-based filtering. The system supports real-time delivery, user-controlled preferences per channel and per org, and permission-aware UI gating via Tier 1.5.

**UI Reference:** Instagram notifications (bell icon → dropdown → full page) — but extended with organizational scoping, scope-based tabs/filters, and granular channel preferences.

---

## 2. The Three Notification Scopes

Every notification carries a `scope_type` and `scope_id`. This determines which context it belongs to and enables frontend filtering.

```
Scope Type       scope_id          Source Examples                           Where User Sees It
──────────────   ─────────────     ─────────────────────────────────────     ──────────────────────
user             null              Login alerts, password changes,           Personal tab (always)
                                   welcome, verification, follow/connect
business         <business_uuid>   Transaction approvals, invitations,       Business tab (filtered)
                                   business-scoped chat messages
platform         <platform_uuid>   Platform transaction approvals,           Platform tab (filtered)
                                   platform-scoped chat messages
```

### 2.1 User Scope — Personal Notifications

Notifications about the user's own account and personal social activity. These have `scope_type="user"`, `scope_id=null` and are always visible regardless of org membership.

**Types:** verify_email, welcome, password_reset, password_changed, new_login, suspicious_activity, newsletter, promotions, new_follower, follow_request_*, connection_request_*, connection_accepted, global-scope chat notifications.

**Key behavior:**
- Always visible — no membership check needed
- Cannot be filtered out by org scope
- Includes social notifications (follows, connections) that are inherently personal

### 2.2 Business Scope — Organization Notifications

Notifications related to a specific business the user is a member of. These have `scope_type="business"`, `scope_id=<business_uuid>`.

**Types:** transaction_invitation_received, transaction_accepted/denied/cancelled/expired, transaction_pending_approval, transaction_info_requested, business-scoped chat notifications.

**Key behaviors:**
- Only visible to users who are active members of that business
- If user loses business membership, they keep historical notifications (no disappearing)
- New notifications stop arriving after membership ends (RBAC gating at send time)
- Frontend can filter "show me only Business X notifications" using scope_type+scope_id params
- Tier 1.5 `_permissions` available when filtering by business scope

### 2.3 Platform Scope — Platform Admin Notifications

Same pattern as business scope but for the platform account. `scope_type="platform"`, `scope_id=<platform_uuid>`.

**Types:** Platform-authority transaction approvals, platform-scoped chat notifications.

---

## 3. Notification Center — UI Structure

### 3.1 Notification Bell (Topbar)

The notification bell is the primary entry point, placed in the Topbar between the spacer and UserMenu.

**Location:** `frontend/src/components/navigation/Topbar.tsx` — authenticated variant, line 33 (`<div className="flex-1" />` before `<UserMenu />`).

**Behavior:**
- Bell icon (lucide `Bell`) with unread count badge
- Badge shows total unread across all scopes
- Badge hidden when count is 0
- Click opens notification popover/dropdown (desktop) or navigates to `/notifications` (mobile)

**Unread Count Source:**
- REST polling via `GET /api/v1/notifications/scopes/` — returns counts per scope
- Future: WebSocket push for real-time count updates
- Zustand store holds the count for reactive rendering across nav components

### 3.2 Notification Dropdown (Desktop Quick View)

A popover/dropdown anchored to the bell icon showing the latest notifications.

**Behavior:**
- Shows the 5–10 most recent notifications across all scopes
- Each item: icon/badge for scope, notification type icon, message preview, relative timestamp
- "View All" link at bottom navigates to `/notifications`
- Scope badge on each item: personal (no badge), business (business icon/name), platform (platform icon)

### 3.3 Notification Page (Full View)

**Route:** `/(app)/(user)/notifications/`
**Current state:** Placeholder page at `frontend/src/app/(app)/(user)/notifications/page.tsx`

**Layout:**
- Scope tabs or filter bar at top: "All" | "Personal" | "Business Name" | "Platform"
  - Tab list populated from `GET /api/v1/notifications/scopes/` — only shows scopes with notifications
  - Each tab shows its count badge
- Notification list below tabs — paginated with offset/limit
- Each notification item is a card/row with: type icon, title, body preview, relative timestamp, scope badge
- Empty state: "No notifications yet" with illustration

**Filters:**
- Scope filter (tabs described above)
- Optional: notification type filter (transaction, chat, social, etc.)
- Optional: status filter (for delivery status — usually hidden from users)

### 3.4 Notification Item Component

Each notification renders based on its `notification_type` and `scope_type`:

**Required fields from API:**
- `id` (UUID)
- `notification_type` (string — maps to display config)
- `scope_type` ("user" | "business" | "platform")
- `scope_id` (UUID | null)
- `channels` (array — which channels were used)
- `status` (delivery status)
- `channel_results` (per-channel delivery details)
- `created_at` (ISO timestamp)

**Display mapping for all 27 types** (frontend config, not from API):

| notification_type | Icon (lucide) | Title Template | Context Keys |
|---|---|---|---|
| **AUTH** | | | |
| verify_email | Mail | "Verify your email" | verification_link, code |
| welcome | PartyPopper | "Welcome to the platform!" | (none) |
| password_reset | KeyRound | "Password reset requested" | reset_link |
| **SECURITY** | | | |
| password_changed | Lock | "Password changed" | (none) |
| new_login | Shield | "New login from {device}" | device, location, time |
| suspicious_activity | ShieldAlert | "Suspicious activity detected" | activity_type, details |
| **MARKETING** | | | |
| newsletter | Newspaper | "New newsletter" | content |
| promotions | Tag | "Special offer: {offer_title}" | offer_title, offer_details |
| **TRANSACTIONAL** | | | |
| transaction_pending_approval | ClipboardCheck | "New request needs your review" | transaction_id, transaction_type |
| transaction_invitation_received | UserPlus | "You received an invitation" | transaction_id, transaction_type |
| transaction_accepted | CheckCircle | "Your request was accepted" | transaction_id, transaction_type |
| transaction_denied | XCircle | "Your request was denied" | transaction_id, reason |
| transaction_cancelled | Ban | "Transaction cancelled" | transaction_id, transaction_type |
| transaction_expired | Timer | "Transaction expired" | transaction_id, transaction_type |
| transaction_expiring_soon | Clock | "Request expiring soon" | transaction_id, expires_at |
| transaction_info_requested | HelpCircle | "More information requested" | transaction_id, message |
| transaction_resubmitted | RefreshCw | "Request updated" | transaction_id |
| **SOCIAL (Network)** | | | |
| new_follower | UserPlus | "New follower" | follower_id, followee_type, followee_id |
| follow_request_received | UserCheck | "Follow request received" | transaction_id, follower_id, followee_type, followee_id |
| follow_request_accepted | UserCheck2 | "Follow request accepted" | followee_type, followee_id |
| connection_request_received | Users | "Connection request" | transaction_id, requester_id |
| connection_accepted | Handshake | "Connection accepted" | connection_id, other_user_id |
| **SOCIAL (Chat)** | | | |
| chat_message_received | MessageSquare | "New message from {sender_name}" | conversation_id, sender_name, preview |
| chat_request_received | MessageCircle | "Chat request from {requester_name}" | conversation_id, requester_name, preview |
| chat_request_accepted | MessageSquareCheck | "Chat request accepted" | conversation_id, accepter_name |
| chat_group_added | UsersRound | "Added to {group_name}" | conversation_id, group_name, added_by_name |
| chat_reaction_received | Heart | "Reaction on your message" | conversation_id, reactor_name, message_preview |

**Context key source:** Each notification's `context` dict (stored as JSON on `NotificationLog.context`) contains the keys listed above. The frontend display config maps `notification_type` to icon + title template. Title templates use `{variable}` placeholders filled from context.

---

## 4. Notification Preferences — Settings UI

### 4.1 Where Preferences Live

Notification preferences are accessible from:
1. **User Settings** — global defaults for all notification types
2. **Business Settings** — per-business overrides (optional, only if user wants different settings for a specific business)
3. **Platform Settings** — per-platform overrides (same pattern)

### 4.2 Preferences Page Structure

**Data source:** `GET /api/v1/notifications/preferences/` — returns all types grouped by category

**Layout:**
- Grouped by category: Security, Transactional, Social, Marketing
- Each notification type shows:
  - Display name and description
  - Three channel toggles: Email (Switch), Push (Switch), SMS (Switch)
  - Disabled/locked indicator for non-configurable types (verify_email, password_reset, etc.)
- Save is per-toggle (PATCH on change), not a global save button

**API calls per toggle change:**
- `PATCH /api/v1/notifications/preferences/{notification_type}/` with `{ "email_enabled": false }`
- Optimistic update in UI, revert on error

**Reset to defaults:**
- "Reset" link per notification type
- `DELETE /api/v1/notifications/preferences/{notification_type}/`
- UI reverts to showing type default values

### 4.3 Scoped Preferences (Per-Org Overrides)

When viewing preferences within a business or platform console, users can override their global settings for that specific org.

**UX flow:**
1. User goes to Business X Settings → Notifications section
2. Sees the same preference grid but with an extra indicator: "Default" or "Custom"
3. Toggling a channel creates/updates a scoped preference for that business
4. A "Reset to global default" option reverts the scoped override

**Backend:** Same PATCH endpoint but the frontend could track scope context. The backend `PreferenceService.get_enabled_channels()` resolves: scoped preference → global preference → type default.

### 4.4 Non-Configurable Types

Some notification types cannot be disabled by users (security-critical). The API returns `user_configurable: false` for these. The frontend should:
- Show them in the list (for transparency)
- Disable all channel toggles (greyed out Switches)
- Show a lock icon or tooltip: "This notification cannot be disabled for security reasons"

Types: verify_email, welcome, password_reset, password_changed, suspicious_activity.

---

## 5. Tier 1.5 — Permission-Aware UI Gating

When the history endpoint is called with `scope_type` + `scope_id`, the response includes `_permissions`:

```json
{
  "notifications": [...],
  "count": 5,
  "_permissions": {
    "can_view_notifications": true,
    "can_manage_preferences": true,
    "can_manage_org_notifications": false
  }
}
```

**Frontend uses:**
- `can_view_notifications` — should always be true if response is non-empty (non-members get empty list)
- `can_manage_preferences` — show/hide the "Notification Settings" link for this org
- `can_manage_org_notifications` — future: show/hide admin features (send announcements, manage org notification rules). Requires `can_manage_notifications` RBAC permission.

**When `_permissions` is NOT present** (no scope_id in request):
- User is viewing their personal/all notifications
- No org-level permissions apply
- All user-level actions (mark read, dismiss) are always available

---

## 6. Feature Gate Degradation

The notification system is fully integrated with the backend Feature Gate system. The frontend MUST handle disabled states gracefully.

### 6.1 System Gate OFF (`systems.notifications: false`)

When the entire notification system is disabled at deployment level:
- ALL 5 notification API endpoints return **404 Not Found**
- Celery tasks silently skip (no notifications dispatched)
- Admin panels hidden

**Frontend behavior when SG is off:**
- API calls to `/api/v1/notifications/*` return 404
- `ApiError.isNotFound` will be `true`
- The frontend should detect this and:
  - **Hide the notification bell** in Topbar (don't render `NotificationBell` if scopes query returns 404)
  - **Hide notification nav items** in sidebar and bottom nav
  - **Show "Notifications unavailable"** on the `/notifications` page instead of crashing
  - **Disable preference UI** in settings
- Use a `useNotificationsAvailable()` hook that returns `false` when scopes endpoint returns 404
- The hook caches the result — don't retry on every render

### 6.2 Feature Gate OFF (`user.notifications.enabled: false`)

When notifications feature is disabled but system is still running:
- API endpoints still respond (no 404)
- Backend `send()` returns `None` for configurable types — fewer notifications arrive
- Mandatory types (verify_email, password_reset, etc.) STILL arrive regardless of FG state
- History endpoint still returns existing notifications

**Frontend behavior when FG is off:**
- No special handling needed — the frontend just sees fewer notifications
- Preferences UI still works (user can still toggle channels)
- Existing notifications still visible in history

### 6.3 Feature Gate Detection Pattern

```typescript
// Hook pattern for detecting notification system availability
function useNotificationsAvailable(): boolean {
  const { isError, error } = useNotificationScopes();
  if (isError && error instanceof ApiError && error.isNotFound) {
    return false; // SG is off — system disabled
  }
  return true;
}
```

Use this hook in:
- `NotificationBell` — don't render if unavailable
- Navigation items — hide badge if unavailable
- Notification page — show fallback UI if unavailable

---

## 7. Backend API Reference

### 7.1 Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/notifications/preferences/` | GET | All preferences grouped by category |
| `/api/v1/notifications/preferences/{type}/` | GET | Single preference detail |
| `/api/v1/notifications/preferences/{type}/` | PATCH | Update channel toggles |
| `/api/v1/notifications/preferences/{type}/` | DELETE | Reset to defaults |
| `/api/v1/notifications/history/` | GET | Notification list with filtering |
| `/api/v1/notifications/scopes/` | GET | Scope summary with counts |
| `/api/v1/notifications/types/` | GET | Configurable notification types |

### 7.2 History Query Parameters

| Param | Type | Default | Description |
|---|---|---|---|
| `notification_type` | string | — | Filter by type name |
| `status` | string | — | Filter by delivery status |
| `limit` | int | 50 | Max results (1–100) |
| `offset` | int | 0 | Skip N results |
| `scope_type` | string | — | Filter by scope (user, business, platform) |
| `scope_id` | UUID | — | Filter by org UUID |

### 7.3 History Response Shape

```typescript
{
  notifications: Array<{
    id: string;                    // UUID
    notification_type: string;     // e.g., "transaction_accepted"
    scope_type: "user" | "business" | "platform";
    scope_id: string | null;       // UUID or null
    channels: string[];            // ["email", "push"]
    status: "pending" | "sent" | "partial" | "failed" | "processing" | "retrying";
    channel_results: Record<string, { status: string; error?: string }>;
    created_at: string;            // ISO 8601
  }>;
  count: number;
  _permissions?: {                 // Only when scope_id provided
    can_view_notifications: boolean;
    can_manage_preferences: boolean;
    can_manage_org_notifications: boolean;
  };
}

// NOTE: The `context` field is stored on the NotificationLog model (JSONField)
// but is NOT included in the NotificationLogSerializer response.
// Context data (transaction_id, conversation_id, etc.) is only available
// in the backend. The frontend must derive display titles and action links
// from `notification_type` alone, or context must be added to the serializer
// in a future backend update.
```

**Important limitation:** The current `NotificationLogSerializer` does NOT include the `context` field in its response. This means:
- The frontend cannot read `transaction_id`, `conversation_id`, `sender_name`, etc. from the API response
- Display titles that reference context variables (e.g., "New message from {sender_name}") cannot be fully rendered
- Action links that require context IDs (e.g., `/transactions/{transaction_id}`) cannot be built

**Resolution options (requires backend change):**
1. Add `context` to `NotificationLogSerializer.Meta.fields` (simple, exposes raw context dict)
2. Add computed fields to serializer (e.g., `title`, `action_url`) that render on the backend
3. Hybrid: add `context` field but also add `display_title` and `action_url` computed fields
```

### 7.4 Scopes Response Shape

```typescript
{
  scopes: Array<{
    scope_type: "user" | "business" | "platform";
    scope_id: string | null;
    count: number;
  }>;
  count: number;
}
```

### 7.5 Preferences Response Shape

```typescript
// GET /preferences/ — grouped by category
{
  auth: Array<PreferenceItem>;
  security: Array<PreferenceItem>;
  transactional: Array<PreferenceItem>;
  marketing: Array<PreferenceItem>;
  social: Array<PreferenceItem>;
}

// PreferenceItem
{
  notification_type: string;
  display_name: string;
  description: string;
  category: string;
  user_configurable: boolean;
  email_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
}
```

### 7.6 Notification Types (27 total)

| Category | Types | Org-Scoped? |
|---|---|---|
| AUTH (3) | verify_email, welcome, password_reset | No (user-scoped) |
| SECURITY (3) | password_changed, new_login, suspicious_activity | No (user-scoped) |
| MARKETING (2) | newsletter, promotions | No (user-scoped) |
| TRANSACTIONAL (9) | transaction_invitation_received, _accepted, _denied, _cancelled, _expired, _expiring_soon, _info_requested, _resubmitted, _pending_approval | Yes (business/platform) |
| SOCIAL (5 network) | new_follower, follow_request_received, follow_request_accepted, connection_request_received, connection_accepted | No (user-scoped) |
| SOCIAL (5 chat) | chat_message_received, chat_request_received, chat_request_accepted, chat_group_added, chat_reaction_received | Depends on conversation scope |

**Note:** All 10 social types share category value `"social"` from the API. The network/chat grouping above is for readability only — the frontend preferences panel will show them together under one "Social" section.

---

## 8. State Management Architecture

### 8.1 What Goes Where

| Data | Location | Reason |
|---|---|---|
| Notification list | TanStack Query cache | Server state, paginated, filterable |
| Preferences | TanStack Query cache | Server state, CRUD via mutations |
| Configurable types | TanStack Query cache | Server state, rarely changes |
| Unread counts per scope | Zustand store | Needs to be reactive across nav components (bell, sidebar, bottom nav), updated by WS |
| Active scope filter | URL query params | Shareable, bookmarkable, survives refresh |
| Dropdown open state | Local component state | UI-only, no persistence needed |

### 8.2 Zustand Store — `stores/notification-store.ts`

```typescript
interface NotificationState {
  // Unread counts by scope (key = "user" or "business:<uuid>" or "platform:<uuid>")
  unreadCounts: Record<string, number>;
  totalUnread: number;
}

interface NotificationActions {
  setUnreadCounts: (counts: Record<string, number>) => void;
  incrementUnread: (scopeKey: string) => void;
  decrementUnread: (scopeKey: string) => void;
  clearUnread: (scopeKey: string) => void;
}
```

**Why Zustand and not just TQ?** The unread count must be reactive in the Topbar bell (always mounted), sidebar nav badge, and bottom nav badge — all outside the notification feature's component tree. Zustand provides cross-tree reactivity. TQ cache is per-query and doesn't broadcast changes to unrelated components.

### 8.3 Query Keys — `lib/query-keys.ts`

Expand the existing minimal keys:

```typescript
notifications: {
  all: ["notifications"] as const,
  history: (params?: Record<string, unknown>) =>
    [...queryKeys.notifications.all, "history", params] as const,
  scopes: () => [...queryKeys.notifications.all, "scopes"] as const,
  preferences: () => [...queryKeys.notifications.all, "preferences"] as const,
  preference: (type: string) =>
    [...queryKeys.notifications.all, "preferences", type] as const,
  types: () => [...queryKeys.notifications.all, "types"] as const,
},
```

---

## 9. Feature Module Structure

Following the established pattern from chat, transactions, and other features:

```
frontend/src/features/notifications/
├── api/
│   └── notifications-api.ts          # All REST endpoint functions
├── hooks/
│   ├── use-notification-queries.ts   # TQ query hooks (history, scopes, preferences)
│   ├── use-notification-mutations.ts # TQ mutation hooks (update/reset preference)
│   └── use-unread-badge.ts           # Unread count hook (Zustand + REST fallback)
├── components/
│   ├── NotificationBell.tsx           # Bell icon + badge + dropdown trigger
│   ├── NotificationDropdown.tsx       # Quick-view popover content
│   ├── NotificationList.tsx           # Full page list with scope tabs
│   ├── NotificationItem.tsx           # Single notification card/row
│   ├── NotificationScopeTabs.tsx      # Scope filter tabs with badges
│   ├── NotificationEmptyState.tsx     # Empty state illustration
│   ├── PreferencesPanel.tsx           # Channel toggle grid
│   └── PreferenceRow.tsx              # Single type with 3 switches
├── constants/
│   └── notification-constants.ts     # Display config, icon mapping, limits
├── types.ts                          # All TypeScript types
└── __tests__/                        # Tests for all components and hooks
```

**Zustand store lives in:** `frontend/src/stores/notification-store.ts` (app-wide, not feature-scoped — same pattern as chat-store.ts and auth-store.ts).

---

## 10. Responsive Design

### Desktop (md+)
- Bell icon in Topbar → click opens Popover dropdown
- Full notification page has sidebar scope filters + main list

### Mobile (<md)
- Bell icon in BottomNavbar ("Alerts" label) → navigates to `/notifications`
- No dropdown — direct navigation to full page
- Scope tabs are horizontal scroll
- Notification items are full-width cards

---

## 11. Current Frontend State (What Already Exists)

| Component | Status | Location |
|---|---|---|
| Navigation item (sidebar) | Wired | `lib/navigation-config.ts` — Bell icon, `/notifications` |
| Navigation item (mobile) | Wired | `components/navigation/BottomNavbar.tsx` — "Alerts", Bell |
| Query keys | Minimal | `lib/query-keys.ts` — `.preferences()`, `.history()` only |
| Notifications page | Placeholder | `app/(app)/(user)/notifications/page.tsx` — "Coming soon" |
| Topbar bell icon | Missing | `components/navigation/Topbar.tsx` — no bell, just logo + UserMenu |
| Feature module | Missing | No `features/notifications/` directory |
| Zustand store | Missing | No `stores/notification-store.ts` |
| API functions | Missing | No API client for notification endpoints |
| Types | Missing | No notification TypeScript types |
| Preference UI | Missing | No settings integration |
| Toast integration | Ready | `sonner` globally available via `Providers.tsx` |
| WebSocket client | Ready | `lib/ws-client.ts` — generic, reusable |
| shadcn components | Ready | Badge, Popover, Switch, Card, Tabs, Skeleton, ScrollArea, Sheet |

---

## 12. Key Design Decisions

### 12.1 No In-App Notification Model

The backend `NotificationLog` is a **delivery audit log**, not an inbox model. It tracks what was sent and delivery status per channel. There is no `is_read`, `read_at`, `title`, `message` field. This means:

- The frontend notification list shows **delivery events**, not rich notification messages
- Notification titles and bodies are **computed on the frontend** from `notification_type` + `context`
- There is no "mark as read" API (this would require a backend model extension)
- The "unread count" is derived from the scopes endpoint counts, not from a read/unread field

**Implication for future:** If we need full inbox functionality (mark as read, dismiss, archive), the backend needs a new `Notification` model or `is_read`/`read_at` fields on `NotificationLog`.

### 12.2 RBAC Gating at Send Time

Notifications are gated at send time (who receives them), not at read time (who can see stored ones). This means:
- If a user was a business manager and received approval notifications, then gets demoted, they keep those notifications
- New approval notifications simply stop arriving (the demoted user no longer has the permission)
- The frontend does NOT need to filter out "unauthorized" notifications — if it's in the user's history, they can see it

### 12.3 Scope Filtering via Query Params

The scope filter uses URL query params (`?scope_type=business&scope_id=<uuid>`) rather than separate endpoints. This means:
- The notification page URL is shareable and bookmarkable
- Changing scope tabs updates the URL, which triggers a new TQ query
- Back/forward browser navigation works correctly with scope changes

---

## 13. Integration Points

### 13.1 Topbar Integration
Add `NotificationBell` component between `<div className="flex-1" />` and `<UserMenu />` in `Topbar.tsx` authenticated variant.

### 13.2 Settings Integration
Add `NotificationPreferencesPanel` as a section in the existing `SettingsPage` component (user settings). For business/platform settings, add a "Notifications" section to business/platform settings pages.

### 13.3 Navigation Badge Integration
Both sidebar and bottom nav notification items should show the unread count badge. Read from `useNotificationStore` (Zustand).

### 13.4 Deep Linking
Notification items that reference transactions, chat conversations, or profiles should link to those resources. The `context` field in the notification contains the relevant IDs.

---

## 14. Performance Considerations

- **Scope counts polling:** `GET /scopes/` should be polled on a reasonable interval (60s) or updated via WebSocket. Don't poll on every render.
- **History pagination:** Use offset/limit with "Load More" button, NOT infinite scroll (notification lists are bounded, not infinite like chat messages).
- **Preference mutations:** Optimistic updates on switch toggles — don't wait for server response to update UI.
- **Memoization:** Notification item components should be `React.memo()` — the list re-renders when new items arrive but most items are unchanged.
- **Skeleton loading:** Show skeleton cards while history query is loading (not a spinner).
