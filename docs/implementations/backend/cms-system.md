# CMS System — Implementation Reference

**Version:** v1
**Last Updated:** 2026-02-26
**Status:** Implemented

---

## 1. Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│  API Layer (api/views.py)                                          │
│  18 views: Admin (sites 2, pages 6, templates 2, placements 3,    │
│            media 2, api-keys 2) + Public (site 1, page 1)         │
│  Admin: PlatformContextMixin + IsAuthenticated                     │
│  Public: No DRF auth — CMSApiKeyMiddleware validates X-CMS-API-KEY │
├────────────────────────────────────────────────────────────────────┤
│  Serializers (api/serializers.py)                                  │
│  9 input + 9 output serializers                                    │
├────────────────────────────────────────────────────────────────────┤
│  Middleware (middleware.py)                                         │
│  CMSApiKeyMiddleware: validates API key, attaches request.cms_site │
├────────────────────────────────────────────────────────────────────┤
│  Service Layer (services.py)                                       │
│  CMSSiteService (3), CMSTemplateService (4), CMSPageService (6),   │
│  CMSContentService (3), CMSMediaService (4), CMSApiKeyService (3)  │
│  + 7 internal helpers (versioning, media sync, export)             │
├─────────────────────┬──────────────────────────────────────────────┤
│  Policies            │  Validators (validators.py)                  │
│  (policies.py)       │  SchemaValidator: validate_schema_structure,  │
│  CMSPagePolicy (2)   │  validate_content (permissive/strict),        │
│  CMSPlacementPolicy  │  sanitize_content (nh3 rich text)             │
│  (2 methods)         │                                               │
├─────────────────────┴──────────────────────────────────────────────┤
│  Selectors (selectors.py)                                          │
│  CMSSiteSelector (3), CMSPageSelector (5), CMSTemplateSelector (5),│
│  CMSBlockPlacementSelector (3), CMSMediaSelector (6),              │
│  CMSContentVersionSelector (3), CMSApiKeySelector (2)              │
├────────────────────────────────────────────────────────────────────┤
│  Managers (managers.py)                                            │
│  SiteManager, PageManager, SectionTemplateManager,                 │
│  BlockTemplateManager, MediaFolderManager, MediaFileManager,       │
│  CMSApiKeyManager — all SoftDeleteManager subclasses               │
├────────────────────────────────────────────────────────────────────┤
│  Data Layer (models.py) — 11 models                                │
│  Site, Page, SectionTemplate, BlockTemplate,                       │
│  PageSectionPlacement, SectionBlockPlacement, ContentVersion,      │
│  MediaFolder, MediaFile, MediaUsage, CMSApiKey                     │
├────────────────────────────────────────────────────────────────────┤
│  Constants (constants.py)                                          │
│  PageStatus, BlockPlacementStatus, ContentVersionAction,           │
│  ContentLayer, CMS_FIELD_TYPES, API_KEY_PREFIX                     │
└────────────────────────────────────────────────────────────────────┘

External dependencies:
  → apps.rbac (MembershipPolicy, PlatformContextMixin, 23 CMS permissions)
  → apps.core (AuditService, exceptions, pagination, UUIDModel, AuditModel)
  → apps.users (User model, FK references)
