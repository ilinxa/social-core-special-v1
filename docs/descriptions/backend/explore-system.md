# Explore System — Description

**Status:** Approved
**Date:** 2026-03-02
**Workspace:** cross-cutting (backend + frontend)

---

## 1. What Is This?

The Explore system is a public-facing search and discovery feature that lets visitors and authenticated users find **businesses** and **users** on the platform. It provides full-text search with typo tolerance, entity-specific filters, and location-based discovery.

The system uses **PostgreSQL Full-Text Search (FTS)** for relevance-ranked results combined with **Trigram similarity** (`pg_trgm`) for typo-tolerant matching. No external search dependencies (e.g., Elasticsearch) are required.

**Access model:**
- **Business search**: Public (no authentication required) — businesses with `is_public=True` are discoverable by anyone.
- **User search**: Authenticated only — user discovery requires a logged-in session to protect user privacy.

---

## 2. Requirements

### Functional Requirements

- FR-1: Users can search for businesses by name, description, tagline, industry, and tags.
- FR-2: Authenticated users can search for other users by username, display name, bio, and tags.
- FR-3: Search results are ranked by relevance using FTS scoring + trigram similarity as fallback.
- FR-4: Results can be filtered by entity-specific fields (10 business filters, 5 user filters).
- FR-5: Location filtering supports cascading Country → City selection from a predefined city list.
- FR-6: The UI provides 3 tabs: "All" (sectioned), "Users", "Businesses".
- FR-7: The "All" tab shows a "Users" section (top N results) and a "Businesses" section (top N results) with "See all" links to the dedicated tabs.
- FR-8: Tags are stored as PostgreSQL ArrayField with GIN indexing, with a SuggestedTag model for autocomplete suggestions.
- FR-9: Platform-owned businesses can be flagged with `is_platform_branch` and filtered accordingly.
- FR-10: Pagination on all list results using StandardPagination (20/page, max 100).

### Non-Functional Requirements

- NFR-1: Search responses must return within 300ms for typical queries on datasets up to 100K entities.
- NFR-2: `pg_trgm` and GIN indexes must be applied to all searchable fields.
- NFR-3: Static city data (JSON file) must be loadable by both frontend (autocomplete) and backend (validation) without DB queries.
- NFR-4: The explore page must be fully functional on mobile (responsive filter panel).

---

## 3. Scope

### In Scope

- New backend explore endpoints (combined search, user search, business search, tag suggestions, city suggestions)
- Model changes: new fields on UserProfile, BusinessAccount, BusinessProfile + new SuggestedTag model
- PostgreSQL `pg_trgm` extension enablement (data migration)
- FTS `SearchVector`/`SearchQuery` setup for both User and Business entities
- Static cities JSON file (curated ~5K cities, keyed by country code)
- Frontend explore page with tabs, search bar, filter panel, result cards
- Frontend city autocomplete with Country → City cascading

### Out of Scope

- Elasticsearch or external search service integration
- Real-time search (typeahead via WebSocket) — debounced HTTP requests only
- Search analytics / tracking (what users search for)
- Geolocation-based search (lat/lng, radius) — country + city only
- Admin panel for managing SuggestedTags (direct DB or Django admin for now)
- Map view of results

---

## 4. User Stories

| ID | As a... | I want to... | So that... |
|----|---------|--------------|------------|
| US-1 | Public visitor | Search for businesses by name or keyword | I can discover businesses on the platform without signing up |
| US-2 | Public visitor | Filter businesses by country and city | I can find businesses near me |
| US-3 | Public visitor | Filter businesses by industry and company size | I can find businesses in my sector |
| US-4 | Public visitor | See if a business is verified | I can trust the business listing |
| US-5 | Public visitor | Filter for platform branch businesses | I can find official platform locations |
| US-6 | Authenticated user | Search for other users by name or username | I can find and connect with people |
| US-7 | Authenticated user | Filter users by country and city | I can find users near me |
| US-8 | Authenticated user | Filter users by tags | I can find users with specific interests or skills |
| US-9 | Authenticated user | View combined results (users + businesses) | I can explore everything in one place |
| US-10 | Business owner | Add tags to my business profile | My business is discoverable by relevant keywords |
| US-11 | User | Add a bio and tags to my profile | I can be found by other users searching for my skills/interests |
| US-12 | User | Set my country and city | I appear in location-based searches |

---

## 5. Design Decisions

### 5.1 Search Engine: PostgreSQL FTS + Trigram

**Decision:** Use PostgreSQL-native search (no external dependencies).

- **FTS** (`tsvector` / `tsquery`): For relevance-ranked full-text search with stemming, stop words, and ranking.
- **Trigram** (`pg_trgm`): For typo-tolerant matching (e.g., "amazn" → "Amazon").
- **Combined ranking**: FTS `ts_rank` as primary score, trigram `similarity()` as fallback for short/misspelled queries.

**Trade-off:** Limited compared to Elasticsearch (no faceting, no complex analyzers), but zero operational overhead and sufficient for our scale.

