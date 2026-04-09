# CMS Frontend Implementation Plan

> **SUPERSEDED:** v2.0 routes (`/pconsole/cms/`, `/bconsole/[slug]/cms/`) were migrated to
> dedicated `/cconsole/` routes on 2026-04-09. See `cconsole-design-decision.md` in project memory.
> Platform CMS: `/cconsole/sites|templates|media|api-keys|businesses` (PlatformGuard).
> Business CMS: `/cconsole/[slug]/sites|catalog|library|media|api-keys` (CmsBusinessGuard).
> Old routes redirect to cconsole via next.config.ts + page-level redirects.

**Version:** 2.0 (revised after deep review) — **SUPERSEDED by cconsole migration (2026-04-09)**
**Date:** 2026-03-29
**Scope:** Frontend (Next.js 16 + React 19)
**Backend Reference:** `docs/implementations/backend/cms-system.md`
**Features Doc:** `docs/descriptions/frontend/cms-system-frontend-features.md`
**Backend Plan:** `docs/plans/backend/cms_business_access/cms_business_access_plan.md`
**Depends on:** CMS Backend (complete), Frontend Foundation (complete), Chat Frontend (reference impl)

---

## 1. Executive Summary

Build the complete CMS frontend using the **existing console architecture** — platform CMS pages under `/pconsole/cms/`, business CMS pages under `/bconsole/[slug]/cms/`. Six placeholder pages already exist in the codebase.

### Why Existing Consoles (Not a Dedicated `/cconsole`)

v1.0 of this plan proposed a dedicated `/cconsole` console. This was rejected because:
1. **Guard nesting flaw**: A PlatformGuard on `/cconsole/layout.tsx` would block business users before `CmsBusinessGuard` could render.
2. **Existing infrastructure**: 6 stub pages + navigation config + permission hooks already exist under pconsole/bconsole.
3. **No new NavContextType needed**: CMS pages under pconsole use `"platform"` context, under bconsole use `"business"` context.
4. **Consistency**: Every other feature (chat, forms, transactions, members) lives within its console. CMS should follow the same pattern.

### Architecture at a Glance

```
Platform CMS:  /pconsole/cms/*                → PlatformGuard (existing)
Business CMS:  /bconsole/[slug]/cms/*         → BusinessGuard (existing) + CMS access check
                                                 ↪ CmsAccessGate component (checks cms_enabled)

features/cms/                                 → Feature module (types, API, hooks, components)
```

### Scope: 5 Phases

| Phase | What | Files | Priority |
|-------|------|-------|----------|
| 1 | Foundation (types, API, hooks, routing, CMS access gate, nav) | ~20 | P0 |
| 2 | Core UI (sites, pages, content editor, publish) | ~25 | P0 |
| 3 | Templates & Media (catalog, library, media library) | ~15 | P1 |
| 4 | Management (API keys, platform admin, activation request) | ~12 | P1 |
| 5 | Polish (auto-save, responsive, a11y, tests) | ~15 | P2 |

---

## 2. Routing Architecture

### 2.1 Route Structure

Routes live within the existing pconsole and bconsole route groups. Guards are inherited from parent layouts (PlatformGuard for pconsole, BusinessGuard for bconsole). CMS-specific access control uses an **inner gate component** (not a layout guard).

```
frontend/src/app/(app)/
├── pconsole/                                  # Existing — PlatformGuard in layout.tsx
│   └── cms/
│       ├── sites/
│       │   ├── page.tsx                       # Platform site list (replaces stub)
│       │   └── [siteSlug]/
│       │       ├── page.tsx                   # Site detail
│       │       └── pages/
│       │           ├── page.tsx               # Page list for site
│       │           └── [pageSlug]/
│       │               └── page.tsx           # Page editor
│       ├── templates/
│       │   └── page.tsx                       # Template browser (read-only, replaces stub)
│       ├── api-keys/
│       │   └── page.tsx                       # API key management (replaces stub)
│       ├── businesses/
│       │   └── page.tsx                       # Business CMS management (NEW)
│       └── media/                             # Note: was at /pconsole/media, move to /pconsole/cms/media
│           └── page.tsx                       # Platform media library
│
├── bconsole/
│   └── [slug]/                                # Existing — BusinessGuard in layout.tsx
│       └── cms/
│           ├── page.tsx                        # CMS landing (redirect to sites or activation page)
│           ├── sites/
│           │   ├── page.tsx                   # Business site list
│           │   └── [siteSlug]/
│           │       ├── page.tsx               # Business site detail
│           │       └── pages/
│           │           ├── page.tsx           # Business page list
│           │           └── [pageSlug]/
│           │               └── page.tsx       # Business page editor
│           ├── catalog/
│           │   └── page.tsx                   # Template catalog (browse + activate)
│           ├── library/
│           │   └── page.tsx                   # Activated templates
│           ├── media/
│           │   └── page.tsx                   # Business media library
│           └── api-keys/
│               └── page.tsx                   # Business API keys
```

