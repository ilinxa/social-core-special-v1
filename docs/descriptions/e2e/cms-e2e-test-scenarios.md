# CMS E2E Test Scenarios — Comprehensive Checklist

**Version:** 1.0
**Date:** 2026-03-30
**Framework:** Playwright (TypeScript)
**Backend Reference:** `docs/implementations/backend/cms-system.md`
**Existing CMS E2E:** `e2e/tests/smoke/cms/` (5 L1 files), `e2e/tests/workflows/cms-content-lifecycle.spec.ts` (1 L2), `e2e/tests/scenarios/persona-gary-cms.spec.ts` (1 L3)
**E2E Helpers:** `e2e/helpers/cms.helper.ts` (createCmsSiteViaApi, createCmsPageViaApi, publishCmsPageViaApi, createCmsApiKeyViaApi)

---

## Table of Contents

1. [Test Architecture Overview](#1-test-architecture-overview)
2. [L1 Smoke Tests — Platform CMS Admin](#2-l1-smoke-tests--platform-cms-admin)
3. [L1 Smoke Tests — Business CMS](#3-l1-smoke-tests--business-cms)
4. [L1 Smoke Tests — Public API](#4-l1-smoke-tests--public-api)
5. [L1 Smoke Tests — CMS Activation & Feature Gates](#5-l1-smoke-tests--cms-activation--feature-gates)
6. [L1 Smoke Tests — Tier 1.5 Permissions](#6-l1-smoke-tests--tier-15-permissions)
7. [L1 Smoke Tests — Limits & Quotas](#7-l1-smoke-tests--limits--quotas)
8. [L2 Workflow Tests](#8-l2-workflow-tests)
9. [L3 Scenario Tests](#9-l3-scenario-tests)
10. [Helper Functions Needed](#10-helper-functions-needed)
11. [Page Object Models Needed](#11-page-object-models-needed)

---

## 1. Test Architecture Overview

### Existing CMS E2E Coverage

| File | Layer | Tests | Coverage |
|------|-------|-------|----------|
| `smoke/cms/site-management.spec.ts` | L1 | ~3 | Placeholder — needs full CRUD |
| `smoke/cms/page-publish.spec.ts` | L1 | ~3 | Placeholder — needs publish flow |
| `smoke/cms/content-editing.spec.ts` | L1 | ~3 | Placeholder — needs block editing |
| `smoke/cms/media-library.spec.ts` | L1 | ~3 | Placeholder — needs upload/grid |
| `smoke/cms/api-keys.spec.ts` | L1 | ~3 | Placeholder — needs create/revoke |
| `workflows/cms-content-lifecycle.spec.ts` | L2 | 1 | Create→publish→unpublish (API-only) |
| `scenarios/persona-gary-cms.spec.ts` | L3 | 18 | Gary persona (platform admin CMS) |

### New Tests to Create

| Layer | New Files | Est. Tests | Focus |
|-------|-----------|------------|-------|
| L1 Smoke | 12 | ~60 | Individual CMS features |
| L2 Workflow | 6 | ~6 | Cross-system flows |
| L3 Scenario | 1 | ~25 | Business CMS persona |
| **Total** | **19** | **~91** | |

---

## 2. L1 Smoke Tests — Platform CMS Admin

### 2.1 `smoke/cms/platform-site-crud.spec.ts`

```
@layer L1
@system cms
@parameters P1(create), P2(read), P3(update), P4(delete)
@priority P0
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | Platform admin can list sites | Login as platform admin → navigate to `/cconsole/sites` | Page renders, heading visible |
| 2 | Platform admin can create a site | Click "New Site" → fill name/slug → submit | 201 response, site appears in list |
| 3 | Platform admin can view site detail | Click site row → site detail page loads | Name, slug, domain, status visible |
| 4 | Platform admin can edit a site | Click Edit → change name → Save | Site name updated in UI |
| 5 | Platform admin can delete a site | Click Delete → confirm dialog → submit | Site removed from list |
| 6 | Duplicate slug shows error | Create site → create another with same slug | Error message on slug field |

### 2.2 `smoke/cms/platform-page-crud.spec.ts`

```
@layer L1
@system cms
@parameters P1(create), P2(read), P4(delete), P5(status-transitions)
@priority P0
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | Create page within a site | Navigate to site → click "New Page" → fill form → submit | Page appears in list with "Draft" badge |
| 2 | Page list shows status tabs | Navigate to page list | All/Draft/Published/Archived tabs visible |
| 3 | Filter pages by status | Click "Published" tab | Only published pages shown |
| 4 | Required page cannot be deleted | Attempt to delete page with `is_required=true` | Error: "Required pages cannot be deleted" |
| 5 | Delete non-required page | Click Delete on regular page → confirm | Page removed |

### 2.3 `smoke/cms/platform-page-publish.spec.ts`

```
@layer L1
@system cms
@parameters P5(status-transitions), P7(validation)
@priority P0
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | Publish page with valid content | Open page editor → click Publish → confirm | Status changes to "Published", toast success |
| 2 | Publish fails with empty required fields | Open page with empty required block → Publish | Publish error panel shows, blocks highlighted in tree |
| 3 | Unpublish published page | Open published page → click Unpublish → confirm | Status reverts to "Draft" |
| 4 | Publish confirmation dialog appears | Click Publish | Confirmation dialog with warning text visible |

### 2.4 `smoke/cms/platform-content-editing.spec.ts`

```
@layer L1
@system cms
@parameters P3(update), P8(content-versioning)
@priority P0
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | Content tree renders sections and blocks | Open page editor with depth=full | Section nodes with block children visible |
| 2 | Click block to open editor | Click a block in tree | Block content editor opens with fields |
| 3 | Edit text field and auto-save | Type in text field → wait 3s | "Saved" indicator appears |
| 4 | Edit richtext field (TipTap) | Click richtext field → type → use bold toolbar | Content saved with HTML formatting |
| 5 | Schema version mismatch warning | Load block where schema_version_validated < template.schema_version | Warning banner shown |

### 2.5 `smoke/cms/platform-version-history.spec.ts`

```
@layer L1
@system cms
@parameters P8(content-versioning)
@priority P1
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | Version history panel opens | Click "History" button on block | Sheet opens with version list |
| 2 | Version items show action badges | Open history | Versions have "Auto-saved", "Published", "Rolled back" badges |
| 3 | Rollback restores previous version | Click "Restore" on old version → confirm | Content reverts, new "Rolled back" version created |

### 2.6 `smoke/cms/platform-export-import.spec.ts`

```
@layer L1
@system cms
@parameters P9(data-portability)
@priority P1
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | Export page downloads JSON | Click Export → file download triggers | JSON file with export_version "3.1" |
| 2 | Import page content from JSON | Click Import → select JSON file → upload | Success toast, content updated |

### 2.7 `smoke/cms/platform-templates-browser.spec.ts`

```
@layer L1
@system cms
@parameters P2(read)
@priority P1
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | Template browser lists section templates | Navigate to `/cconsole/templates` | Section template cards visible |
| 2 | Template browser lists block templates | Switch to Block Templates tab | Block template cards visible |
| 3 | Template cards show org_type badges | Inspect template card | org_type badge (All/Platform/Business) visible |
| 4 | Template cards show schema version | Inspect block template card | "v1" or version badge visible |

### 2.8 `smoke/cms/platform-media-library.spec.ts`

```
@layer L1
@system cms
@parameters P1(create), P2(read), P4(delete), P10(file-upload)
@priority P0
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | Media library renders grid view | Navigate to `/cconsole/media` | Grid of thumbnails visible |
| 2 | Switch to list view | Click list view toggle | Table with columns visible |
| 3 | Upload image file | Click Upload → select PNG file | File appears in grid, success toast |
| 4 | Upload rejected for invalid type | Select .exe file | Error toast: "File type not allowed" |
| 5 | View file detail panel | Click file thumbnail | Sheet with metadata opens |
| 6 | Delete file with confirmation | Click Delete in detail → confirm | File removed, toast success |
| 7 | Drag-and-drop upload | Drag PNG onto drop zone | File uploaded, success toast |

### 2.9 `smoke/cms/platform-api-keys.spec.ts`

```
@layer L1
@system cms
@parameters P1(create), P4(delete), P11(api-key-auth)
@priority P0
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | API key list renders | Navigate to site detail → API Keys tab | Empty state or key list visible |
| 2 | Create API key shows one-time reveal | Click "Create Key" → fill name → submit | Reveal dialog with cmsk_ prefixed key |
| 3 | Copy key to clipboard | Click copy button in reveal dialog | Clipboard contains key text |
| 4 | After dialog close, key is not retrievable | Close reveal dialog → check list | Only key_prefix shown, no full key |
| 5 | Revoke API key | Click Revoke → confirm | Key marked as revoked |

### 2.10 `smoke/cms/platform-business-management.spec.ts`

```
@layer L1
@system cms
@parameters P12(cms-activation)
@priority P1
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | Business CMS management page lists businesses | Navigate to `/cconsole/businesses` | Business list with CMS toggle visible |
| 2 | Toggle CMS on for a business | Flip switch ON | Toast: "CMS enabled for {name}" |
| 3 | Toggle CMS off for a business | Flip switch OFF | Toast: "CMS disabled for {name}" |
| 4 | View activated templates for business | Click business row | Sheet showing activated templates |

---

## 3. L1 Smoke Tests — Business CMS

### 3.1 `smoke/cms/business-site-crud.spec.ts`

```
@layer L1
@system cms, organization
@parameters P1(create), P2(read), P3(update), P4(delete)
@priority P0
```

**Precondition:** Business with `cms_enabled=true` (set via API helper)

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | Business owner can list sites | Login as business owner → navigate to `/cconsole/{slug}/sites` | Page renders via CmsBusinessGuard |
| 2 | Business can create site | Click "New Site" → fill form → submit | Site created with owner_type="business" |
| 3 | Business can view site detail with _permissions | Click site → detail page | `_permissions` object present on response (Tier 1.5) |
| 4 | Business can edit site | Click Edit → change name → Save | Updated |
| 5 | Business can delete site | Delete → confirm | Removed |
| 6 | Site scoped to business | Create site → list sites | Only business's own sites shown |

### 3.2 `smoke/cms/business-template-catalog.spec.ts`

```
@layer L1
@system cms
@parameters P13(template-activation)
@priority P0
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | Catalog shows eligible templates | Navigate to `/cconsole/{slug}/catalog` | Templates with org_type "all" or "business" visible |
| 2 | Platform-only templates NOT shown | Check catalog | No templates with org_type "platform" |
| 3 | Activate section template | Click "Activate" on a section template | Template moves to library, toast success |
| 4 | Activate block template | Click "Activate" on a block template | Template moves to library |
| 5 | Already-activated templates excluded from catalog | Activate template → check catalog | Template no longer in catalog list |

### 3.3 `smoke/cms/business-template-library.spec.ts`

```
@layer L1
@system cms
@parameters P13(template-activation)
@priority P0
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | Library shows activated templates | Navigate to `/cconsole/{slug}/library` | Activated templates listed |
| 2 | Remove template from library | Click "Remove" → confirm | Template removed, appears back in catalog |
| 3 | Cannot remove template in use | Create page using template → try remove | Error: "Cannot remove — template in use" |

### 3.4 `smoke/cms/business-media-library.spec.ts`

```
@layer L1
@system cms
@parameters P1(create), P10(file-upload)
@priority P1
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | Business media library renders | Navigate to `/cconsole/{slug}/media` | Grid/list view visible |
| 2 | Upload file (business context) | Upload PNG → check list | File appears with owner_type="business" |
| 3 | File size limit enforced | Upload file > max_media_file_size_mb | Error: "File exceeds XMB limit" |
| 4 | Quota bar shows count | Check header area | "X/Y files" quota indicator (when limit > 0) |

---

## 4. L1 Smoke Tests — Public API

### 4.1 `smoke/cms/public-api-key-auth.spec.ts`

```
@layer L1
@system cms
@parameters P11(api-key-auth)
@priority P0
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | Public site with valid API key | GET `/cms/public/sites/{slug}` with valid X-CMS-API-Key | 200 with site data |
| 2 | Public site without API key | GET without header | 401 Unauthorized |
| 3 | Public site with invalid API key | GET with random key | 401 Unauthorized |
| 4 | Public published page returns content | GET `/cms/public/pages/{slug}` with key | 200 with published_content, NO draft_content |
| 5 | Public draft page returns 404 | GET draft page slug with key | 404 Not Found |
| 6 | API key origin validation | GET with mismatched Origin header | 403 Forbidden |
| 7 | Expired API key rejected | Use key with expires_at in past | 403 Forbidden |

---

## 5. L1 Smoke Tests — CMS Activation & Feature Gates

### 5.1 `smoke/cms/feature-gate-cms-disabled.spec.ts`

```
@layer L1
@system cms, feature-gates
@parameters P14(feature-gates)
@priority P0
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | business.cms.enabled=false returns 403 | Disable gate → request CMS endpoint | 403 feature_disabled |
| 2 | platform.cms=false blocks admin | Disable gate → request admin endpoint | 403 feature_disabled |
| 3 | CMS navigation hides when gate disabled | Login → check sidebar | CMS nav items not visible |

### 5.2 `smoke/cms/business-cms-activation.spec.ts`

```
@layer L1
@system cms, transactions
@parameters P12(cms-activation)
@priority P1
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | CmsBusinessGuard shows activation page when disabled | Login as business owner (cms_enabled=false) → navigate to CMS | "CMS Not Enabled" card shown |
| 2 | Request CMS access button visible | Check activation page | "Request CMS Access" button visible |
| 3 | Submit activation request | Click button → submit | Transaction created, status changes to "Pending" |
| 4 | Pending request shows status | Revisit CMS page | "Request Pending" card shown |
| 5 | Platform admin approves request | Login as platform admin → approve transaction | Business cms_enabled=true, default templates provisioned |
| 6 | After approval, CMS accessible | Login as business owner → navigate to CMS | CmsBusinessGuard passes, sites page renders |
| 7 | Cooldown after denial | Platform denies → business tries again within 14 days | "Request denied, try again later" card |

---

## 6. L1 Smoke Tests — Tier 1.5 Permissions

### 6.1 `smoke/cms/permissions-tier-1-5.spec.ts`

```
@layer L1
@system cms, rbac
@parameters P6(permissions)
@priority P0
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | Site detail returns _permissions for business user | GET business site detail | Response has _permissions with 14 booleans |
| 2 | Owner sees all permissions true | Login as business owner → GET site detail | All 14 permissions true |
| 3 | Base member sees limited permissions | Login as base member → GET site detail | Only can_view_content true, others false |
| 4 | Edit button hidden without can_edit_site | Login as base member → view site detail UI | No Edit button visible |
| 5 | Delete button hidden without can_delete_site | Login as base member → view site detail UI | No Delete button visible |
| 6 | Publish button hidden without can_publish_content | Login as base member → view page editor UI | No Publish button visible |
| 7 | Create Site button hidden without can_create_site | Login as base member → view sites list | No "New Site" button visible |

---

## 7. L1 Smoke Tests — Limits & Quotas

### 7.1 `smoke/cms/limits-enforcement.spec.ts`

```
@layer L1
@system cms, feature-gates
@parameters P7(validation), P14(feature-gates)
@priority P1
```

| # | Test | Steps | Assertions |
|---|------|-------|------------|
| 1 | max_sites limit enforced | Set max_sites=1 → create 1 site → create 2nd | Error: "CMS Site limit reached" |
| 2 | max_pages_per_site limit enforced | Set max_pages=2 → create 2 pages → create 3rd | Error: "CMS Page limit reached" |
| 3 | max_active_section_templates limit enforced | Set limit=1 → activate 1 → activate 2nd | Error: "Section template activation limit reached" |
| 4 | max_media_files limit enforced | Set limit=1 → upload 1 file → upload 2nd | Error: "CMS Media File limit reached" |
| 5 | max_api_keys_per_site limit enforced | Set limit=1 → create 1 key → create 2nd | Error: "CMS API Key limit reached" |
| 6 | Limit 0 means unlimited | Set all limits to 0 → create many resources | No errors |
| 7 | Quota bar reflects limit | Set max_sites=5 → create 2 sites | QuotaBar shows "2/5 Sites" |

---

## 8. L2 Workflow Tests

### 8.1 `workflows/cms-business-onboarding.spec.ts`

```
@layer L2
@system cms, transactions, organization
@parameters P12(cms-activation), P13(template-activation)
@priority P0
```

**Flow:** Business requests CMS → Platform approves → Default templates provisioned → Business creates first site → Creates first page → Publishes

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Register user, create business | Business exists, cms_enabled=false |
| 2 | Business owner navigates to CMS | CmsBusinessGuard shows activation page |
| 3 | Owner submits CMS activation request | Transaction created with status "pending" |
| 4 | Platform admin approves request | cms_enabled=true, default templates activated |
| 5 | Owner navigates to CMS again | Sites page loads (no activation page) |
| 6 | Owner browses template catalog | Available templates shown (not yet activated are in catalog) |
| 7 | Owner creates first site | Site with owner_type="business" |
| 8 | Owner creates first page | Page with status "draft" |
| 9 | Owner edits block content | Draft auto-saved |
| 10 | Owner publishes page | Status changes to "published" |
| 11 | Public API serves published content | GET with API key returns published_content |

### 8.2 `workflows/cms-template-lifecycle.spec.ts`

```
@layer L2
@system cms
@parameters P13(template-activation), P5(status-transitions)
@priority P1
```

**Flow:** Business activates template → Creates page using it → Tries to deactivate → Blocked → Deletes page → Deactivates successfully

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Business activates block template from catalog | Activation created |
| 2 | Creates page using activated template | Page created with block placement |
| 3 | Attempts to deactivate template | Error: "template_in_use" |
| 4 | Deletes the page | Page soft-deleted |
| 5 | Deactivates template successfully | Activation removed, template back in catalog |

### 8.3 `workflows/cms-content-versioning-workflow.spec.ts`

```
@layer L2
@system cms
@parameters P8(content-versioning)
@priority P1
```

**Flow:** Create page → Edit block → Check version → Edit again → Rollback → Verify restored content → Publish → Check version

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Create site + page with block | Block has draft_content |
| 2 | Edit block content (title="V1") | Version 1 created (draft_save) |
| 3 | Wait 30s (throttle) + edit again (title="V2") | Version 2 created |
| 4 | Check history | 2 versions in list |
| 5 | Rollback to version 1 | draft_content restored to "V1" |
| 6 | Check history | Version 3 with action=rollback |
| 7 | Publish page | Version 4 with action=publish, published_content = "V1" |

### 8.4 `workflows/cms-public-api-full-cycle.spec.ts`

```
@layer L2
@system cms
@parameters P11(api-key-auth), P5(status-transitions)
@priority P0
```

**Flow:** Create site → Create API key → Create page → Publish → Verify public access → Unpublish → Verify 404 → Revoke key → Verify 401

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Create site | 201 |
| 2 | Create API key | Returns key with cmsk_ prefix |
| 3 | Create page + add content | Draft page |
| 4 | Public API: page not visible | 404 (draft page) |
| 5 | Publish page | Status = published |
| 6 | Public API: page visible | 200 with published_content, NO draft_content |
| 7 | Unpublish page | Status = draft |
| 8 | Public API: page not visible again | 404 |
| 9 | Revoke API key | Key inactive |
| 10 | Public API: key rejected | 401 |

### 8.5 `workflows/cms-platform-business-management.spec.ts`

```
@layer L2
@system cms, organization
@parameters P12(cms-activation)
@priority P1
```

**Flow:** Platform admin enables CMS for business → Business creates content → Platform admin disables CMS → Business loses access → Re-enable → Content preserved

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Platform admin toggles CMS ON for business | cms_enabled=true, default templates activated |
| 2 | Business owner creates site + page | Content exists |
| 3 | Platform admin toggles CMS OFF | cms_enabled=false |
| 4 | Business owner navigates to CMS | CmsBusinessGuard shows activation page (content NOT deleted) |
| 5 | Platform admin toggles CMS back ON | cms_enabled=true |
| 6 | Business owner accesses CMS | Content still there (preserved) |

### 8.6 `workflows/cms-cross-context-isolation.spec.ts`

```
@layer L2
@system cms, organization
@parameters P6(permissions)
@priority P1
```

**Flow:** Two businesses with CMS → Each creates sites → Verify complete isolation

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Create Business A + enable CMS | cms_enabled=true |
| 2 | Create Business B + enable CMS | cms_enabled=true |
| 3 | Business A creates site "alpha" | Site exists for Business A |
| 4 | Business B creates site "beta" | Site exists for Business B |
| 5 | Business A lists sites | Only sees "alpha" |
| 6 | Business B lists sites | Only sees "beta" |
| 7 | Business A cannot access Business B's site | 404 or 403 |

---

## 9. L3 Scenario Tests

### 9.1 `scenarios/persona-helen-business-cms.spec.ts`

```
@layer L3
@system cms, transactions, organization, rbac
@parameters P1-P14
@priority P1
```

**Persona:** Helen is a business owner who requests CMS access, gets approved, builds a website, and manages content with her team.

| Step | Action |
|------|--------|
| 1 | Register Helen, create business |
| 2 | Navigate to business CMS → see activation page |
| 3 | Submit CMS activation request |
| 4 | Login as platform admin → approve request |
| 5 | Login as Helen → CMS now accessible |
| 6 | Browse template catalog → activate 3 templates |
| 7 | Create site "Helen's Blog" |
| 8 | Create page "Home" with hero + content sections |
| 9 | Edit hero block: title, richtext body, media image |
| 10 | Edit content block: text, list, select fields |
| 11 | Check version history → 2 versions exist |
| 12 | Publish page → success |
| 13 | Create API key for site |
| 14 | Verify public API returns published content |
| 15 | Create page "About" |
| 16 | Publish "About" |
| 17 | Unpublish "Home" |
| 18 | Verify public API: "Home" returns 404, "About" returns 200 |
| 19 | Export "About" page as JSON |
| 20 | Import JSON into "Home" page |
| 21 | Re-publish "Home" |
| 22 | Invite team member (editor role with cms permissions) |
| 23 | Login as editor → verify CMS access with limited permissions |
| 24 | Editor cannot delete site (no can_delete_site) |
| 25 | Editor can edit content (has can_edit_content) |

---

## 10. Helper Functions Needed

### Update `e2e/helpers/cms.helper.ts`

Existing helpers are API-only. Add these for the new business CMS features:

| Function | Purpose |
|----------|---------|
| `enableCmsForBusinessViaApi(apiClient, businessId)` | PATCH `/cms/admin/businesses/{id}/` with cms_enabled=true |
| `createCmsPageWithContentViaApi(apiClient, ctx, siteId, content)` | Create page + placement + block + set draft_content |
| `activateTemplateViaApi(apiClient, businessSlug, templateId, type)` | POST to library activate endpoint |
| `getPublicPageViaApi(apiClient, apiKey, pageSlug)` | GET public page with X-CMS-API-Key header |
| `uploadMediaFileViaApi(apiClient, ctx, filePath)` | POST multipart to media upload |
| `setBusinessCmsLimits(dbClient, businessId, limits)` | Direct DB update for test limit enforcement |

### Update `e2e/fixtures/`

| Fixture | Purpose |
|---------|---------|
| `businessWithCmsPage` | Pre-created business + CMS enabled + site + page (for smoke tests) |
| `platformWithTemplates` | Platform with section + block templates seeded (for catalog tests) |

---

## 11. Page Object Models Needed

### Update `e2e/pages/cms/`

| POM | Pages Covered |
|-----|--------------|
| `PlatformCmsSites.page.ts` | `/cconsole/sites`, site list, create dialog |
| `PlatformCmsSiteDetail.page.ts` | `/cconsole/sites/{slug}`, info card, edit form, tabs |
| `PlatformCmsPageEditor.page.ts` | Page editor: content tree, block editor, publish/unpublish, history |
| `PlatformCmsTemplates.page.ts` | `/cconsole/templates`, section/block tabs |
| `PlatformCmsMedia.page.ts` | `/cconsole/media`, grid/list, upload, detail sheet |
| `PlatformCmsApiKeys.page.ts` | API Keys tab in site detail |
| `PlatformCmsBusinesses.page.ts` | `/cconsole/businesses`, toggle, activations sheet |
| `BusinessCmsSites.page.ts` | `/cconsole/{slug}/sites`, with CmsBusinessGuard |
| `BusinessCmsCatalog.page.ts` | `/cconsole/{slug}/catalog`, activate button |
| `BusinessCmsLibrary.page.ts` | `/cconsole/{slug}/library`, remove button |
| `BusinessCmsMedia.page.ts` | `/cconsole/{slug}/media`, upload, grid |
| `CmsActivationPage.page.ts` | Activation request states (request, pending, cooldown) |

---

## Summary

| Category | Files | Tests |
|----------|-------|-------|
| L1 Smoke — Platform | 10 | ~45 |
| L1 Smoke — Business | 4 | ~18 |
| L1 Smoke — Public API | 1 | ~7 |
| L1 Smoke — Activation/Gates | 2 | ~10 |
| L1 Smoke — Permissions | 1 | ~7 |
| L1 Smoke — Limits | 1 | ~7 |
| L2 Workflows | 6 | ~6 |
| L3 Scenarios | 1 | ~25 |
| **Total New** | **26** | **~125** |
| **Existing CMS E2E** | **7** | **~30** |
| **Combined CMS E2E** | **33** | **~155** |
