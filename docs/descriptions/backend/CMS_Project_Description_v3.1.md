# ARENA-Z Content Management System (CMS)

## Comprehensive Project Description & Architecture Specification

**Version:** 3.1
**Status:** Planning & Requirements
**Platform:** Django REST Framework + Next.js 16
**Storage:** Local filesystem (development) / AWS S3 or Cloudflare R2 via `django-storages` (production)
**Last Updated:** February 2026

---

## 1. Executive Summary

The ARENA-Z CMS is a **template-based, headless content management system** designed around a strict separation between **structural definition** (developer/superuser domain) and **content population** (organization admin domain).

The core philosophy is: **do the hard things once, reuse everywhere.** A developer defines page structures, section layouts, block schemas, and field definitions as **templates** — reusable, platform-wide structural blueprints. These templates are then **placed** onto pages, and each placement is a unique, isolated content container that organization admins can fill. The admin receives a fixed structure — essentially a form — and can only fill in, update, or clear field values. They cannot create pages, add sections, remove blocks, or modify field definitions.

The system uses a **placement-as-instance** architecture: the join tables that connect templates to pages are themselves the content-bearing entities. This guarantees content isolation by construction — there is no way for content to leak across pages because each placement row is structurally unique to its parent context.

This CMS integrates with the existing ARENA-Z ecosystem: the **RBAC permission system** (`apps.rbac`) governs access via `ActorContext` and `MembershipPolicy`, the **audit/observability system** (`apps.core.observability`) tracks every mutation via `AuditService` and structured logging, and the **media library** provides centralized asset management with full reference tracking.

---

## 2. Core Architecture Philosophy

### 2.1 Template + Placement Architecture

This is the most critical architectural decision in the system. It solves the **reusable structure with isolated content** problem through a two-entity model.

**The Problem:** If content lives on a shared block or a shared instance that can be placed on multiple pages, editing one page's content can unintentionally affect another. Content must be isolated per-placement while the structural definition (schema) remains shared.

**The Solution — Placements ARE Instances:**

| Entity | Who Creates | What It Holds | Reusable? |
|---|---|---|---|
| **Template** (e.g., `BlockTemplate`) | Superuser | Schema, field definitions, validation rules, default content, metadata | Yes — referenced across pages, sections, organizations |
| **Placement** (e.g., `SectionBlockPlacement`) | Superuser (structure) / System (auto-creates on attach) | Order, visibility, config overrides, **draft_content**, **published_content**, status | No — structurally unique to its parent context |

There are no separate "Instance" models. The placement join tables themselves carry the content. This makes content isolation a **structural guarantee** rather than a convention that must be enforced with business logic.

**How It Works:**

1. Superuser creates a `BlockTemplate` with a schema defining fields like "title (text, required)", "image (media, optional)", etc.
2. Superuser attaches that template to a section on a page — the system creates a `SectionBlockPlacement` row. This row IS the content container.
3. The admin fills in `SectionBlockPlacement.draft_content`. On publish, `draft_content` is copied to `published_content`.
4. If the same `BlockTemplate` is attached to another section or page, a completely separate `SectionBlockPlacement` row is created. Content is isolated by construction.

**The Hierarchy:**

```
Page
  +-- PageSectionPlacement (order, visibility, overrides -> SectionTemplate)
       +-- SectionBlockPlacement (order, visibility, overrides -> BlockTemplate,
                                  draft_content, published_content, status)
```

### 2.2 Template-Based Design

The system operates on a **two-layer interaction model**:

**Structural Layer (Superuser-Only)**
The superuser defines the complete tree of a page — which section templates exist, in what order, which block templates each section contains, and what fields each block exposes. This layer is immutable from the admin's perspective. Structural definitions are created and managed exclusively through the Django Admin panel, which must be well-organized with proper inlines, fieldsets, and custom actions.

**Content Layer (Organization Admin)**
The admin interacts with a pre-built form. Every page they see has a fixed skeleton. Their **only** capability is populating field **values** within the constraints set by the superuser — respecting required/nullable flags, field types, validation rules, and min/max constraints. They cannot add or remove structural elements. **Critically, admins have zero access to field definitions themselves — they cannot see, modify, create, or delete field schemas, field types, field names, or validation rules. The admin's entire interaction surface is limited to the content values within existing fields. The fields are the form; the admin fills in the form. Nothing more.**

### 2.3 Dual-Content Draft/Publish Model

Every content-bearing placement maintains **two separate JSONB fields**:

- **`draft_content`** — the working copy that admins edit freely
- **`published_content`** — the frozen copy that the public API serves

When an admin edits content, only `draft_content` changes. The live site is unaffected. When the admin triggers "Publish," the system validates `draft_content` against the template's schema, and if valid, copies it to `published_content` **within a single atomic database transaction**. This creates a clear, unambiguous separation between "what's being worked on" and "what's live."

### 2.4 JSONB-Driven Field Flexibility

Rather than creating database columns for every possible field type, block templates use a **schema JSONB** that defines what fields exist and their constraints. Placements use **draft_content** and **published_content** JSONB fields to hold actual values. This gives unlimited field variety without schema migrations, while the schema definition enforces structure and validation at the API level.

### 2.5 Public vs Admin API Separation

The API is split into two distinct prefixes with different authorization and data exposure rules:

- **`/api/v1/cms/admin/`** — for authenticated admin/superuser access. Returns `draft_content` by default, includes template schemas for form rendering, supports all mutation operations.
- **`/api/v1/cms/public/`** — for public/frontend consumption. Returns `published_content` only, never exposes `draft_content` or template schemas (unless explicitly needed for frontend rendering), read-only.

This separation is enforced at the endpoint level, not just via query parameters, making it impossible for public consumers to accidentally access draft content.

### 2.6 Layered Architecture Integration

The CMS follows the same layered architecture as all apps in this project:

```
HTTP REQUEST -> urls.py (routing only)
    -> views.py (HTTP orchestration, OpenAPI schema via @extend_schema)
        |-> INPUT SERIALIZERS (validation via BaseInputSerializer)
        |-> SELECTORS (read-only queries, keyword-only args)
        +-> SERVICES (writes, business rules, @transaction.atomic)
            -> ActorContext + MembershipPolicy (authorization)
            -> AuditService.log() (audit trail)
            -> get_logger(__name__) (structured logging)
            -> MODELS (from apps.core.models base classes)
                -> DATABASE
    <- OUTPUT SERIALIZERS (response shaping via BaseOutputSerializer) <- HTTP RESPONSE
```

**Key rules from `django-app-creator` skill:**
- Business logic ONLY in services — never in views, serializers, or models
- All service/selector/policy methods use **keyword-only arguments**: `def method(*, arg: type)`
- All writes wrapped in `@transaction.atomic`
- Exceptions from `apps.core.exceptions` — never Django/DRF exceptions directly
- Permissions from `apps.core.permissions`
- Pagination from `apps.core.pagination`

---

## 3. Data Model Architecture

### 3.1 Model Hierarchy Overview

```
PlatformAccount (singleton)
  +-- Site (website container / grouping, owner_type=PLATFORM)
        +-- Page
              +-- PageSectionPlacement (join + section-level config)
                    |   |-- order, is_required, is_visible, config_overrides
                    |   +-- template -> SectionTemplate
                    |
                    +-- SectionBlockPlacement (join + content container)
                          |-- order, is_required, is_visible, config_overrides
                          |-- template -> BlockTemplate
                          |-- draft_content (JSONB) -- working copy [EDITABLE BY ADMIN]
                          |-- published_content (JSONB) -- frozen live copy [SET ON PUBLISH]
                          +-- status
```

### 3.2 Base Model Composition (from `apps.core.models`)

CMS models inherit from the **existing composable abstract base models** in `apps/core/models/base.py`. No custom base model is defined for CMS.

**Available base models:**

| Base Model | Provides | Use When |
|---|---|---|
| `UUIDModel` | `id` (UUID v4 primary key) | All CMS models — non-guessable IDs |
| `TimeStampedModel` | `created_at` (auto_now_add, indexed), `updated_at` (auto_now) | Lightweight timestamp tracking |
| `UserStampedModel` | Extends TimeStamped + `created_by` (FK->User), `updated_by` (FK->User) | When tracking who created/modified |
| `SoftDeleteModel` | `is_deleted`, `deleted_at`, `deleted_by`, `soft_delete()`, `restore()`. Managers: `objects` (excludes deleted), `all_objects` (includes deleted) | When records should not be hard-deleted |
| `BaseModel` | TimeStamped + SoftDelete | Standard domain models |
| `AuditModel` | UserStamped + SoftDelete | Full audit trail models |

**CMS model inheritance map:**

| CMS Model | Inherits From | Rationale |
|---|---|---|
| `Site` | `UUIDModel, AuditModel` | UUID PK, user tracking, soft delete (protect pages). Uses `owner_type`/`owner_id` pattern |
| `Page` | `UUIDModel, AuditModel` | UUID PK, user tracking, soft delete |
| `SectionTemplate` | `UUIDModel, AuditModel` | UUID PK, user tracking, soft delete (protect placements) |
| `BlockTemplate` | `UUIDModel, AuditModel` | UUID PK, user tracking, soft delete (protect placements) |
| `PageSectionPlacement` | `UUIDModel, TimeStampedModel` | UUID PK, timestamps. No user stamps (system-created). Cascade-deletes with page |
| `SectionBlockPlacement` | `UUIDModel, UserStampedModel` | UUID PK, user tracking (content editing attribution). No soft delete (cascade-deletes with section placement) |
| `ContentVersion` | `UUIDModel` | UUID PK only. Has its own `created_at` and `created_by` fields |
| `MediaFolder` | `UUIDModel, AuditModel` | UUID PK, user tracking, soft delete. Uses `owner_type`/`owner_id` pattern |
| `MediaFile` | `UUIDModel, AuditModel` | UUID PK, user tracking, soft delete. Tombstoning is separate from soft delete. Uses `owner_type`/`owner_id` pattern |
| `CMSApiKey` | `UUIDModel, AuditModel` | UUID PK, user tracking, soft delete (revocation) |
| `MediaUsage` | `UUIDModel, TimeStampedModel` | UUID PK, timestamps. System-managed tracking record |

**Slug fields** are defined per-model where needed (Site, Page, SectionTemplate, BlockTemplate, MediaFolder) — they are NOT part of any base model.

**Import pattern:**
```python
from apps.core.models import UUIDModel, AuditModel, TimeStampedModel, UserStampedModel
```

### 3.3 Slug vs UUID Access Strategy

| Model | Identification | API Access Pattern | Rationale |
|---|---|---|---|
| Site | Slug (unique per owner) | `/sites/{slug}/` | Human-named, few per owner account |
| Page | Slug (unique per site) | `/pages/{slug}/` | Human-named, URL-friendly |
| SectionTemplate | Slug (globally unique) | `/templates/sections/{slug}/` | Platform-wide reusable, named |
| BlockTemplate | Slug (globally unique) | `/templates/blocks/{slug}/` | Platform-wide reusable, named |
| PageSectionPlacement | UUID | `/section-placements/{uuid}/` | Auto-created, many per page |
| SectionBlockPlacement | UUID | `/block-placements/{uuid}/` | Auto-created, content container |
| MediaFolder | Slug (unique per owner+parent) | `/media/folders/{slug}/` | Human-named |
| MediaFile | UUID | `/media/files/{uuid}/` | Many files, auto-generated names |

