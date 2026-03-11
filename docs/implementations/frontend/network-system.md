# Network System (Frontend) — Implementation Reference

**Version:** v1
**Last Updated:** 2026-03-10
**Status:** Implemented

---

## 1. Architecture Overview

```
Profile Pages (Business/User/Platform)
  └─ FollowButton / ConnectButton (smart CTA)
       └─ useFollow / useUnfollow / useConnectUser / useDisconnectUser
       └─ useCancelTransaction / useAcceptTransaction / useDenyTransaction (reused)
       └─ ConfirmActionDialog (reused)
       └─ _relationship from entity detail response

My Network Page (/network)
  └─ ConnectionCard / FollowingCard
       └─ useConnections / useFollowing / useNetworkStats

Business Console (/bconsole/[slug]/network/*)
  └─ BusinessFollowersPage / BusinessConnectionsPage
       └─ useBusinessFollowers / useBusinessConnections / useBusinessNetworkStats
       └─ useHasPermission (RBAC gate for Remove/Disconnect actions)
```

## 2. Core Concepts & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| CTA state source | `_relationship` from entity detail response | Single data source — no extra API calls. Backend computes membership, follow, and connection status |
| Connect dialog | Reuse `ConfirmActionDialog` with `showReasonField=true` | Zero new dialog components needed |
| Transaction action reuse | Import `useCancelTransaction/useAcceptTransaction/useDenyTransaction` from transactions feature | Follow and connection actions route through the Transaction system |
| Permission gating (business console) | `useHasPermission` from membership store | `can_manage_followers`/`can_manage_connections` are RBAC permissions from the network app, not in `BusinessPermissions` type — they're checked from cached memberships |
| Hover-to-destructive | `useState(isHovered)` on Following/Connected buttons | Hover swaps text and variant to indicate destructive action |

## 3. Data Layer

### 3.1 API Functions

Location: `src/features/network/api/network-api.ts`

| Function | Method | Endpoint | Returns |
|----------|--------|----------|---------|
| `createFollowApi(data)` | POST | `/network/follow/` | `{ transaction_id, status }` |
| `unfollowApi(followId)` | DELETE | `/network/follow/{id}/` | void |
| `fetchFollowingApi(params?)` | GET | `/network/following/` | `PaginatedResponse<FollowingItem>` |
| `createConnectionRequestApi(data)` | POST | `/network/connections/request/` | `{ transaction_id, status }` |
| `disconnectUserApi(connectionId)` | DELETE | `/network/connections/{id}/` | void |
| `fetchConnectionsApi(params?)` | GET | `/network/connections/` | `PaginatedResponse<UserConnectionItem>` |
| `fetchBusinessFollowersApi(slug, params?)` | GET | `/network/business/{slug}/followers/` | `PaginatedResponse<FollowerItem>` |
| `removeBusinessFollowerApi(slug, followId)` | DELETE | `/network/business/{slug}/followers/{id}/` | void |
| `fetchBusinessConnectionsApi(slug, params?)` | GET | `/network/business/{slug}/connections/` | `PaginatedResponse<AccountConnectionItem>` |
| `createBusinessConnectionApi(slug, data)` | POST | `/network/business/{slug}/connections/request/` | `{ transaction_id, status }` |
| `disconnectBusinessConnectionApi(slug, connId)` | DELETE | `/network/business/{slug}/connections/{id}/` | void |
| `fetchNetworkStatsApi()` | GET | `/network/stats/` | `NetworkStats` |
| `fetchBusinessNetworkStatsApi(slug)` | GET | `/network/business/{slug}/stats/` | `NetworkStats` |

### 3.2 Input Types (in network-api.ts)

```typescript
interface CreateFollowData {
  followee_type: "business" | "platform";
  followee_id: string;
}

interface CreateConnectionData {
  target_user_id: string;
  note?: string;
}

interface CreateBusinessConnectionData {
  target_account_type: string;
  target_account_id: string;
  note?: string;
}

interface FollowingParams extends PaginationParams {
  type?: "business" | "platform";
}

interface ConnectionsParams extends PaginationParams {
  status?: string;
  search?: string;
}

interface FollowersParams extends PaginationParams {
  search?: string;
}
```

### 3.3 Query Keys

Location: `src/lib/query-keys.ts` — `network` section