```

---

## 2. Core Concepts & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Dual-content model | `draft_content` + `published_content` as separate JSONB fields | Allows admins to edit drafts without affecting live site; publish copies draft→published atomically |
| Placement = Instance | No separate "instance" models; SectionBlockPlacement carries content | Reduces model count; placement is the content-bearing entity |
| Schema validation modes | Permissive (draft save) + Strict (publish) | Admins can save incomplete work; publish enforces all required fields |
| Content versioning | Throttled (30s window) + retention-limited (max 50) | Prevents version explosion on autosave while maintaining rollback capability |
| Media tombstoning | Separate from soft delete | File stays accessible while published content references it; cleaned up async |
| API key auth | SHA-256 hashed, `cmsk_` prefix, plaintext returned once | Zero-knowledge storage; middleware pattern for public endpoints |
| Two-pass reorder | High offset (100000) → final values | Avoids UniqueConstraint violations on PositiveIntegerField (cannot use negative values) |
| Rich text sanitization | nh3 library | Strips unsafe HTML/scripts from richtext fields before persistence |
| owner_type/owner_id | Polymorphic ownership (same as FormTemplate) | Future-proof for business account CMS expansion |

---

## 3. Data Layer

### 3.1 Site

Location: `apps/cms/models.py`

Inherits: `UUIDModel` + `AuditModel` (soft-delete, timestamps, user stamps)

| Field | Type | Notes |
|-------|------|-------|
| `owner_type` | CharField(20, OwnerType) | PLATFORM, BUSINESS, SYSTEM |
| `owner_id` | UUIDField(null) | Account record UUID |
| `name` | CharField(255) | Display name |
| `slug` | SlugField(100) | URL-safe identifier |
| `domain` | CharField(255) | Associated domain |
| `default_locale` | CharField(10) | Default "en" |
| `metadata` | JSONField(null) | SEO defaults, theme, global config |
| `is_active` | BooleanField | Live/offline toggle |
| `homepage` | FK(Page, SET_NULL, null) | Designated homepage |

Constraints: UniqueConstraint(owner_type, owner_id, slug) WHERE is_deleted=False

### 3.2 Page

Inherits: `UUIDModel` + `AuditModel`

| Field | Type | Notes |
|-------|------|-------|
| `site` | FK(Site, CASCADE) | Parent site |
| `title` | CharField(255) | Page title |
| `slug` | SlugField(100) | Per-site unique |
| `path` | CharField(500) | URL path (e.g., /about) |
| `page_type` | CharField(50) | landing, content, legal, blog_post |
| `metadata` | JSONField(null) | SEO, OG tags |
| `status` | CharField(20, PageStatus) | DRAFT, PUBLISHED, ARCHIVED |
| `published_at` | DateTimeField(null) | Last publish timestamp |
| `order` | PositiveIntegerField | Position within site |
| `is_required` | BooleanField | Blocks delete/hide if true |
| `is_visible` | BooleanField | Admin toggle (only if !is_required) |

Constraints: 3 UniqueConstraints (site+slug, site+path, site+order) WHERE is_deleted=False

### 3.3 SectionTemplate

Inherits: `UUIDModel` + `AuditModel`

| Field | Type | Notes |
|-------|------|-------|
| `name` | CharField(255) | Internal name |
| `display_name` | CharField(255) | Admin UI label |
| `slug` | SlugField(100) | Globally unique |
| `section_type` | CharField(50) | header, content, footer, sidebar |
| `ui_config` | JSONField(null) | Rendering hints |

### 3.4 BlockTemplate

Inherits: `UUIDModel` + `AuditModel`

| Field | Type | Notes |
|-------|------|-------|
| `name` | CharField(255) | Internal name |
| `display_name` | CharField(255) | Admin UI label |
| `slug` | SlugField(100) | Globally unique |
| `block_type` | CharField(50) | text, media, composite, repeater |
| `schema` | JSONField | Field definitions with validation rules |
| `schema_version` | PositiveIntegerField | Auto-increments on schema change |
| `default_content` | JSONField(null) | Pre-populate new placements |

### 3.5 PageSectionPlacement

Inherits: `UUIDModel` + `TimeStampedModel` (no user stamps, no soft delete)

| Field | Type | Notes |
|-------|------|-------|
| `page` | FK(Page, CASCADE) | Parent page |
| `template` | FK(SectionTemplate, PROTECT) | Layout blueprint |
| `label` | CharField(255) | Admin-friendly label |
| `order` | PositiveIntegerField | Unique per page |
| `is_required/is_visible` | BooleanField | Visibility controls |

### 3.6 SectionBlockPlacement

Inherits: `UUIDModel` + `UserStampedModel` (created_by, updated_by, timestamps)

| Field | Type | Notes |
|-------|------|-------|
| `section_placement` | FK(PageSectionPlacement, CASCADE) | Parent section |
| `template` | FK(BlockTemplate, PROTECT) | Schema blueprint |
| `order` | PositiveIntegerField | Unique per section |
| `draft_content` | JSONField(null) | Working copy — admin edits this |
| `published_content` | JSONField(null) | Frozen live copy — set on publish |
| `status` | CharField(BlockPlacementStatus) | DRAFT or PUBLISHED |
| `schema_version_validated` | PositiveIntegerField | Last validated schema version |

### 3.7 ContentVersion

Inherits: `UUIDModel` only (own created_at, created_by)

| Field | Type | Notes |
|-------|------|-------|
| `block_placement` | FK(SectionBlockPlacement, CASCADE) | Source |
| `content_snapshot` | JSONField | Full copy of draft_content |
| `version_number` | PositiveIntegerField | Auto-incrementing per placement |
| `action` | CharField(ContentVersionAction) | draft_save, publish, rollback, import |
| `created_by` | FK(User, PROTECT) | Who made this change |
| `notes` | TextField | Optional change description |

### 3.8 MediaFolder, MediaFile, MediaUsage

- **MediaFolder** (UUIDModel + AuditModel): Nested folders with owner_type/owner_id, self-FK parent, materialized path
- **MediaFile** (UUIDModel + AuditModel): Storage key, MIME type, dimensions, alt_text, `is_tombstoned` flag
- **MediaUsage** (UUIDModel + TimeStampedModel): Tracks (media_file, block_placement, field_key, content_layer) references

### 3.9 CMSApiKey

Inherits: `UUIDModel` + `AuditModel`

| Field | Type | Notes |
|-------|------|-------|
| `site` | FK(Site, CASCADE) | Scoped to site |
| `name` | CharField(255) | Descriptive label |
| `key_prefix` | CharField(16) | First 12 chars for display |
| `key_hash` | CharField(64, unique) | SHA-256 hash |
| `allowed_origins` | JSONField(list) | CORS restriction |
| `is_active` | BooleanField | Active toggle |
| `expires_at` | DateTimeField(null) | Optional expiration |
| `rate_limit` | PositiveIntegerField | Requests/minute (default 60) |

### Migrations

- `cms/0001_initial.py` — All 11 models with constraints and indexes
- `rbac/0004_seed_cms_permissions.py` — Seeds 23 CMS permissions into Permission table

---

## 4. Service Layer

### 4.1 CMSSiteService (3 methods)

| Method | Returns | Notes |
|--------|---------|-------|
| `create_site` | Site | Validates uniqueness, sets owner_type/owner_id |
| `update_site` | Site | Allows name, domain, description, metadata, is_active |
| `delete_site` | None | Soft delete |

### 4.2 CMSTemplateService (4 methods)

| Method | Returns | Notes |
|--------|---------|-------|
| `create_section_template` | SectionTemplate | Validates slug uniqueness |
| `create_block_template` | BlockTemplate | Validates schema structure |
| `update_block_schema` | BlockTemplate | Increments schema_version, logs change |
| `reorder_section_placements` | None | Two-pass atomic reorder |
| `reorder_block_placements` | None | Two-pass atomic reorder |

### 4.3 CMSPageService (6 methods)

| Method | Returns | Notes |
|--------|---------|-------|
| `create_page` | Page | Status=DRAFT, validates slug uniqueness |
| `reorder_pages` | None | Two-pass atomic reorder |
| `publish_page` | Page | Validates ALL blocks, copies draft→published atomically |
| `unpublish_page` | Page | Reverts to DRAFT (published_content preserved) |
| `export_page` | dict | Full tree JSON with export_version "3.1" |
| `import_page` | Page | Content-only import, matches by UUID |

### 4.4 CMSContentService (3 methods)

| Method | Returns | Notes |
|--------|---------|-------|
| `update_draft_content` | SectionBlockPlacement | Sanitize → validate (permissive) → save → version (throttled) |
| `rollback_content` | SectionBlockPlacement | Restores from ContentVersion snapshot |
| `toggle_visibility` | SectionBlockPlacement | Blocks hiding required placements |

### 4.5 CMSMediaService (4 methods)

| Method | Returns | Notes |
|--------|---------|-------|
| `upload_file` | MediaFile | Saves to default_storage, creates record |
| `delete_file` | MediaFile | Tombstones if published refs exist, else soft-deletes |
| `delete_folder` | None | Recursive soft-delete of children |
| `cleanup_tombstoned` | int | Celery task: removes files with zero published refs |

### 4.6 CMSApiKeyService (3 methods)

| Method | Returns | Notes |
|--------|---------|-------|
| `create_api_key` | (CMSApiKey, str) | Returns plaintext ONCE |
| `revoke_api_key` | CMSApiKey | Sets is_active=False + soft-delete |
| `validate_api_key` | CMSApiKey | Checks exists, active, not expired |

### 4.7 Selectors (7 classes, 27 methods)

| Class | Methods | Key Patterns |
|-------|---------|--------------|
| `CMSSiteSelector` | 3 | get_by_slug, get_by_id, list_for_owner |
| `CMSPageSelector` | 5 | get_by_slug, get_by_id, get_with_full_tree (3-level prefetch), list_by_site, list_published_for_site |
| `CMSTemplateSelector` | 5 | get_section/block by slug/id, list section/block templates |
| `CMSBlockPlacementSelector` | 3 | get_by_id (select_related 2 levels), list_for_section, list_for_page |
| `CMSMediaSelector` | 6 | get_file_by_id, list_files, get_usage, list_folders, get_folder_by_slug/id |
| `CMSContentVersionSelector` | 3 | list_for_placement, get_version, get_latest_version |
| `CMSApiKeySelector` | 2 | get_by_hash, list_for_site |

---

## 5. API Layer

### 5.1 Admin Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/cms/admin/sites/` | GET, POST | List/create sites |
| `/api/v1/cms/admin/sites/{slug}/` | GET, PATCH, DELETE | Site detail/update/delete |
| `/api/v1/cms/admin/pages/` | GET, POST | List/create pages |
| `/api/v1/cms/admin/pages/{slug}/` | GET | Page detail (supports ?depth=full) |
| `/api/v1/cms/admin/pages/{slug}/publish/` | POST | Validate & publish page |
| `/api/v1/cms/admin/pages/{slug}/unpublish/` | POST | Revert to draft |
| `/api/v1/cms/admin/pages/{slug}/export/` | POST | Export page tree as JSON |
| `/api/v1/cms/admin/pages/{slug}/import/` | POST | Import page content |
| `/api/v1/cms/admin/templates/sections/` | GET, POST | List/create section templates |
| `/api/v1/cms/admin/templates/blocks/` | GET, POST | List/create block templates |
| `/api/v1/cms/admin/block-placements/{uuid}/` | GET, PATCH | Get/update draft content |
| `/api/v1/cms/admin/block-placements/{uuid}/history/` | GET | Content version history |
| `/api/v1/cms/admin/block-placements/{uuid}/rollback/{version_number}/` | POST | Rollback to version |
| `/api/v1/cms/admin/media/files/` | GET, POST | List/upload files |
| `/api/v1/cms/admin/media/files/{uuid}/` | GET, PATCH, DELETE | File detail/update/delete |
| `/api/v1/cms/admin/api-keys/` | GET, POST | List/create API keys |
| `/api/v1/cms/admin/api-keys/{uuid}/` | DELETE | Revoke API key |