### 2.2 Guard Architecture

**No new layout guards needed.** Existing guards handle authentication and membership:

```
/pconsole/* → PlatformGuard (layout.tsx)
  /pconsole/cms/* → No additional guard (platform members with CMS permissions see nav items)

/bconsole/[slug]/* → BusinessGuard (layout.tsx)
  /bconsole/[slug]/cms/* → CmsAccessGate (inner component, checks cms_enabled)
```

**CmsAccessGate** is NOT a route layout guard — it's a **wrapper component** used inside each business CMS page:

```typescript
// features/cms/components/CmsAccessGate.tsx
"use client";

export function CmsAccessGate({ children }: { children: React.ReactNode }) {
  // 1. Probe CMS access by attempting to fetch sites
  //    - If 403 feature_disabled (business.cms.enabled OFF) → show "CMS unavailable" card
  //    - If 403 feature_disabled (business.cms_enabled=false) → show CmsActivationPage
  //    - If success → render children
  //
  // 2. Cache result in feature gate handler (session-level)
  //    - Subsequent pages skip the probe
}
```

**Why a component, not a layout guard:**
- Business users are already authenticated and membership-checked by `BusinessGuard`.
- The CMS check is a **feature flag** check, not an access control check.
- Using a component avoids the nested-guard problem and allows the CMS activation page to render within the bconsole layout (sidebar still visible).

**Usage pattern in business CMS pages:**
```typescript
// app/(app)/bconsole/[slug]/cms/sites/page.tsx
import { CmsAccessGate } from "@/features/cms/components/CmsAccessGate";
import { SiteListPage } from "@/features/cms/components/SiteListPage";

export default function BusinessSitesPage() {
  return (
    <CmsAccessGate>
      <SiteListPage context="business" />
    </CmsAccessGate>
  );
}
```

Platform CMS pages do NOT use `CmsAccessGate` — platform CMS is always available when `platform.cms=true` and the user has the right permissions.

### 2.3 Navigation

**No new NavContextType values.** CMS items are added to existing `business` and `platform` nav sections.

**Extend existing `platform` section in NAV_CONFIG:**

The CMS section already exists in `navigation-config.ts` (lines 258-293):
```
"CMS" section:
  - Sites → /pconsole/cms/sites (can_create_cms_site)
  - Templates → /pconsole/cms/templates (can_create_cms_template)
  - API Keys → /pconsole/cms/api-keys (can_create_cms_api_key)
  - Media → /pconsole/media (can_upload_cms_media)
```

**Changes needed:**
1. Move Media href from `/pconsole/media` to `/pconsole/cms/media`
2. Add "Businesses" item: `/pconsole/cms/businesses` (permission: `can_manage_business_cms`)

**Extend existing `business` section in NAV_CONFIG:**

The "Content" section already exists (lines 147-162):
```
"Content" section:
  - Content → /bconsole/{slug}/content (can_view_cms_content)
  - Media → /bconsole/{slug}/media (can_upload_cms_media)
```

**Changes needed:**
1. Rename "Content" to "CMS" as the section label
2. Change Content href from `/bconsole/{slug}/content` to `/bconsole/{slug}/cms`
3. Change Media href from `/bconsole/{slug}/media` to `/bconsole/{slug}/cms/media`
4. Add "Template Catalog" → `/bconsole/{slug}/cms/catalog` (permission: `can_activate_cms_template`)
5. Add "My Templates" → `/bconsole/{slug}/cms/library` (permission: `can_activate_cms_template`)
6. Add "API Keys" → `/bconsole/{slug}/cms/api-keys` (permission: `can_create_cms_api_key`)

**No changes needed to:**
- `types/navigation.ts` — no new context types
- `hooks/use-nav-context.ts` — context detection unchanged
- `hooks/use-filtered-nav.ts` — filtering logic unchanged
- `components/navigation/AccountSwitcher.tsx` — no new console entries
- `components/navigation/Sidebar.tsx` — renders from useFilteredNav, no change

---

## 3. Phase 1: Foundation

### 3.1 Types

**File:** `features/cms/types.ts`

All types from features doc Section 2 — domain types matching backend serializers exactly (with ALL fields), enums as union literals, permission types, input types, `WithPermissions<CmsPermissions>` composed types.

Critical type decisions:
- Use `type` not `interface` for all CMS types (backend contract matching)
- No `enum` — use union literal types
- Import `WithPermissions` from `@/types/api`

