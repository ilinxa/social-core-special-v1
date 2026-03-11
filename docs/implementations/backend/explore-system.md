# Explore System — Backend Implementation Reference

**Version:** v1
**Last Updated:** 2026-03-03
**Status:** Implemented

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (views.py)                  │
│  ExploreCombinedView  ExploreBusinessSearchView          │
│  ExploreUserSearchView  TagSuggestView  CityListView    │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  Serializers (serializers.py)            │
│  ExploreBusinessOutput  ExploreUserOutput                │
│  ExploreCombinedOutput  SuggestedTagOutput               │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  Selectors (selectors.py)                │
│  ExploreSelector.search_businesses()                     │
│  ExploreSelector.search_users()                          │
│  ExploreSelector.suggest_tags()                          │
│  (FTS + Trigram + Filters → QuerySet)                   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  Models (models.py)                      │
│  SuggestedTag                                            │
│  + UserProfile (bio, country, city, tags)                │
│  + BusinessAccount (city, is_platform_branch)            │
│  + BusinessProfile (tags)                                │
└─────────────────────────────────────────────────────────┘
```

No service layer — Explore is read-only (selectors + views only).

## 2. Core Concepts & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Search technology | PostgreSQL FTS + pg_trgm | No external dependency (Elasticsearch), good enough for <100K records, built-in to PostgreSQL |
| Tag storage | JSONField (not ArrayField) | ArrayField breaks SQLite migrations used in unit tests. JSONField works on both |
| Tag filtering | `__contains` with `reduce(operator.or_)` | Replacement for ArrayField's `__overlap` operator. Works with JSONField on both SQLite and PostgreSQL |
| City data | Static JSON file (`cities.json`) | No extra table/migration, `lru_cache` for performance, ~500KB for 3551 cities across 205 countries |
| User search auth | IsAuthenticated | Business directory is public; user directory requires login for privacy |
| Combined endpoint | Top 6 per section | "All" tab shows preview; dedicated tabs for full pagination |
| Search ranking | `Greatest(FTS, Trigram * 0.5)` | FTS for exact/stemmed matches, trigram for typo tolerance. Trigram scaled down to not overshadow FTS |

## 3. Data Layer

### 3.1 SuggestedTag

Location: `apps/explore/models.py`

| Field | Type | Notes |
|-------|------|-------|
| `id` | AutoField | PK (not UUID) |
| `name` | CharField(50) | unique, db_index |
| `slug` | SlugField(50) | unique, auto-generated from name |
| `category` | CharField(20) | choices: user, business, both |
| `usage_count` | PositiveIntegerField | default=0, for ordering |
| `is_active` | BooleanField | default=True, soft-deactivation |

Ordering: `-usage_count`, `name`

### 3.2 UserProfile (modified fields)

Location: `apps/users/models.py`

| Field | Type | Notes |
|-------|------|-------|
| `bio` | TextField | max_length=500, blank=True, default="" |
| `country` | CharField(2) | ISO 3166-1 alpha-2, blank=True, default="", db_index |
| `city` | CharField(100) | blank=True, default="", db_index |
| `tags` | JSONField | default=list, blank=True |

GIN index: `userprofile_tags_gin` on `tags`.

### 3.3 BusinessAccount (modified fields)

Location: `apps/organization/business/models.py`

| Field | Type | Notes |
|-------|------|-------|
| `city` | CharField(100) | blank=True, default="", db_index |
| `is_platform_branch` | BooleanField | default=False, db_index |

### 3.4 BusinessProfile (modified fields)

Location: `apps/organization/business/models.py`

| Field | Type | Notes |
|-------|------|-------|
| `tags` | JSONField | default=list, blank=True |

GIN index: `bizprofile_tags_gin` on `tags`.

### Migrations

- `explore/0001_initial.py` — TrigramExtension + SuggestedTag model
- `explore/0002_seed_suggested_tags.py` — Seeds 50 initial tags (technology, saas, healthcare, etc.)
- `organization/0003_explore_fields.py` — BusinessAccount city/is_platform_branch + BusinessProfile tags
- `users/0008_explore_fields.py` — UserProfile bio/country/city/tags

## 4. Selectors

Location: `apps/explore/selectors.py`

### 4.1 ExploreSelector.search_businesses()

| Arg | Type | Default | Notes |
|-----|------|---------|-------|
| `query` | str | "" | FTS + trigram search text |
| `country` | list[str] \| None | None | `country__in` filter |
| `city` | list[str] \| None | None | `city__in` filter |
| `industry` | list[str] \| None | None | `profile__industry__in` |
| `company_size` | list[str] \| None | None | `profile__company_size__in` |
| `business_type` | list[str] \| None | None | `business_type__in` |
| `verified` | bool \| None | None | `verification_status=VERIFIED` |
| `is_platform_branch` | bool \| None | None | exact match |
| `tags` | list[str] \| None | None | `profile__tags__contains` with OR |
| `founded_year_min` | int \| None | None | `profile__founded_year__gte` |
| `founded_year_max` | int \| None | None | `profile__founded_year__lte` |
| `has_website` | bool \| None | None | exclude empty website |
| `ordering` | str | "relevance" | relevance, name, newest |

**Base queryset:** `BusinessAccount.objects.filter(status=ACTIVE, is_deleted=False, profile__is_public=True).select_related("profile")`

**FTS search vector weights:** display_name (A), legal_name (A), tagline (B), industry (B), description (C)

**Returns:** `QuerySet[BusinessAccount]` annotated with `search_rank`.

### 4.2 ExploreSelector.search_users()

| Arg | Type | Default | Notes |
|-----|------|---------|-------|
| `query` | str | "" | FTS + trigram |
| `country` | list[str] \| None | None | `profile__country__in` |
| `city` | list[str] \| None | None | `profile__city__in` |
| `language` | str \| None | None | `profile__language` exact |
| `verified` | bool \| None | None | `is_verified=True` |
| `tags` | list[str] \| None | None | `profile__tags__contains` with OR |
| `ordering` | str | "relevance" | relevance, name, newest |

**Base queryset:** `User.objects.filter(is_active=True).select_related("profile")`

**FTS search vector weights:** username (A), first_name (A), last_name (A), bio (B)

### 4.3 ExploreSelector.suggest_tags()

| Arg | Type | Default | Notes |
|-----|------|---------|-------|
| `query` | str | "" | trigram similarity on name |
| `category` | str \| None | None | "user"/"business" (includes "both") |
| `limit` | int | 20 | max results |

## 5. API Layer

### 5.1 Endpoints

| Endpoint | Method | Permission | Description |
|----------|--------|------------|-------------|
| `/api/v1/explore/` | GET | AllowAny | Combined: top 6 businesses + top 6 users (users only if authenticated) |
| `/api/v1/explore/businesses/` | GET | AllowAny | Paginated business search with 10+ filters |
| `/api/v1/explore/users/` | GET | IsAuthenticated | Paginated user search with 5 filters |
| `/api/v1/explore/tags/` | GET | AllowAny | Tag autocomplete: `?q=`, `?category=` |
| `/api/v1/explore/cities/` | GET | AllowAny | City list: `?country=US` |

### 5.2 Serializers

Location: `apps/explore/serializers.py`

| Serializer | Type | Fields |
|------------|------|--------|
| `ExploreBusinessProfileOutput` | Output | display_name, tagline, logo, industry, company_size, tags, website |
| `ExploreBusinessOutput` | Output | id, slug, legal_name, country, city, business_type, is_platform_branch, is_verified, profile, search_rank |
| `ExploreUserProfileOutput` | Output | first_name, last_name, bio, avatar_url, country, city, tags |
| `ExploreUserOutput` | Output | id, username, is_verified, display_name, profile, search_rank |
| `ExploreCombinedOutput` | Output | users[], businesses[], users_count, businesses_count |
| `SuggestedTagOutput` | Output | id, name, slug, category, usage_count |
| `CityListOutput` | Output | country, cities[] |

**Note:** `profile` in `ExploreUserOutput` can be `null` when a user has no UserProfile record. DRF renders nested serializer as null for missing reverse OneToOneField.

### 5.3 URLs

Location: `apps/explore/urls.py` (namespace: `explore`)

Included in main urls.py: `path("api/v1/explore/", include("apps.explore.urls", namespace="explore"))`

## 6. Utilities

### City Data Loader

Location: `apps/core/utils/city_data.py`

| Function | Returns | Notes |
|----------|---------|-------|
| `load_city_data()` | `dict[str, list[str]]` | `@lru_cache(maxsize=1)`, reads `cities.json` |
| `get_cities_for_country(code)` | `list[str]` | Empty list for unknown countries |
| `get_all_countries()` | `list[str]` | Sorted ISO codes |
| `is_valid_city(code, city)` | `bool` | Case-insensitive lookup |

Data file: `apps/core/data/cities.json` (~500KB, 205 countries, 3551 cities)

## 7. Key Flows

### Flow 1: Public Business Search

1. Anonymous user visits `/explore?tab=businesses&q=tech&industry=Technology`
2. `ExploreBusinessSearchView.get()` extracts params via `_extract_business_params()`
3. Calls `ExploreSelector.search_businesses(query="tech", industry=["Technology"])`
4. Selector builds FTS SearchVector + SearchQuery + TrigramSimilarity, filters by industry, returns QuerySet
5. View paginates via `StandardPagination`, serializes with `ExploreBusinessOutput`
6. Returns paginated response with `search_rank` per result

### Flow 2: Combined "All" Tab

1. User visits `/explore` (All tab)
2. `ExploreCombinedView.get()` calls `search_businesses(query=q)[:6]` and (if authenticated) `search_users(query=q)[:6]`
3. Returns `businesses`, `users`, `businesses_count`, `users_count`
4. Anonymous users get `users: []` and `users_count: 0`

### Flow 3: Tag Autocomplete

1. User types "tec" in tag input
2. Frontend calls `GET /explore/tags/?q=tec&category=business`
3. `ExploreSelector.suggest_tags(query="tec", category="business")` uses TrigramSimilarity on tag name
4. Returns matching tags ordered by similarity then usage_count

### Flow 4: City Cascading Select

1. User selects country "US" in country dropdown
2. Frontend calls `GET /explore/cities/?country=US`
3. `ExploreCityListView.get()` calls `get_cities_for_country("US")` from cached JSON
4. Returns `{ country: "US", cities: ["New York", "Los Angeles", ...] }`

## 8. Configuration & Gotchas

### Settings
| Setting | Location | Value | Notes |
|---------|----------|-------|-------|
| `django.contrib.postgres` | INSTALLED_APPS in base.py | Required | For FTS, ArrayField, GinIndex, pg_trgm |
| `apps.explore` | INSTALLED_APPS in base.py | Required | After `apps.cms` |

### Gotchas

- **JSONField vs ArrayField:** Tags use `JSONField` (not `ArrayField`) because ArrayField breaks SQLite migrations used in unit tests. Tag filtering uses `__contains` with `reduce(operator.or_)` instead of `__overlap`.
- **pg_trgm extension:** Created by `0001_initial.py` migration via `TrigramExtension()`. Requires PostgreSQL superuser or `CREATE EXTENSION` privilege.
- **Null profiles in API response:** `ExploreUserOutput.profile` is `null` when user has no UserProfile record (reverse OneToOneField). Frontend must handle this.
- **Selector tests require PostgreSQL:** FTS, Trigram, and `__contains` on JSONField don't work on SQLite. Selector tests are marked with `requires_postgres` and skipped in unit test suite. Run via `make test-api`.
- **Seed data conflicts in tests:** Migration `0002_seed_suggested_tags.py` seeds ~50 tags. Test factories must use unique names (e.g., prefix with "test-") to avoid `UNIQUE constraint` violations.

## 9. Testing

### Test Strategy

| SQLite (unit tests) | PostgreSQL (integration) |
|---------------------|--------------------------|
| View tests (mock selectors) | Selector tests (real FTS/trigram) |
| Model tests (SuggestedTag CRUD) | Full API integration |
| City data tests | |

### Test Counts

| Module | Tests | Status |
|--------|-------|--------|
| `test_models.py` | 5 | Pass |
| `test_views.py` | 11 | Pass |
| `test_city_data.py` | 9 | Pass |
| `test_selectors.py` | 33 | Skipped on SQLite, pass on PostgreSQL |
| **Total** | **58** (25 active + 33 skipped) | **Pass** |

```bash
# Unit tests (SQLite, selector tests skipped)
powershell -Command "Set-Location backend; & .\venv\Scripts\python.exe -m pytest apps/explore/ -v"