### 5.2 Public Endpoints (API key required)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/cms/public/sites/{slug}/` | GET | Published site info |
| `/api/v1/cms/public/pages/{slug}/` | GET | Published page (supports ?depth=full) |

---

## 6. Types & Constants

| Constant | Values/Notes |
|----------|-------------|
| `PageStatus` | DRAFT, PUBLISHED, ARCHIVED |
| `BlockPlacementStatus` | DRAFT, PUBLISHED |
| `ContentVersionAction` | DRAFT_SAVE, PUBLISH, ROLLBACK, IMPORT |
| `ContentLayer` | DRAFT, PUBLISHED |
| `CMS_FIELD_TYPES` | 18 types (text, richtext, media, repeater, etc.) |
| `VERSION_THROTTLE_SECONDS` | 30 |
| `MAX_VERSIONS_PER_PLACEMENT` | 50 |
| `MAX_FOLDER_DEPTH` | 5 |
| `API_KEY_PREFIX` | "cmsk_" |

---

## 7. Key Flows

### Flow 1: Publish Page (Atomic)
1. Acquire locks: `select_for_update()` on page, section placements, block placements
2. Validate ALL visible/required blocks against their template schemas (strict mode)
3. If any validation errors: raise ValidationError with `publish_errors` detail
4. Copy `draft_content → published_content` on all block placements
5. Set status=PUBLISHED, create content versions (action=publish)
6. Sync media usage for published layer
7. Update page status and published_at timestamp