### 3.2 API Client

**File:** `features/cms/api/cms-api.ts`

**Context-aware base URL:**
```typescript
type CmsApiContext =
  | { type: "platform" }
  | { type: "business"; businessSlug: string };

function cmsBaseUrl(context: CmsApiContext): string {
  if (context.type === "platform") return "/api/v1/cms/admin";
  return `/api/v1/cms/business/${context.businessSlug}`;
}
```

**38 API functions organized by domain:**

| Domain | Functions | Count |
|--------|-----------|-------|
| Sites | fetchSites, fetchSite, createSite, updateSite, deleteSite | 5 |
| Pages | fetchPages, fetchPage (`?depth=full`), createPage, publishPage (`?site=`), unpublishPage, exportPage, importPage | 7 |
| Block Placements | fetchBlockPlacement, updateDraftContent, fetchBlockHistory, rollbackBlock | 4 |
| Template Catalog | fetchCatalogSections, fetchCatalogBlocks | 2 |
| Template Library | fetchLibrarySections, activateSection, deactivateSection, fetchLibraryBlocks, activateBlock, deactivateBlock | 6 |
| Templates (admin) | fetchAdminSectionTemplates, fetchAdminBlockTemplates | 2 |
| Media | fetchMediaFiles, fetchMediaFile, uploadMediaFile (FormData), updateMediaFile, deleteMediaFile | 5 |
| API Keys | fetchApiKeys (`?site={uuid}`), createApiKey, revokeApiKey | 3 |
| Platform Mgmt | fetchBusinessCmsStatus, toggleBusinessCms, fetchBusinessActivations | 3 |
| **Total** | | **37** |

**Key implementation notes:**
- Publish/unpublish/export/import require `?site={siteSlug}` query param
- Page detail supports `?depth=full` for tree response
- API key list uses `?site={uuid}` (UUID, not slug)
- Upload uses `FormData` with `multipart/form-data` content type
- `createApiKey` returns `key` field (one-time) — must be captured before cache invalidation

### 3.3 Query Keys

