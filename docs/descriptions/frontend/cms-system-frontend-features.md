# CMS System — Frontend Features & Developer Checklist

**Version:** v1.1 (reviewed 2026-03-29)
**Created:** 2026-03-29
**Backend Reference:** `docs/implementations/backend/cms-system.md`
**Backend Plan:** `docs/plans/backend/cms_business_access/cms_business_access_plan.md`
**Existing Frontend Stubs:** 6 placeholder pages, navigation config, permission hooks

---

## Table of Contents

1. [Architecture Overview & Scope](#1-architecture-overview--scope)
2. [Types & Enums](#2-types--enums)
3. [API Client Layer](#3-api-client-layer)
4. [Query Keys & Hooks](#4-query-keys--hooks)
5. [Feature Gate Degradation](#5-feature-gate-degradation)
6. [Tier 1.5 Permission Integration](#6-tier-15-permission-integration)
7. [Navigation & Routing](#7-navigation--routing)
8. [Template Catalog & Library](#8-template-catalog--library)
9. [Site Management](#9-site-management)
10. [Page Management](#10-page-management)
11. [Content Editing (Block Placements)](#11-content-editing-block-placements)
12. [Content Versioning & Rollback](#12-content-versioning--rollback)
13. [Publish / Unpublish Flow](#13-publish--unpublish-flow)
14. [Export / Import](#14-export--import)
15. [Media Library](#15-media-library)
16. [API Key Management](#16-api-key-management)
17. [Platform CMS Admin — Business Management](#17-platform-cms-admin--business-management)
18. [CMS Activation Request Flow](#18-cms-activation-request-flow)
19. [State Management](#19-state-management)
20. [Constants & Display Config](#20-constants--display-config)
21. [Error Handling & Edge Cases](#21-error-handling--edge-cases)
22. [Accessibility](#22-accessibility)
23. [Responsive / Mobile](#23-responsive--mobile)
24. [Testing](#24-testing)

---

## 1. Architecture Overview & Scope

### Three API Surfaces

The CMS has three separate API surfaces, each serving a different context:

| Surface | Prefix | Auth | Who Uses It |
|---------|--------|------|-------------|
| **Platform Admin** | `/api/v1/cms/admin/` | JWT + `platform.cms` gate | Platform members managing CMS |
| **Business** | `/api/v1/cms/business/<slug>/` | JWT + `business.cms.enabled` gate + `cms_enabled` flag | Business members managing their CMS |
| **Public** | `/api/v1/cms/public/` | `X-CMS-API-Key` header | External websites rendering content |

**The frontend consumes Platform Admin + Business APIs.** The Public API is consumed by external client-side apps (not this frontend).

### Four-Layer Access Model (Business Context)

```
Layer 1: Deployment Config   →  business.cms.enabled = true?    → 403 feature_disabled
Layer 2: Business Membership →  user is active member?          → 403 permission_denied
Layer 3: Per-Business Flag   →  business.cms_enabled = true?    → 403 feature_disabled
Layer 4: RBAC Permission     →  has required permission?        → 403 permission_denied
```

### Context Isolation

- **Platform admin** sees ALL sites, pages, and templates across the platform
- **Business member** sees ONLY their business's sites, pages, media, and activated templates
- **Template catalog** is shared — businesses browse and activate from a global pool
- **Content is always isolated** — each business's content is completely separate

### Key Design Decisions

1. **Templates are read-only for org users** — superuser creates/edits via Django Admin. Orgs can only browse catalog and activate.
2. **Activation is required before use** — businesses must activate a template before creating placements with it.
3. **Auto-provisioning on CMS enable** — when CMS is enabled for a business, all `is_default=true` templates are auto-activated.
4. **Dual content model** — blocks have `draft_content` (editable) and `published_content` (frozen). Publish copies draft to published atomically.
5. **Limits are per-business** — platform context has no limits; business context enforces VG limits (max sites, pages, templates, media, API keys).

---

## 2. Types & Enums

### File: `features/cms/types.ts`

- [ ] **Enum types** (union literals matching backend TextChoices):

```typescript
type PageStatus = "draft" | "published" | "archived"
type BlockPlacementStatus = "draft" | "published"
type ContentVersionAction = "draft_save" | "publish" | "rollback" | "import"
type ContentLayer = "draft" | "published"
type TemplateOrgType = "system" | "platform" | "business" | "all"
type OwnerType = "platform" | "business"
```

- [ ] **Domain types** (matching backend output serializers exactly):

| Type | Backend Serializer | ALL Fields |
|------|-------------------|------------|
| `CmsSite` | `SiteOutputSerializer` | id, owner_type, owner_id, name, slug, domain, description, default_locale, metadata, is_active, created_at, updated_at |
| `CmsPage` | `PageOutputSerializer` | id, site, site_slug, title, slug, description, path, page_type, metadata, status, published_at, order, is_required, is_visible, created_at, updated_at |
| `CmsPageDetail` | `PageDetailOutputSerializer` | extends CmsPage + section_placements[] |
| `CmsSectionTemplate` | `SectionTemplateOutputSerializer` | id, name, display_name, slug, description, section_type, metadata, ui_config, created_at |
| `CmsBlockTemplate` | `BlockTemplateOutputSerializer` | id, name, display_name, slug, description, block_type, schema, schema_version, default_content, metadata, ui_config, created_at |
| `CmsSectionPlacement` | `SectionPlacementOutputSerializer` | id, page, template (nested), label, order, is_required, is_visible, config_overrides, created_at, block_placements[] |
| `CmsBlockPlacement` | `BlockPlacementOutputSerializer` | id, section_placement, template (nested), label, order, is_required, is_visible, config_overrides, schema_version_validated, draft_content, published_content, status, created_at, updated_at |
| `CmsContentVersion` | `ContentVersionOutputSerializer` | id, block_placement, content_snapshot, version_number, action, created_by, created_by_username, created_at, notes |
| `CmsMediaFile` | `MediaFileOutputSerializer` | id, owner_type, owner_id, folder, storage_key, original_filename, mime_type, file_size, width, height, alt_text, title, metadata, is_tombstoned, usage_count, created_at, updated_at |
| `CmsApiKey` | `ApiKeyOutputSerializer` | id, site, name, key_prefix, allowed_origins, is_active, expires_at, last_used_at, rate_limit, created_at |
| `CmsApiKeyCreated` | `ApiKeyCreatedOutputSerializer` | id, site, name, key_prefix, allowed_origins, is_active, expires_at, rate_limit, created_at + **key** (plaintext, one-time return) |
| `CmsTemplateCatalogSection` | `TemplateCatalogSectionSerializer` | id, name, display_name, slug, section_type, description, ui_config, org_type, is_default |
| `CmsTemplateCatalogBlock` | `TemplateCatalogBlockSerializer` | id, name, display_name, slug, block_type, description, schema, schema_version, default_content, ui_config, org_type, is_default |
| `CmsSectionActivation` | `SectionActivationOutputSerializer` | id, template (nested catalog), is_active, created_at, updated_at |
| `CmsBlockActivation` | `BlockActivationOutputSerializer` | id, template (nested catalog), is_active, created_at, updated_at |
| `CmsPageExport` | `PageExportOutputSerializer` | export_version, exported_at, exported_by, source_site, source_owner_type, source_owner_id, page (JSON tree) |
| `BusinessCmsStatus` | `BusinessCMSStatusSerializer` | id, slug, legal_name, cms_enabled |

- [ ] **Permission type** (Tier 1.5):

```typescript
type CmsPermissions = {
  can_view_content: boolean
  can_edit_content: boolean
  can_publish_content: boolean
  can_create_site: boolean
  can_edit_site: boolean
  can_delete_site: boolean
  can_create_page: boolean
  can_edit_page: boolean
  can_delete_page: boolean
  can_upload_media: boolean
  can_edit_media: boolean
  can_delete_media: boolean
  can_create_api_key: boolean
  can_activate_template: boolean
}
```

- [ ] **Composed permission-aware types** (using `WithPermissions<T>` from `@/types/api`):

```typescript
type CmsSiteWithPerms = CmsSite & WithPermissions<CmsPermissions>
type CmsPageDetailWithPerms = CmsPageDetail & WithPermissions<CmsPermissions>
type CmsBlockPlacementWithPerms = CmsBlockPlacement & WithPermissions<CmsPermissions>
type CmsMediaFileWithPerms = CmsMediaFile & WithPermissions<CmsPermissions>
```

- [ ] **Input types** (matching backend input serializers):

| Type | Fields |
|------|--------|
| `CreateSiteInput` | name, slug, domain?, description?, metadata? |
| `UpdateSiteInput` | name?, domain?, description?, metadata?, is_active? |
| `CreatePageInput` | site_id, title, slug, path, page_type, order, description?, metadata?, is_required? |
| `UpdateDraftContentInput` | draft_content: Record<string, unknown> |
| `ImportPageInput` | export_version, page: Record<string, unknown> |
| `UploadMediaInput` | file: File, folder_id?, alt_text?, title? |
| `UpdateMediaInput` | alt_text?, title?, folder_id? |
| `CreateApiKeyInput` | site_id, name, allowed_origins?, rate_limit?, expires_at? |
| `ActivateTemplateInput` | template_id: string |
| `ToggleBusinessCmsInput` | cms_enabled: boolean |

### Things to Consider

- `draft_content` is excluded from `CmsBlockPlacement` when served via public API (`context.public=True`). The admin/business API always includes it.
- `CmsPageDetail.section_placements` is only returned when `?depth=full` is passed. Without it, page responses are flat (`CmsPage`).
- `CmsApiKeyCreated.key` is returned **exactly once** at creation time. It's never stored or retrievable again. The UI must show it in a copy-to-clipboard dialog.
- Template types have two variants: the standard output (used in placements) and the catalog variant (adds `org_type` and `is_default`).

---

## 3. API Client Layer

### File: `features/cms/api/cms-api.ts`

Organize functions by domain section. All use `apiClient` from `@/lib/api-client`.

- [ ] **Sites** (5 functions):

| Function | Method | Endpoint | Context |
|----------|--------|----------|---------|
| `fetchSitesApi(params?)` | GET | `/cms/admin/sites/` or `/cms/business/{slug}/sites/` | Both |
| `fetchSiteApi(siteSlug)` | GET | `.../sites/{slug}/` | Both |
| `createSiteApi(data)` | POST | `.../sites/` | Both |
| `updateSiteApi(siteSlug, data)` | PATCH | `.../sites/{slug}/` | Both |
| `deleteSiteApi(siteSlug)` | DELETE | `.../sites/{slug}/` | Both |

- [ ] **Pages** (7 functions — note: page PATCH/DELETE endpoints not yet implemented in backend):

| Function | Method | Endpoint |
|----------|--------|----------|
| `fetchPagesApi(params?)` | GET | `.../pages/?site={slug}&status={status}` |
| `fetchPageApi(pageSlug, params?)` | GET | `.../pages/{slug}/?site={slug}&depth=full` |
| `createPageApi(data)` | POST | `.../pages/` |
| `publishPageApi(pageSlug, siteSlug)` | POST | `.../pages/{slug}/publish/?site={slug}` |
| `unpublishPageApi(pageSlug, siteSlug)` | POST | `.../pages/{slug}/unpublish/?site={slug}` |
| `exportPageApi(pageSlug, siteSlug)` | POST | `.../pages/{slug}/export/?site={slug}` |
| `importPageApi(pageSlug, siteSlug, data)` | POST | `.../pages/{slug}/import/?site={slug}` |

- [ ] **Block Placements** (4 functions):

| Function | Method | Endpoint |
|----------|--------|----------|
| `fetchBlockPlacementApi(uuid)` | GET | `.../block-placements/{uuid}/` |
| `updateDraftContentApi(uuid, data)` | PATCH | `.../block-placements/{uuid}/` |
| `fetchBlockHistoryApi(uuid)` | GET | `.../block-placements/{uuid}/history/` |
| `rollbackBlockApi(uuid, versionNumber)` | POST | `.../block-placements/{uuid}/rollback/{ver}/` |

- [ ] **Template Catalog** (2 functions — business context only):

| Function | Method | Endpoint |
|----------|--------|----------|
| `fetchCatalogSectionsApi(businessSlug)` | GET | `/cms/business/{slug}/catalog/sections/` |
| `fetchCatalogBlocksApi(businessSlug)` | GET | `/cms/business/{slug}/catalog/blocks/` |

- [ ] **Template Library** (6 functions — business context only):

| Function | Method | Endpoint |
|----------|--------|----------|
| `fetchLibrarySectionsApi(businessSlug)` | GET | `/cms/business/{slug}/library/sections/` |
| `activateSectionTemplateApi(businessSlug, data)` | POST | `/cms/business/{slug}/library/sections/` |
| `deactivateSectionTemplateApi(businessSlug, uuid)` | DELETE | `/cms/business/{slug}/library/sections/{uuid}/` |
| `fetchLibraryBlocksApi(businessSlug)` | GET | `/cms/business/{slug}/library/blocks/` |
| `activateBlockTemplateApi(businessSlug, data)` | POST | `/cms/business/{slug}/library/blocks/` |
| `deactivateBlockTemplateApi(businessSlug, uuid)` | DELETE | `/cms/business/{slug}/library/blocks/{uuid}/` |

- [ ] **Media** (5 functions):

| Function | Method | Endpoint |
|----------|--------|----------|
| `fetchMediaFilesApi(params?)` | GET | `.../media/files/?folder={uuid}&type={mime}` |
| `fetchMediaFileApi(uuid)` | GET | `.../media/files/{uuid}/` |
| `uploadMediaFileApi(data)` | POST | `.../media/files/` (multipart) |
| `updateMediaFileApi(uuid, data)` | PATCH | `.../media/files/{uuid}/` |
| `deleteMediaFileApi(uuid)` | DELETE | `.../media/files/{uuid}/` |

- [ ] **API Keys** (3 functions):

| Function | Method | Endpoint |
|----------|--------|----------|
| `fetchApiKeysApi(siteId?)` | GET | `.../api-keys/?site={uuid}` |
| `createApiKeyApi(data)` | POST | `.../api-keys/` |
| `revokeApiKeyApi(uuid)` | DELETE | `.../api-keys/{uuid}/` |

- [ ] **Platform Management** (3 functions — platform admin only):

| Function | Method | Endpoint |
|----------|--------|----------|
| `fetchBusinessCmsStatusApi()` | GET | `/cms/admin/businesses/` |
| `toggleBusinessCmsApi(uuid, data)` | PATCH | `/cms/admin/businesses/{uuid}/` |
| `fetchBusinessActivationsApi(uuid)` | GET | `/cms/admin/businesses/{uuid}/activations/` |

### Things to Consider

- **Context-aware base URL**: API functions must accept a `context` parameter (`"admin"` or `"business"`) to build the correct base URL. Business context URLs include the business slug.
- **Multipart uploads**: `uploadMediaFileApi` uses `FormData`, not JSON. Set correct `Content-Type`.
- **Pagination**: All list endpoints return DRF `{ count, next, previous, results }` format. Use `StandardPagination` helper from `@/lib/pagination`.
- **Query params**: Several endpoints require `?site={slug}` for scoping (publish, unpublish, export, import, page detail).
- **One-time key**: `createApiKeyApi` response includes `key` field that is **never returned again**. Display in a copy dialog immediately.

---

## 4. Query Keys & Hooks

### File: `lib/query-keys.ts` — add `cms` section

```typescript
cms: {
  all: ["cms"] as const,
  sites: (params?) => [...queryKeys.cms.all, "sites", params] as const,
  site: (slug: string) => [...queryKeys.cms.all, "site", slug] as const,
  pages: (params?) => [...queryKeys.cms.all, "pages", params] as const,
  page: (slug: string) => [...queryKeys.cms.all, "page", slug] as const,
  blockPlacement: (uuid: string) => [...queryKeys.cms.all, "block-placement", uuid] as const,
  blockHistory: (uuid: string) => [...queryKeys.cms.all, "block-history", uuid] as const,
  catalogSections: (slug: string) => [...queryKeys.cms.all, "catalog-sections", slug] as const,
  catalogBlocks: (slug: string) => [...queryKeys.cms.all, "catalog-blocks", slug] as const,
  librarySections: (slug: string) => [...queryKeys.cms.all, "library-sections", slug] as const,
  libraryBlocks: (slug: string) => [...queryKeys.cms.all, "library-blocks", slug] as const,
  mediaFiles: (params?) => [...queryKeys.cms.all, "media-files", params] as const,
  mediaFile: (uuid: string) => [...queryKeys.cms.all, "media-file", uuid] as const,
  apiKeys: (siteId?: string) => [...queryKeys.cms.all, "api-keys", siteId] as const,
  businessStatus: () => [...queryKeys.cms.all, "business-status"] as const,
  businessActivations: (uuid: string) => [...queryKeys.cms.all, "business-activations", uuid] as const,
}
```

### File: `features/cms/hooks/use-cms-queries.ts`

- [ ] `useSites(params?)` — list sites with pagination
- [ ] `useSite(slug)` — single site detail (returns `CmsSiteWithPerms`)
- [ ] `usePages(params?)` — list pages with pagination, filterable by site and status
- [ ] `usePage(slug, params?)` — page detail, supports `depth=full` (returns `CmsPageDetailWithPerms`)
- [ ] `useBlockPlacement(uuid)` — single block placement detail (returns `CmsBlockPlacementWithPerms`)
- [ ] `useBlockHistory(uuid)` — content version list with pagination
- [ ] `useCatalogSections(businessSlug)` — available section templates (business context)
- [ ] `useCatalogBlocks(businessSlug)` — available block templates (business context)
- [ ] `useLibrarySections(businessSlug)` — activated section templates (business context)
- [ ] `useLibraryBlocks(businessSlug)` — activated block templates (business context)
- [ ] `useMediaFiles(params?)` — media list with folder/type filters
- [ ] `useMediaFile(uuid)` — single media file detail
- [ ] `useApiKeys(siteId?)` — API key list for a site
- [ ] `useBusinessCmsStatus()` — platform admin: list businesses with CMS status
- [ ] `useBusinessActivations(uuid)` — platform admin: view business template activations

### File: `features/cms/hooks/use-cms-mutations.ts`

- [ ] `useCreateSite()` — invalidates sites list
- [ ] `useUpdateSite(slug)` — invalidates site detail + sites list
- [ ] `useDeleteSite(slug)` — invalidates sites list
- [ ] `useCreatePage()` — invalidates pages list
- [ ] `usePublishPage()` — invalidates page detail + pages list
- [ ] `useUnpublishPage()` — invalidates page detail + pages list
- [ ] `useExportPage()` — returns export data (no cache mutation)
- [ ] `useImportPage()` — invalidates page detail
- [ ] `useUpdateDraftContent(uuid)` — invalidates block placement detail
- [ ] `useRollbackContent(uuid)` — invalidates block placement detail + history
- [ ] `useActivateSectionTemplate(businessSlug)` — invalidates library + catalog
- [ ] `useDeactivateSectionTemplate(businessSlug)` — invalidates library + catalog
- [ ] `useActivateBlockTemplate(businessSlug)` — invalidates library + catalog
- [ ] `useDeactivateBlockTemplate(businessSlug)` — invalidates library + catalog
- [ ] `useUploadMediaFile()` — invalidates media list
- [ ] `useUpdateMediaFile(uuid)` — invalidates media file detail + list
- [ ] `useDeleteMediaFile(uuid)` — invalidates media list
- [ ] `useCreateApiKey()` — invalidates API key list. **Must return full response with `key` field.**
- [ ] `useRevokeApiKey()` — invalidates API key list
- [ ] `useToggleBusinessCms(uuid)` — invalidates business status list (platform admin)

### Things to Consider

- **Draft auto-save**: `useUpdateDraftContent` will be called frequently as users edit. Consider debouncing (the backend already throttles versions at 30s intervals, but avoid unnecessary API calls).
- **Publish can fail**: If required fields are empty, publish returns 400 with `publish_errors` detail array. The hook should expose these errors for field-level highlighting.
- **API key creation**: The `useCreateApiKey` mutation must NOT invalidate before the user copies the key. Show the key dialog on success, then invalidate after dialog closes.

---

## 5. Feature Gate Degradation

### File: `features/cms/utils/cms-feature-gate-handler.ts`

Follow the chat system's reactive feature gate pattern:

- [ ] **Define CMS feature flags**:

```typescript
type CmsFeatureFlag =
  | "business_cms"        // business.cms.enabled gate
  | "activation_request"  // business.cms.activation_request gate
```

- [ ] **Handle 403 `feature_disabled` errors**: When any CMS API call returns 403 with `code: "feature_disabled"`:
  1. Record the disabled feature in a session-level `Set<CmsFeatureFlag>`
  2. Use `useSyncExternalStore` to reactively hide CMS UI elements
  3. Business CMS navigation items disappear without page reload

- [ ] **Handle per-business `cms_enabled=false`**: When a business doesn't have CMS enabled, the API returns 403. The UI should show an "Activate CMS" call-to-action instead of the CMS content.

### Navigation Gating

CMS navigation entries already have `permission` fields in `navigation-config.ts`:
- Platform: `can_create_cms_site`, `can_create_cms_template`, `can_create_cms_api_key`, `can_upload_cms_media`
- Business: `can_view_cms_content`, `can_upload_cms_media`

These filter correctly via the `use-filtered-nav` hook. No change needed there.

### Things to Consider

- **Platform CMS is always available** when `platform.cms=true` and user has permissions. No per-instance flag.
- **Business CMS has two gates**: deployment config (`business.cms.enabled`) AND per-business flag (`cms_enabled`). Both must be true.
- **CMS activation request** is gated by `business.cms.activation_request`. If disabled, business owners can't request CMS access (platform admin must enable directly).

---

## 6. Tier 1.5 Permission Integration

### Backend Support

Business CMS detail views inject `_permissions` into GET responses:
- `BusinessSiteDetailView` → `_permissions` on site GET
- `BusinessPageDetailView` → `_permissions` on page GET
- `BusinessBlockPlacementDetailView` → `_permissions` on block GET
- `BusinessMediaFileDetailView` → `_permissions` on media file GET

### Frontend Requirements

- [ ] **Use `<Can>` component** from `@/components/common/Can` for all permission-gated UI:

```tsx
const permissions = site._permissions;

<Can allowed={permissions.can_edit_site}>
  <EditSiteButton />
</Can>

<Can allowed={permissions.can_delete_site}>
  <DeleteSiteButton variant="destructive" />
</Can>
```

- [ ] **Gate these specific UI elements**:

| Permission | UI Element |
|------------|-----------|
| `can_create_site` | "New Site" button on sites list |
| `can_edit_site` | Edit site button/form on site detail |
| `can_delete_site` | Delete site button (danger zone) |
| `can_create_page` | "New Page" button on pages list |
| `can_edit_page` | Edit page metadata |
| `can_delete_page` | Delete page button |
| `can_edit_content` | Edit draft content on block placements |
| `can_publish_content` | Publish/unpublish buttons |
| `can_upload_media` | Upload button in media library |
| `can_edit_media` | Edit metadata on media files |
| `can_delete_media` | Delete media button |
| `can_create_api_key` | "Create API Key" button |
| `can_activate_template` | "Add to Library" button in template catalog |

### Things to Consider

- **`_permissions` is only on GET detail responses**, not on list responses, POST, or PATCH. Use list-level permissions from the membership store (Tier 1) for list page actions.
- **Platform admin context**: Platform admin views don't use `_permissions` (platform admin is assumed to have full access). Only business-scoped views inject `_permissions`.
- **Unauthenticated users**: GET responses for unauthenticated users return all `_permissions` as `false`.

---

## 7. Navigation & Routing

### Existing Routes (update stubs)

| Route | Context | Current State | Target |
|-------|---------|--------------|--------|
| `/cconsole/sites` | Platform | Placeholder | Site list + CRUD |
| `/cconsole/templates` | Platform | Placeholder | Template list (read-only, superuser manages) |
| `/cconsole/api-keys` | Platform | Placeholder | API key list + create/revoke |
| `/pconsole/media` | Platform | Placeholder | Media library |
| `/bconsole/[slug]/content` | Business | Placeholder | Site + page list + content editor |
| `/bconsole/[slug]/media` | Business | Placeholder | Media library (business-scoped) |

### New Routes Needed

| Route | Context | Purpose |
|-------|---------|---------|
| `/cconsole/[slug]/catalog` | Business | Template catalog (browse & activate) |
| `/cconsole/[slug]/library` | Business | Activated template library |
| `/cconsole/[slug]/api-keys` | Business | Business API key management |
| `/cconsole/businesses` | Platform | Business CMS management (enable/disable) |

### Navigation Config Updates

- [ ] **Business sidebar** — expand "Content" section:
  - Content (sites + pages) → `/bconsole/{slug}/content`
  - Media → `/bconsole/{slug}/media`
  - Template Library → `/cconsole/{slug}/library` (permission: `can_activate_cms_template`)
  - API Keys → `/cconsole/{slug}/api-keys` (permission: `can_create_cms_api_key`)

- [ ] **Platform sidebar** — add "Businesses" under CMS section:
  - Sites → `/cconsole/sites`
  - Templates → `/cconsole/templates`
  - API Keys → `/cconsole/api-keys`
  - Media → `/pconsole/media`
  - **Businesses** → `/cconsole/businesses` (permission: `can_manage_business_cms`)

### Things to Consider

- **Business CMS not enabled**: If `business.cms_enabled=false`, the business CMS routes should show an "Activate CMS" page instead of 404. This page either shows a "Request CMS Access" button (if `activation_request` gate is enabled) or an info message.
- **Navigation should only show CMS items** when user has at least one CMS permission. The `use-filtered-nav` hook already handles this.

---

## 8. Template Catalog & Library

### Business Only Feature

Templates are superuser-managed (Django Admin). Business users interact through:
1. **Catalog** — browse available templates they can activate
2. **Library** — manage their activated templates

### Catalog Page

- [ ] **Grid/list of available templates** — shows templates NOT yet activated for this business
- [ ] **Template card**: display_name, section_type/block_type, description, `org_type` badge, `is_default` indicator
- [ ] **"Activate" button** on each card → calls `activateTemplateApi`
- [ ] **Search/filter**: by type (header, content, footer, sidebar for sections; text, media, composite for blocks)
- [ ] **Tab split**: Section Templates | Block Templates
- [ ] **Empty state**: "All available templates are already in your library"

### Library Page

- [ ] **Grid/list of activated templates** — only active activations
- [ ] **Template card**: display_name, type, schema preview, status badge (active)
- [ ] **"Remove" button** → calls `deactivateTemplateApi`. Show confirmation dialog.
- [ ] **Deactivation blocked if in use**: Backend returns `template_in_use` error. Show toast: "Cannot remove — this template is used by active pages"
- [ ] **Tab split**: Section Templates | Block Templates

### Things to Consider

- **Limit enforcement**: When activating, backend checks `max_active_section_templates` / `max_active_block_templates`. Show limit info ("3/20 templates activated") and disable "Activate" button when at limit.
- **Auto-provisioned templates**: Templates marked `is_default=true` are auto-activated on CMS enable. They appear in the library immediately.
- **Platform context**: Platform admin doesn't need catalog/library — platform uses templates directly without activation.

---

## 9. Site Management

### Endpoints Used
- `GET/POST .../sites/` — list/create
- `GET/PATCH/DELETE .../sites/{slug}/` — detail/update/delete

### Page: Sites List

- [ ] **Table/card list** of sites with: name, slug, domain, is_active badge, created_at
- [ ] **"Create Site" button** (gated by `can_create_site`)
- [ ] **Create dialog/form**: name (required), slug (required, auto-generated from name), domain (optional), description (optional)
- [ ] **Slug validation**: Show error if 409 Conflict (duplicate slug)
- [ ] **Click row** → navigate to site detail

### Page: Site Detail

- [ ] **Site info card**: name, slug, domain, locale, metadata (JSON editor), is_active toggle
- [ ] **Pages tab**: List pages for this site (ordered by `order` field)
- [ ] **API Keys tab**: List API keys for this site
- [ ] **Edit form** (gated by `can_edit_site`): inline editing or edit dialog for name, domain, description, is_active
- [ ] **Delete button** (gated by `can_delete_site`): confirmation dialog, handles cascade warning

### Things to Consider

- **Business context limits**: Display remaining site quota ("1/3 sites used") when `max_sites > 0`
- **`is_active` toggle**: Deactivating a site doesn't delete it — just hides from public API
- **Slug uniqueness**: Scoped per owner. Two different businesses CAN have sites with the same slug.

---

## 10. Page Management

### Page: Pages List (within a site)

- [ ] **Table with columns**: title, slug, path, status (color-coded badge), order, published_at
- [ ] **Status filter tabs**: All | Draft | Published | Archived
- [ ] **"Create Page" button** (gated by `can_create_page`)
- [ ] **Drag-to-reorder** (future enhancement — backend supports `reorder_pages` but no API view yet)
- [ ] **Click row** → navigate to page detail/editor

### Page: Page Detail / Editor

- [ ] **Page metadata panel**: title, slug, path, page_type, is_visible, is_required (read-only badge)
- [ ] **Section/block tree view**: Visual tree showing PageSectionPlacements → SectionBlockPlacements (use `?depth=full`)
- [ ] **Block content editor**: Click a block → opens content editor form (see Section 11)
- [ ] **Status bar**: Current status badge + Publish/Unpublish buttons
- [ ] **Action buttons**: Export, Import (gated by permissions)

### Things to Consider

- **`is_required` pages**: Cannot delete or hide — show disabled delete button with tooltip explaining why
- **Page order**: Integer field. When creating, suggest next available order number.
- **Business context limits**: Display remaining page quota when `max_pages_per_site > 0`
- **Backend gap: Page PATCH/DELETE not implemented**: `PageUpdateSerializer` exists in backend serializers but NO view endpoint exposes it. Page update and delete views are planned (see cms-system.md vNext). For now, pages can only be created and their content edited via block placements. The frontend should prepare the UI but disable/hide update and delete actions until backend support is added.

---

## 11. Content Editing (Block Placements)

### The Core CMS Experience

This is the main editing interface. A block placement holds `draft_content` — a JSON object whose fields are defined by the block template's `schema`.

### Schema-Driven Form Renderer

- [ ] **Dynamic form generator**: Read `block_placement.template.schema.fields[]` and render appropriate form controls:

| Schema Field Type | UI Control |
|-------------------|-----------|
| `text` | `<Input type="text">` with max_length validation |
| `textarea` | `<Textarea>` with character counter |
| `richtext` | Rich text editor (TipTap, Plate, or similar) |
| `number` | `<Input type="number">` with min/max |
| `boolean` | `<Switch>` or `<Checkbox>` |
| `url` | `<Input type="url">` with URL validation |
| `email` | `<Input type="email">` with email validation |
| `date` | Date picker |
| `datetime` | DateTime picker |
| `select` | `<Select>` with options from `schema.choices` |
| `multiselect` | Multi-select / checkbox group |
| `media` | Media picker (opens media library, returns `{ media_id: uuid }`) |
| `color` | Color picker |
| `repeater` | Nested form group with add/remove items |
| `list` | Tag-like input for string arrays |
| `json` | JSON editor (code editor) |
| `relation` | Entity reference picker (ID input with search) |
| `icon` | Icon picker (icon name from icon library) |

- [ ] **Validation**: Client-side validation matching backend's `SchemaValidator`:
  - Required fields: show error if empty on save
  - `max_length`, `min_length` for text fields
  - `pattern` regex for text fields (display match error)
  - `min`, `max` for number fields
  - `min_selected`, `max_selected` for multiselect
  - `min_items`, `max_items` for repeaters

- [ ] **Auto-save with debounce**: Save draft content after 2-3 seconds of inactivity. Backend throttles versions at 30s.
- [ ] **Save indicator**: Show "Saving...", "Saved", "Unsaved changes" states
- [ ] **Visibility toggle**: If block `is_required=false`, show hide/show toggle (gated by `can_edit_content` permission)

### Things to Consider

- **Richtext sanitization**: Backend sanitizes HTML via `nh3` on save. Frontend should use a safe HTML editor that produces clean output. Don't rely on client-side sanitization alone.
- **Media references**: Media fields store `{ media_id: "uuid" }` objects. The media picker should allow selecting from the org's media library.
- **Repeater nesting**: Repeaters can contain any field type EXCEPT other repeaters (backend enforces this). The form renderer must handle one level of nesting.
- **Schema version tracking**: The block placement has `schema_version_validated` — if it's behind the template's `schema_version`, show a warning that the schema has been updated.

---

## 12. Content Versioning & Rollback

### Endpoints Used
- `GET .../block-placements/{uuid}/history/` — paginated version list
- `POST .../block-placements/{uuid}/rollback/{version_number}/` — rollback to version

### UI Requirements

- [ ] **Version history panel** (slide-out or tab): List of `ContentVersion` entries ordered newest-first
- [ ] **Version item**: version_number, action badge (draft_save/publish/rollback/import), created_by_username, created_at, notes
- [ ] **Preview version**: Click a version → show `content_snapshot` in read-only form view
- [ ] **Rollback button**: "Restore this version" → confirmation dialog → calls rollback API
- [ ] **Diff view** (nice-to-have): Side-by-side comparison of current draft vs selected version

### Things to Consider

- **Throttled versions**: Backend creates max 1 version per 30s. Rapid saves update the latest version in-place. The UI doesn't need to handle this — just display what the API returns.
- **Max 50 versions**: Backend auto-prunes oldest beyond 50. No UI action needed.
- **Rollback creates a new version**: After rollback, a new version with `action=rollback` appears in history.

---

## 13. Publish / Unpublish Flow

### Publish

- [ ] **"Publish" button** on page detail (gated by `can_publish_content`)
- [ ] **Confirmation dialog**: "This will validate all blocks and make the page live. Continue?"
- [ ] **Success**: Status changes to "published", `published_at` updates, toast notification
- [ ] **Failure (validation errors)**: Backend returns 400 with `publish_errors` array. Each error has:
  - `section_placement_id`, `block_placement_id`, `block_template` name
  - `field_key`, `error_type`, `message`
- [ ] **Error display**: Highlight failing blocks in the tree view, show field-level errors in the content editor
- [ ] **Publish error summary**: Modal/panel listing all validation failures with "Jump to block" links

### Unpublish

- [ ] **"Unpublish" button** on published pages (gated by `can_publish_content`)
- [ ] **Confirmation dialog**: "This will revert the page to draft. Published content will be preserved but not visible. Continue?"
- [ ] **Note**: Unpublishing does NOT delete `published_content` — it just changes status to draft

### Things to Consider

- **Only published + visible pages** appear in the public API. Unpublished pages are invisible to external consumers.
- **Block-level validation on publish**: The backend validates ALL visible required blocks with strict mode. This catches missing required fields that draft save allows.
- **Concurrent publish protection**: Backend uses `select_for_update()`. If two users publish simultaneously, one will succeed and one will get a conflict. Handle gracefully.

---

## 14. Export / Import

- [ ] **Export button** on page detail → calls `exportPageApi` → downloads JSON file
- [ ] **Import button** on page detail → file picker → upload JSON → calls `importPageApi`
- [ ] **Import is content-only**: Matches block placements by UUID. Structure changes are NOT imported.
- [ ] **Export format**: `{ export_version: "3.1", exported_at, exported_by, source_site, source_owner_type, source_owner_id, page: { ... } }`
- [ ] **Import validation**: Backend validates permissively (skips blocks that don't match). Show toast with count of blocks imported.

---

## 15. Media Library

### Page: Media Library

- [ ] **Grid view**: Thumbnail gallery with file info overlay (name, type, size)
- [ ] **List view**: Table with columns: filename, type, size, folder, usage_count, uploaded
- [ ] **Upload area**: Drag-and-drop zone + "Upload" button. Multipart form upload.
- [ ] **Folder navigation**: Breadcrumb path, folder tree sidebar (max 5 levels deep)
- [ ] **File detail panel**: Click file → side panel with: preview, alt_text, title, metadata, usage list, edit/delete actions
- [ ] **Filter by type**: All | Images | Videos | Documents | Audio
- [ ] **Search** (future): By filename, alt_text, title

### Allowed File Types

```
Images: JPEG, PNG, GIF, WebP, SVG
Documents: PDF
Video: MP4, WebM
Audio: MP3, OGG
```

Max file size for business context: configurable via `business.cms.max_media_file_size_mb` (default 10MB).

### Things to Consider

- **Usage count**: Shows how many block placements reference this file. Files with published references can't be fully deleted — they get tombstoned.
- **Tombstoned files**: `is_tombstoned=true` means the file is marked for removal but still accessible because published content references it. Show a warning icon.
- **Business limits**: Display "12/100 files" quota indicator when `max_media_files > 0`.
- **Image dimensions**: Backend stores `width` and `height` for images. Use for layout/preview.
- **Backend gap: No folder CRUD API**: `MediaFolderOutputSerializer` exists but NO API endpoint for creating, listing, or deleting folders. The `folder` query param on media list works for filtering, but folder management is not yet exposed. Folder navigation UI should be planned but marked as dependent on backend folder endpoints being added.

---

## 16. API Key Management

### Page: API Keys (per site)

- [ ] **Table**: name, key_prefix (masked), is_active badge, rate_limit, last_used_at, expires_at, created_at
- [ ] **"Create API Key" button** (gated by `can_create_api_key`)
- [ ] **Create dialog**: name (required), allowed_origins (optional, multi-input), rate_limit (optional, default 60), expires_at (optional, date picker)
- [ ] **Key reveal dialog**: After creation, show the full `key` value with a **copy-to-clipboard** button and warning: "This key will not be shown again. Copy it now."
- [ ] **Revoke button**: Confirmation dialog → calls revoke API → key becomes inactive and soft-deleted

### Things to Consider

- **Key format**: Always starts with `cmsk_` prefix. Display the prefix portion for identification.
- **One-time display**: The full key is returned ONLY in the creation response. After that, only `key_prefix` is available. The UI MUST handle this correctly.
- **Rate limiting**: The `rate_limit` field sets max requests per minute for this key. Display in the table.
- **Business limits**: Display "2/5 API keys" quota indicator when `max_api_keys_per_site > 0`.

---

## 17. Platform CMS Admin — Business Management

### Page: `/cconsole/businesses`

Platform admins can manage which businesses have CMS access.

- [ ] **Business list table**: slug, legal_name, cms_enabled toggle/badge
- [ ] **Toggle CMS**: Switch component per row → calls `toggleBusinessCmsApi`. On enable, backend auto-provisions default templates.
- [ ] **View activations**: Click row → detail panel showing activated section and block templates
- [ ] **Search/filter**: Filter by cms_enabled status

### Things to Consider

- **Auto-provision**: When platform admin enables CMS for a business, all `is_default=true` templates are auto-activated. The UI should show a success toast: "CMS enabled for {business}. {N} default templates activated."
- **Disable CMS**: Toggling OFF doesn't delete the business's content — it just prevents access. The content is preserved for re-enable.
- **Permission required**: `can_manage_business_cms` (platform_only scope)

---

## 18. CMS Activation Request Flow

### Business Owner Perspective

When `business.cms_enabled=false` and `business.cms.activation_request=true`:

- [ ] **"Request CMS Access" page**: Shown instead of CMS content when business doesn't have CMS. Business owner sees a call-to-action.
- [ ] **Request form**: Reason textarea (optional, max 1000 chars)
- [ ] **Submit**: Creates `cms_activation_request` transaction via transaction API
- [ ] **Pending state**: Show "Your CMS activation request is pending approval" with request status
- [ ] **Cooldown**: After denial, 14-day cooldown before re-request (backend enforces)

### Platform Admin Perspective

CMS activation requests appear in the standard transaction management UI:
- Transaction type: `cms_activation_request`
- Category: `cms`
- Approvers: Platform members with `can_approve_cms_activation` permission
- On approval: Backend auto-enables CMS + provisions default templates

### Things to Consider

- **Conflict group**: Only one active `cms_activation_request` per business. If a request is pending, the "Request" button should show "Request Pending" and be disabled.
- **Owner only**: Only the business owner can submit the activation request (`owner_only=true` on the transaction type).
- **No request flow**: If `business.cms.activation_request=false` in deployment config, the request button is hidden. Platform admin must enable CMS directly.

---

## 19. State Management

### Zustand Store (if needed): `stores/cms-store.ts`

CMS may NOT need a dedicated Zustand store. Most state lives in TanStack Query cache.

Consider a store only if:
- [ ] **Unsaved draft tracking**: Track which blocks have unsaved changes (for "Leave page?" warnings)
- [ ] **Active editor state**: Which block is currently being edited
- [ ] **Media picker state**: Currently selected file for media field insertion

If a store is needed, keep it minimal:

```typescript
interface CmsState {
  activeBlockId: string | null
  unsavedBlocks: Set<string>  // Block UUIDs with unsaved draft changes
  mediaPickerOpen: boolean
  mediaPickerCallback: ((mediaId: string) => void) | null
}
```

### Things to Consider

- **Server data in TQ cache, client state in Zustand** — never duplicate API data in Zustand.
- **Draft auto-save state**: The debounced auto-save should use local component state or the Zustand store to track "saving" / "saved" / "error" indicator state.

---

## 20. Constants & Display Config

### File: `features/cms/constants/cms-constants.ts`

- [ ] **Status display config**:

```typescript
const PAGE_STATUS_CONFIG: Record<PageStatus, { label: string; color: string }> = {
  draft: { label: "Draft", color: "yellow" },
  published: { label: "Published", color: "green" },
  archived: { label: "Archived", color: "gray" },
}
```

- [ ] **Block type display config**: Map `block_type` values to icons and labels
- [ ] **Section type display config**: Map `section_type` values to icons and labels
- [ ] **Version action labels**: `{ draft_save: "Auto-saved", publish: "Published", rollback: "Rolled back", import: "Imported" }`
- [ ] **Allowed media types and extensions**: Mirror backend constants for client-side validation
- [ ] **CMS field type to form control mapping**: Map each of the 18 schema field types to the appropriate UI component

---

## 21. Error Handling & Edge Cases

- [ ] **409 Conflict (duplicate slug)**: Show inline form error on slug field
- [ ] **400 Publish validation errors**: Parse `publish_errors` array, highlight failing blocks
- [ ] **403 FeatureDisabled**: Detect `feature_disabled` code, handle per Section 5
- [ ] **403 PermissionDenied**: Show "You don't have permission" toast
- [ ] **400 Template not activated** (rule: `template_not_activated`): Show "This template is not in your library" message with link to catalog
- [ ] **400 Template not eligible** (rule: `template_not_eligible`): "This template is not available for your organization type"
- [ ] **400 Template in use** (rule: `template_in_use`): "Cannot remove — this template is used by active pages"
- [ ] **400 Limit exceeded**: Parse `rule` from error details, show user-friendly message with current/max counts
- [ ] **400 Required page/block**: "Required pages/blocks cannot be deleted or hidden"
- [ ] **404 Not found**: Standard not-found handling
- [ ] **Network errors**: Retry with backoff for transient failures
- [ ] **Concurrent edit**: If two users edit the same block, last-write-wins (backend is atomic). Consider showing "Last edited by {user} at {time}" indicator.

---

## 22. Accessibility

- [ ] **Form labels**: All schema-driven form fields must have proper labels from `schema.fields[].label`
- [ ] **ARIA roles**: Content tree uses `role="tree"` / `role="treeitem"` for section/block hierarchy
- [ ] **Keyboard navigation**: Tab through blocks, Enter to open editor, Escape to close
- [ ] **Status announcements**: Use `aria-live="polite"` for save status, publish result
- [ ] **Color contrast**: Status badges (draft/published/archived) meet WCAG AA
- [ ] **Media alt text**: Encourage alt_text input when uploading (show warning if empty)

---

## 23. Responsive / Mobile

- [ ] **Desktop**: Full layout — site list + page tree + content editor side-by-side
- [ ] **Tablet**: Collapsible sidebar — toggle between page tree and content editor
- [ ] **Mobile**: Stack layout — list view → tap to navigate → editor fills screen
- [ ] **Media library**: Grid adapts from 4 columns (desktop) to 2 (tablet) to 1 (mobile)
- [ ] **Template catalog**: Card grid adapts similarly
- [ ] **Content editor**: Full-width on mobile with sticky save/publish bar

---

## 24. Testing

### Test Structure

Follow the project's Vitest + React Testing Library pattern.

### Files to Create

| Test File | Covers |
|-----------|--------|
| `features/cms/api/__tests__/cms-api.test.ts` | All API functions (mock apiClient) |
| `features/cms/hooks/__tests__/use-cms-queries.test.ts` | All query hooks |
| `features/cms/hooks/__tests__/use-cms-mutations.test.ts` | All mutation hooks |
| `features/cms/components/__tests__/SiteList.test.tsx` | Site list rendering, create dialog |
| `features/cms/components/__tests__/PageEditor.test.tsx` | Page detail, section/block tree |
| `features/cms/components/__tests__/ContentEditor.test.tsx` | Schema-driven form, auto-save |
| `features/cms/components/__tests__/MediaLibrary.test.tsx` | Upload, grid, file detail |
| `features/cms/components/__tests__/TemplateCatalog.test.tsx` | Catalog browsing, activation |
| `features/cms/components/__tests__/ApiKeyManagement.test.tsx` | Key creation, copy dialog, revoke |
| `features/cms/components/__tests__/PublishFlow.test.tsx` | Publish, validation errors, unpublish |
| `features/cms/components/__tests__/VersionHistory.test.tsx` | History list, rollback |
| `features/cms/utils/__tests__/cms-feature-gate-handler.test.ts` | Feature gate detection |

### Key Test Scenarios

- [ ] **Permission gating**: Verify `<Can>` hides buttons when permissions are false
- [ ] **Feature gate degradation**: Verify CMS UI hides on 403 feature_disabled
- [ ] **Publish error handling**: Verify validation errors are displayed per-block
- [ ] **API key one-time display**: Verify key dialog shows and handles copy
- [ ] **Draft auto-save**: Verify debounced save behavior
- [ ] **Limit enforcement**: Verify quota indicators and disabled states at limit
- [ ] **Template activation/deactivation**: Verify catalog → library flow
- [ ] **Context isolation**: Verify business CMS only shows business's own resources

---

## Summary: Implementation Priority

### Phase 1 — Foundation (Types, API, Hooks, Feature Gates)
1. `features/cms/types.ts` — all types
2. `features/cms/api/cms-api.ts` — all API functions
3. `lib/query-keys.ts` — add cms section
4. `features/cms/hooks/use-cms-queries.ts` — all query hooks
5. `features/cms/hooks/use-cms-mutations.ts` — all mutation hooks
6. `features/cms/utils/cms-feature-gate-handler.ts` — feature gate handling
7. `features/cms/constants/cms-constants.ts` — display configs

### Phase 2 — Core UI (Sites, Pages, Content Editor)
8. Site management pages (list + detail)
9. Page management pages (list + detail + tree view)
10. Content editor (schema-driven form renderer — the most complex component)
11. Publish/unpublish flow with validation error handling
12. Content versioning & rollback panel

### Phase 3 — Template System & Media
13. Template catalog page (business context)
14. Template library page (business context)
15. Media library (upload, grid, folders, file detail)
16. Media picker integration in content editor

### Phase 4 — Management & Advanced
17. API key management
18. Platform admin — business CMS management page
19. CMS activation request flow
20. Export/import functionality

### Phase 5 — Polish
21. Auto-save refinement
22. Responsive layout optimization
23. Accessibility audit
24. Performance optimization (memo, lazy loading)
25. Comprehensive test coverage