### 5.2 Tags: ArrayField + SuggestedTag (Hybrid)

**Decision:** Store tags as `ArrayField(CharField)` with GIN index on the model, plus a `SuggestedTag` model for autocomplete.

- **ArrayField**: Fast containment queries (`@>` operator), no JOINs, GIN indexed.
- **SuggestedTag**: Provides curated tag suggestions for the UI autocomplete. Fields: `name`, `category` (user/business/both), `usage_count`.
- Users/businesses can use any tag (free-form), but the UI suggests from `SuggestedTag` first.

### 5.3 Geo Data: Static JSON + Validated CharField

**Decision:** Curated static JSON file with ~5K major cities, keyed by ISO country code.

- **Location**: `backend/apps/core/data/cities.json` (shared between backend validation and frontend autocomplete)
- **Frontend**: Reads JSON for Country → City cascading dropdown
- **Backend**: Validates city value against JSON on model save (via model validator)
- **No extra DB tables** for geography data

**Format:**
```json
{
  "US": ["New York", "Los Angeles", "Chicago", ...],
  "GB": ["London", "Manchester", "Birmingham", ...],
  ...
}
```

### 5.4 Access Control

| Endpoint | Auth Required | Rationale |
|----------|--------------|-----------|
| Business search | No | Businesses are public entities; discovery drives platform adoption |
| User search | Yes | User profiles are private by default; auth prevents scraping |
| Tag suggestions | No | Needed for public business search filter UI |
| City suggestions | No | Needed for public business search filter UI |

### 5.5 "All" Tab Layout: Sections

**Decision:** The "All" tab shows two sections stacked vertically:
1. **Users section**: Top 4-6 results with a "See all users" link (only visible if authenticated)
2. **Businesses section**: Top 4-6 results with a "See all businesses" link

This avoids the complexity of interleaved/unified ranking across different entity types.

---

## 6. Model Changes

### 6.1 UserProfile (existing model — add fields)

| Field | Type | Details |
|-------|------|---------|
| `bio` | TextField | max_length=500, blank=True, default="" |
| `country` | CharField(2) | ISO 3166-1 alpha-2, blank=True, default="", db_index=True |
| `city` | CharField(100) | Validated against static JSON, blank=True, default="", db_index=True |
| `tags` | ArrayField(CharField(50)) | default=list, blank=True, GIN indexed |

### 6.2 BusinessAccount (existing model — add fields)

| Field | Type | Details |
|-------|------|---------|
| `city` | CharField(100) | Validated against static JSON, blank=True, default="", db_index=True |
| `is_platform_branch` | BooleanField | default=False, db_index=True |

### 6.3 BusinessProfile (existing model — add field)

| Field | Type | Details |
|-------|------|---------|
| `tags` | ArrayField(CharField(50)) | default=list, blank=True, GIN indexed |

### 6.4 SuggestedTag (new model — in `apps.core` or new `apps.explore`)

| Field | Type | Details |
|-------|------|---------|
| `id` | AutoField | Primary key |
| `name` | CharField(50) | unique, db_index=True |
| `slug` | SlugField(50) | unique, auto-generated from name |
| `category` | CharField(20) | choices: "user", "business", "both" |
| `usage_count` | PositiveIntegerField | default=0, for sorting suggestions |
| `is_active` | BooleanField | default=True |

---

## 7. API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `GET /api/v1/explore/` | GET | Public* | Combined search — returns business section + user section (user section empty if unauthenticated) |
| `GET /api/v1/explore/users/` | GET | Required | User search with text query + 5 filters, paginated |
| `GET /api/v1/explore/businesses/` | GET | Public | Business search with text query + 10 filters, paginated |
| `GET /api/v1/explore/tags/` | GET | Public | Tag autocomplete — query param: `q`, optional `category` |
| `GET /api/v1/explore/cities/` | GET | Public | City list for a country — query param: `country` (ISO code) |

### Query Parameters

**Common (users + businesses):**
- `q` — Search text (FTS + trigram)
- `page` / `page_size` — Pagination
- `ordering` — Sort field (relevance, name, newest)

**Business-specific:**
- `country` — ISO code(s), comma-separated
- `city` — City name(s), comma-separated
- `industry` — Industry value(s), comma-separated
- `company_size` — Enum value(s)
- `business_type` — Enum value(s)
- `verified` — Boolean (show only verified)
- `is_platform_branch` — Boolean
- `tags` — Tag name(s), comma-separated
- `founded_year_min` / `founded_year_max` — Year range
- `has_website` — Boolean

**User-specific:**
- `country` — ISO code(s), comma-separated
- `city` — City name(s), comma-separated
- `language` — Language code
- `verified` — Boolean (show only verified)
- `tags` — Tag name(s), comma-separated

---

## 8. Search Indexing

### FTS Search Vectors (weighted)