**File:** `lib/query-keys.ts` — add `cms` namespace

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
  adminSectionTemplates: () => [...queryKeys.cms.all, "admin-section-templates"] as const,
  adminBlockTemplates: () => [...queryKeys.cms.all, "admin-block-templates"] as const,
  mediaFiles: (params?) => [...queryKeys.cms.all, "media-files", params] as const,
  mediaFile: (uuid: string) => [...queryKeys.cms.all, "media-file", uuid] as const,
  apiKeys: (siteId?: string) => [...queryKeys.cms.all, "api-keys", siteId] as const,
  businessStatus: () => [...queryKeys.cms.all, "business-status"] as const,
  businessActivations: (uuid: string) => [...queryKeys.cms.all, "business-activations", uuid] as const,
},
```

### 3.4 Query Hooks

**File:** `features/cms/hooks/use-cms-queries.ts`

17 query hooks using `queryOptions()` factory pattern:

| Hook | staleTime | Notes |
|------|-----------|-------|
| `useSites(ctx, params?)` | 30s | |
| `useSite(ctx, slug)` | 1min | Returns `CmsSiteWithPerms` (business) |
| `usePages(ctx, params?)` | 30s | `?site=slug&status=filter` |
| `usePage(ctx, slug, params?)` | 1min | `?depth=full` for tree. Returns `CmsPageDetailWithPerms` (business) |
| `useBlockPlacement(ctx, uuid)` | 10s | Returns `CmsBlockPlacementWithPerms` (business) |
| `useBlockHistory(ctx, uuid)` | 30s | Paginated version list |
| `useCatalogSections(bizSlug)` | 5min | Business only |
| `useCatalogBlocks(bizSlug)` | 5min | Business only |
| `useLibrarySections(bizSlug)` | 5min | Business only |
| `useLibraryBlocks(bizSlug)` | 5min | Business only |
| `useAdminSectionTemplates()` | 5min | Platform only |
| `useAdminBlockTemplates()` | 5min | Platform only |
| `useMediaFiles(ctx, params?)` | 1min | `?folder=uuid&type=mime` |
| `useMediaFile(ctx, uuid)` | 1min | Returns `CmsMediaFileWithPerms` (business) |
| `useApiKeys(ctx, siteId?)` | 5min | `?site=uuid` |
| `useBusinessCmsStatus()` | 5min | Platform only |
| `useBusinessActivations(uuid)` | 5min | Platform only |

### 3.5 Mutation Hooks

**File:** `features/cms/hooks/use-cms-mutations.ts`

20 mutation hooks. Each invalidates related queries on success:

| Hook | Invalidates |
|------|-------------|
| `useCreateSite(ctx)` | sites list |
| `useUpdateSite(ctx, slug)` | site detail + sites list |
| `useDeleteSite(ctx, slug)` | sites list |
| `useCreatePage(ctx)` | pages list |
| `usePublishPage(ctx)` | page detail + pages list |
| `useUnpublishPage(ctx)` | page detail + pages list |
| `useExportPage(ctx)` | none (returns data) |
| `useImportPage(ctx)` | page detail |
| `useUpdateDraftContent(ctx, uuid)` | block placement detail |
| `useRollbackContent(ctx, uuid)` | block placement + history |
| `useActivateSectionTemplate(bizSlug)` | library + catalog |
| `useDeactivateSectionTemplate(bizSlug)` | library + catalog |
| `useActivateBlockTemplate(bizSlug)` | library + catalog |
| `useDeactivateBlockTemplate(bizSlug)` | library + catalog |
| `useUploadMediaFile(ctx)` | media list |
| `useUpdateMediaFile(ctx, uuid)` | media file + media list |
| `useDeleteMediaFile(ctx, uuid)` | media list |
| `useCreateApiKey(ctx)` | api keys (after key dialog closes) |
| `useRevokeApiKey(ctx)` | api keys |
| `useToggleBusinessCms(uuid)` | business status list |

### 3.6 Feature Gate Handler

**File:** `features/cms/utils/cms-feature-gate-handler.ts`

**Hook file:** `features/cms/hooks/use-cms-feature-gate.ts` (separate file, follows chat pattern)

Reactive feature gate detection using `Set<CmsFeatureFlag>` + `useSyncExternalStore`:

```typescript
type CmsFeatureFlag = "business_cms" | "activation_request";
```

When any CMS API call returns 403 with `code: "feature_disabled"`:
1. Map the `feature` detail to a `CmsFeatureFlag`
2. Add to session-level `Set`
3. Fire listeners → `useCmsFeatureEnabled()` returns `false` → UI hides elements reactively

### 3.7 CmsAccessGate Component

**File:** `features/cms/components/CmsAccessGate.tsx`

**Used inside every business CMS page** (not as a layout guard):

```typescript
export function CmsAccessGate({ children }: { children: React.ReactNode }) {
  const cmsEnabled = useCmsFeatureEnabled("business_cms");

  // First visit: probe API (fetchSites) to detect feature gate
  // Subsequent visits: read from feature gate handler cache

  if (cmsEnabled === false) {
    return <CmsActivationPage />;
  }

  return <>{children}</>;
}
```

**CmsActivationPage** — shown when business.cms_enabled=false:
- If `activation_request` feature enabled → "Request CMS Access" button (uses transaction system)
- If disabled → "Contact platform admin" message
- If request pending → "Your request is pending" status

### 3.8 Constants

**File:** `features/cms/constants/cms-constants.ts`

- `PAGE_STATUS_CONFIG` — label + color per status
- `BLOCK_STATUS_CONFIG` — label + color
- `VERSION_ACTION_CONFIG` — label per action type
- `CMS_FIELD_TYPE_CONFIG` — maps 18 backend field types to UI components
- `ALLOWED_MEDIA_TYPES` — mirrors backend whitelist
- `TEMPLATE_ORG_TYPE_LABELS` — display labels

### 3.9 Schema-to-Form-Field Mapper

**File:** `features/cms/utils/schema-to-form-fields.ts`

Converts CMS block template schema fields to form builder `FormField` objects for reuse:

| CMS Type | Maps To | Reusable? |
|----------|---------|-----------|
| `text` | `text` | YES — FieldRenderer |
| `textarea` | `textarea` | YES — FieldRenderer |
| `richtext` | — | NO — needs TipTap/Plate editor (NEW component) |
| `number` | `decimal` | YES — FieldRenderer |
| `boolean` | `boolean` | YES — FieldRenderer |
| `url` | `url` | YES — FieldRenderer |
| `email` | `email` | YES — FieldRenderer |
| `date` | `date` | YES — FieldRenderer |
| `datetime` | `datetime` | YES — FieldRenderer |
| `select` | `select` | YES — FieldRenderer |
| `multiselect` | `checkbox_group` | YES — FieldRenderer |
| `media` | — | NO — needs CMS media picker (NEW component) |
| `color` | — | NO — needs color picker (NEW component) |
| `icon` | — | NO — needs icon picker (NEW component) |
| `repeater` | — | NO — needs nested field group (NEW component) |
| `list` | — | NO — needs tag-like input (NEW component) |
| `relation` | — | NO — needs entity reference picker (NEW component) |
| `json` | — | NO — needs code editor (NEW component) |

**Reuse count: 11 of 18 types reuse FieldRenderer. 7 need new components.**

---

## 4. Phase 2: Core UI

### 4.1 Site Management

**Components:**
- `SiteListPage` — context-aware (reads `ctx` prop: platform or business)
- `SiteCreateDialog` — form: name, slug (auto-gen from name), domain, description
- `SiteDetailPage` — info card + tabs (Pages, API Keys). Tier 1.5: reads `_permissions`
- `SiteEditForm` — inline edit (gated by `can_edit_site`)

**Tier 1.5 pattern:**
```tsx
const { data: site } = useSite(ctx, slug);
const permissions = site?._permissions;