```typescript
network: {
  all: ["network"] as const,
  following: (type?: string) =>
    [...queryKeys.network.all, "following", type] as const,
  connections: (status?: string) =>
    [...queryKeys.network.all, "connections", status] as const,
  stats: () => [...queryKeys.network.all, "stats"] as const,
  businessFollowers: (slug: string) =>
    [...queryKeys.network.all, "business-followers", slug] as const,
  businessConnections: (slug: string) =>
    [...queryKeys.network.all, "business-connections", slug] as const,
  businessStats: (slug: string) =>
    [...queryKeys.network.all, "business-stats", slug] as const,
},
```

## 4. Types

### `types/network.ts`

| Type | Shape |
|------|-------|
| `FollowingItem` | `{ id, followee_type: "business"\|"platform", followee_id, followee_name, followee_slug: string\|null, created_at }` |
| `FollowerItem` | `{ id, follower: NetworkUser, followee_type, followee_id, followee_name, status, created_at }` |
| `UserConnectionItem` | `{ id, other_user: NetworkUser, note, status, connected_at: string\|null, created_at }` |
| `AccountConnectionItem` | `{ id, other_account: { type, id, name }, note, status, connected_at: string\|null, created_at }` |
| `NetworkUser` | `{ id, username, display_name, avatar_url }` |
| `NetworkStats` | `{ followers_count, following_count, connections_count }` |

### Expanded types in `types/organization.ts`

```typescript
type ActiveTransactionSummary = {
  id: string;
  type: string;
  status: string;
  mode: "invitation" | "request";
  viewer_role: "initiator" | "target";  // Added for network CTA state
};

type EntityRelationship = {
  membership_status: string | null;
  active_transaction: ActiveTransactionSummary | null;
  // Follow (business/platform)
  follow_status?: string | null;
  follow_id?: string | null;
  active_follow_transaction?: ActiveTransactionSummary | null;
  // Connection (user profiles)
  connection_status?: string | null;
  connection_id?: string | null;
  active_connection_transaction?: ActiveTransactionSummary | null;
};
```

### Expanded types in `types/index.ts`

```typescript
type UserLimited = {
  id: string;
  username: string;
  is_verified: boolean;
  date_joined: string;
  profile: UserLimitedProfile;
  is_limited: true;
  _permissions?: UserPublicPermissions;     // Added
  _relationship?: EntityRelationship;       // Added
};

// New type
type UserPublicWithRelationship = UserPublicWithPerms & {
  _relationship?: EntityRelationship;
};
```

## 5. Hooks

Location: `src/features/network/hooks/`

### Query Hooks (`use-network-queries.ts`)

| Hook | Query Key | staleTime |
|------|-----------|-----------|
| `useFollowing(type?)` | `network.following(type)` | 5 min |
| `useConnections(status?)` | `network.connections(status)` | 5 min |
| `useNetworkStats()` | `network.stats()` | 5 min |
| `useBusinessFollowers(slug)` | `network.businessFollowers(slug)` | 5 min |
| `useBusinessConnections(slug)` | `network.businessConnections(slug)` | 5 min |
| `useBusinessNetworkStats(slug)` | `network.businessStats(slug)` | 5 min |

### Mutation Hooks (`use-network-mutations.ts`)

| Hook | API | Invalidates |
|------|-----|-------------|
| `useFollow()` | `createFollowApi` | `network.all` |
| `useUnfollow()` | `unfollowApi` | `network.all` |
| `useConnectUser()` | `createConnectionRequestApi` | `network.all` |
| `useDisconnectUser()` | `disconnectUserApi` | `network.all` |
| `useRemoveBusinessFollower(slug)` | `removeBusinessFollowerApi` | `network.businessFollowers(slug)` |
| `useBusinessConnect(slug)` | `createBusinessConnectionApi` | `network.businessConnections(slug)` |
| `useBusinessDisconnect(slug)` | `disconnectBusinessConnectionApi` | `network.businessConnections(slug)` |

### Reused Hooks (from transactions feature)

- `useCancelTransaction()` — cancel pending follow/connection requests
- `useAcceptTransaction()` — accept incoming connection requests
- `useDenyTransaction()` — decline incoming connection requests

## 6. Components

### Smart CTA Components

| Component | Props | States |
|-----------|-------|--------|
| `FollowButton` | `followeeType, followeeId, followStatus, followId, activeFollowTransaction, onAction?, size?` | Follow → Cancel Request → Following (hover: Unfollow) |
| `ConnectButton` | `targetUserId, targetUsername, connectionStatus, connectionId, activeConnectionTransaction, onAction?, size?` | Connect → Cancel Request → Accept/Decline → Connected (hover: Disconnect) |