# Integration tests (PostgreSQL, full suite)
make test-api
```

## 10. File Summary

### New Files

| File | Description |
|------|-------------|
| `apps/explore/__init__.py` | App init |
| `apps/explore/apps.py` | ExploreConfig |
| `apps/explore/models.py` | SuggestedTag model |
| `apps/explore/selectors.py` | FTS + trigram search selectors |
| `apps/explore/serializers.py` | 7 output serializers |
| `apps/explore/views.py` | 5 API views |
| `apps/explore/urls.py` | URL routing |
| `apps/explore/migrations/0001_initial.py` | TrigramExtension + SuggestedTag |
| `apps/explore/migrations/0002_seed_suggested_tags.py` | Seeds 50 tags |
| `apps/explore/tests/conftest.py` | Fixtures, requires_postgres marker |
| `apps/explore/tests/factories.py` | SuggestedTagFactory |
| `apps/explore/tests/test_models.py` | SuggestedTag CRUD tests |
| `apps/explore/tests/test_selectors.py` | FTS/trigram/filter tests (PostgreSQL) |
| `apps/explore/tests/test_views.py` | View tests (mocked selectors) |
| `apps/explore/tests/test_city_data.py` | City data loader tests |
| `apps/core/data/cities.json` | Static city data (205 countries, 3551 cities) |
| `apps/core/utils/city_data.py` | City data loader with lru_cache |

### Modified Files

| File | Change |
|------|--------|
| `backend_core/settings/base.py` | Added `django.contrib.postgres` + `apps.explore` to INSTALLED_APPS |
| `backend_core/urls.py` | Added explore URL include |
| `apps/users/models.py` | Added bio, country, city, tags to UserProfile |
| `apps/organization/business/models.py` | Added city, is_platform_branch to BusinessAccount; tags to BusinessProfile |
| `apps/users/serializers.py` | Added new fields to output + input serializers |
| `apps/organization/business/serializers.py` | Added new fields to output + input serializers |
| `apps/users/tests/factories.py` | Added defaults for bio, country, city, tags |
| `apps/organization/tests/factories.py` | Added defaults for city, is_platform_branch, tags |

## 11. Known Limitations

1. **No search index caching** — FTS queries hit the database directly. For high-traffic, consider materialized views or search index.
2. **No tag usage tracking** — `usage_count` on SuggestedTag is seeded statically, not auto-updated when users apply tags.
3. **No saved searches** — Users can't bookmark or save search queries server-side.
4. **Single-language FTS** — `SearchQuery` uses default (English) text search config. No multi-language support.

## 12. vNext TODOs

| Item | Context | Priority |
|------|---------|----------|
| Auto-update tag usage counts | Celery periodic task or signal on profile save | P2 |
| Search analytics | Track popular queries for discovery improvement | P2 |
| Geolocation search | PostgreSQL PostGIS for distance-based filtering | P3 |
| Elasticsearch migration | When record count exceeds PostgreSQL FTS performance limits | P3 |

## 13. Changelog

### v1 (2026-03-03)
- Initial implementation: FTS + trigram search, 5 endpoints, 50 seeded tags, static city data
- 10 business filters, 5 user filters
- Public business search, authenticated user search