<Can allowed={permissions?.can_edit_site}><EditButton /></Can>
<Can allowed={permissions?.can_delete_site}><DeleteButton /></Can>
```

**Quota indicator** (business context only):
```tsx
<QuotaBar current={sites.length} limit={maxSites} label="Sites" />
```

### 4.2 Page Management

**Components:**
- `PageListPage` — table filtered by site, status tabs (All/Draft/Published/Archived)
- `PageCreateDialog` — form: site_id (pre-selected), title, slug, path, page_type, order

**Backend gap noted:** Page update (PATCH) and delete (DELETE) endpoints don't exist yet. UI shows disabled edit/delete buttons with tooltip "Coming soon".

### 4.3 Page Editor

**The most complex component.** Desktop layout:

```
┌─────────────────────────────────────────────────────────┐
│ Page Header: Title, Status Badge, Publish/Unpublish     │
├──────────────┬──────────────────────────────────────────┤
│ Content Tree │ Block Content Editor                     │
│              │ (schema-driven form for selected block)  │
│ □ Section 1  │                                          │
│   ├ Block A  │ ┌ Title: [______________]               │
│   └ Block B  │ │ Body:  [__________________]           │
│ □ Section 2  │ │ Image: [Select Media...]              │
│   └ Block C  │ │ CTA:   [______________]               │
│              │ └───────────────────────────             │
├──────────────┴──────────────────────────────────────────┤
│ Footer: Version History | Export | Import               │
└─────────────────────────────────────────────────────────┘
```

**Components:**
- `PageEditor` — orchestrator, fetches page with `?depth=full`, manages selected block
- `ContentTree` — tree view: section_placements → block_placements, `role="tree"`
- `ContentTreeItem` — individual node with icon, label, status dot, click to select
- `BlockContentEditor` — renders schema-driven form for selected block's template
- `CmsFieldRenderer` — renders one field; delegates to FieldRenderer (11 types) or CMS-specific components (7 types)

**Schema version mismatch warning:**
```tsx
{placement.schema_version_validated < placement.template.schema_version && (
  <Alert variant="warning">
    Template schema has been updated. Content may need adjustment.
  </Alert>
)}
```

### 4.4 CMS-Specific Field Components

**New components for 7 field types not in form builder:**

| Component | CMS Type | Description |
|-----------|----------|-------------|
| `CmsRichTextField` | `richtext` | TipTap or Plate editor with nh3-safe HTML output |
| `CmsMediaPicker` | `media` | Dialog opening media library, returns `{ media_id: uuid }` |
| `CmsColorPicker` | `color` | Color swatch grid + hex/rgba input |
| `CmsIconPicker` | `icon` | Icon grid selector (Lucide icons or custom set) |
| `CmsRepeaterField` | `repeater` | Nested field group with add/remove items (max 1 nesting level) |
| `CmsListField` | `list` | Tag-like input for string arrays |
| `CmsRelationField` | `relation` | Entity search + select (UUID reference) |
| `CmsJsonEditor` | `json` | Code editor with JSON syntax highlighting |

### 4.5 Publish Flow

**Components:**
- `PublishButton` — gated by `can_publish_content`
- `PublishConfirmDialog` — "Validate and publish all blocks?"
- `PublishErrorPanel` — parses `publish_errors` array, maps to tree items, shows field-level errors
- `UnpublishButton` — confirmation dialog, gated by `can_publish_content`

**Error handling:**
```typescript
// publish_errors shape from backend:
[{
  section_placement_id: string,
  block_placement_id: string,
  block_template: string,
  field_key: string,
  error_type: string,
  message: string,
}]