**FollowButton state machine:**

| follow_status | active_follow_txn | Render |
|---|---|---|
| `null`/`"removed"` | `null` | "Follow" → calls `useFollow()` |
| `null` | `{ viewer_role: "initiator" }` | "Cancel Request" → `useCancelTransaction()` |
| `"active"` | `null` | "Following" → hover: "Unfollow" → `ConfirmActionDialog` (destructive) → `useUnfollow()` |

**ConnectButton state machine:**

| connection_status | active_conn_txn | viewer_role | Render |
|---|---|---|---|
| `null`/`"disconnected"` | `null` | — | "Connect" → opens `ConfirmActionDialog` (showReasonField, reasonLabel="Note (optional)") → `useConnectUser()` |
| `null` | `{ mode: "request" }` | `"initiator"` | "Cancel Request" → `useCancelTransaction()` |
| `null` | `{ mode: "request" }` | `"target"` | "Accept" (primary) + "Decline" (ghost) → `useAcceptTransaction()` / `useDenyTransaction()` |
| `"active"` | `null` | — | "Connected" → hover: "Disconnect" → `ConfirmActionDialog` (destructive) → `useDisconnectUser()` |

Both buttons return `null` when `useIsAuthenticated()` returns `false`.

### Card Components

| Component | Props |
|-----------|-------|
| `ConnectionCard` | `connection: UserConnectionItem, onDisconnect, isDisconnecting?` |
| `FollowingCard` | `item: FollowingItem, onUnfollow, isUnfollowing?` |

### Page Components

| Component | Features |
|-----------|----------|
| `MyNetworkPage` | Connections/Following tabs with counts, search filter, stats header, skeleton loading, empty states |
| `BusinessFollowersPage` | `useParams` slug extraction, follower list with count, RBAC-gated Remove action via `useHasPermission` |
| `BusinessConnectionsPage` | `useParams` slug extraction, connection list with count, RBAC-gated Disconnect action via `useHasPermission` |

### Constants

Location: `src/features/network/constants/network-statuses.ts`

```typescript
const CONNECTION_STATUS_CONFIG = {
  active: { label: "Connected", className: "bg-green-100 text-green-800" },
  disconnected: { label: "Disconnected", className: "bg-gray-100 text-gray-600" },
};

const FOLLOW_STATUS_CONFIG = {
  active: { label: "Following", className: "bg-blue-100 text-blue-800" },
  removed: { label: "Removed", className: "bg-gray-100 text-gray-600" },
};
```

## 7. Pages & Routes

| Route | Component | Guard |
|-------|-----------|-------|
| `/network` | `MyNetworkPage` | AuthGuard |
| `/bconsole/[slug]/network/followers` | `BusinessFollowersPage` | BusinessGuard + `FeatureErrorBoundary` |
| `/bconsole/[slug]/network/connections` | `BusinessConnectionsPage` | BusinessGuard + `FeatureErrorBoundary` |

### Profile Integration (modified routes)

| Route | Change |
|-------|--------|
| `/business/[slug]` | Added `FollowButton` alongside `RequestToJoinButton` in `BusinessDiscoveryPage` |
| `/users/[username]` | Added `ConnectButton` in both `UserPublicProfileView` and `UserLimitedProfileView` (gated by `!is_own_profile` via `<Can>`) |
| `/platform/profile` | Added `FollowButton` below `PlatformProfileView` in `PlatformPublicProfilePage` |

## 8. Key Flows

### Flow 1: Follow a Business

1. User visits `/business/{slug}` — business detail includes `_relationship.follow_status`
2. `FollowButton` renders "Follow" (status=null)
3. User clicks → `useFollow()` → `POST /network/follow/` → transaction created
4. `onAction` callback invalidates business detail query
5. Re-render: button shows "Cancel Request" (private) or "Following" (auto-approved public)

### Flow 2: Send Connection Request

1. User visits `/users/{username}` — `_relationship.connection_status` is null
2. `ConnectButton` renders "Connect"
3. User clicks → `ConfirmActionDialog` opens with note field (`showReasonField=true`, `reasonLabel="Note (optional)"`)
4. User submits → `useConnectUser()` → `POST /network/connections/request/`
5. Re-render: button shows "Cancel Request" (viewer_role=initiator)

### Flow 3: Accept Incoming Connection