Placement models may optionally have a `label` CharField for admin UI display purposes, but this is never used for routing or uniqueness.

---

### 3.4 Site Model

The Site model acts as a **website container** — a logical grouping of pages managed by the CMS. Currently, the CMS is a **platform-level feature only** — only the platform account owns and manages CMS sites. Individual business accounts do not have CMS access in the initial build.

The model uses the **`owner_type` / `owner_id` polymorphic pattern** (same as the Form Builder) to support future expansion to business accounts without migration.

| Field | Type | Description |
|---|---|---|
| _From UUIDModel_ | | `id` (UUID v4 primary key) |
| _From AuditModel_ | | `created_at`, `updated_at`, `created_by`, `updated_by`, `is_deleted`, `deleted_at`, `deleted_by` |
| `owner_type` | CharField (choices: OwnerType) | Which **account type** owns this site. Currently always `OwnerType.PLATFORM`. Future: `OwnerType.BUSINESS` |
| `owner_id` | UUIDField (nullable, indexed) | UUID of the **owning account record** — NOT a user. For platform: `PlatformAccount.id` (the singleton platform account's PK). For future business: `BusinessAccount.id`. Null only for `OwnerType.SYSTEM` |
| `name` | CharField | Display name of the site |
| `slug` | SlugField | URL-safe identifier |
| `domain` | CharField (nullable) | Associated domain, if any |
| `description` | TextField (nullable) | Internal description/notes |
| `default_locale` | CharField | Default language code (e.g., `en`) |
| `metadata` | JSONB (nullable) | SEO defaults, theme settings, global config |
| `is_active` | BooleanField | Whether the site is live |

**Slug Uniqueness:** `Unique(owner_type, owner_id, slug)` — filtered to `is_deleted=False`

**Relationships:**

- Owned by one account via `owner_type` + `owner_id` (polymorphic, like Form Builder)
- Has many Pages (reverse ForeignKey)
- Has one designated homepage (nullable ForeignKey to Page)

**Note on Ownership Pattern:** Using `owner_type`/`owner_id` follows the same pattern as `FormTemplate` in the Form Builder system (see `apps.core.constants.OwnerType`). **`owner_id` always refers to an account record (PlatformAccount or BusinessAccount), never a user.** The `created_by`/`updated_by` fields (from AuditModel) track which user made changes. For the initial build, all sites will be `owner_type=PLATFORM`, `owner_id=PlatformAccount.id`. When business CMS access is added in the future, sites can be created with `owner_type=BUSINESS`, `owner_id=BusinessAccount.id` without schema changes.

**Import:**
```python
from apps.core.constants import OwnerType
# OwnerType.SYSTEM = "system"
# OwnerType.PLATFORM = "platform"
# OwnerType.BUSINESS = "business"
```

---

### 3.5 Page Model

A Page represents a single routable page within a Site. Its structure (which sections, in what order) is defined by the superuser and is immutable by admins.

| Field | Type | Description |
|---|---|---|
| _From UUIDModel_ | | `id` (UUID v4 primary key) |
| _From AuditModel_ | | `created_at`, `updated_at`, `created_by`, `updated_by`, `is_deleted`, `deleted_at`, `deleted_by` |
| `site` | ForeignKey -> Site | The site this page belongs to |
| `title` | CharField | Page title |
| `slug` | SlugField | URL-safe identifier |
| `description` | TextField (nullable) | Internal description |
| `path` | CharField | URL path relative to the site (e.g., `/about`, `/pricing`) |
| `page_type` | CharField | Categorization (e.g., `landing`, `content`, `legal`, `blog_post`) |
| `metadata` | JSONB (nullable) | SEO title, description, OG tags, structured data |
| `status` | CharField | One of: `draft`, `published`, `archived` |
| `published_at` | DateTimeField (nullable) | When the page was last published |
| `order` | PositiveIntegerField | Ordering within the site's page list |
| `is_required` | BooleanField | Default `false`. Set by superuser. If `true`, admins cannot delete or hide this page. Used for essential pages (e.g., homepage, terms, privacy) that must remain present in the site structure |
| `is_visible` | BooleanField | Default `true`. Admin can toggle to `false` ONLY if `is_required=false`. Hidden pages are excluded from public API navigation but remain accessible by direct URL if published |

**Constraints:**

- `Unique(site, slug)` — filtered to `is_deleted=False`
- `Unique(site, path)` — no duplicate URL paths within a site
- `Unique(site, order)` — prevents ordering collisions
- If `is_required=true`, the API must prevent setting `is_visible=false` and must prevent deletion (soft or hard)

**Relationships:**

- Belongs to one Site (ForeignKey)
- Has many section placements through `PageSectionPlacement` (reverse ForeignKey)

---

### 3.6 SectionTemplate Model

A SectionTemplate is a **reusable layout definition** — the structural blueprint for a region of a page (hero area, feature grid, footer, etc.). It defines what type of section this is and carries layout metadata. SectionTemplates hold **no content** — content lives in block placements within the section.

| Field | Type | Description |
|---|---|---|
| _From UUIDModel_ | | `id` (UUID v4 primary key) |
| _From AuditModel_ | | `created_at`, `updated_at`, `created_by`, `updated_by`, `is_deleted`, `deleted_at`, `deleted_by` |
| `name` | CharField | Internal name (e.g., `hero_banner`, `feature_grid`, `testimonials`) |
| `display_name` | CharField | Human-readable name for admin UI |
| `slug` | SlugField | Globally unique URL-safe identifier |
| `description` | TextField (nullable) | Description of the section's purpose |
| `section_type` | CharField | Categorization (e.g., `header`, `content`, `footer`, `sidebar`) |
| `metadata` | JSONB (nullable) | General metadata, tags, categorization |
| `ui_config` | JSONB (nullable) | UI rendering hints — component name, layout mode, CSS classes, conditional display rules |

**Slug Uniqueness:** `Unique(slug)` — globally unique.

**Relationships:**

- Has many PageSectionPlacements (reverse ForeignKey)

**Note:** SectionTemplates are purely structural. They have no `status`, `content`, or organization scope. They are platform-wide reusable definitions.

---

### 3.7 PageSectionPlacement Model

The **placement record** that attaches a SectionTemplate to a Page. This is a one-to-many relationship from Page (each placement belongs to exactly one page). It carries ordering, visibility, and per-placement configuration.

| Field | Type | Description |
|---|---|---|
| _From UUIDModel_ | | `id` (UUID v4 primary key) — used for API access |
| _From TimeStampedModel_ | | `created_at`, `updated_at` |
| `page` | ForeignKey -> Page | The page this section is placed on |
| `template` | ForeignKey -> SectionTemplate | The section template being placed |
| `label` | CharField (nullable) | Optional admin-friendly label (e.g., "Hero Section on About Page") |
| `order` | PositiveIntegerField | Position of this section within the page |
| `is_required` | BooleanField | Set by superuser. If true, admin cannot hide this section |
| `is_visible` | BooleanField | Default `true`. Admin can toggle to `false` ONLY if `is_required=false` |
| `config_overrides` | JSONB (nullable) | Per-placement overrides (e.g., different background, spacing) |

**Constraints:**

- `Unique(page, order)` — exactly one section per position on a page
- If `is_required=true`, the API must prevent setting `is_visible=false`

**Relationships:**

- Belongs to exactly one Page (ForeignKey — NOT M2M)
- References one SectionTemplate (ForeignKey)
- Has many SectionBlockPlacements (reverse ForeignKey)

**Key Design Point:** This is a ForeignKey from placement to page, not a M2M through table. Each placement row belongs to exactly one page. Reusing a SectionTemplate on another page creates a completely separate PageSectionPlacement row.

---

### 3.8 BlockTemplate Model

A BlockTemplate is the **reusable schema definition** for a content block. It defines what fields exist, their types, validation rules, and required/nullable flags. BlockTemplates hold **no content** — content lives in SectionBlockPlacement rows.

| Field | Type | Description |
|---|---|---|
| _From UUIDModel_ | | `id` (UUID v4 primary key) |
| _From AuditModel_ | | `created_at`, `updated_at`, `created_by`, `updated_by`, `is_deleted`, `deleted_at`, `deleted_by` |
| `name` | CharField | Internal name (e.g., `hero_text`, `cta_button`, `team_card`) |
| `display_name` | CharField | Human-readable name for admin UI |
| `slug` | SlugField | Globally unique URL-safe identifier |
| `description` | TextField (nullable) | Description of the block's purpose |
| `block_type` | CharField | Categorization (e.g., `text`, `media`, `composite`, `repeater`) |
| `schema` | JSONB | **Field definitions** — types, validation, required/nullable flags. **Immutable by admins.** |
| `schema_version` | PositiveIntegerField | Auto-incremented on every schema change. Used to track affected placements |
| `default_content` | JSONB (nullable) | Default values set by superuser, used to pre-populate new placements |
| `metadata` | JSONB (nullable) | General metadata, tags, categorization |
| `ui_config` | JSONB (nullable) | Rendering hints — frontend component name, CSS classes, layout rules |

**Slug Uniqueness:** `Unique(slug)` — globally unique.

**Relationships:**

- Has many SectionBlockPlacements (reverse ForeignKey)

**Critical Design Note:** The `schema` field is **absolutely immutable by admins**. Admins cannot view schema editing interfaces, cannot modify field names, types, validation rules, or any structural aspect of the block. The schema is the form definition; the admin fills in the form. Only superusers can modify schemas through the Django Admin panel.

---

### 3.9 SectionBlockPlacement Model — The Content Container

This is the **core content-bearing entity** of the entire CMS. It attaches a BlockTemplate to a PageSectionPlacement and carries the actual draft and published content. Each placement is structurally unique — it belongs to exactly one section placement, which belongs to exactly one page. **Content isolation is guaranteed by construction.**

| Field | Type | Description |
|---|---|---|
| _From UUIDModel_ | | `id` (UUID v4 primary key) — used for API access |
| _From UserStampedModel_ | | `created_at`, `updated_at`, `created_by`, `updated_by` |
| `section_placement` | ForeignKey -> PageSectionPlacement | The section placement this block belongs to |
| `template` | ForeignKey -> BlockTemplate | The block template defining the schema |
| `label` | CharField (nullable) | Optional admin-friendly label for this placement |
| `order` | PositiveIntegerField | Position of this block within the section |
| `is_required` | BooleanField | Set by superuser. If true, admin cannot hide this block |
| `is_visible` | BooleanField | Default `true`. Admin can toggle to `false` ONLY if `is_required=false` |
| `config_overrides` | JSONB (nullable) | Per-placement overrides |
| `schema_version_validated` | PositiveIntegerField | The `BlockTemplate.schema_version` this placement was last validated against |
| `draft_content` | JSONB (nullable) | **Working copy** — the content admins edit. Not visible to public API. Pre-populated from `BlockTemplate.default_content` on creation |
| `published_content` | JSONB (nullable) | **Frozen live copy** — set only when the page is published. Public API serves this |
| `status` | CharField | One of: `draft`, `published` |

**Constraints:**

- `Unique(section_placement, order)` — exactly one block per position in a section
- Same `is_required` / `is_visible` logic as `PageSectionPlacement`

**Relationships:**

- Belongs to exactly one PageSectionPlacement (ForeignKey — NOT M2M)
- References one BlockTemplate (ForeignKey)
- Has many ContentVersions (reverse ForeignKey)

**Content Flow:**

1. Superuser places a BlockTemplate into a section — system creates a `SectionBlockPlacement` row with `draft_content` pre-populated from `BlockTemplate.default_content`.
2. Admin edits `draft_content` — saved freely, creates a ContentVersion with `action=draft_save`.
3. Admin triggers publish on the parent page — system validates ALL `draft_content` fields against their template schemas within a single transaction.
4. If valid, `draft_content` is copied to `published_content` for ALL block placements on the page — creates ContentVersions with `action=publish`.
5. Public API always reads `published_content`. Admin UI reads `draft_content`.
6. Rollback restores `draft_content` from a ContentVersion snapshot — requires re-publish to go live.

**Content Isolation Guarantee:**

```
Page A
  +-- PageSectionPlacement #1 (template: hero_banner)
       +-- SectionBlockPlacement #1 (template: hero_text)
            |-- draft_content: {"title": "Welcome to Page A"}    <- ISOLATED
            +-- published_content: {"title": "Welcome to Page A"}

Page B
  +-- PageSectionPlacement #2 (template: hero_banner)  <- same template, different placement
       +-- SectionBlockPlacement #2 (template: hero_text)  <- same template, different placement
            |-- draft_content: {"title": "Welcome to Page B"}    <- COMPLETELY SEPARATE
            +-- published_content: {"title": "Welcome to Page B"}
```

Editing Page A's hero text has zero effect on Page B. This is structural, not enforced by validation.

---

### 3.10 ContentVersion Model

Provides **content history** for rollback capability. A snapshot is stored when an admin saves or publishes block placement content.

| Field | Type | Description |
|---|---|---|
| _From UUIDModel_ | | `id` (UUID v4 primary key) |
| `block_placement` | ForeignKey -> SectionBlockPlacement | The block placement this version belongs to |
| `content_snapshot` | JSONB | Full copy of `draft_content` at this point in time |
| `version_number` | PositiveIntegerField | Auto-incrementing per block placement |
| `action` | CharField | One of: `draft_save`, `publish`, `rollback`, `import` |
| `created_by` | ForeignKey -> User | Who made this change |
| `created_at` | DateTimeField (auto_now_add) | When this version was created |
| `notes` | TextField (nullable) | Optional description of the change |

**Behavior:**

- On every `save` (draft) or `publish` action, a new `ContentVersion` is created automatically.
- Rollback restores `draft_content` from a selected version and creates a new version entry with `action=rollback`. **Rollback does NOT update `published_content`** — the admin must re-publish to push rolled-back content live.
- Versions are ordered by `version_number` descending.

**Cost Control:**

- **Retention policy**: Configurable maximum versions per block placement (default: 50). Oldest versions beyond this limit are automatically pruned.
- **Throttling**: If the admin UI autosaves, version creation is debounced — no more than 1 version per 30 seconds per block placement. Rapid edits within the throttle window update the latest version in-place (only if same user, same action=`draft_save`, and within window) rather than creating new ones.
- **Future optimization**: Switch to diff-based storage (store only changed fields) once the system is stable. The audit system already captures diffs for lightweight change tracking.

---

### 3.11 Complete Entity Relationship Summary

```
Account (owner_type + owner_id) --1:N--> Site --1:N--> Page
  (Currently: owner_type=PLATFORM only. Future: BUSINESS)

SectionTemplate (platform-wide, reusable schema)
BlockTemplate   (platform-wide, reusable schema + field definitions)

Page --1:N--> PageSectionPlacement
               |-- order, is_required, is_visible, config_overrides
               |-- template -> SectionTemplate
               |
               +--1:N--> SectionBlockPlacement
                          |-- order, is_required, is_visible, config_overrides
                          |-- template -> BlockTemplate
                          |-- draft_content (JSONB, admin-editable)
                          |-- published_content (JSONB, set on publish)
                          |-- status
                          +--1:N--> ContentVersion (history snapshots)

Account (owner_type + owner_id) --1:N--> MediaFolder --1:N--> MediaFile
  (Currently: owner_type=PLATFORM only. Future: BUSINESS)

CMSApiKey --N:1--> Site (public API access control)

Ownership chain (strict 1:N at every level):
  Page -> PageSectionPlacement -> SectionBlockPlacement -> ContentVersion
  (no M2M anywhere in the content chain -- isolation guaranteed)
```

### 3.12 Slug Uniqueness Scope

| Model | Slug/ID Strategy | Uniqueness Scope | Rationale |
|---|---|---|---|
| Site | Slug | `Unique(owner_type, owner_id, slug)` (filtered `is_deleted=False`) | Named, few per owner |
| Page | Slug | `Unique(site, slug)` + `Unique(site, path)` | Named, URL-friendly |
| SectionTemplate | Slug | `Unique(slug)` — globally unique | Platform-wide reusable |
| BlockTemplate | Slug | `Unique(slug)` — globally unique | Platform-wide reusable |
| PageSectionPlacement | UUID only | N/A (UUID is inherently unique) | Auto-created, accessed by UUID |
| SectionBlockPlacement | UUID only | N/A (UUID is inherently unique) | Auto-created, content container |
| MediaFolder | Slug | `Unique(owner_type, owner_id, parent, slug)` | Named, nested hierarchy |
| MediaFile | UUID only | N/A | Many files, auto-generated |

---

## 4. JSONB Schema Specification

### 4.1 Block Schema Structure

The `schema` JSONB field on each BlockTemplate defines the complete field structure. It follows this format:

```json
{
  "fields": [
    {
      "key": "field_machine_name",
      "type": "text",
      "label": "Field Display Name",
      "required": true,
      "editable": true,
      "help_text": "Guidance text for the admin",
      "default": null,
      "validation": {}
    }
  ]
}
```

### 4.2 Supported Field Types

**Important:** CMS field types are a **separate set** from the Form Builder's `FieldType` enum in `apps.core.constants`. The CMS defines its own `CMSFieldType` enum within the CMS app because the two systems have different field needs (CMS has `media`, `richtext`, `color`, `icon`, `relation`; Form Builder has `phone`, `currency`, `rating`, `location`, `checkbox_group`).

| Type | Description | Validation Options | Content Value Format |
|---|---|---|---|
| `text` | Single-line plain text | `max_length`, `min_length`, `pattern` (regex) | `"string value"` |
| `textarea` | Multi-line plain text | `max_length`, `min_length` | `"multi\nline\nstring"` |
| `richtext` | HTML rich text content | `max_length`, `allowed_tags` | `"<p>HTML content</p>"` |
| `number` | Integer or decimal number | `min`, `max`, `decimal_places` | `42` or `3.14` |
| `boolean` | True/false toggle | — | `true` or `false` |
| `url` | URL string | `allowed_protocols` | `"https://example.com"` |
| `email` | Email address | — | `"user@example.com"` |
| `date` | Date value | `min_date`, `max_date` | `"2026-02-25"` |
| `datetime` | Date and time value | `min_datetime`, `max_datetime` | `"2026-02-25T14:30:00Z"` |
| `select` | Single choice from options | `choices` (array of `{value, label}`) | `"selected_value"` |
| `multiselect` | Multiple choices from options | `choices`, `min_selected`, `max_selected` | `["value1", "value2"]` |
| `media` | Reference to media library file | `allowed_types` (e.g., `["image/*", "video/*"]`), `max_size_mb` | `{"media_id": "uuid", "alt": "text"}` |
| `list` | Ordered or unordered list of primitives | `ordered`, `min_items`, `max_items`, `item_type` | `["item1", "item2"]` |
| `repeater` | List of structured objects | `min_items`, `max_items`, `item_schema` | `[{...}, {...}]` |
| `relation` | Reference to another CMS entity | `target_model` (page, block_placement), `multiple` | `"uuid"` or `["uuid1", "uuid2"]` |
| `json` | Raw JSON (for advanced use) | `json_schema` (optional JSON Schema) | Any valid JSON |
| `color` | Color value | `format` (`hex`, `rgb`, `hsl`) | `"#FF5733"` |
| `icon` | Icon identifier | `icon_set` (e.g., `lucide`, `heroicons`) | `"arrow-right"` |

### 4.3 The Repeater Type — Nested Structured Objects

The `repeater` field type is critical for complex, dynamic content like card grids, team member lists, FAQ accordions, and pricing tiers. It allows a block placement to contain an **ordered list of structured items**, each conforming to a sub-schema.

**Schema Example — Team Members:**

```json
{
  "key": "team_members",
  "type": "repeater",
  "label": "Team Members",
  "required": true,
  "validation": {
    "min_items": 1,
    "max_items": 12
  },
  "item_schema": {
    "fields": [
      { "key": "name", "type": "text", "label": "Full Name", "required": true },
      { "key": "role", "type": "text", "label": "Job Title", "required": true },
      { "key": "photo", "type": "media", "label": "Photo", "required": false, "validation": { "allowed_types": ["image/*"] } },
      { "key": "bio", "type": "textarea", "label": "Short Bio", "required": false, "validation": { "max_length": 300 } },
      { "key": "linkedin", "type": "url", "label": "LinkedIn URL", "required": false }
    ]
  }
}
```

**Corresponding Content (in `draft_content` or `published_content`):**

```json
{
  "team_members": [
    {
      "name": "Jane Doe",
      "role": "CEO",
      "photo": { "media_id": "uuid-123", "alt": "Jane Doe headshot" },
      "bio": "Visionary leader with 15 years of experience.",
      "linkedin": "https://linkedin.com/in/janedoe"
    },
    {
      "name": "John Smith",
      "role": "CTO",
      "photo": null,
      "bio": null,
      "linkedin": null
    }
  ]
}
```

**Repeater Behavior:**

- Admin can add items up to `max_items`, remove items down to `min_items`
- Each item is validated independently against the `item_schema`
- Items are ordered — admin can reorder within the repeater
- Repeaters **cannot be nested** (no repeater inside a repeater) to keep complexity manageable
- Ordering is implicit by array index position

### 4.4 Field-Level Flags

Every field in the schema supports these universal flags:

| Flag | Type | Default | Description |
|---|---|---|---|
| `required` | boolean | `false` | If true, admin must provide a non-empty value before publishing |
| `editable` | boolean | `true` | If false, admin can see but not modify this field (superuser locks it) |
| `help_text` | string | `null` | Guidance text displayed to admin in the editing UI |
| `default` | varies | `null` | Default value pre-populated for admin |
| `placeholder` | string | `null` | Placeholder text in input fields |
| `group` | string | `null` | Logical grouping for admin UI organization (e.g., `"seo"`, `"content"`, `"settings"`) |

### 4.5 Media Field — Alt Text Precedence

When a `media` field references a `MediaFile`, two alt text sources exist:

1. **`MediaFile.alt_text`** — the file's default alt text (set in media library)
2. **Block-level `alt`** — per-reference override in content JSONB: `{"media_id": "uuid", "alt": "text"}`

**Precedence:** Block-level `alt` overrides `MediaFile.alt_text`. If block-level `alt` is null or empty, fall back to `MediaFile.alt_text`. The public API should resolve this and return the effective alt text.

---

## 5. Schema Validation Engine

### 5.1 Architecture

Content validation is handled by a server-side **`SchemaValidator`** service class (located in `apps/cms/validators.py` or `apps/cms/services/schema_validator.py`) that takes a BlockTemplate's schema and validates a content JSONB against it. This is not a loose convention — it is a concrete, testable component.

### 5.2 Validation Points

Validation runs at **two points** with different strictness levels:

| Point | Trigger | Strictness | Behavior on Failure |
|---|---|---|---|
| **Draft Save** | Admin saves `draft_content` | Permissive | Save succeeds. Warnings are returned to the admin UI (e.g., "Title is required but empty — you'll need to fill this before publishing"). |
| **Publish** | Admin triggers page publish | Strict | Publish is rejected. A structured, machine-readable error response is returned listing every failing field. |

### 5.3 Validation Rules by Field Type

The `SchemaValidator` enforces the following per field type:

- **text / textarea**: `min_length`, `max_length`, `pattern` (regex match)
- **richtext**: `max_length` (on stripped text), `allowed_tags` whitelist. **Sanitization is applied on every save** (draft and publish) using `nh3` or `bleach` — unsanitized HTML is never stored in the database.
- **number**: `min`, `max`, `decimal_places`, type coercion check (integer vs decimal)
- **url**: protocol whitelist (`allowed_protocols`), format validation
- **email**: RFC 5322 format validation
- **date / datetime**: range checks (`min_date`, `max_date`), ISO format validation
- **select / multiselect**: value must be in `choices` list, `min_selected` / `max_selected` count checks
- **media**: referenced `media_id` must exist in the media library and not be tombstoned, `allowed_types` MIME check
- **list**: `min_items` / `max_items` count, `item_type` validation per element, `ordered` flag (informational for frontend)
- **repeater**: `min_items` / `max_items` count, each item validated recursively against `item_schema`
- **relation**: referenced UUID must exist and be of the correct `target_model` type
- **json**: optional JSON Schema validation if `json_schema` is provided
- **color**: format validation (`hex`, `rgb`, `hsl`)
- **icon**: value must be in the specified `icon_set` (if validation is enabled)

### 5.4 Rich Text Sanitization

Rich text fields are **always sanitized on save**, not just on publish. This means:

- `draft_content` never contains unsanitized HTML
- `published_content` is guaranteed clean (since it's copied from already-sanitized draft)
- The `allowed_tags` whitelist from the schema is used as the sanitizer's tag allowlist
- Attributes are stripped unless explicitly whitelisted (e.g., `href` on `<a>`, `src` on `<img>`)

---

## 6. Media Library

### 6.1 Architecture

The media library is a **centralized, folder-based asset management system** scoped per owner account (using the same `owner_type`/`owner_id` pattern as Site). Currently, only the platform account owns CMS media. All media references in block content point to media library files by UUID. **Files are stored by path/key in the configured storage backend — URLs are generated at read time, never stored.**

**Storage backend:**
- **Development:** Django's default `FileSystemStorage` — files stored locally under `MEDIA_ROOT`
- **Production:** AWS S3 or Cloudflare R2 via `django-storages` — aligns with existing AWS infrastructure (SES for email) + `AWS_STORAGE_BUCKET_NAME` / `AWS_S3_*` env vars. R2 is S3-compatible and uses the same `django-storages` S3 backend.

The `storage_key` pattern in this spec works with all three backends (local, S3, R2) since `django-storages` abstracts the underlying provider.

### 6.2 MediaFolder Model

| Field | Type | Description |
|---|---|---|
| _From UUIDModel_ | | `id` (UUID v4 primary key) |
| _From AuditModel_ | | `created_at`, `updated_at`, `created_by`, `updated_by`, `is_deleted`, `deleted_at`, `deleted_by` |
| `owner_type` | CharField (choices: OwnerType) | Which **account type** owns this folder. Currently always `OwnerType.PLATFORM` |
| `owner_id` | UUIDField (nullable, indexed) | UUID of the **owning account record** (PlatformAccount.id or BusinessAccount.id) — NOT a user |
| `name` | CharField | Folder display name |
| `slug` | SlugField | URL-safe identifier |
| `parent` | ForeignKey -> self (nullable) | Parent folder for nesting |
| `path` | CharField | Full materialized path (e.g., `/images/heroes/2026/`) |

**Slug Uniqueness:** `Unique(owner_type, owner_id, parent, slug)`

**Constraints:**

- Unique together: `(owner_type, owner_id, parent, name)` — no duplicate folder names at the same level
- Maximum nesting depth enforced at API level (recommended: 5 levels)

### 6.3 MediaFile Model

| Field | Type | Description |
|---|---|---|
| _From UUIDModel_ | | `id` (UUID v4 primary key) |
| _From AuditModel_ | | `created_at`, `updated_at`, `created_by`, `updated_by`, `is_deleted`, `deleted_at`, `deleted_by` |
| `owner_type` | CharField (choices: OwnerType) | Which **account type** owns this file. Currently always `OwnerType.PLATFORM` |
| `owner_id` | UUIDField (nullable, indexed) | UUID of the **owning account record** (PlatformAccount.id or BusinessAccount.id) — NOT a user |
| `folder` | ForeignKey -> MediaFolder (nullable) | Containing folder (null = root) |
| `storage_key` | CharField | **Storage path/key** (e.g., `platform/images/hero-banner.png`). This is the permanent reference — never a URL |
| `original_filename` | CharField | Original upload filename |
| `mime_type` | CharField | MIME type (e.g., `image/png`, `application/pdf`) |
| `file_size` | PositiveIntegerField | Size in bytes |
| `width` | PositiveIntegerField (nullable) | Image/video width in pixels |
| `height` | PositiveIntegerField (nullable) | Image/video height in pixels |
| `alt_text` | CharField (nullable) | Default alt text (see Section 4.5 for precedence) |
| `title` | CharField (nullable) | Display title |
| `metadata` | JSONB (nullable) | EXIF data, custom tags, processing info |
| `is_tombstoned` | BooleanField | Default `false`. Set to `true` when admin deletes the file but it's still referenced by published content |

**URL Generation:** The API generates signed URLs at read time using `storage_key` + storage SDK. URLs are never stored in the database. Tombstoned files remain accessible (their storage key still resolves) until the cleanup job removes them.

**Note on Soft Delete vs Tombstone:** `is_deleted` (from `AuditModel`) is for when the model record is soft-deleted. `is_tombstoned` is a separate concept — the record is still active but the file is marked for eventual removal from storage once no published content references it.

### 6.4 MediaUsage Tracking Model

Tracks where every media file is referenced, enabling safe deletion warnings and cascade cleanup.

| Field | Type | Description |
|---|---|---|
| _From UUIDModel_ | | `id` (UUID v4 primary key) |
| _From TimeStampedModel_ | | `created_at`, `updated_at` |
| `media_file` | ForeignKey -> MediaFile | The referenced file |
| `block_placement` | ForeignKey -> SectionBlockPlacement | The block placement containing the reference |
| `field_key` | CharField | Which field in the block's content references this file |
| `content_layer` | CharField | One of: `draft`, `published` — which content JSONB holds this reference |

**Behavior — Aligned with Draft/Publish Model:**

- **MediaUsage records are created/updated** whenever block placement content is saved (draft) or published. Both `draft_content` and `published_content` references are tracked separately via the `content_layer` field.
- **When a media file is deleted from the library**:
  - `draft_content` references are set to `null` across all block placements. This is safe because draft content is not live.
  - `published_content` references are **NOT immediately nulled**. The media file enters tombstoned state (`is_tombstoned=true`) — it remains in storage and its URL still resolves. On next publish, the SchemaValidator catches the tombstoned reference and forces the admin to replace it.
  - A pre-deletion check warns the admin how many block placements (draft and published) will be affected.
- **When a media reference is removed from a block field**: only the MediaUsage record is deleted. The file remains in the library untouched.
- **Tombstone cleanup job**: A periodic Celery task (using `base=LoggedTask`) checks for tombstoned files that have zero `published` layer MediaUsage records. These files are permanently deleted from storage.
- **Lookup**: given a media file, query MediaUsage to find every block placement, field, and content layer that references it.

---

## 7. Permission Model & RBAC Integration

### 7.1 Integration with Existing RBAC System

The CMS integrates with the existing RBAC system in `apps/rbac/`. Permissions follow the established conventions:

- **Permission codes** use `can_*` prefix (matching `can_invite_member`, `can_create_form`, etc.)
- **Each permission** has a `category` and `applicable_scopes` list
- **Enforcement** uses `MembershipPolicy.authorize_action(actor_context=..., required_permission=...)`
- **Permissions are immutable** — defined in `apps/rbac/permissions/registry.py` and seeded via data migration
- **View layer** uses `PlatformContextMixin` to build `ActorContext` (since CMS is currently platform-only). When business CMS access is added, views will use `BusinessContextMixin` for business-scoped operations

### 7.2 CMS Permission Set

**Structural Permissions (Platform scope — superuser/developer):**

| Code | Name | Description | Category | Applicable Scopes |
|---|---|---|---|---|
| `can_create_cms_site` | Create CMS Site | Create new Sites | `cms_structure` | `["platform_only"]` |
| `can_edit_cms_site` | Edit CMS Site | Edit existing Sites | `cms_structure` | `["platform_only"]` |
| `can_delete_cms_site` | Delete CMS Site | Delete Sites | `cms_structure` | `["platform_only"]` |
| `can_create_cms_page` | Create CMS Page | Create new Pages and attach structural placements | `cms_structure` | `["platform_only"]` |
| `can_edit_cms_page` | Edit CMS Page | Edit page metadata and structural placements | `cms_structure` | `["platform_only"]` |
| `can_delete_cms_page` | Delete CMS Page | Delete Pages | `cms_structure` | `["platform_only"]` |
| `can_create_cms_template` | Create CMS Template | Create new SectionTemplates and BlockTemplates | `cms_structure` | `["platform_only"]` |
| `can_edit_cms_template` | Edit CMS Template | Edit existing templates and block schemas | `cms_structure` | `["platform_only"]` |
| `can_delete_cms_template` | Delete CMS Template | Delete SectionTemplates and BlockTemplates | `cms_structure` | `["platform_only"]` |
| `can_assign_cms_to_business` | Assign CMS to Business | Assign sites/pages to business accounts | `cms_structure` | `["platform_only", "global_only"]` |
| `can_create_cms_api_key` | Create CMS API Key | Create API keys for public CMS access | `cms_structure` | `["platform_only"]` |
| `can_revoke_cms_api_key` | Revoke CMS API Key | Revoke (soft-delete) API keys | `cms_structure` | `["platform_only"]` |

**Content Permissions (Platform scope — currently platform-only, `business` scope included for future expansion):**

| Code | Name | Description | Category | Applicable Scopes |
|---|---|---|---|---|
| `can_view_cms_content` | View CMS Content | View pages, placements, and their content | `cms_content` | `["platform_only", "business", "global_only"]` |
| `can_edit_cms_content` | Edit CMS Content | Edit draft_content values within assigned block placements | `cms_content` | `["platform_only", "business", "global_only"]` |
| `can_publish_cms_content` | Publish CMS Content | Publish pages (copy draft -> published) | `cms_content` | `["platform_only", "business", "global_only"]` |
| `can_toggle_cms_visibility` | Toggle CMS Visibility | Hide/show non-required section and block placements | `cms_content` | `["platform_only", "business"]` |
| `can_view_cms_history` | View CMS History | View content version history | `cms_content` | `["platform_only", "business"]` |
| `can_rollback_cms_content` | Rollback CMS Content | Rollback draft_content to a previous version | `cms_content` | `["platform_only", "business"]` |
| `can_export_cms_content` | Export CMS Content | Export page data as JSON | `cms_content` | `["platform_only", "business"]` |
| `can_import_cms_content` | Import CMS Content | Import page data from JSON (content-only) | `cms_content` | `["platform_only", "business"]` |

**Media Permissions:**

| Code | Name | Description | Category | Applicable Scopes |
|---|---|---|---|---|
| `can_upload_cms_media` | Upload CMS Media | Upload media files to the library | `cms_media` | `["platform_only", "business", "global_only"]` |
| `can_edit_cms_media` | Edit CMS Media | Edit media metadata, move between folders, organize | `cms_media` | `["platform_only", "business", "global_only"]` |
| `can_delete_cms_media` | Delete CMS Media | Delete media files (tombstone if published refs exist) | `cms_media` | `["platform_only", "business", "global_only"]` |

### 7.3 Permission Enforcement Pattern

Every CMS service method follows the standard authorization pattern:

```python
from apps.core.types import ActorContext
from apps.rbac.policies import MembershipPolicy
from apps.core.observability import AuditService, AuditLog, get_logger

logger = get_logger(__name__)

class CMSContentService:
    @staticmethod
    @transaction.atomic
    def update_draft_content(
        *,
        actor_context: ActorContext,
        block_placement_id: UUID,
        content: dict,
        request=None,
    ):
        # 1. Authorize
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=None,
            required_permission="can_edit_cms_content",
        )

        # 2. Business logic
        placement = CMSBlockPlacementSelector.get_by_id(block_placement_id=block_placement_id)
        # ... validate, update draft_content ...

        # 3. Audit
        AuditService.log(
            action=AuditLog.Action.CMS_CONTENT_DRAFT_SAVED,
            actor=_resolve_actor(actor_context),  # Resolves User from ActorContext.user_id for audit logging
            resource=placement,
            request=request,
        )

        return placement
```

**Django Admin panel**: Structural permissions for superusers use Django's built-in `is_superuser` check. The Django Admin ModelAdmin classes restrict access to structural models (templates, placements) to superusers only.

**Public API**: Requires a valid API key and origin validation (see Section 7.5). The `/api/v1/cms/public/` prefix serves `published_content` only.

### 7.4 Interaction Mode Summary

| Action | Superuser (platform) | Platform Member (with permissions) | Unauthenticated (with API key) |
|---|---|---|---|
| Create/edit/delete Sites | via Django Admin | No | No |
| Create/edit/delete Pages | via Django Admin | No | No |
| Create/edit/delete Templates | via Django Admin | No | No |
| Define or modify block schema | via Django Admin | No | No |
| Attach/reorder placements | via Django Admin | No | No |
| Edit field **values** (draft_content) | Yes | `can_edit_cms_content` | No |
| Add/remove repeater items | Yes | `can_edit_cms_content` | No |
| Toggle placement visibility | Yes | `can_toggle_cms_visibility` (only if `is_required=false`) | No |
| Save as draft | Yes | `can_edit_cms_content` | No |
| Publish page | Yes | `can_publish_cms_content` | No |
| Upload media | Yes | `can_upload_cms_media` | No |
| Edit/organize media | Yes | `can_edit_cms_media` | No |
| Delete media | Yes | `can_delete_cms_media` | No |
| Export JSON | Yes | `can_export_cms_content` | No |
| Import JSON (content-only) | Yes | `can_import_cms_content` | No |
| Import JSON (full structural) | Yes (via Django Admin) | No | No |
| View content (admin API) | Yes | `can_view_cms_content` | No |
| Toggle page visibility | Yes | `can_toggle_cms_visibility` (only if page `is_required=false`) | No |
| Delete page | Yes (only if `is_required=false`) | No | No |
| View content (public API) | Yes | Yes | Yes (via API key) |
| View content history | Yes | `can_view_cms_history` | No |
| Rollback draft content | Yes | `can_rollback_cms_content` | No |

### 7.5 Public API Access Control — API Key + Origin Restriction

The public CMS API (`/api/v1/cms/public/`) is consumed by the frontend website to render published CMS content. Unlike the admin API (which uses JWT authentication), the public API uses an **API key + origin restriction** model to prevent unauthorized scraping while keeping the frontend integration simple.

**CMSApiKey Model:**

| Field | Type | Description |
|---|---|---|
| _From UUIDModel_ | | `id` (UUID v4 primary key) |
| _From AuditModel_ | | `created_at`, `updated_at`, `created_by`, `updated_by`, `is_deleted`, `deleted_at`, `deleted_by` |
| `site` | ForeignKey -> Site | The site this key grants access to |
| `name` | CharField | Descriptive label (e.g., "Production Website", "Staging") |
| `key_prefix` | CharField | First 8 chars of the key (for display/identification without exposing the full key) |
| `key_hash` | CharField | Hashed API key (never store plaintext). Use `hashlib.sha256` |
| `allowed_origins` | JSONField (list of strings) | Allowed `Origin` / `Referer` header values. E.g., `["https://arena-z.com", "https://staging.arena-z.com"]`. Empty list = no origin restriction (for server-to-server) |
| `is_active` | BooleanField | Whether the key is currently valid |
| `expires_at` | DateTimeField (nullable) | Optional expiration date. Null = never expires |
| `last_used_at` | DateTimeField (nullable) | Automatically updated on each use |
| `rate_limit` | PositiveIntegerField | Max requests per minute (default: 60) |

**Key Generation:** API keys are generated on creation and returned **once** to the superuser. The plaintext key is never stored — only `key_hash` and `key_prefix` are persisted. Format: `cmsk_{random_32_hex_chars}` (e.g., `cmsk_a1b2c3d4e5f6...`).

**Authentication Flow:**

```
1. Frontend sends request with header: X-CMS-API-Key: cmsk_a1b2c3d4...
2. Middleware hashes the key and looks up CMSApiKey by key_hash
3. Validate: is_active=True, not expired, site matches request
4. Validate: Origin header matches allowed_origins (if list is non-empty)
5. Check rate limit (per-key, using Django cache)
6. If all pass → allow request. Otherwise → 401/403
```

**Origin Validation:**

- If `allowed_origins` is non-empty, the request must include an `Origin` or `Referer` header matching one of the allowed values
- Comparison is case-insensitive and ignores trailing slashes
- For server-to-server usage (e.g., SSR from Next.js), set `allowed_origins` to an empty list and rely on the API key alone
- Origin validation is a defense-in-depth measure (not a security boundary), since `Origin` headers can be spoofed outside browsers

**Permission — API Key Management:**

| Code | Name | Description | Category | Applicable Scopes |
|---|---|---|---|---|
| `can_create_cms_api_key` | Create CMS API Key | Create new API keys for public CMS access | `cms_structure` | `["platform_only"]` |
| `can_revoke_cms_api_key` | Revoke CMS API Key | Revoke (soft-delete) existing API keys | `cms_structure` | `["platform_only"]` |

**Key management endpoints (admin API):**

```
GET    /api/v1/cms/admin/api-keys/                      -> List API keys for a site (key_prefix only, never full key)
POST   /api/v1/cms/admin/api-keys/                      -> Create API key (returns full key ONCE)
PATCH  /api/v1/cms/admin/api-keys/{uuid}/               -> Update name, allowed_origins, is_active, rate_limit
DELETE /api/v1/cms/admin/api-keys/{uuid}/               -> Revoke (soft-delete) API key
```

**Audit Actions:**

```python
CMS_API_KEY_CREATED = "cms.api_key.created", "CMS API Key Created"
CMS_API_KEY_REVOKED = "cms.api_key.revoked", "CMS API Key Revoked"
CMS_API_KEY_UPDATED = "cms.api_key.updated", "CMS API Key Updated"
```

---

## 8. API Design

### 8.1 Design Principles

- **Public/Admin split**: Two endpoint prefixes with different authorization and data exposure rules
- **URL versioning**: All endpoints under `/api/v1/cms/` following the project's existing convention
- **Every entity is independently accessible** via its own endpoint
- **Nested retrieval with depth control** allows fetching a full page tree in one request
- **Templates use slug-based access**, placements use **UUID-based access**
- **Platform-scoped**: admin API queries are scoped to the platform account (via `PlatformContextMixin`). When business CMS access is added in the future, `BusinessContextMixin` will scope queries to the requesting user's business
- **RESTful conventions** with consistent response envelopes
- **OpenAPI documentation**: All view methods decorated with `@extend_schema()` (via `drf-spectacular`)
- **Pagination**: List endpoints use `StandardPagination` (20 items/page) from `apps.core.pagination`

### 8.2 Admin API Endpoints (`/api/v1/cms/admin/`)

All admin endpoints require authentication. Platform scoping is enforced via `PlatformContextMixin`. When business CMS access is added in the future, business-scoped views will use `BusinessContextMixin`.

**Sites:**

```
GET    /api/v1/cms/admin/sites/                              -> List sites (platform-scoped)
POST   /api/v1/cms/admin/sites/                              -> Create site (superuser)
GET    /api/v1/cms/admin/sites/{slug}/                        -> Get site details
PATCH  /api/v1/cms/admin/sites/{slug}/                        -> Update site
DELETE /api/v1/cms/admin/sites/{slug}/                        -> Delete site (superuser)
```

**Pages:**

```
GET    /api/v1/cms/admin/pages/                               -> List pages (filterable by site, status)
POST   /api/v1/cms/admin/pages/                               -> Create page (superuser)
GET    /api/v1/cms/admin/pages/{slug}/                        -> Get page
GET    /api/v1/cms/admin/pages/{slug}/?depth=sections         -> Page + section placements
GET    /api/v1/cms/admin/pages/{slug}/?depth=full             -> Page + sections + blocks + draft_content
PATCH  /api/v1/cms/admin/pages/{slug}/                        -> Update page metadata
DELETE /api/v1/cms/admin/pages/{slug}/                        -> Delete page (superuser)
POST   /api/v1/cms/admin/pages/{slug}/publish/                -> Validate & publish page (transactional)
POST   /api/v1/cms/admin/pages/{slug}/unpublish/              -> Revert to draft status
POST   /api/v1/cms/admin/pages/{slug}/export/                 -> Export page tree as JSON
POST   /api/v1/cms/admin/pages/{slug}/import/                 -> Import page content from JSON
```

**Templates (Superuser-only):**

```
GET    /api/v1/cms/admin/templates/sections/                  -> List section templates
POST   /api/v1/cms/admin/templates/sections/                  -> Create section template
GET    /api/v1/cms/admin/templates/sections/{slug}/            -> Get section template
PATCH  /api/v1/cms/admin/templates/sections/{slug}/            -> Update section template
DELETE /api/v1/cms/admin/templates/sections/{slug}/            -> Delete section template

GET    /api/v1/cms/admin/templates/blocks/                    -> List block templates
POST   /api/v1/cms/admin/templates/blocks/                    -> Create block template
GET    /api/v1/cms/admin/templates/blocks/{slug}/              -> Get block template (with schema)
PATCH  /api/v1/cms/admin/templates/blocks/{slug}/              -> Update block template/schema
DELETE /api/v1/cms/admin/templates/blocks/{slug}/              -> Delete block template
```

**Section Placements:**

```
GET    /api/v1/cms/admin/section-placements/{uuid}/           -> Get section placement details
PATCH  /api/v1/cms/admin/section-placements/{uuid}/           -> Update visibility/overrides (admin)
```

**Block Placements (content interaction):**

```
GET    /api/v1/cms/admin/block-placements/{uuid}/             -> Get block placement (draft_content + template schema)
PATCH  /api/v1/cms/admin/block-placements/{uuid}/             -> Update draft_content (admin)
GET    /api/v1/cms/admin/block-placements/{uuid}/history/     -> List content versions
POST   /api/v1/cms/admin/block-placements/{uuid}/rollback/{version}/ -> Rollback draft_content to version
```

**Media:**

```
GET    /api/v1/cms/admin/media/folders/                       -> List folders (nested tree)
POST   /api/v1/cms/admin/media/folders/                       -> Create folder
PATCH  /api/v1/cms/admin/media/folders/{slug}/                -> Rename/move folder
DELETE /api/v1/cms/admin/media/folders/{slug}/                 -> Delete folder (must be empty)
GET    /api/v1/cms/admin/media/files/                         -> List files (filterable by folder, type)
POST   /api/v1/cms/admin/media/files/                         -> Upload file
GET    /api/v1/cms/admin/media/files/{uuid}/                  -> Get file details + usage info + signed URL
PATCH  /api/v1/cms/admin/media/files/{uuid}/                  -> Update metadata
DELETE /api/v1/cms/admin/media/files/{uuid}/                  -> Delete file (tombstone if published refs exist)
GET    /api/v1/cms/admin/media/files/{uuid}/usage/            -> List all block placements referencing this file
```

### 8.3 Public API Endpoints (`/api/v1/cms/public/`)

Public endpoints are read-only and require a valid **API key** (see Section 7.5). They return `published_content` only. No `draft_content`, no template schemas (unless `?include_schema=true` for frontend rendering needs), no structural editing capabilities.

**Authentication:** All requests must include the `X-CMS-API-Key` header with a valid, active API key for the target site. Origin validation is enforced per the key's `allowed_origins` configuration.

```
GET    /api/v1/cms/public/sites/{slug}/                       -> Get published site info
GET    /api/v1/cms/public/pages/{slug}/                       -> Get published page
GET    /api/v1/cms/public/pages/{slug}/?depth=full            -> Full published page tree
GET    /api/v1/cms/public/media/files/{uuid}/url/             -> Get signed URL for a media file
```

### 8.4 Depth Control Parameter

The `depth` query parameter controls how much related data is included in responses:

| Value | Behavior |
|---|---|
| _omitted_ | Returns only the requested model's fields |
| `sections` | (Pages only) Includes section placements with ordering |
| `blocks` | (Section placements only) Includes block placements with ordering |
| `full` | (Pages only) Includes sections -> blocks -> content, fully resolved |

**Admin API** returns `draft_content` by default. Add `?layer=published` to see published content for comparison.

**Public API** always returns `published_content`. The `layer` parameter is not available.

### 8.5 Filtering & Querying

All list endpoints support:

- `?status=draft|published|archived` — filter by status
- `?site={slug}` — filter by site
- `?template={slug}` — filter placements by their template
- `?section_type={type}` — filter by section template type
- `?block_type={type}` — filter by block template type
- `?search={query}` — full-text search across names, display names, descriptions
- `?ordering=order|-created_at|name` — sorting control
- Standard pagination via `?page=1&page_size=20` (using `StandardPagination`)

---

## 9. Draft & Publish Workflow

### 9.1 States

Every Page has a `status` field with these states:

```
draft ---- publish ----> published
  ^                          |
  +---- unpublish -----------+

published -- archive --> archived
                            |
  draft <-- unarchive ------+
```

### 9.2 The Dual-Content Model

Content exists in two parallel realities on every `SectionBlockPlacement`:

| Field | Who Writes | Who Reads | When Updated |
|---|---|---|---|
| `draft_content` | Admin (via edit) | Admin API | On every save |
| `published_content` | System (via publish action) | Public API, frontend | Only on page publish |

This means:

- Admins can save freely without affecting the live site
- The live site shows `published_content` until the page is re-published
- After publish, `draft_content` and `published_content` are identical — until the admin makes the next edit
- "What's live?" is always unambiguous: it's whatever is in `published_content`

### 9.3 Publish Operation — Transactional & Concurrency-Safe

The publish operation is the most critical write path in the CMS. It must be **atomic, validated, and concurrency-safe**.

**Publish Flow (single database transaction via `@transaction.atomic`):**

```
1. ACQUIRE LOCK
   - select_for_update() on the Page row
   - select_for_update() on all PageSectionPlacement rows for this page
   - select_for_update() on all SectionBlockPlacement rows for this page
   (This prevents two admins from publishing the same page simultaneously)

2. VALIDATE ALL (before any writes)
   - For each block placement in required, visible sections:
     a. Load the BlockTemplate.schema
     b. Run SchemaValidator against draft_content (strict mode)
     c. Collect all errors
   - If ANY errors exist -> ABORT transaction, return structured error response

3. WRITE ALL (only if validation passed)
   - For each block placement:
     a. Copy draft_content -> published_content
     b. Set status = 'published'
     c. Create ContentVersion (action=publish)
     d. Update MediaUsage records for published layer
   - Set Page.status = 'published'
   - Set Page.published_at = now()

4. COMMIT TRANSACTION
   - All changes are committed atomically
   - If any step fails, entire transaction rolls back -- nothing changes

5. POST-COMMIT (outside transaction, via transaction.on_commit())
   - Invalidate cached published page tree (if caching is enabled)
   - AuditService.log(action=AuditLog.Action.CMS_PAGE_PUBLISHED, ...)
   - Trigger webhooks (future)
```

**Unpublish behavior:** When a page is unpublished, `Page.status` reverts to `draft`. `SectionBlockPlacement.status` fields also revert to `draft`. `published_content` is NOT cleared — it remains as a snapshot of the last published state, but the public API no longer serves it (because the page status check filters it out).

**Concurrency Guarantee:** If Admin A and Admin B both click "Publish" on the same page simultaneously, one will acquire the lock first and complete. The other will wait for the lock and then either succeed (if validation still passes) or fail.

**Scope:** Publish always copies ALL block placements on the page, not just changed ones. This keeps the published state consistent and the mental model simple.

### 9.4 Publish Validation Error Response

If validation fails, the publish action returns a **structured, machine-readable error response**:

```json
{
  "publish_errors": [
    {
      "section_placement_id": "uuid-of-section-placement",
      "section_template": "hero_banner",
      "block_placement_id": "uuid-of-block-placement",
      "block_template": "hero_text",
      "field_key": "title",
      "error_type": "required_field_empty",
      "message": "Title is required but has no value"
    },
    {
      "section_placement_id": "uuid-of-section-placement",
      "section_template": "team_section",
      "block_placement_id": "uuid-of-block-placement",
      "block_template": "team_grid",
      "field_key": "team_members[2].photo",
      "error_type": "media_reference_tombstoned",
      "message": "Referenced media file has been deleted"
    }
  ]
}
```

---

## 10. Export & Import System

### 10.1 Export Format

Exporting a page produces a self-contained JSON file representing the full page tree with template references and placement content:

```json
{
  "export_version": "3.1",
  "exported_at": "2026-02-25T14:30:00Z",
  "exported_by": "user-uuid",
  "source_site": "main-website",
  "source_owner_type": "platform",
  "source_owner_id": "platform-uuid",
  "page": {
    "slug": "about-us",
    "title": "About Us",
    "path": "/about",
    "page_type": "content",
    "status": "published",
    "metadata": { "...": "..." },
    "section_placements": [
      {
        "id": "uuid-of-section-placement",
        "template_slug": "hero_banner",
        "order": 1,
        "is_required": true,
        "is_visible": true,
        "block_placements": [
          {
            "id": "uuid-of-block-placement",
            "template_slug": "hero_text",
            "order": 1,
            "is_required": true,
            "is_visible": true,
            "schema": { "...": "..." },
            "draft_content": { "...": "..." },
            "published_content": { "...": "..." },
            "default_content": { "...": "..." }
          }
        ]
      }
    ]
  }
}
```

**Note:** `schema` is included in exports for diff detection and full-import mode. Content-only imports ignore it.

### 10.2 Import Behavior

- **Content-only import** (admin with `can_import_cms_content`): Matches block placements by UUID and updates `draft_content` values only. Ignores structural differences. Validates against existing template schemas.
- **Full import** (superuser via Django Admin): Can create or update structural elements. Used for migrating page structures between environments.
- **Conflict resolution**: UUID matches update existing entities. New UUIDs in full-import mode create new placements (superuser only).
- **Validation**: Import always validates content against template schema before applying.

---

## 11. Django Admin Panel Configuration

### 11.1 Design Principles

The Django Admin panel is the **primary interface for superusers** to manage the CMS structure. Access is restricted to users with `is_superuser=True`. It must be well-organized, intuitive, and prevent accidental destructive operations.

### 11.2 Admin Structure

**SiteAdmin:**
- Fieldsets: Basic Info (name, slug, domain), Ownership (owner_type, owner_id), Settings (locale, metadata), Status
- Inlines: Pages list (read-only summary with links)
- List display: name, owner_type, domain, is_active, page count
- List filters: owner_type, is_active
- Search: name, domain

**PageAdmin:**
- Fieldsets: Basic Info (title, slug, path), Site Assignment, Page Type, SEO (metadata), Status & Publishing
- Inlines: `PageSectionPlacementInline` — tabular inline showing section placements with order, template name, is_required, is_visible
- List display: title, site, path, status, published_at, section count
- List filters: site, status, page_type
- Search: title, slug, path
- Custom actions: "Publish selected pages", "Archive selected pages"

**SectionTemplateAdmin:**
- Fieldsets: Basic Info (name, display_name, slug), Type, Description, Metadata, UI Config
- List display: display_name, section_type, placement count
- Search: name, display_name

**BlockTemplateAdmin:**
- Fieldsets: Basic Info (name, display_name, slug), Type, Schema (JSONB with pretty-print widget), Schema Version, Default Content, Metadata, UI Config
- List display: display_name, block_type, schema_version, placement count
- Custom actions: "Export block schema", "Duplicate template"
- Search: name, display_name

**PageSectionPlacementAdmin:**
- Fieldsets: Page (read-only link), Template (read-only link), Order, Required, Visible, Config Overrides
- Inlines: `SectionBlockPlacementInline`
- List display: page title, template display_name, order, is_visible
- List filters: page__site, template
- Search: page__title, label

**SectionBlockPlacementAdmin:**
- Fieldsets: Section Placement (read-only), Template Info (read-only), Draft Content (editable JSONB), Published Content (read-only JSONB), Status, Order, Required, Visible
- Read-only fields: template, published_content, section_placement, order
- List display: label, template display_name, page (via section_placement), status
- List filters: template, status, section_placement__page__site
- Search: label

**MediaFileAdmin:**
- List display: thumbnail preview, original_filename, mime_type, file_size, folder, usage count, is_tombstoned
- List filters: mime_type, folder, is_tombstoned
- Search: original_filename, title, alt_text
- Read-only: usage count with link to MediaUsage list

**ContentVersionAdmin:**
- Read-only admin — versions should never be manually edited
- List display: block_placement, version_number, action, created_by, created_at
- List filters: action, block_placement__template
- Custom action: "Rollback to this version"

---

## 12. Audit & Observability Integration

### 12.1 Observability Stack

The CMS uses the existing observability system in `apps/core/observability/`:

**Structured Logging** (required in all services):
```python
from apps.core.observability import get_logger
logger = get_logger(__name__)

# Event naming: cms.{resource}.{action}.{outcome}
logger.info("cms.page.publish.start", page_id=str(page.id), block_count=count)
logger.info("cms.page.publish.success", page_id=str(page.id))
logger.error("cms.page.publish.failed", page_id=str(page.id), error=str(e))
```

**Audit Logging** (required for all mutations):
```python
from apps.core.observability import AuditService, AuditLog

AuditService.log(
    action=AuditLog.Action.CMS_PAGE_PUBLISHED,
    actor=user,
    resource=page,
    request=request,
    details={"block_count": 5, "site_slug": "main"},
)
```

**Metrics** (optional, NoOp by default):
```python
from apps.core.observability import metrics
metrics.increment("cms.publish.total", tags={"site": site.slug})
metrics.histogram("cms.publish.duration_ms", duration_ms)
```

### 12.2 CMS Audit Actions

The following `AuditLog.Action` entries must be added to `apps/core/observability/audit/models.py` (requires migration):

```python
# CMS - Sites
CMS_SITE_CREATED = "cms.site.created", "CMS Site Created"
CMS_SITE_UPDATED = "cms.site.updated", "CMS Site Updated"
CMS_SITE_DELETED = "cms.site.deleted", "CMS Site Deleted"

# CMS - Pages
CMS_PAGE_CREATED = "cms.page.created", "CMS Page Created"
CMS_PAGE_UPDATED = "cms.page.updated", "CMS Page Updated"
CMS_PAGE_DELETED = "cms.page.deleted", "CMS Page Deleted"
CMS_PAGE_PUBLISHED = "cms.page.published", "CMS Page Published"
CMS_PAGE_UNPUBLISHED = "cms.page.unpublished", "CMS Page Unpublished"
CMS_PAGE_ARCHIVED = "cms.page.archived", "CMS Page Archived"

# CMS - Templates
CMS_SECTION_TEMPLATE_CREATED = "cms.section_template.created", "Section Template Created"
CMS_SECTION_TEMPLATE_UPDATED = "cms.section_template.updated", "Section Template Updated"
CMS_SECTION_TEMPLATE_DELETED = "cms.section_template.deleted", "Section Template Deleted"
CMS_BLOCK_TEMPLATE_CREATED = "cms.block_template.created", "Block Template Created"
CMS_BLOCK_TEMPLATE_UPDATED = "cms.block_template.updated", "Block Template Updated"
CMS_BLOCK_TEMPLATE_DELETED = "cms.block_template.deleted", "Block Template Deleted"
CMS_BLOCK_SCHEMA_CHANGED = "cms.block_template.schema_changed", "Block Schema Changed"

# CMS - Content
CMS_CONTENT_DRAFT_SAVED = "cms.content.draft_saved", "CMS Content Draft Saved"
CMS_CONTENT_ROLLBACK = "cms.content.rollback", "CMS Content Rolled Back"
CMS_VISIBILITY_TOGGLED = "cms.placement.visibility_toggled", "CMS Visibility Toggled"

# CMS - Media
CMS_MEDIA_UPLOADED = "cms.media.uploaded", "CMS Media Uploaded"
CMS_MEDIA_DELETED = "cms.media.deleted", "CMS Media Deleted"
CMS_MEDIA_TOMBSTONED = "cms.media.tombstoned", "CMS Media Tombstoned"

# CMS - Import/Export
CMS_PAGE_EXPORTED = "cms.page.exported", "CMS Page Exported"
CMS_PAGE_IMPORTED = "cms.page.imported", "CMS Page Imported"

# CMS - API Keys
CMS_API_KEY_CREATED = "cms.api_key.created", "CMS API Key Created"
CMS_API_KEY_REVOKED = "cms.api_key.revoked", "CMS API Key Revoked"
CMS_API_KEY_UPDATED = "cms.api_key.updated", "CMS API Key Updated"
```

### 12.3 Audited Operations

| Category | Operations | Audit Action |
|---|---|---|
| **Structural** | Create/update/delete site | `CMS_SITE_CREATED/UPDATED/DELETED` |
| **Structural** | Create/update/delete page | `CMS_PAGE_CREATED/UPDATED/DELETED` |
| **Structural** | Create/update/delete templates | `CMS_*_TEMPLATE_CREATED/UPDATED/DELETED` |
| **Structural** | Block schema change | `CMS_BLOCK_SCHEMA_CHANGED` (use `AuditService.log_change()` with before/after) |
| **Content** | Draft save | `CMS_CONTENT_DRAFT_SAVED` |
| **Content** | Publish | `CMS_PAGE_PUBLISHED` (one entry per page, details lists all block placement IDs) |
| **Content** | Unpublish | `CMS_PAGE_UNPUBLISHED` |
| **Content** | Rollback | `CMS_CONTENT_ROLLBACK` |
| **Content** | Visibility toggle | `CMS_VISIBILITY_TOGGLED` |
| **Media** | File upload | `CMS_MEDIA_UPLOADED` |
| **Media** | File delete/tombstone | `CMS_MEDIA_DELETED` or `CMS_MEDIA_TOMBSTONED` |
| **Access** | Export triggered | `CMS_PAGE_EXPORTED` |
| **Access** | Import triggered | `CMS_PAGE_IMPORTED` |
| **API Keys** | Create/update/revoke API key | `CMS_API_KEY_CREATED/UPDATED/REVOKED` |

### 12.4 Content Change Tracking

For content updates, use `AuditService.log_change()` to capture before/after diffs:

```python
AuditService.log_change(
    action=AuditLog.Action.CMS_CONTENT_DRAFT_SAVED,
    actor=user,
    resource=block_placement,
    before={"title": "Welcome"},
    after={"title": "Welcome to Arena-Z"},
    request=request,
)
```

Full content snapshots live in `ContentVersion` — the audit system only stores diffs.

---

## 13. Service Layer Architecture

### 13.1 Service Classes

Following the project's layered architecture, the CMS app defines these service classes:

| Service | Responsibility | Key Methods |
|---|---|---|
| `CMSTemplateService` | Create/update/delete templates, placement ordering (superuser) | `create_section_template()`, `create_block_template()`, `update_block_schema()`, `reorder_section_placements()`, `reorder_block_placements()` |
| `CMSPageService` | Page lifecycle, ordering, publish/unpublish, export/import | `create_page()`, `reorder_pages()`, `publish_page()`, `unpublish_page()`, `export_page()`, `import_page()` |
| `CMSContentService` | Draft content editing, rollback, visibility | `update_draft_content()`, `rollback_content()`, `toggle_visibility()` |
| `CMSMediaService` | File upload, delete, tombstone cleanup | `upload_file()`, `delete_file()`, `cleanup_tombstoned()` |
| `CMSApiKeyService` | API key lifecycle for public API access | `create_api_key()`, `revoke_api_key()`, `validate_api_key()` |

**Reorder Pattern — Atomic Bulk Reassignment:**

All three ordering levels use the same atomic reorder pattern. The caller provides the complete ordered list of IDs, and the service atomically reassigns `order` values in a single transaction:

```python
# Example: CMSPageService.reorder_pages
@staticmethod
@transaction.atomic
def reorder_pages(
    *,
    actor_context: ActorContext,
    site_id: UUID,
    ordered_page_ids: list[UUID],
) -> None:
    # 1. Authorize (superuser only — structural operation)
    # 2. Validate all IDs belong to the site and list is complete
    # 3. Bulk update order values
    for index, page_id in enumerate(ordered_page_ids):
        Page.objects.filter(id=page_id).update(order=index)
    # 4. Audit
```

The same pattern applies to:
- `CMSTemplateService.reorder_section_placements(*, actor_context, page_id, ordered_placement_ids)` — reorders `PageSectionPlacement` within a page
- `CMSTemplateService.reorder_block_placements(*, actor_context, section_placement_id, ordered_placement_ids)` — reorders `SectionBlockPlacement` within a section

**Implementation note:** Since PostgreSQL defers unique constraint checks to the end of the transaction (when using `DEFERRABLE INITIALLY DEFERRED`), the bulk sequential update works atomically. For SQLite (tests), the same pattern works because the entire operation is within `@transaction.atomic`.

### 13.2 Selector Classes

| Selector | Responsibility | Key Methods |
|---|---|---|
| `CMSSiteSelector` | Site queries | `get_by_slug()`, `list_for_owner()` |
| `CMSPageSelector` | Page queries with depth control | `get_by_slug()`, `get_with_full_tree()`, `list_by_site()` |
| `CMSTemplateSelector` | Template queries | `get_section_template_by_slug()`, `get_block_template_by_slug()` |
| `CMSBlockPlacementSelector` | Block placement queries | `get_by_id()`, `list_for_section()` |
| `CMSMediaSelector` | Media queries | `get_file_by_id()`, `list_files()`, `get_usage()` |
| `CMSContentVersionSelector` | Version history queries | `list_for_placement()`, `get_version()` |
| `CMSApiKeySelector` | API key queries | `get_by_hash()`, `list_for_site()` |

### 13.3 Exception Handling

All exceptions use `apps.core.exceptions` — never Django/DRF exceptions:

| Situation | Exception | Example |
|---|---|---|
| Page/template/placement not found | `NotFound` | `NotFound(resource="Page", resource_id=slug)` |
| Schema validation failure | `ValidationError` | `ValidationError(message="...", field="title")` |
| Publish with validation errors | `ValidationError` | Custom structured response (see Section 9.4) |
| Permission denied | `PermissionDenied` | Raised by `MembershipPolicy.authorize_action()` |
| Duplicate slug | `ConflictError` | `ConflictError(resource="BlockTemplate", conflict_type="duplicate")` |
| Concurrent publish conflict | `ConflictError` | `ConflictError(resource="Page", conflict_type="state_conflict")` |

---

## 14. Indexing & Performance Considerations

### 14.1 Database Indexes

| Table | Index | Type | Purpose |
|---|---|---|---|
| Site | `(owner_type, owner_id, slug)` | Unique composite | Slug unique per owner |
| Page | `(site_id, slug)` | Unique composite | Slug unique per site |
| Page | `(site_id, path)` | Unique composite | Ensure unique paths within a site |
| Page | `(site_id, status)` | Composite | Filter published pages per site |
| Page | `(site_id, order)` | Unique composite | Ordering within site |
| SectionTemplate | `slug` | Unique | Globally unique template slug |
| BlockTemplate | `slug` | Unique | Globally unique template slug |
| PageSectionPlacement | `(page_id, order)` | Unique composite | One section per position |
| SectionBlockPlacement | `(section_placement_id, order)` | Unique composite | One block per position |
| SectionBlockPlacement | `template_id` | B-tree | Find all placements of a template |
| SectionBlockPlacement | `draft_content` | GIN | JSONB content search |
| SectionBlockPlacement | `published_content` | GIN | JSONB published content search |
| SectionBlockPlacement | `status` | B-tree | Filter by publish status |
| MediaFile | `(owner_type, owner_id, folder_id)` | Composite | Folder browsing |
| MediaFile | `mime_type` | B-tree | Type filtering |
| MediaFile | `is_tombstoned` | B-tree | Filter tombstoned files |
| MediaUsage | `(media_file_id)` | B-tree | Reverse lookup |
| MediaUsage | `(block_placement_id)` | B-tree | Forward lookup |
| ContentVersion | `(block_placement_id, version_number)` | Composite, descending | Latest version retrieval |
| CMSApiKey | `key_hash` | Unique | API key lookup |
| CMSApiKey | `site_id` | B-tree | Keys per site |

### 14.2 Query Optimization Notes

- The `?depth=full` endpoint on pages involves joins across Page -> PageSectionPlacement -> SectionBlockPlacement -> BlockTemplate. Use `select_related` and `prefetch_related` aggressively. Only 3 joins deep.
- JSONB GIN indexes on both content fields enable efficient searching but avoid unbounded JSONB queries in list endpoints.
- Media usage tracking via `MediaUsage` avoids expensive JSONB scans.
- **Published page cache**: Cache the full `depth=full` public API response per page. Invalidate only on publish/unpublish.
- Template queries are infrequent and small — no special optimization needed.

---

## 15. Test Structure

### 15.1 Directory Layout

Following the project's established test patterns:

```
backend/apps/cms/
    tests/
        __init__.py
        conftest.py              # Fixtures: site, page, templates, placements, RBAC setup
        factories.py             # SiteFactory, PageFactory, SectionTemplateFactory, etc.
        test_models.py           # Model constraints, __str__, properties
        test_selectors.py        # Selector queries, depth control, filtering
        test_services.py         # Service methods, publish flow, rollback, media
        test_policies.py         # Permission checks per action
        test_validators.py       # SchemaValidator (draft permissive, publish strict)
        test_views.py            # API endpoints, request/response contracts
        test_admin.py            # Django Admin configuration (optional)
```

### 15.2 Factory Examples

```python
# apps/cms/tests/factories.py
from apps.users.tests.factories import UserFactory  # Canonical source
from apps.organization.tests.factories import PlatformAccountFactory
from apps.core.constants import OwnerType

class SiteFactory(DjangoModelFactory):
    class Meta:
        model = Site
    owner_type = OwnerType.PLATFORM
    owner_id = factory.LazyFunction(lambda: PlatformAccountFactory().id)
    name = factory.Sequence(lambda n: f"Test Site {n}")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)

class BlockTemplateFactory(DjangoModelFactory):
    class Meta:
        model = BlockTemplate
    name = factory.Sequence(lambda n: f"block_template_{n}")
    slug = factory.LazyAttribute(lambda obj: obj.name)
    display_name = factory.LazyAttribute(lambda obj: obj.name.replace("_", " ").title())
    block_type = "text"
    schema = {"fields": [{"key": "title", "type": "text", "label": "Title", "required": True}]}
    schema_version = 1
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)
```

### 15.3 Conftest Pattern

```python
# apps/cms/tests/conftest.py
@pytest.fixture
def platform_account(db):
    """Get or create the singleton PlatformAccount."""
    return PlatformAccountFactory()

@pytest.fixture
def platform_with_rbac(db, user, platform_account):
    """Platform account with RBAC initialized (roles + owner membership)."""
    RBACService.initialize_platform_account(platform_id=platform_account.id)
    # Create owner membership separately (initialize_platform_account only creates roles)
    RBACService.create_membership(
        account_type=AccountType.PLATFORM,
        account_id=platform_account.id,
        user=user,
        role=RoleSelector.get_owner_role(
            account_type=AccountType.PLATFORM,
            account_id=platform_account.id,
        ),
        is_owner=True,
    )
    return platform_account

@pytest.fixture
def site(db, platform_with_rbac):
    """Create a CMS site owned by the platform."""
    return SiteFactory(
        owner_type=OwnerType.PLATFORM,
        owner_id=platform_with_rbac.id,
    )
```

### 15.4 Test Coverage Expectations

Following the project's 80% coverage threshold:
- Models: constraint validation, properties, manager filtering
- Selectors: get_by_slug/id, list queries, depth control, not-found cases
- Services: authorization (denied + granted), business logic, audit trail verification
- Policies: permission boundary tests per the `rbac-integration` skill
- Validators: each field type, permissive vs strict mode, repeater validation
- Views: request/response contracts, status codes, serializer output

---

## 16. Risks & Edge Cases

### 16.1 Schema Change Breaking Existing Content

**Risk:** When a superuser modifies a BlockTemplate's schema, existing content may become invalid.

**Mitigations:**

- **Schema versioning:** `schema_version` on BlockTemplate increments on every schema change. `schema_version_validated` on SectionBlockPlacement tracks the last validated version. The system can identify all affected placements.
- **Compatibility rules:** Backward-compatible changes (adding optional fields, relaxing validation) apply silently. Breaking changes (adding required fields, changing types, removing fields) trigger a warning in Django Admin.
- **Migration scripts:** Management command to batch-update affected `draft_content`.
- **Publish-time fallback:** SchemaValidator ignores unknown fields (permissive) to prevent stale fields from blocking publish.

### 16.2 Large Repeater Payloads

**Risk:** Large JSONB payloads from repeater fields.

**Mitigations:**
- Enforce `max_items` limits (superuser-configured, default ceilings like 50)
- Log response sizes for `depth=full` requests
- Future: repeater pagination for large collections

### 16.3 Concurrent Editing Conflict

**Current behavior (v1):** Last write wins. Acceptable for initial launch.

**Future mitigations:**
- Optimistic locking via `updated_at`
- Edit presence indicators (WebSocket/polling)
- Field-level merging

### 16.4 Tombstoned Media Accumulation

**Mitigations:**
- Celery cleanup job (using `base=LoggedTask`) with monitoring
- Tombstone age limit (90 days safety net)
- Admin visibility in Django Admin

### 16.5 ContentVersion Storage Growth

**Mitigations:**
- Retention policy (default: 50 versions per block placement)
- Throttling (max 1 version per 30 seconds, update-in-place within window for same user + draft_save)
- Future: diff-based storage

---

## 17. Future Considerations

Not in scope for initial build, but the architecture should not prevent them:

- **Multi-language / Localization**: Content JSONB keyed by locale
- **Visual Page Builder**: Frontend drag-and-drop for superusers
- **Workflow Approvals**: Multi-step publish flow
- **Component Marketplace**: Pre-built block templates
- **A/B Testing**: Multiple content variants
- **Webhooks**: External notifications on publish/unpublish
- **Business Account CMS Access**: Multi-tenant via `owner_type=BUSINESS` (architecture already supports it via `owner_type`/`owner_id` pattern)
- **Full Page Snapshots**: Point-in-time reconstruction
- **Diff-based ContentVersions**: Field-level diffs to reduce storage

---

## 18. Glossary

| Term | Definition |
|---|---|
| **Site** | A website container grouping pages under one owner account (currently platform-only, future: business). Uses `owner_type`/`owner_id` polymorphic pattern. |
| **Page** | A routable page with a fixed structure of section and block placements. |
| **SectionTemplate** | A reusable, platform-wide layout definition. Holds no content. |
| **BlockTemplate** | A reusable, platform-wide schema definition for a content block. Holds field definitions and default content, but no live content. |
| **PageSectionPlacement** | A record attaching a SectionTemplate to a specific Page. Carries order, visibility, and config overrides. Belongs to exactly one page. |
| **SectionBlockPlacement** | The core content container. Attaches a BlockTemplate to a PageSectionPlacement and carries draft_content, published_content, and status. Belongs to exactly one section placement. |
| **Schema** | The JSONB definition on a BlockTemplate specifying what fields exist — types, constraints, flags. Immutable by admins. |
| **draft_content** | The working JSONB on a SectionBlockPlacement. Editable by admins. Served by the admin API. |
| **published_content** | The frozen JSONB on a SectionBlockPlacement. Set only during the publish transaction. Served by the public API. |
| **SchemaValidator** | The server-side validation engine that checks content JSONB against a BlockTemplate's schema. Runs permissively on draft save, strictly on publish. |
| **ActorContext** | Dataclass (`apps.core.types.ActorContext`) capturing the complete context of an actor — user, account, role, permissions snapshot. Passed to all service methods. |
| **MembershipPolicy** | Authorization engine (`apps.rbac.policies.MembershipPolicy`) that checks ActorContext permissions. Used in all CMS service methods. |
| **Repeater** | A field type that holds an ordered list of structured objects, each conforming to a sub-schema. |
| **Superuser** | A platform administrator with `is_superuser=True` who defines CMS structure via Django Admin. |
| **Admin** | A platform account member with CMS content permissions who populates draft_content. Cannot modify templates, schemas, or structural placements. In the future, business account members may also serve this role. |
| **ContentVersion** | A historical snapshot of block placement draft_content, enabling rollback. Subject to retention limits and save throttling. |
| **MediaUsage** | A tracking record linking a media file to the block placement, field, and content layer that references it. |
| **CMSApiKey** | An API key record authorizing public API access to a specific site. Includes origin restrictions and rate limits. Key is hashed at rest. |
| **Tombstoned** | A media file state indicating it has been deleted from the library but remains in storage because published content still references it. |
| **Publish Transaction** | The atomic database operation that validates all draft_content on a page and copies it to published_content. Uses row-level locking for concurrency safety. |
| **Schema Version** | An integer on BlockTemplate that increments on every schema change. Used to identify affected placements. |

---

*This document serves as the authoritative specification for the ARENA-Z CMS system (v3.1). All implementation — models, serializers, views, admin configuration, and API endpoints — must conform to the architecture described here and follow the project's established patterns: `apps.core` base models, `apps.core.exceptions`, `apps.core.observability` (AuditService + get_logger + metrics), `apps.rbac` (ActorContext + MembershipPolicy), `apps.core.permissions`, `apps.core.pagination`, and the layered service/selector/policy architecture enforced by the `django-app-creator` skill.*