// Build error map: Map<blockPlacementId, errors[]>
// Highlight failing blocks in ContentTree
// Show field-level errors in BlockContentEditor
```

### 4.6 Version History

**Components:**
- `VersionHistoryPanel` — slide-out panel, paginated version list
- `VersionItem` — version_number, action badge (using VERSION_ACTION_CONFIG), author, timestamp
- `VersionPreview` — read-only view of `content_snapshot`
- `RollbackConfirmDialog` — "Restore version {N}? This creates a new version."

### 4.7 Export / Import

**In page editor footer:**
- Export button → calls `exportPageApi` → triggers JSON file download
- Import button → file picker → validates JSON → calls `importPageApi`
- Import is content-only (matches blocks by UUID, skips unmatched)

---

## 5. Phase 3: Templates & Media

### 5.1 Template Catalog (Business Only)

**Page:** `/bconsole/[slug]/cms/catalog`

- `TemplateCatalogPage` — tabs: Section Templates | Block Templates
- `TemplateCatalogGrid` — card grid of available (not yet activated) templates
- `TemplateCatalogCard` — display_name, type badge, org_type badge, is_default indicator, "Activate" button
- Quota indicator: "5/20 templates activated"
- Empty state: "All available templates are already in your library"

### 5.2 Template Library (Business Only)

**Page:** `/bconsole/[slug]/cms/library`

- `TemplateLibraryPage` — tabs: Section Templates | Block Templates
- `TemplateLibraryCard` — display_name, type, "Remove" button
- Deactivation confirmation + `template_in_use` error handling (400 → toast message)

### 5.3 Template Browser (Platform)

**Page:** `/pconsole/cms/templates`

Read-only view of ALL templates (superuser manages via Django Admin):
- Cards show org_type, is_default badge, schema_version
- No activate/deactivate (platform uses templates directly without activation)
- **Note:** No template detail endpoint exists — cards show inline info only, no drill-down page

### 5.4 Media Library

**Shared component between platform and business contexts.**

- `MediaLibraryPage` — grid/list toggle + upload zone + file detail panel
- `MediaGrid` — thumbnail grid with file info overlay
- `MediaListView` — table alternative (filename, type, size, usage_count, date)
- `MediaUploadZone` — drag-and-drop + click-to-upload (FormData, multipart)
- `MediaFileDetail` — side panel: preview, alt_text edit, title edit, usage info, delete
- `MediaPicker` — dialog variant for content editor `media` fields

**Backend gap:** No folder management API. The `?folder=uuid` filter works but folder CRUD (create/list/delete folders) has no endpoint. Media library shows flat file list for now. Folder navigation is deferred.

**Quota indicator** (business): "45/100 files" + "Max 10MB per file"

---

## 6. Phase 4: Management & Advanced

### 6.1 API Key Management

**Page:** Within site detail (tab) OR standalone `/pconsole/cms/api-keys`, `/bconsole/[slug]/cms/api-keys`

- `ApiKeyListPage` — table: name, key_prefix (masked), is_active, rate_limit, last_used_at
- `ApiKeyCreateDialog` — name, allowed_origins (multi-input), rate_limit, expires_at
- `ApiKeyRevealDialog` — shown ONCE after creation with copy-to-clipboard + "This key won't be shown again" warning
- `ApiKeyRevokeConfirmDialog` — "This action cannot be undone"

**One-time key reveal pattern:**
```typescript
const createMutation = useCreateApiKey(ctx);
const [revealedKey, setRevealedKey] = useState<string | null>(null);

createMutation.mutate(data, {
  onSuccess: (response) => {
    setRevealedKey(response.key); // Show dialog FIRST
  },
});

// On dialog close: invalidate query cache
const handleDialogClose = () => {
  setRevealedKey(null);
  queryClient.invalidateQueries({ queryKey: queryKeys.cms.apiKeys(siteId) });
};
```

### 6.2 Platform Business CMS Management

**Page:** `/pconsole/cms/businesses`

- `BusinessCmsManagementPage` — table: legal_name, slug, cms_enabled toggle
- `BusinessActivationsPanel` — slide-out showing activated templates per business
- Toggle CMS → on enable, toast: "CMS enabled for {name}. {N} default templates activated."

### 6.3 CMS Activation Request Flow

**Reuses transaction system components.**

**New hook:** `features/cms/hooks/use-cms-activation-request.ts`

Follows `use-business-creation-request.ts` pattern exactly:

```typescript
type CmsActivationStatus =
  | "loading"
  | "can_request"
  | "pending"
  | "has_info_requested"
  | "accepted"
  | "denied"
  | "in_cooldown";

