# Notification System — Frontend Features & Developer Checklist

**Version:** v2
**Date:** 2026-03-29
**Backend Reference:** `backend/apps/notifications/CLAUDE.md`
**Frontend Description:** `docs/descriptions/frontend/notification-system-frontend-description.md`

---

## Table of Contents

1. [Types & API Layer](#1-types--api-layer)
2. [Query Keys & Hooks](#2-query-keys--hooks)
3. [Zustand Store](#3-zustand-store)
4. [Notification Bell & Badge](#4-notification-bell--badge)
5. [Notification Dropdown](#5-notification-dropdown)
6. [Notification Page](#6-notification-page)
7. [Notification Item Component](#7-notification-item-component)
8. [Scope Tabs & Filtering](#8-scope-tabs--filtering)
9. [Notification Preferences UI](#9-notification-preferences-ui)
10. [Navigation Integration](#10-navigation-integration)
11. [Display Config & Constants](#11-display-config--constants)
12. [Feature Gate Degradation](#12-feature-gate-degradation)
13. [Error Handling & Edge Cases](#13-error-handling--edge-cases)
14. [Accessibility](#14-accessibility)
15. [Responsive / Mobile](#15-responsive--mobile)
16. [Testing](#16-testing)

---

## 1. Types & API Layer

### Backend Support
- 5 REST endpoints under `/api/v1/notifications/`
- All require `IsAuthenticated`
- History endpoint supports scope filtering and Tier 1.5 `_permissions` injection

### Frontend Requirements

- [ ] **Create `features/notifications/types.ts`** with:
  - `NotificationScope` type: `"user" | "business" | "platform"`
  - `NotificationStatus` type: `"pending" | "sent" | "partial" | "failed" | "processing" | "retrying"`
  - `NotificationLogItem` type matching history response shape
  - `NotificationHistoryResponse` type with `notifications`, `count`, optional `_permissions`
  - `NotificationHistoryParams` type with all query params
  - `NotificationScopeItem` type: `{ scope_type, scope_id, count }`
  - `NotificationScopesResponse` type
  - `NotificationPreferenceItem` type with all preference fields
  - `NotificationPreferencesResponse` type (dict keyed by category)
  - `NotificationPreferenceUpdate` input type
  - `ConfigurableNotificationType` type
  - `NotificationPermissions` type: `{ can_view_notifications, can_manage_preferences, can_manage_org_notifications }`
  - `NotificationHistoryWithPerms` composed type using `WithPermissions<NotificationPermissions>`

- [ ] **Create `features/notifications/api/notifications-api.ts`** with:
  - `fetchNotificationHistoryApi(params?: NotificationHistoryParams)` → `NotificationHistoryResponse`
  - `fetchNotificationScopesApi()` → `NotificationScopesResponse`
  - `fetchNotificationPreferencesApi()` → `NotificationPreferencesResponse`
  - `fetchNotificationPreferenceApi(type: string)` → `NotificationPreferenceItem`
  - `updateNotificationPreferenceApi(type: string, data: NotificationPreferenceUpdate)` → `NotificationPreferenceItem`
  - `resetNotificationPreferenceApi(type: string)` → `void`
  - `fetchConfigurableTypesApi()` → `{ types: ConfigurableNotificationType[]; count: number }`

### Business Rules
- All API functions use `apiClient` from `@/lib/api-client`
- Return `response.data` (not the raw Axios response)
- Type all inputs and outputs explicitly
- Handle 404 responses for SG-off state (notification system disabled at deployment level)

### Known Limitation: Missing `context` Field
- The current `NotificationLogSerializer` does NOT include the `context` field
- This means context keys (transaction_id, conversation_id, sender_name, etc.) are NOT in the API response
- **Impact:** display titles with `{variables}` and action links requiring context IDs cannot be fully rendered
- **Prerequisite backend change:** add `context` to `NotificationLogSerializer.Meta.fields` before implementing display config titles and action links

---

## 2. Query Keys & Hooks

### Backend Support
- History: paginated with offset/limit, filterable by scope, type, status
- Scopes: aggregated counts per scope
- Preferences: CRUD per notification type

### Frontend Requirements

- [ ] **Expand `lib/query-keys.ts`** notification section:
  ```
  notifications.all → base key
  notifications.history(params) → history list with filters
  notifications.scopes() → scope summary
  notifications.preferences() → all preferences
  notifications.preference(type) → single preference
  notifications.types() → configurable types
  ```

- [ ] **Create `features/notifications/hooks/use-notification-queries.ts`**:
  - `useNotificationHistory(params?)` — `useQuery` with history key + params
  - `useNotificationScopes()` — `useQuery` for scope summary (staleTime: 60s)
  - `useNotificationPreferences()` — `useQuery` for all preferences grouped by category
  - `useConfigurableTypes()` — `useQuery` for type list (staleTime: 5min, rarely changes)

- [ ] **Create `features/notifications/hooks/use-notification-mutations.ts`**:
  - `useUpdatePreference(type: string)` — `useMutation`, invalidates preferences key on success
  - `useResetPreference(type: string)` — `useMutation`, invalidates preferences key on success

### Business Rules
- History query should include scope params from URL query params
- Preferences query should be refetched when scope changes (if scoped preferences are in use)
- Optimistic updates on preference toggle mutations

---

## 3. Zustand Store

### Backend Support
- `GET /scopes/` returns counts per scope
- Future: WebSocket events for real-time unread updates

### Frontend Requirements

- [ ] **Create `stores/notification-store.ts`**:
  - State: `unreadCounts: Record<string, number>` (key format: `"user"`, `"business:<uuid>"`, `"platform:<uuid>"`)
  - Computed: `totalUnread` (sum of all counts)
  - Actions: `setUnreadCounts()`, `incrementUnread(scopeKey)`, `decrementUnread(scopeKey)`, `clearUnread(scopeKey)`
  - Non-React accessor: `getNotificationStore()` for API/WS layer

- [ ] **Create `features/notifications/hooks/use-unread-badge.ts`**:
  - Returns `totalUnread` from Zustand store
  - On mount, fetches `/scopes/` and syncs counts into store
  - Polls `/scopes/` every 60 seconds as REST fallback
  - Future: WebSocket events replace polling

### Business Rules
- Store lives in `src/stores/` (not `features/`) — same pattern as `chat-store.ts`
- Use `useShallow` from `zustand/react/shallow` in selectors to prevent unnecessary re-renders
- `getNotificationStore()` for non-React access (API interceptors, WS handlers)

---

## 4. Notification Bell & Badge

### Frontend Requirements

- [ ] **Create `features/notifications/components/NotificationBell.tsx`**:
  - Bell icon (`lucide-react` `Bell`)
  - Badge overlay showing `totalUnread` from Zustand store
  - Badge hidden when count is 0
  - On desktop: click toggles notification dropdown (Popover)
  - On mobile: click navigates to `/notifications`
  - Use `useUnreadBadge()` hook for count

- [ ] **Integrate into `Topbar.tsx`** authenticated variant:
  - Insert `<NotificationBell />` between `<div className="flex-1" />` and `<UserMenu />`

### Business Rules
- Badge uses shadcn `Badge` component with `variant="destructive"` for red unread indicator
- Badge text: show count if <= 99, show "99+" if over 99
- Bell icon should have subtle animation (pulse or shake) on new notification (future)

---

## 5. Notification Dropdown

### Frontend Requirements

- [ ] **Create `features/notifications/components/NotificationDropdown.tsx`**:
  - Wraps `Popover` + `PopoverTrigger` + `PopoverContent` from shadcn
  - Content: list of 5–10 most recent notifications via `useNotificationHistory({ limit: 10 })`
  - Each item renders via `NotificationItem` component (compact variant)
  - Footer: "View all notifications" link → `/notifications`
  - Empty state: "No notifications" message
  - Loading state: 3 Skeleton rows

- [ ] **Dropdown should close** when:
  - User clicks a notification item (navigate to action link)
  - User clicks "View all"
  - User clicks outside

### Business Rules
- Desktop only (md+) — on mobile the bell navigates directly
- Don't fetch if dropdown is closed (use `enabled` option on TQ query)
- Dropdown width: `w-80` to `w-96` — similar to Instagram's notification dropdown

---

## 6. Notification Page

### Frontend Requirements

- [ ] **Replace placeholder at `app/(app)/(user)/notifications/page.tsx`**:
  - Import and render `NotificationList` from `features/notifications/components/`
  - Read scope params from URL: `searchParams.scope_type`, `searchParams.scope_id`
  - Pass to `NotificationList` as props

- [ ] **Create `features/notifications/components/NotificationList.tsx`**:
  - Renders `NotificationScopeTabs` at top
  - Renders paginated list of `NotificationItem` components
  - "Load More" button at bottom (NOT infinite scroll) using offset pagination
  - Skeleton loading state (3-5 skeleton cards)
  - Empty state component when no notifications

### Business Rules
- Page title: "Notifications"
- "Load More" increments offset by limit (50)
- When scope tab changes, reset offset to 0 and update URL params
- If `_permissions` is present in response, store for Tier 1.5 UI gating

---

## 7. Notification Item Component

### Frontend Requirements

- [ ] **Create `features/notifications/components/NotificationItem.tsx`**:
  - Props: `notification: NotificationLogItem`, `variant: "full" | "compact"`
  - Full variant: for notification page (more detail, wider)
  - Compact variant: for dropdown (shorter, narrower)
  - Renders: type icon, title (from display config), relative timestamp, scope badge
  - Clickable: navigates to action link (if defined in display config)
  - Scope badge: business name/icon for business-scoped, platform icon for platform, none for user-scoped

- [ ] **Memoize**: wrap in `React.memo()` — list re-renders on new items but most items unchanged

### Business Rules
- Relative timestamp: "2m ago", "1h ago", "Yesterday", "Mar 15" (use date-fns or similar)
- Type icon and title derived from `notification_type` via display config map
- Context data (transaction_id, conversation_id) used to build action links
- For unknown notification types: show generic bell icon + type name as title (graceful degradation)

---

## 8. Scope Tabs & Filtering

### Backend Support
- `GET /scopes/` returns distinct scopes with counts
- `GET /history/?scope_type=business&scope_id=<uuid>` filters by scope

### Frontend Requirements

- [ ] **Create `features/notifications/components/NotificationScopeTabs.tsx`**:
  - Fetches scopes via `useNotificationScopes()`
  - Renders tabs: "All" + one tab per scope from API
  - Each tab shows: label + count badge
  - "All" tab: total across all scopes
  - Business tab: business name (need to resolve from scope_id — use membership store)
  - Platform tab: "Platform"
  - User tab: "Personal"
  - Active tab tracked via URL query param `scope_type` + `scope_id`

- [ ] **Tab change behavior**:
  - Update URL params: `?scope_type=business&scope_id=<uuid>`
  - Reset pagination offset to 0
  - TQ query refetches with new scope params

### Business Rules
- Only show tabs for scopes that have notifications (from `/scopes/` response)
- Business name resolution: use `useMembershipStore()` to get business name from scope_id
- Horizontal scroll on mobile if many scopes
- "All" tab is the default when no scope params in URL

---

## 9. Notification Preferences UI

### Backend Support
- `GET /preferences/` returns all types grouped by category
- `PATCH /preferences/{type}/` updates channel toggles
- `DELETE /preferences/{type}/` resets to defaults
- Non-configurable types have `user_configurable: false`

### Frontend Requirements

- [ ] **Create `features/notifications/components/PreferencesPanel.tsx`**:
  - Fetches preferences via `useNotificationPreferences()`
  - Groups by category (tabs or accordion sections)
  - Each type renders via `PreferenceRow`
  - Categories from API: `auth`, `security`, `transactional`, `marketing`, `social` (all returned, including non-configurable)
  - Non-configurable types shown with disabled toggles (auth/security critical types)

- [ ] **Create `features/notifications/components/PreferenceRow.tsx`**:
  - Props: `preference: NotificationPreferenceItem`
  - Renders: display_name, description, 3 Switch toggles (email, push, sms)
  - If `user_configurable === false`: all switches disabled + lock icon
  - On toggle change: call `useUpdatePreference(type).mutate({ email_enabled: value })`
  - Optimistic update: toggle immediately, revert on error with toast

- [ ] **Integrate into Settings**:
  - User settings: add "Notifications" Card section in `SettingsPage` or as a sub-route
  - Business settings: add "Notification Preferences" section (scoped preferences, future)

### Business Rules
- Switches use shadcn `Switch` component
- Disabled switches show `opacity-50 cursor-not-allowed`
- Toast on error: "Failed to update notification preference"
- Toast on reset: "Preference reset to default"

---

## 10. Navigation Integration

### Frontend Requirements

- [ ] **Sidebar badge**: notification nav item shows unread count badge from `useUnreadBadge()`
- [ ] **Bottom nav badge**: same for mobile BottomNavbar "Alerts" item
- [ ] **Business/platform console**: if notification scopes include the current business/platform, show count in that console's nav too (future)

### Business Rules
- Badge component: small red dot or number
- Hide badge when count is 0
- Animate badge on increment (subtle scale animation, future)

---

## 11. Display Config & Constants

### Frontend Requirements

- [ ] **Create `features/notifications/constants/notification-constants.ts`**:
  - `NOTIFICATION_DISPLAY_CONFIG`: map from `notification_type` to `{ icon, title, actionLinkBuilder }`
  - `NOTIFICATION_CATEGORY_LABELS`: map from category to human-readable label
  - `NOTIFICATION_POLLING_INTERVAL_MS`: 60_000 (for scope count polling)
  - `NOTIFICATION_HISTORY_PAGE_SIZE`: 50
  - `NOTIFICATION_DROPDOWN_LIMIT`: 10
  - `NOTIFICATION_SCOPE_LABELS`: map for scope display names

### Business Rules
- Icons from `lucide-react`
- Title templates can include `{variables}` from notification context
- Action link builders receive `context` dict and return a URL path or null

---

## 12. Feature Gate Degradation

### Backend Support
- System Gate (SG): `systems.notifications` — when `false`, ALL endpoints return 404
- Feature Gate (FG): `user.notifications.enabled` — when `false`, backend `send()` returns None for configurable types, mandatory auth types still arrive
- Value Gate (VG): channel toggles and retention days configurable at runtime

### Frontend Requirements

- [ ] **Create `features/notifications/hooks/use-notifications-available.ts`**:
  - Returns `boolean` — `true` if notification system is available
  - Detects SG-off by checking if scopes query returns 404 (`ApiError.isNotFound`)
  - Caches result — don't retry 404 on every render (use TQ `retry: false` for 404)
  - Used by NotificationBell, nav items, notification page to conditionally render

- [ ] **NotificationBell**: don't render when `useNotificationsAvailable()` returns `false`
- [ ] **Navigation items**: hide badge (or entire item) when system unavailable
- [ ] **Notification page**: show "Notifications are not available" fallback when system off
- [ ] **Preferences UI**: disable all toggles when system off, show info message

### Business Rules
- SG off = entire UI hidden (404 on all endpoints)
- FG off = fewer notifications arrive but UI still works normally
- The frontend only needs to handle SG-off state — FG-off is invisible to the frontend
- Use `retry: false` on TQ queries when 404 is detected — don't poll a disabled system
- When system becomes available again (config change + redeploy), a page refresh should re-enable

---

## 13. Error Handling & Edge Cases

### Frontend Requirements

- [ ] **API errors**: all query/mutation errors should show toast via `sonner`
- [ ] **System disabled (404)**: when all notification endpoints return 404, hide bell, show fallback page, don't toast repeatedly
- [ ] **Empty scopes**: if user has zero notifications, scopes endpoint returns empty list — show "All" tab only
- [ ] **Unknown notification types**: display with generic icon and raw type name (don't crash)
- [ ] **Invalid scope_id in URL**: ignore and show all notifications (default to no scope filter)
- [ ] **Stale unread counts**: if REST poll shows count but WS has different count, WS takes precedence (future)
- [ ] **Network offline**: show cached notifications from TQ cache, disable preference mutations

---

## 14. Accessibility

### Frontend Requirements

- [ ] **Bell button**: `aria-label="Notifications"`, `aria-haspopup="dialog"` for dropdown
- [ ] **Unread badge**: `aria-label="X unread notifications"` (screen reader accessible count)
- [ ] **Notification list**: `role="list"` with `role="listitem"` on each NotificationItem
- [ ] **Scope tabs**: use shadcn `Tabs` component (built on Radix — handles ARIA tabs pattern)
- [ ] **Preference switches**: each switch has `aria-label="{type} {channel} notifications"`
- [ ] **Focus management**: when dropdown opens, focus moves to first notification item
- [ ] **Keyboard navigation**: arrow keys in dropdown list, Enter to activate, Escape to close

---

## 15. Responsive / Mobile

### Frontend Requirements

- [ ] **Breakpoint**: `md` (768px) — above = desktop, below = mobile
- [ ] **Desktop**: bell in Topbar → Popover dropdown + full page at `/notifications`
- [ ] **Mobile**: bell in BottomNavbar → direct navigation to `/notifications` (no dropdown)
- [ ] **Notification page**: scope tabs horizontal scroll on mobile, full-width notification cards
- [ ] **Preferences page**: single-column layout, switches stack vertically per type
- [ ] **Dropdown**: hidden on mobile — bell navigates directly

---

## 16. Testing

### Frontend Requirements

- [ ] **API layer tests**: mock `apiClient`, verify correct URL/params for each function
- [ ] **Query hook tests**: mock API functions, verify TQ query keys and options
- [ ] **Mutation hook tests**: verify invalidation of correct query keys on success
- [ ] **NotificationBell tests**: renders badge with count, hides badge at 0, opens dropdown
- [ ] **NotificationItem tests**: renders correct icon/title for each notification type, handles unknown types
- [ ] **NotificationScopeTabs tests**: renders tabs from scopes data, active tab from URL params
- [ ] **PreferenceRow tests**: toggles call mutation, disabled for non-configurable types
- [ ] **NotificationList tests**: renders items, shows empty state, "Load More" works
- [ ] **Zustand store tests**: increment/decrement/clear unread counts, total computation
- [ ] **Feature gate tests**: useNotificationsAvailable returns false on 404, bell hidden when unavailable, page shows fallback
- [ ] **Snapshot tests**: key components render consistently

### Business Rules
- Use `vitest` + `@testing-library/react` + `happy-dom`
- Use `renderWithProviders()` from `src/test/utils.tsx`
- Mock API calls at the function level (not axios level)
- Test both full and compact variants of NotificationItem