1. User visits profile of someone who sent them a request
2. `_relationship.active_connection_transaction.viewer_role` = `"target"`
3. `ConnectButton` renders "Accept" (primary) + "Decline" (ghost) buttons
4. User clicks Accept → `useAcceptTransaction()` → transaction accepted
5. Re-render: button shows "Connected" with hover-to-disconnect

### Flow 4: Unfollow (hover pattern)

1. `FollowButton` shows "Following" (variant=secondary)
2. User hovers → text changes to "Unfollow" (variant=destructive)
3. User clicks → `ConfirmActionDialog` opens ("Unfollow?", destructive)
4. User confirms → `useUnfollow()` → `DELETE /network/follow/{id}/`

### Flow 5: Business Console — Remove Follower

1. Owner/admin visits `/bconsole/{slug}/network/followers`
2. Component extracts slug via `useParams`, finds matching membership via `useBusinessMemberships()`
3. `useHasPermission("can_manage_followers", "business", accountId)` returns true
4. "Remove" button visible on each follower card
5. Click → `ConfirmActionDialog` → `useRemoveBusinessFollower()` → `DELETE /network/business/{slug}/followers/{id}/`

## 9. Navigation

### Personal Nav (added "Network" between Explore and Notifications)

```
Main: Home, Explore, Network, Notifications, Activity
```

- `network` item: `icon=Users2`, `href=/network`, `activeMatch=prefix`

### Business Nav (new "Network" section between Team and Content)

```
Network:
  - Followers (permission: can_manage_followers, icon: Heart)
  - Connections (permission: can_manage_connections, icon: Users2)
```

## 10. Backend Changes (Phase 0)

### `_relationship` expansion

Three view files modified to add fields:

| View | New Fields |
|------|-----------|
| `BusinessDetailView` / `BusinessByIdView` | `viewer_role` on `active_transaction` and `active_follow_transaction`; `follow_id` |
| `PlatformAccountView` | `viewer_role` on `active_transaction`; `active_follow_transaction` dict (was missing); `follow_id` |
| `UserPublicDetailView` | `viewer_role` on `active_connection_transaction`; `connection_id` |

**`viewer_role` logic:** `"initiator" if txn.initiator_id == viewer.id else "target"`

## 11. Testing

| Module | Tests | Status |
|--------|-------|--------|
| Network API functions | 13 | Pass |
| FollowButton states | 6 | Pass |
| ConnectButton states | 8 | Pass |
| MyNetworkPage | 6 | Pass |
| ConnectionCard | 3 | Pass |
| FollowingCard | 4 | Pass |
| BusinessFollowersPage | 3 | Pass |
| **Frontend total** | **43** | **Pass** |
| Backend relationship tests | 7 | Pass |
| **Grand total** | **50** | **Pass** |

## 12. File Summary

### New Files (15 source + 7 test = 22)

| File | Description |
|------|-------------|
| `types/network.ts` | 6 network type definitions (`FollowingItem`, `FollowerItem`, `UserConnectionItem`, `AccountConnectionItem`, `NetworkUser`, `NetworkStats`) |
| `features/network/api/network-api.ts` | 13 API functions + 6 input/params interfaces |
| `features/network/hooks/use-network-queries.ts` | 6 query hooks with `queryOptions()` factories |
| `features/network/hooks/use-network-mutations.ts` | 7 mutation hooks |
| `features/network/constants/network-statuses.ts` | `CONNECTION_STATUS_CONFIG` + `FOLLOW_STATUS_CONFIG` badge configs |
| `features/network/components/FollowButton.tsx` | Smart follow CTA with 3-state machine + hover-to-destructive |
| `features/network/components/ConnectButton.tsx` | Smart connect CTA with 4-state machine + hover-to-destructive |
| `features/network/components/MyNetworkPage.tsx` | My Network page with Connections/Following tabs, search, stats |
| `features/network/components/ConnectionCard.tsx` | Connection list card (avatar, name, note, disconnect action) |
| `features/network/components/FollowingCard.tsx` | Following list card (name, type badge, link, unfollow action) |
| `features/network/components/BusinessFollowersPage.tsx` | Business followers management with RBAC-gated Remove |
| `features/network/components/BusinessConnectionsPage.tsx` | Business connections management with RBAC-gated Disconnect |
| `app/(app)/(user)/network/page.tsx` | `/network` route page |
| `app/(app)/bconsole/[slug]/network/followers/page.tsx` | Business followers route page with `FeatureErrorBoundary` |
| `app/(app)/bconsole/[slug]/network/connections/page.tsx` | Business connections route page with `FeatureErrorBoundary` |
| `features/network/api/__tests__/network-api.test.ts` | 13 API tests |
| `features/network/components/__tests__/FollowButton.test.tsx` | 6 FollowButton state tests |
| `features/network/components/__tests__/ConnectButton.test.tsx` | 8 ConnectButton state tests |
| `features/network/components/__tests__/MyNetworkPage.test.tsx` | 6 page tests (tabs, search, stats) |
| `features/network/components/__tests__/ConnectionCard.test.tsx` | 3 card tests |
| `features/network/components/__tests__/FollowingCard.test.tsx` | 4 card tests |
| `features/network/components/__tests__/BusinessFollowersPage.test.tsx` | 3 page tests |