export function useCmsActivationRequest(businessSlug: string) {
  // 1. fetchTransactionsApi({ transaction_type: "cms_activation_request", role: "initiator" })
  // 2. Derive status from latest transaction
  // 3. Return: { status, activeTransaction, submit, isSubmitting }
}
```

**CmsActivationPage** (rendered by CmsAccessGate when cms_enabled=false):

```tsx
function CmsActivationPage({ businessSlug }) {
  const { status, submit, isSubmitting, activeTransaction } = useCmsActivationRequest(businessSlug);
  const requestEnabled = useCmsFeatureEnabled("activation_request");

  switch (status) {
    case "can_request":
      return requestEnabled
        ? <RequestCard onSubmit={submit} isSubmitting={isSubmitting} />
        : <ContactAdminCard />;
    case "pending":
      return <PendingCard transaction={activeTransaction} />;
    case "has_info_requested":
      return <ActionNeededCard transaction={activeTransaction} />;
    case "in_cooldown":
      return <CooldownCard />;
    default:
      return <LoadingCard />;
  }
}
```

**Reusable from transactions:**
- `RequestWithFormDialog` — if activation requires a form
- `TRANSACTION_STATUS_CONFIG` — status badges
- `TransactionFormFieldInput` — form field rendering

---

## 7. Phase 5: Polish

### 7.1 Auto-Save

```typescript
const debouncedSave = useDebouncedCallback((content) => {
  updateDraftMutation.mutate({ draft_content: content });
}, 2000);