**User search vector:**
```sql
setweight(to_tsvector('english', username), 'A') ||
setweight(to_tsvector('english', display_name), 'A') ||
setweight(to_tsvector('english', bio), 'B') ||
setweight(to_tsvector('english', array_to_string(tags, ' ')), 'B')
```

**Business search vector:**
```sql
setweight(to_tsvector('english', display_name), 'A') ||
setweight(to_tsvector('english', legal_name), 'A') ||
setweight(to_tsvector('english', tagline), 'B') ||
setweight(to_tsvector('english', industry), 'B') ||
setweight(to_tsvector('english', array_to_string(tags, ' ')), 'B') ||
setweight(to_tsvector('english', description), 'C')
```

### Indexes Required

| Table | Index Type | Fields |
|-------|-----------|--------|
| `users_userprofile` | GIN | `tags` |
| `users_userprofile` | GIN (trgm) | `city` |
| `organization_businessprofile` | GIN | `tags` |
| `organization_businessaccount` | GIN (trgm) | `city` |
| `core_suggestedtag` | GIN (trgm) | `name` |

FTS vectors will be computed at query time (not stored) initially. If performance demands it, `SearchVectorField` can be added later with triggers.

---

## 9. Filters Summary

### Business Filters (10)

| # | Filter | Field Source | UI Control | Query Param |
|---|--------|-------------|------------|-------------|
| 1 | Country | `BusinessAccount.country` | Multi-select dropdown | `country` |
| 2 | City | `BusinessAccount.city` | Cascading autocomplete | `city` |
| 3 | Industry | `BusinessProfile.industry` | Multi-select | `industry` |
| 4 | Company Size | `BusinessProfile.company_size` | Select (enum) | `company_size` |
| 5 | Business Type | `BusinessAccount.business_type` | Select (enum) | `business_type` |
| 6 | Verified | `BusinessAccount.verification_status` | Toggle | `verified` |
| 7 | Platform Branch | `BusinessAccount.is_platform_branch` | Toggle | `is_platform_branch` |
| 8 | Tags | `BusinessProfile.tags` | Multi-select (SuggestedTag) | `tags` |
| 9 | Founded Year | `BusinessProfile.founded_year` | Range slider/inputs | `founded_year_min/max` |
| 10 | Has Website | `BusinessProfile.website != ""` | Toggle | `has_website` |

### User Filters (5)

| # | Filter | Field Source | UI Control | Query Param |
|---|--------|-------------|------------|-------------|
| 1 | Country | `UserProfile.country` | Multi-select dropdown | `country` |
| 2 | City | `UserProfile.city` | Cascading autocomplete | `city` |
| 3 | Language | `UserProfile.language` | Select | `language` |
| 4 | Verified | `User.is_verified` | Toggle | `verified` |
| 5 | Tags | `UserProfile.tags` | Multi-select (SuggestedTag) | `tags` |

---

## 10. Frontend Route & UI

### Route
- `/explore` — Inside `(public)` route group (accessible to everyone)
- Authenticated users see the full nav shell; public visitors see public topbar

### Page Structure
```
+---------------------------------------------------+
| Search bar: [🔍 Search businesses, users...]       |
+---------------------------------------------------+
| [All] [Users*] [Businesses]                        |
|                 * requires auth                     |
+---------------------------------------------------+
| Filter panel (collapsible, entity-specific)        |
+---------------------------------------------------+
| Results:                                           |
|   "All" tab → Users section + Businesses section   |
|   "Users" tab → User cards + pagination            |
|   "Businesses" tab → Business cards + pagination   |
+---------------------------------------------------+
```

### Result Cards

**Business card:** Logo, display_name, tagline, industry, country/city, verified badge, tags
**User card:** Avatar, display_name, username, bio excerpt, country/city, verified badge, tags

---

## 11. Dependencies

- PostgreSQL `pg_trgm` extension (must be enabled via migration)
- Existing models: `User`, `UserProfile`, `BusinessAccount`, `BusinessProfile`
- Existing serializers: `UserMinimalOutputSerializer`, `BusinessAccountListOutput`
- Existing pagination: `StandardPagination` from `apps.core.pagination`
- Existing public layout: `(public)/layout.tsx` with auth-aware rendering

---

## 12. Acceptance Criteria

- [ ] Business search works without authentication
- [ ] User search requires authentication (returns 401 for anonymous requests)
- [ ] Combined "All" endpoint returns both sections for authenticated users, businesses-only for anonymous
- [ ] FTS search returns relevance-ranked results for multi-word queries
- [ ] Trigram search handles typos (e.g., "amazn" finds "Amazon")
- [ ] All 10 business filters work individually and combined
- [ ] All 5 user filters work individually and combined
- [ ] Country → City cascading works with predefined city data
- [ ] Tags autocomplete suggests from SuggestedTag model
- [ ] `is_platform_branch` filter correctly filters platform branches
- [ ] Pagination works on all list endpoints
- [ ] Frontend displays 3 tabs with correct auth gating on Users tab
- [ ] Mobile-responsive filter panel
- [ ] Search performance < 300ms on typical queries