### Flow 2: Draft Content Save (Throttled)
1. Sanitize content (nh3 for richtext fields)
2. Validate permissively (warnings only, no errors)
3. Update `draft_content` on block placement
4. Create or update content version:
   - If latest version is <30s old, same user, same action → update in-place
   - Otherwise → create new version
5. Prune versions beyond MAX_VERSIONS_PER_PLACEMENT
6. Sync media usage for draft layer

### Flow 3: API Key Authentication (Public API)
1. Request hits `/api/v1/cms/public/` path
2. CMSApiKeyMiddleware extracts `X-CMS-API-KEY` header
3. Hashes key with SHA-256, looks up in `cms_api_key` table
4. Validates: exists, is_active, not expired
5. Attaches `request.cms_site` (the key's associated site)
6. Updates `last_used_at` timestamp
7. View uses `request.cms_site` for scoped queries

### Flow 4: Media Deletion (Tombstone Pattern)
1. Check `MediaUsage` for published-layer references
2. If published refs exist → tombstone (set `is_tombstoned=True`, null draft refs)
3. If no published refs → soft-delete immediately
4. Celery task periodically scans tombstoned files
5. If tombstoned file has zero published refs → delete from storage + hard-delete record

---

## 8. Permissions & Authorization

| Action | RBAC Permission | Audit Action |
|--------|----------------|--------------|
| Create site | `can_create_cms_site` | `CMS_SITE_CREATED` |
| Edit site | `can_edit_cms_site` | `CMS_SITE_UPDATED` |
| Delete site | `can_delete_cms_site` | `CMS_SITE_DELETED` |
| Create page | `can_create_cms_page` | `CMS_PAGE_CREATED` |
| Edit page | `can_edit_cms_page` | `CMS_PAGE_UPDATED` |
| Delete page | `can_delete_cms_page` | `CMS_PAGE_DELETED` |
| Publish content | `can_publish_cms_content` | `CMS_PAGE_PUBLISHED` |
| Unpublish content | `can_publish_cms_content` | `CMS_PAGE_UNPUBLISHED` |
| Edit content | `can_edit_cms_content` | `CMS_CONTENT_DRAFT_SAVED` |
| Rollback content | `can_rollback_cms_content` | `CMS_CONTENT_ROLLBACK` |
| Toggle visibility | `can_toggle_cms_visibility` | `CMS_VISIBILITY_TOGGLED` |
| Export page | `can_export_cms_content` | `CMS_PAGE_EXPORTED` |
| Import page | `can_import_cms_content` | `CMS_PAGE_IMPORTED` |
| Create template | `can_create_cms_template` | `CMS_*_TEMPLATE_CREATED` |
| Edit template | `can_edit_cms_template` | `CMS_BLOCK_SCHEMA_CHANGED` |
| Upload media | `can_upload_cms_media` | `CMS_MEDIA_UPLOADED` |
| Delete media | `can_delete_cms_media` | `CMS_MEDIA_DELETED` / `CMS_MEDIA_TOMBSTONED` |
| Create API key | `can_create_cms_api_key` | `CMS_API_KEY_CREATED` |
| Revoke API key | `can_revoke_cms_api_key` | `CMS_API_KEY_REVOKED` |

23 total permissions seeded via `rbac/migrations/0004_seed_cms_permissions.py`.
28 total audit actions added to `AuditLog.Action` choices.

---

## 9. Configuration & Gotchas

### Gotchas
- **PositiveIntegerField reorder**: Cannot use negative values in two-pass reorder. Use high offset (100000+) for pass 1, then final values in pass 2.
- **DRF URLPathVersioning**: Intercepts URL kwargs named `version`. Never name URL parameters `version` — use `version_number` instead.
- **soft_delete() signature**: `soft_delete(self, user=None)`, NOT `soft_delete(deleted_by=...)`.
- **BusinessRuleViolation.rule**: Stored in `exc.value.details["rule"]`, not `exc.value.rule`.
- **AccountContextMixin.get_actor_context()**: Takes NO arguments — uses `self.request` internally.
- **ValidationError details**: Constructor only accepts `message`, `field`, `value`. Set `.details` dict manually after creation for publish errors.
- **nh3 package**: Required for rich text sanitization in `SchemaValidator.sanitize_content()`.
- **CMS permissions**: Must be seeded via data migration — RBAC's `initialize_platform_account` assigns all Permission records to owner role.

---

## 10. Testing

| Module | Tests | Coverage |
|--------|-------|----------|
| test_models.py | 15 | Models, properties, __str__, constraints, soft-delete |
| test_validators.py | 34 | Schema validation, content validation (permissive/strict), sanitization |
| test_selectors.py | 20 | All 7 selector classes, filters, edge cases |
| test_services.py | 30 | All 6 service classes, state transitions, error paths |
| test_policies.py | 8 | Page delete/hide, section/block placement hide policies |
| test_views.py | 40 | Admin (14 classes) + Public (2 classes), auth, API keys |
| conftest.py | — | 10+ fixtures (site, page, templates, placements, published_page, etc.) |
| factories.py | — | 10 factories (Site, Page, SectionTemplate, BlockTemplate, placements, versions, media, API key) |
| **Total** | **165** | **All passing** |

Full suite: 2591 passed, 3 skipped, 0 failures.

---

## 11. File Summary

### New Files

| File | Description |
|------|-------------|
| `apps/cms/__init__.py` | App init |
| `apps/cms/apps.py` | CMSConfig |
| `apps/cms/constants.py` | PageStatus, BlockPlacementStatus, ContentVersionAction, ContentLayer, CMS_FIELD_TYPES |
| `apps/cms/models.py` | 11 models with constraints and indexes |
| `apps/cms/managers.py` | 7 SoftDeleteManager subclasses |
| `apps/cms/selectors.py` | 7 selector classes (27 methods) |
| `apps/cms/services.py` | 6 service classes (23 methods) + 7 internal helpers |
| `apps/cms/validators.py` | SchemaValidator (validate_schema_structure, validate_content, sanitize_content) |
| `apps/cms/policies.py` | CMSPagePolicy, CMSPlacementPolicy |
| `apps/cms/middleware.py` | CMSApiKeyMiddleware |
| `apps/cms/admin.py` | Django Admin with inlines |
| `apps/cms/tasks.py` | Celery tasks (cleanup_tombstoned_media) |
| `apps/cms/api/__init__.py` | API package |
| `apps/cms/api/serializers.py` | 9 input + 9 output serializers |
| `apps/cms/api/views.py` | 18 API views |
| `apps/cms/api/urls.py` | Admin URL routing |
| `apps/cms/api/urls_public.py` | Public URL routing |
| `apps/cms/migrations/0001_initial.py` | Initial migration |
| `apps/cms/tests/` | 8 test files (factories, conftest, 6 test modules) |
| `apps/rbac/migrations/0004_seed_cms_permissions.py` | Seeds 23 CMS permissions |

### Modified Files

| File | Change |
|------|--------|
| `apps/core/observability/audit/models.py` | Added 28 CMS audit actions |
| `apps/rbac/permissions/registry.py` | Added 23 CMS permission registrations |
| `backend_core/settings/base.py` | Added `"apps.cms"` to INSTALLED_APPS |
| `backend_core/urls.py` | Added CMS URL includes (admin + public) |

---

## 12. Known Limitations

1. **No page PATCH/DELETE views**: Page update and deletion are service-layer only — no admin views wired yet.
2. **No media folder CRUD views**: Folders can be created via services but no API views exist.
3. **No import view tests**: The import endpoint exists but tests focus on export.
4. **Media upload requires real storage**: upload_file uses `default_storage.save()` — local testing needs FileSystemStorage or mock.

---

## 13. vNext TODOs

| Item | Context | Priority |
|------|---------|----------|
| Wire page PATCH/DELETE admin views | Service methods exist | P1 |
| Add media folder CRUD views | MediaSelector has all methods | P1 |
| Add reorder views (pages, sections, blocks) | Service methods exist, need view + URL | P2 |
| Add media MIME type validation | Currently trusts `file.content_type` | P2 |
| Add origin checking in middleware | `allowed_origins` field exists but not enforced | P3 |

---

## 14. Changelog

### v1 (2026-02-26)
- Initial implementation: 11 models, 7 managers, 7 selectors, 6 services, validators, policies, middleware, admin, celery tasks
- 18 API views (admin + public), 18 serializers
- 23 RBAC permissions (seeded via migration), 28 audit actions
- 165 tests, all passing
- Bugs found and fixed during testing:
  - `get_actor_context(request)` → `get_actor_context()` (no args)
  - `soft_delete(deleted_by=)` → `soft_delete(user=)`
  - PositiveIntegerField reorder: negative values → high offset
  - DRF URLPathVersioning: `<int:version>` → `<int:version_number>`
  - Missing owner_type/owner_id in create site view
  - CMS permissions not in DB → data migration