// Status indicator in editor header:
// "Saving..." | "Saved" | "Unsaved changes" | "Error saving"
```

### 7.2 Responsive Layout

- **Desktop (>1024px):** Tree panel (280px) + Content editor (flex-1)
- **Tablet (768-1024px):** Collapsible tree panel + full-width editor
- **Mobile (<768px):** Stack: list → tap → editor fills screen
- Sticky save/publish bar on mobile

### 7.3 Accessibility

- Content tree: `role="tree"` / `role="treeitem"`, `aria-expanded`, `aria-selected`
- Status announcements: `aria-live="polite"` for save status, publish result
- Form labels from schema `label` field
- Color contrast on status badges
- Keyboard: Tab through tree, Enter to select, Escape to deselect

### 7.4 Error Handling (All Scenarios)

| Error | HTTP | Rule/Code | UI Response |
|-------|------|-----------|-------------|
| Duplicate slug | 409 | `conflict` | Inline form error on slug field |
| Publish validation | 400 | `validation_error` | Per-block error panel + tree highlighting |
| Feature disabled | 403 | `feature_disabled` | CmsAccessGate → activation page |
| Permission denied | 403 | `permission_denied` | Toast: "You don't have permission" |
| Template not activated | 400 | `template_not_activated` | Toast + link to catalog |
| Template not eligible | 400 | `template_not_eligible` | Toast: "Not available for your org type" |
| Template in use | 400 | `template_in_use` | Toast: "Cannot remove — template in use" |
| Limit exceeded | 400 | `*_exceeded` | Toast with current/max counts |
| Required page/block | 400 | `required_page_*` | Disabled delete button + tooltip |
| Not found | 404 | `not_found` | Redirect to list page |
| Network error | — | — | Retry with backoff |

### 7.5 Tests

| Test File | Covers | Priority |
|-----------|--------|----------|
| `cms-api.test.ts` | All 37 API functions | P0 |
| `use-cms-queries.test.ts` | Query hooks | P0 |
| `use-cms-mutations.test.ts` | Mutation hooks | P0 |
| `CmsFieldRenderer.test.tsx` | All 18 field type renderings | P0 |
| `CmsAccessGate.test.tsx` | Guard logic, activation page | P0 |
| `cms-feature-gate-handler.test.ts` | Feature gate detection | P0 |
| `SiteListPage.test.tsx` | Site CRUD | P1 |
| `PageEditor.test.tsx` | Content tree, block selection | P1 |
| `BlockContentEditor.test.tsx` | Schema-driven form, auto-save | P1 |
| `PublishFlow.test.tsx` | Publish, validation errors, unpublish | P1 |
| `TemplateCatalog.test.tsx` | Browse, activate, limits | P1 |
| `MediaLibrary.test.tsx` | Upload, grid, file detail | P1 |
| `ApiKeyManagement.test.tsx` | Create, reveal, revoke | P1 |
| `CmsActivationRequest.test.tsx` | Request flow states | P1 |

---

## 8. Reuse Matrix

| Existing System | Reused For | How |
|----------------|-----------|-----|
| Form Builder `FieldRenderer` | 11 of 18 CMS field types | `CmsFieldRenderer` delegates common types |
| Form Builder `FileUploadField` | Media upload + image fields | Use as-is for upload zone |
| Form Builder `field-validation.ts` | Client-side content validation | Adapt validation patterns |
| Transaction `use-business-creation-request` | CMS activation request state machine | Clone + adapt for `cms_activation_request` type |
| Transaction `RequestWithFormDialog` | Activation request form | Use as-is (generic props) |
| Transaction `TRANSACTION_STATUS_CONFIG` | Activation request status badges | Reference for styling |
| Common `<Can>` | All 14 Tier 1.5 permission gates | Wrap action buttons |
| Common `QuotaBar` | Site/page/media/template limit indicators | Pass current/limit |
| Common `ConfirmActionDialog` | Delete, revoke, rollback confirmations | Use as-is |
| Common `StatusBadge` | Page/block status display | Use with CMS status configs |

---

## 9. Implementation Order

### Phase 1 — Foundation (~Week 1)
1. `features/cms/types.ts`
2. `features/cms/constants/cms-constants.ts`
3. `features/cms/api/cms-api.ts`
4. `lib/query-keys.ts` (add cms)
5. `features/cms/hooks/use-cms-queries.ts`
6. `features/cms/hooks/use-cms-mutations.ts`
7. `features/cms/utils/cms-feature-gate-handler.ts`
8. `features/cms/hooks/use-cms-feature-gate.ts`
9. `features/cms/utils/schema-to-form-fields.ts`
10. `features/cms/components/CmsAccessGate.tsx`
11. `features/cms/components/CmsActivationPage.tsx`
12. `lib/navigation-config.ts` (update business + platform CMS sections)
13. Route page files (stubs replacing placeholders)
14. P0 tests (API, queries, mutations, feature gate, guard)

### Phase 2 — Core UI (~Week 2-3)
15. `SiteListPage`, `SiteCreateDialog`, `SiteDetailPage`, `SiteEditForm`
16. `PageListPage`, `PageCreateDialog`
17. `CmsFieldRenderer` (with FieldRenderer delegation)
18. 7 CMS-specific field components (richtext, media, color, icon, repeater, list, json)
19. `ContentTree`, `ContentTreeItem`
20. `BlockContentEditor`
21. `PageEditor` (orchestrator)
22. `PublishButton`, `PublishConfirmDialog`, `PublishErrorPanel`, `UnpublishButton`
23. `VersionHistoryPanel`, `VersionItem`, `RollbackConfirmDialog`
24. Export/Import buttons

### Phase 3 — Templates & Media (~Week 3-4)
25. `TemplateCatalogPage`, `TemplateCatalogGrid`, `TemplateCatalogCard`
26. `TemplateLibraryPage`, `TemplateLibraryCard`
27. `TemplateBrowserPage` (platform, read-only)
28. `MediaLibraryPage`, `MediaGrid`, `MediaUploadZone`
29. `MediaFileDetail`, `MediaPicker` (dialog for content editor)

### Phase 4 — Management (~Week 4)
30. `ApiKeyListPage`, `ApiKeyCreateDialog`, `ApiKeyRevealDialog`
31. `BusinessCmsManagementPage`
32. `use-cms-activation-request.ts` hook
33. Full CmsActivationPage states

### Phase 5 — Polish (~Week 5)
34. Auto-save + status indicators
35. Responsive layout breakpoints
36. Accessibility audit (ARIA, keyboard, contrast)
37. All P1 tests
38. Performance (`React.memo`, lazy loading for heavy components)

---

## 10. Risks & Mitigations

| Risk | Level | Mitigation |
|------|-------|------------|
| Rich text editor complexity | HIGH | Use TipTap (battle-tested, React-native). Sanitize output matches backend nh3 whitelist. |
| 7 custom field components | MEDIUM | Build incrementally. Start with text/number/select (reuse). Add rich fields in Phase 3. |
| Page editor state management | MEDIUM | Use component state + TQ cache. No Zustand store. Auto-save via debounced mutation. |
| Context-aware API calls | LOW | Single `CmsApiContext` parameter on all API fns. Components derive context from route params. |
| Feature gate race condition | LOW | CmsAccessGate probes on mount, caches result with `staleTime: Infinity`. |
| Publish error UX | MEDIUM | Build error map: `Map<blockId, errors[]>`. Highlight in tree, show inline in editor. |
| Missing backend endpoints (page PATCH/DELETE, folders) | LOW | Show disabled UI with "Coming soon" tooltip. Don't build what can't work. |

---

## 11. Definition of Done

Each phase is complete when:
1. All components render correctly with mock data
2. API integration works against live backend (Docker dev environment)
3. Permission gating works — Tier 1 (nav items) + Tier 1.5 (`_permissions` in detail views)
4. Feature gates work — 403 detection + CmsAccessGate graceful degradation
5. Tests pass — P0 tests in Phase 1, all tests by Phase 5
6. `npm run lint` + `npm run typecheck` pass with zero errors
7. Responsive layout works on desktop + tablet + mobile
8. No `any` types, no eslint suppressions
