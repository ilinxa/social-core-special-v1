# Explore System — Frontend Implementation Reference

**Version:** v1
**Last Updated:** 2026-03-03
**Status:** Implemented

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│          Route: /explore  (public)                   │
│          app/(public)/explore/page.tsx               │
│                    │                                 │
│          ┌────────▼────────┐                        │
│          │   ExplorePage    │ (URL-synced state)     │
│          └────────┬────────┘                        │
│    ┌──────────────┼──────────────┐                  │
│    │              │              │                   │
│  AllTab    BusinessSearch    UserSearch              │
│    │              │              │                   │
│ ┌──┴──┐    ┌─────┴─────┐  ┌────┴────┐             │
│ │Cards│    │FilterPanel │  │FilterPanel│             │
│ └─────┘    │+Cards+Page│  │+Cards+Page│             │
│            └───────────┘  └──────────┘              │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│           Hooks (TanStack Query)                     │
│  useExploreCombined  useBusinessSearch               │
│  useUserSearch  useTagSuggestions  useCities         │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│              API Layer                               │
│  fetchExploreCombinedApi  searchBusinessesApi         │
│  searchUsersApi  fetchTagSuggestionsApi              │
│  fetchCitiesApi                                      │
└────────────────────┬────────────────────────────────┘
                     │
                GET /api/v1/explore/*
```

All components are client-side rendered ("use client"). Search state is synced to URL search params for shareability.

## 2. Core Concepts & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Route location | `(public)/explore` | Business search is public; auth only needed for user tab |
| State management | URL search params | Shareable URLs, browser back/forward, no Zustand needed |
| Search debounce | 300ms in SearchBar | Balance between responsiveness and API call reduction |
| Tab switching | URL `?tab=` param | Persists across page refreshes, enables deep linking |
| Pagination | Simple previous/next | Matches DRF's `StandardPagination` response format |
| Filter panel | Inline sidebar (lg:), Sheet (mobile) | Responsive without complex state |
| Null profile guards | Fallback objects in cards | Backend can return null profiles for users without UserProfile records |

## 3. Data Layer

### 3.1 API Functions

Location: `src/features/explore/api/explore-api.ts`

| Function | Endpoint | Notes |
|----------|----------|-------|
| `fetchExploreCombinedApi(params)` | `GET /explore/` | `?q=` only |
| `searchBusinessesApi(params)` | `GET /explore/businesses/` | All 12 filter params |
| `searchUsersApi(params)` | `GET /explore/users/` | 7 filter params, requires auth |
| `fetchTagSuggestionsApi(q, category, limit)` | `GET /explore/tags/` | Autocomplete |
| `fetchCitiesApi(country)` | `GET /explore/cities/` | Static data |

Helper: `buildQueryString(params)` — converts object to `?key=value&...`, skipping undefined/null/empty.

### 3.2 Query Keys

Location: `src/lib/query-keys.ts`

```typescript
explore: {
  all: ["explore"],
  combined: (params) => [..., "combined", params],
  businesses: (params) => [..., "businesses", params],
  users: (params) => [..., "users", params],
  tags: (q?, category?) => [..., "tags", q, category],
  cities: (country) => [..., "cities", country],
}
```

## 4. Types & Interfaces

Location: `src/types/explore.ts`

```typescript
// Business search result
interface ExploreBusinessProfile {
  display_name, tagline, logo, industry, company_size, tags, website
}
interface ExploreBusiness {
  id, slug, legal_name, country, city, business_type,
  is_platform_branch, is_verified,
  profile: ExploreBusinessProfile | null,  // null when no profile record
  search_rank
}

// User search result
interface ExploreUserProfile {
  first_name, last_name, bio, avatar_url, country, city, tags
}
interface ExploreUser {
  id, username, is_verified, display_name,
  profile: ExploreUserProfile | null,  // null when no profile record
  search_rank
}

// Combined "All" tab response
interface ExploreCombinedResponse {
  businesses, users, businesses_count, users_count
}

// Supporting types
interface SuggestedTag { id, name, slug, category, usage_count }
interface CityListResponse { country, cities[] }
type BusinessSearchParams = { q?, country?, city?, industry?, ... page?, page_size? }
type UserSearchParams = { q?, country?, city?, language?, ... page?, page_size? }
```

**Note:** `BusinessSearchParams` and `UserSearchParams` are `type` aliases (not `interface`) because interfaces don't satisfy `Record<string, T>` constraints used by query key factories.

## 5. Hooks

Location: `src/features/explore/hooks/use-explore-queries.ts`

| Hook | Query Key | staleTime | Notes |
|------|-----------|-----------|-------|
| `useExploreCombined(params)` | `explore.combined` | 30s | `placeholderData: prev` for smooth transitions |
| `useBusinessSearch(params)` | `explore.businesses` | 30s | `placeholderData: prev` |
| `useUserSearch(params)` | `explore.users` | 30s | `placeholderData: prev`, enabled when auth'd |
| `useTagSuggestions(q, cat)` | `explore.tags` | 5min | enabled when `q.length >= 1` |
| `useCities(country)` | `explore.cities` | 30min | Static data, long cache |

Each hook exports both a query options factory (`fooQueryOptions`) and a `useFoo` hook wrapper.

## 6. Components

Location: `src/features/explore/components/`

### Page & Layout

| Component | Purpose |
|-----------|---------|
| `ExplorePage` | Main page: URL state management, debounced search, tab routing, filter changes, pagination |
| `SearchBar` | Debounced text input (300ms) with search icon |
| `ExploreTabs` | Tab navigation: All, Businesses, Users (Users auth-gated) |
| `FilterPanel` | Responsive wrapper: inline sidebar (lg:), Sheet (mobile). Hidden on "all" tab |

### Tab Content

| Component | Purpose |
|-----------|---------|
| `AllTabContent` | Combined view: top 6 businesses + top 6 users (auth-gated). "See all" links |
| `BusinessSearchContent` | Paginated business results grid + Previous/Next pagination |
| `UserSearchContent` | Paginated user results grid + Previous/Next pagination |

### Cards

| Component | Purpose |
|-----------|---------|
| `BusinessCard` | Card: logo/initial, display_name, tagline, industry, location, website, verified badge, tags (max 3 + overflow) |
| `UserCard` | Card: avatar/initials, display_name, @username, bio (2-line clamp), location, verified badge, tags |

### Filters

| Component | Purpose |
|-----------|---------|
| `BusinessFilters` | Industry select, company size select, ordering select, verified toggle, has website toggle |
| `UserFilters` | Ordering select, verified toggle |

## 7. Pages & Routes

| Route | Type | Auth | Component |
|-------|------|------|-----------|
| `/explore` | Client | Public | `ExplorePage` (wrapped in Suspense) |
| `/explore?tab=businesses` | Client | Public | BusinessSearchContent within ExplorePage |
| `/explore?tab=users` | Client | Required | UserSearchContent within ExplorePage |

Route file: `src/app/(public)/explore/page.tsx`

Previous route `(app)/(user)/explore/` was deleted to resolve Next.js parallel route conflict.

## 8. Key Flows

### Flow 1: Initial Page Load (All Tab)

1. User navigates to `/explore`
2. `ExplorePage` reads URL params: no `tab` → defaults to "all"
3. Renders `SearchBar` + `ExploreTabs` + `AllTabContent`
4. `AllTabContent` calls `useExploreCombined({ q: undefined })`
5. Shows loading spinner, then business cards + user cards (if authenticated)

### Flow 2: Search with Debounce

1. User types "tech startup" in SearchBar
2. SearchBar debounces for 300ms, then calls `onSearch("tech startup")`
3. `ExplorePage.handleSearch()` updates URL: `?q=tech+startup`
4. `useExploreCombined` / `useBusinessSearch` re-fires with new params
5. `placeholderData: prev` keeps old results visible during loading

### Flow 3: Tab Switch to Businesses

1. User clicks "Businesses" tab
2. `ExplorePage.handleTabChange("businesses")` updates URL: `?tab=businesses&q=tech+startup`
3. Renders `BusinessSearchContent` + `FilterPanel` with `BusinessFilters`
4. `useBusinessSearch` fires with current params

### Flow 4: Apply Filter

1. User selects "Technology" industry in BusinessFilters
2. `BusinessFilters.onChange({ industry: "Technology", page: 1 })` propagates up
3. `ExplorePage.handleBusinessFilterChange` updates URL: `?tab=businesses&industry=Technology&page=1`
4. `useBusinessSearch` re-fires with updated params

### Flow 5: Pagination

1. User clicks "Next" button
2. `handleBusinessPageChange(2)` updates URL: `?tab=businesses&page=2`
3. `useBusinessSearch` fires with `page: 2`
4. Previous data stays visible via `placeholderData`

## 9. Route Protection

| Path | Anonymous | Authenticated | Notes |
|------|-----------|---------------|-------|
| `/explore` (All tab) | Business cards only | Business + User cards | Users section auth-gated in `AllTabContent` |
| `/explore?tab=businesses` | Full access | Full access | Public |
| `/explore?tab=users` | Tab hidden, redirects to All | Full access | Tab only rendered when `isAuthenticated` |

No route guard needed — the component conditionally hides/shows based on `useIsAuthenticated()`.

## 10. Configuration & Gotchas

### Gotchas

- **Null profiles:** Backend can return `profile: null` for users without UserProfile records. Both `UserCard` and `BusinessCard` have defensive fallback objects. Types are `ExploreUserProfile | null` and `ExploreBusinessProfile | null`.
- **`type` vs `interface` for search params:** `BusinessSearchParams` and `UserSearchParams` must be `type` aliases (not `interface`) because TypeScript interfaces don't satisfy `Record<string, T>` generic constraints used by query key factories.
- **Route conflict:** `(app)/(user)/explore/` and `(public)/explore/` both resolve to `/explore`. The old route was deleted entirely.
- **Select component:** Required `npx shadcn@latest add select` — used by BusinessFilters and UserFilters.
- **Mock data in tests:** 15+ existing test files needed updates when new fields were added to UserProfile/BusinessProfile/BusinessAccount types. All mock objects must include `bio`, `country`, `city`, `tags`, `is_platform_branch`.

## 11. Testing

| Module | Tests | Status |
|--------|-------|--------|
| `explore-api.test.ts` | 8 | Pass |
| `ExplorePage.test.tsx` | 8 | Pass |
| `BusinessCard.test.tsx` | 7 | Pass |
| `UserCard.test.tsx` | 8 | Pass |
| **Total** | **31** | **Pass** |

Tests use mocked child components (ExplorePage) and mocked `next/navigation` + `auth-store`.

## 12. File Summary

### New Files

| File | Description |
|------|-------------|
| `src/types/explore.ts` | 12 types for explore API contracts |
| `src/features/explore/api/explore-api.ts` | 5 API functions + buildQueryString helper |
| `src/features/explore/api/explore-api.test.ts` | API function tests |
| `src/features/explore/hooks/use-explore-queries.ts` | 5 TanStack Query hooks |
| `src/features/explore/components/ExplorePage.tsx` | Main page with URL-synced state |
| `src/features/explore/components/SearchBar.tsx` | Debounced search input |
| `src/features/explore/components/ExploreTabs.tsx` | Tab navigation |
| `src/features/explore/components/AllTabContent.tsx` | Combined "All" tab |
| `src/features/explore/components/BusinessSearchContent.tsx` | Paginated business results |
| `src/features/explore/components/UserSearchContent.tsx` | Paginated user results |
| `src/features/explore/components/BusinessCard.tsx` | Business result card |
| `src/features/explore/components/UserCard.tsx` | User result card |
| `src/features/explore/components/FilterPanel.tsx` | Responsive filter wrapper |
| `src/features/explore/components/BusinessFilters.tsx` | Business filter controls |
| `src/features/explore/components/UserFilters.tsx` | User filter controls |
| `src/features/explore/components/ExplorePage.test.tsx` | ExplorePage tests |
| `src/features/explore/components/BusinessCard.test.tsx` | BusinessCard tests |
| `src/features/explore/components/UserCard.test.tsx` | UserCard tests |
| `src/app/(public)/explore/page.tsx` | Route entry point |
| `public/data/cities.json` | Static city data (copy of backend) |
| `src/components/ui/select.tsx` | shadcn Select component |

### Modified Files

| File | Change |
|------|--------|
| `src/types/index.ts` | Added bio, country, city, tags to UserProfile |
| `src/types/organization.ts` | Added tags to BusinessProfile; city, is_platform_branch to BusinessAccount/List |
| `src/lib/query-keys.ts` | Added explore query key factories |
| 15+ test files | Updated mock objects for new type fields |

### Deleted Files

| File | Reason |
|------|--------|
| `src/app/(app)/(user)/explore/page.tsx` | Moved to `(public)` route group; old location caused parallel route conflict |

## 13. Known Limitations

1. **No CityCombobox or TagMultiSelect** — Planned in design but not yet implemented. Current filters use simple Select dropdowns.
2. **No FilterPanel test file** — FilterPanel.test.tsx was planned but not created.
3. **No use-explore-queries.test.ts** — Hook tests were planned but not created.
4. **Country/city cascading filter not wired** — Frontend has `useCities` hook but no country/city filter UI in BusinessFilters/UserFilters yet.

## 14. vNext TODOs

| Item | Context | Priority |
|------|---------|----------|
| CityCombobox component | Country→City cascading select using `useCities` hook | P1 |
| TagMultiSelect component | Free-form + autocomplete using `useTagSuggestions` hook | P1 |
| Wire country/city to business filters | BusinessFilters currently has industry/size/ordering/verified/website only | P1 |
| FilterPanel tests | Test responsive behavior (sidebar vs Sheet) | P2 |
| Hook tests | Test query key shapes, staleTime, enabled gates | P2 |
| Infinite scroll | Replace previous/next with intersection observer | P3 |

## 15. Changelog

### v1 (2026-03-03)
- Initial implementation: 5 API functions, 5 TQ hooks, 15 components
- URL-synced search/filter/tab/pagination state
- Public business search, auth-gated user search
- Null profile safety guards on card components