### Modified Files (11)

| File | Change |
|------|--------|
| `types/organization.ts` | Added `viewer_role` to `ActiveTransactionSummary`; expanded `EntityRelationship` with `follow_status`, `follow_id`, `active_follow_transaction`, `connection_status`, `connection_id`, `active_connection_transaction` |
| `types/index.ts` | Added optional `_permissions` and `_relationship` to `UserLimited`; added `UserPublicWithRelationship` type |
| `features/users/api/users-api.ts` | Updated `fetchUserByUsernameApi` return type to `UserPublicWithRelationship \| UserLimited` |
| `features/business/components/BusinessDiscoveryPage.tsx` | Added `FollowButton` alongside `RequestToJoinButton` |
| `features/users/components/UserPublicProfilePage.tsx` | Added `ConnectButton` to both `UserPublicProfileView` and `UserLimitedProfileView` (gated by `!is_own_profile`) |
| `features/platform/components/PlatformPublicProfilePage.tsx` | Added `FollowButton` below `PlatformProfileView` |
| `lib/query-keys.ts` | Added `network` section with 6 key factories |
| `lib/navigation-config.ts` | Added `Heart` and `Users2` icon imports; added "Network" to personal nav; added "Network" section to business nav with Followers + Connections |
| `hooks/use-filtered-nav.test.ts` | Added `can_manage_followers` and `can_manage_connections` to all-permissions test case |
| `backend: organization/business/views.py` | Added `viewer_role`, `follow_id` to `_build_business_relationship()` |
| `backend: organization/platform/views.py` | Added `viewer_role`, `active_follow_transaction`, `follow_id` to `_build_platform_relationship()` |
| `backend: users/views.py` | Added `viewer_role`, `connection_id` to `_build_relationship_data()` |

## 13. Gotchas

- **Platform `active_follow_transaction` always null**: `platform_follow_request` uses AUTO_APPROVAL — follows never stay pending. The FollowButton on platform will only show "Follow" or "Following".
- **`can_manage_followers` not on business `_permissions`**: These are RBAC permissions from the network app, not business policy permissions. Use `useHasPermission("can_manage_followers", "business", accountId)` from the membership store, NOT `business._permissions.can_manage_followers`.
- **`viewer_role` determines CTA state**: The same pending transaction shows "Cancel Request" for the initiator but "Accept/Decline" for the target. Without `viewer_role`, the frontend can't distinguish.
- **`follow_id`/`connection_id` needed for DELETE**: The unfollow/disconnect endpoints need the record ID, which isn't available from the transaction — it must come from `_relationship`.
- **BusinessFollowersPage/BusinessConnectionsPage use `useParams` internally**: They don't receive slug as a prop — they extract it from the URL, matching the pattern in `BusinessMemberDashboardPage`.
- **ConnectButton on limited (private) profiles**: Users can send connection requests even to private profiles — the Connect button appears on `UserLimitedProfileView`.

## 14. Known Limitations

1. **No pagination on My Network page** — client-side search only. Backend returns full list (first page). For large networks, add server-side pagination params to hooks.
2. **No CTA buttons on explore cards** — Explore API doesn't return `_relationship` data. Users click through to profile pages.
3. **Business connections: no target selector** — `BusinessConnectionsPage` shows existing connections but doesn't yet have a "New Connection" workflow with account search.

## 15. Changelog

### v1 (2026-03-10)
- Initial implementation: FollowButton, ConnectButton, My Network page, business console network pages
- 43 frontend tests across 7 test files, 7 backend relationship tests
- Integration with Business, User, and Platform profile pages
- Navigation config updates for personal + business contexts
