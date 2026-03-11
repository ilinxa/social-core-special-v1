ok # ARENA-Z Content Management System (CMS)

## Comprehensive Project Description & Architecture Specification

**Version:** 3.0
**Status:** Planning & Requirements
**Platform:** Django REST Framework + Next.js 16 + Supabase
**Last Updated:** February 2026

---

## 1. Executive Summary

The ARENA-Z CMS is a **template-based, headless content management system** designed around a strict separation between **structural definition** (developer/superuser domain) and **content population** (organization admin domain).

The core philosophy is: **do the hard things once, reuse everywhere.** A developer defines page structures, section layouts, block schemas, and field definitions as **templates** — reusable, platform-wide structural blueprints. These templates are then **placed** onto pages, and each placement is a unique, isolated content container that organization admins can fill. The admin receives a fixed structure — essentially a form — and can only fill in, update, or clear field values. They cannot create pages, add sections, remove blocks, or modify field definitions.

The system uses a **placement-as-instance** architecture: the join tables that connect templates to pages are themselves the content-bearing entities. This guarantees content isolation by construction — there is no way for content to leak across pages because each placement row is structurally unique to its parent context.

This CMS integrates with the existing ARENA-Z ecosystem: the **RBAC permission system** governs access, the **audit/observability system** tracks every mutation, and the **media library** provides centralized asset management with full reference tracking.

---

## 2. Core Architecture Philosophy

### 2.1 Template + Placement Architecture

This is the most critical architectural decision in the system. It solves the **reusable structure with isolated content** problem through a two-entity model.

**The Problem:** If content lives on a shared block or a shared instance that can be placed on multiple pages, editing one page's content can unintentionally affect another. Content must be isolated per-placement while the structural definition (schema) remains shared.

**The Solution — Placements ARE Instances:**

| Entity | Who Creates | What It Holds | Reusable? |
|---|---|---|---|
| **Template** (e.g., `BlockTemplate`) | Superuser | Schema, field definitions, validation rules, default content, metadata | ✅ Yes — referenced across pages, sections, organizations |
| **Placement** (e.g., `SectionBlockPlacement`) | Superuser (structure) / System (auto-creates on attach) | Order, visibility, config overrides, **draft_content**, **published_content**, status | ❌ No — structurally unique to its parent context |

There are no separate "Instance" models. The placement join tables themselves carry the content. This makes content isolation a **structural guarantee** rather than a convention that must be enforced with business logic.

**How It Works:**

1. Superuser creates a `BlockTemplate` with a schema defining fields like "title (text, required)", "image (media, optional)", etc.
2. Superuser attaches that template to a section on a page → the system creates a `SectionBlockPlacement` row. This row IS the content container.
3. The admin fills in `SectionBlockPlacement.draft_content`. On publish, `draft_content` is copied to `published_content`.
4. If the same `BlockTemplate` is attached to another section or page, a completely separate `SectionBlockPlacement` row is created. Content is isolated by construction.

**The Hierarchy:**

```
Page
  └─ PageSectionPlacement (order, visibility, overrides → SectionTemplate)
       └─ SectionBlockPlacement (order, visibility, overrides → BlockTemplate,
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

- **`/api/cms/admin/`** — for authenticated admin/superuser access. Returns `draft_content` by default, includes template schemas for form rendering, supports all mutation operations.
- **`/api/cms/public/`** — for public/frontend consumption. Returns `published_content` only, never exposes `draft_content` or template schemas (unless explicitly needed for frontend rendering), read-only.

This separation is enforced at the endpoint level, not just via query parameters, making it impossible for public consumers to accidentally access draft content.

---

## 3. Data Model Architecture

### 3.1 Model Hierarchy Overview

```
Organization
  └── Site (website container / grouping)
        └── Page
              └── PageSectionPlacement (join + section-level config)
                    │   ├── order, is_required, is_visible, config_overrides
                    │   └── template → SectionTemplate
                    │
                    └── SectionBlockPlacement (join + content container)
                          ├── order, is_required, is_visible, config_overrides
                          ├── template → BlockTemplate
                          ├── draft_content (JSONB) — working copy [EDITABLE BY ADMIN]
                          ├── published_content (JSONB) — frozen live copy [SET ON PUBLISH]
                          └── status
```

### 3.2 Base Model (Abstract)

Every model in the CMS inherits from a shared abstract base providing:

| Field | Type | Description |
|---|---|---|
| `id` | UUID (v4) | Primary key, auto-generated |
| `slug` | SlugField | URL-safe identifier, indexed. **Only on template models and Page/Site.** Placement models use UUID for identification. |
| `created_at` | DateTimeField | Auto-set on creation |
| `updated_at` | DateTimeField | Auto-set on every save |
| `created_by` | ForeignKey → User | Tracks who created the record |
| `updated_by` | ForeignKey → User | Tracks who last modified the record |

All models use **UUID primary keys** for security and portability. Slug fields exist on human-named entities (templates, pages, sites) but **not** on placement rows, which are accessed by UUID.

### 3.3 Slug vs UUID Access Strategy

| Model | Identification | API Access Pattern | Rationale |
|---|---|---|---|
| Site | Slug (unique per org) | `/sites/{slug}/` | Human-named, few per org |
| Page | Slug (unique per site) | `/pages/{slug}/` | Human-named, URL-friendly |
| SectionTemplate | Slug (globally unique) | `/templates/sections/{slug}/` | Platform-wide reusable, named |
| BlockTemplate | Slug (globally unique) | `/templates/blocks/{slug}/` | Platform-wide reusable, named |
| PageSectionPlacement | UUID | `/section-placements/{uuid}/` | Auto-created, many per page |
| SectionBlockPlacement | UUID | `/block-placements/{uuid}/` | Auto-created, content container |
| MediaFolder | Slug (unique per org+parent) | `/media/folders/{slug}/` | Human-named |
| MediaFile | UUID | `/media/files/{uuid}/` | Many files, auto-generated names |

Placement models may optionally have a `label` CharField for admin UI display purposes, but this is never used for routing or uniqueness.

---

### 3.4 Site Model

The Site model acts as a **website container** — a logical grouping of pages that belong to a single organization. This enables multi-site support per organization in the future.

| Field | Type | Description |
|---|---|---|
| _Base fields_ | — | UUID, slug, timestamps, created_by, updated_by |
| `organization` | ForeignKey → Organization | The owning organization |
| `name` | CharField | Display name of the site |
| `domain` | CharField (nullable) | Associated domain, if any |
| `description` | TextField (nullable) | Internal description/notes |
| `default_locale` | CharField | Default language code (e.g., `en`) |
| `metadata` | JSONB (nullable) | SEO defaults, theme settings, global config |
| `is_active` | BooleanField | Whether the site is live |

**Slug Uniqueness:** `Unique(organization, slug)`

**Relationships:**

- Belongs to one Organization (ForeignKey)
- Has many Pages (reverse ForeignKey)
- Has one designated homepage (nullable ForeignKey to Page)

---

### 3.5 Page Model

A Page represents a single routable page within a Site. Its structure (which sections, in what order) is defined by the superuser and is immutable by admins.

| Field | Type | Description |
|---|---|---|
| _Base fields_ | — | UUID, slug, timestamps, created_by, updated_by |
| `site` | ForeignKey → Site | The site this page belongs to |
| `title` | CharField | Page title |
| `description` | TextField (nullable) | Internal description |
| `path` | CharField | URL path relative to the site (e.g., `/about`, `/pricing`) |
| `page_type` | CharField | Categorization (e.g., `landing`, `content`, `legal`, `blog_post`) |
| `metadata` | JSONB (nullable) | SEO title, description, OG tags, structured data |
| `status` | CharField | One of: `draft`, `published`, `archived` |
| `published_at` | DateTimeField (nullable) | When the page was last published |
| `is_required` | BooleanField | If true, this page cannot be hidden by admin |
| `order` | PositiveIntegerField | Ordering within the site's page list |

**Slug Uniqueness:** `Unique(site, slug)`

**Additional Constraint:** `Unique(site, path)` — no duplicate URL paths within a site.

**Relationships:**

- Belongs to one Site (ForeignKey)
- Has many section placements through `PageSectionPlacement` (reverse ForeignKey)

---

### 3.6 SectionTemplate Model

A SectionTemplate is a **reusable layout definition** — the structural blueprint for a region of a page (hero area, feature grid, footer, etc.). It defines what type of section this is and carries layout metadata. SectionTemplates hold **no content** — content lives in block placements within the section.

| Field | Type | Description |
|---|---|---|
| _Base fields_ | — | UUID, slug (globally unique), timestamps, created_by, updated_by |
| `name` | CharField | Internal name (e.g., `hero_banner`, `feature_grid`, `testimonials`) |
| `display_name` | CharField | Human-readable name for admin UI |
| `description` | TextField (nullable) | Description of the section's purpose |
| `section_type` | CharField | Categorization (e.g., `header`, `content`, `footer`, `sidebar`) |
| `metadata` | JSONB (nullable) | General metadata, tags, categorization |
| `ui_config` | JSONB (nullable) | UI rendering hints — component name, layout mode, CSS classes, conditional display rules (separated from metadata for clarity) |

**Slug Uniqueness:** `Unique(slug)` — globally unique.

**Relationships:**

- Has many PageSectionPlacements (reverse ForeignKey)

**Note:** SectionTemplates are purely structural. They have no `status`, `content`, or organization scope. They are platform-wide reusable definitions.

---

### 3.7 PageSectionPlacement Model

The **placement record** that attaches a SectionTemplate to a Page. This is a one-to-many relationship from Page (each placement belongs to exactly one page). It carries ordering, visibility, and per-placement configuration.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key — used for API access |
| `page` | ForeignKey → Page | The page this section is placed on. **Each placement belongs to exactly one page.** |
| `template` | ForeignKey → SectionTemplate | The section template being placed |
| `label` | CharField (nullable) | Optional admin-friendly label for this placement (e.g., "Hero Section on About Page") |
| `order` | PositiveIntegerField | Position of this section within the page |
| `is_required` | BooleanField | Set by superuser. If true, admin cannot hide this section |
| `is_visible` | BooleanField | Default `true`. Admin can toggle to `false` ONLY if `is_required=false` |
| `config_overrides` | JSONB (nullable) | Per-placement overrides (e.g., different background, spacing) |
| `created_at` | DateTimeField | Timestamp |
| `updated_at` | DateTimeField | Timestamp |

**Constraints:**

- `Unique(page, order)` — exactly one section per position on a page. Prevents ordering collisions.
- If `is_required=true`, the API must prevent setting `is_visible=false`.

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
| _Base fields_ | — | UUID, slug (globally unique), timestamps, created_by, updated_by |
| `name` | CharField | Internal name (e.g., `hero_text`, `cta_button`, `team_card`) |
| `display_name` | CharField | Human-readable name for admin UI |
| `description` | TextField (nullable) | Description of the block's purpose |
| `block_type` | CharField | Categorization (e.g., `text`, `media`, `composite`, `repeater`) |
| `schema` | JSONB | **Field definitions** — types, validation, required/nullable flags. **Immutable by admins.** |
| `default_content` | JSONB (nullable) | Default values set by superuser, used to pre-populate new placements |
| `metadata` | JSONB (nullable) | General metadata, tags, categorization |
| `ui_config` | JSONB (nullable) | Rendering hints — frontend component name, CSS classes, layout rules (separated from metadata) |

**Slug Uniqueness:** `Unique(slug)` — globally unique.

**Relationships:**

- Has many SectionBlockPlacements (reverse ForeignKey)

**Critical Design Note:** The `schema` field is **absolutely immutable by admins**. Admins cannot view schema editing interfaces, cannot modify field names, types, validation rules, or any structural aspect of the block. The schema is the form definition; the admin fills in the form. Only superusers can modify schemas through the Django Admin panel.

---

### 3.9 SectionBlockPlacement Model — The Content Container

This is the **core content-bearing entity** of the entire CMS. It attaches a BlockTemplate to a PageSectionPlacement and carries the actual draft and published content. Each placement is structurally unique — it belongs to exactly one section placement, which belongs to exactly one page. **Content isolation is guaranteed by construction.**

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key — used for API access |
| `section_placement` | ForeignKey → PageSectionPlacement | The section placement this block belongs to. **Each block placement belongs to exactly one section placement.** |
| `template` | ForeignKey → BlockTemplate | The block template defining the schema |
| `label` | CharField (nullable) | Optional admin-friendly label for this placement |
| `order` | PositiveIntegerField | Position of this block within the section |
| `is_required` | BooleanField | Set by superuser. If true, admin cannot hide this block |
| `is_visible` | BooleanField | Default `true`. Admin can toggle to `false` ONLY if `is_required=false` |
| `config_overrides` | JSONB (nullable) | Per-placement overrides |
| `draft_content` | JSONB (nullable) | **Working copy** — the content admins edit. Not visible to public API. Pre-populated from `BlockTemplate.default_content` on creation. |
| `published_content` | JSONB (nullable) | **Frozen live copy** — set only when the page is published. Public API serves this. |
| `status` | CharField | One of: `draft`, `published` |
| `created_at` | DateTimeField | Timestamp |
| `updated_at` | DateTimeField | Timestamp |
| `created_by` | ForeignKey → User | Who created this placement |
| `updated_by` | ForeignKey → User | Who last modified content |

**Constraints:**

- `Unique(section_placement, order)` — exactly one block per position in a section. Prevents ordering collisions.
- Same `is_required` / `is_visible` logic as `PageSectionPlacement`.

**Relationships:**

- Belongs to exactly one PageSectionPlacement (ForeignKey — NOT M2M)
- References one BlockTemplate (ForeignKey)
- Has many ContentVersions (reverse ForeignKey)

**Content Flow:**

1. Superuser places a BlockTemplate into a section → system creates a `SectionBlockPlacement` row with `draft_content` pre-populated from `BlockTemplate.default_content`.
2. Admin edits `draft_content` → saved freely, creates a ContentVersion with `action=draft_save`.
3. Admin triggers publish on the parent page → system validates ALL `draft_content` fields against their template schemas within a single transaction.
4. If valid, `draft_content` is copied to `published_content` for ALL block placements on the page → creates ContentVersions with `action=publish`.
5. Public API always reads `published_content`. Admin UI reads `draft_content`.
6. Rollback restores `draft_content` from a ContentVersion snapshot → requires re-publish to go live.

**Content Isolation Guarantee:**

```
Page A
  └─ PageSectionPlacement #1 (template: hero_banner)
       └─ SectionBlockPlacement #1 (template: hero_text)
            ├── draft_content: {"title": "Welcome to Page A"}    ← ISOLATED
            └── published_content: {"title": "Welcome to Page A"}

Page B
  └─ PageSectionPlacement #2 (template: hero_banner)  ← same template, different placement
       └─ SectionBlockPlacement #2 (template: hero_text)  ← same template, different placement
            ├── draft_content: {"title": "Welcome to Page B"}    ← COMPLETELY SEPARATE
            └── published_content: {"title": "Welcome to Page B"}
```

Editing Page A's hero text has zero effect on Page B. This is structural, not enforced by validation.

---

### 3.10 ContentVersion Model

Provides **content history** for rollback capability. A snapshot is stored when an admin saves or publishes block placement content.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `block_placement` | ForeignKey → SectionBlockPlacement | The block placement this version belongs to |
| `content_snapshot` | JSONB | Full copy of `draft_content` at this point in time |
| `version_number` | PositiveIntegerField | Auto-incrementing per block placement |
| `action` | CharField | One of: `draft_save`, `publish`, `rollback`, `import` |
| `created_by` | ForeignKey → User | Who made this change |
| `created_at` | DateTimeField | When this version was created |
| `notes` | TextField (nullable) | Optional description of the change |

**Behavior:**

- On every `save` (draft) or `publish` action, a new `ContentVersion` is created automatically.
- Rollback restores `draft_content` from a selected version and creates a new version entry with `action=rollback`. **Rollback does NOT update `published_content`** — the admin must re-publish to push rolled-back content live.
- Versions are ordered by `version_number` descending.

**Cost Control:**

- **Retention policy**: Configurable maximum versions per block placement (default: 50). Oldest versions beyond this limit are automatically pruned.
- **Throttling**: If the admin UI autosaves, version creation is debounced — no more than 1 version per 30 seconds per block placement. Rapid edits within the throttle window update the latest version in-place rather than creating new ones.
- **Future optimization**: Switch to diff-based storage (store only changed fields) once the system is stable. The audit system already captures diffs for lightweight change tracking.

---

### 3.11 Complete Entity Relationship Summary

```
Organization ─1:N──→ Site ─1:N──→ Page

SectionTemplate (platform-wide, reusable schema)
BlockTemplate   (platform-wide, reusable schema + field definitions)

Page ─1:N──→ PageSectionPlacement
               ├── order, is_required, is_visible, config_overrides
               ├── template → SectionTemplate
               │
               └─1:N──→ SectionBlockPlacement
                          ├── order, is_required, is_visible, config_overrides
                          ├── template → BlockTemplate
                          ├── draft_content (JSONB, admin-editable)
                          ├── published_content (JSONB, set on publish)
                          ├── status
                          └─1:N──→ ContentVersion (history snapshots)

Ownership chain (strict 1:N at every level):
  Page → PageSectionPlacement → SectionBlockPlacement → ContentVersion
  (no M2M anywhere in the content chain — isolation guaranteed)
```

### 3.12 Slug Uniqueness Scope

| Model | Slug/ID Strategy | Uniqueness Scope | Rationale |
|---|---|---|---|
| Site | Slug | `Unique(organization, slug)` | Named, few per org |
| Page | Slug | `Unique(site, slug)` + `Unique(site, path)` | Named, URL-friendly |
| SectionTemplate | Slug | `Unique(slug)` — globally unique | Platform-wide reusable |
| BlockTemplate | Slug | `Unique(slug)` — globally unique | Platform-wide reusable |
| PageSectionPlacement | UUID only | N/A (UUID is inherently unique) | Auto-created, accessed by UUID |
| SectionBlockPlacement | UUID only | N/A (UUID is inherently unique) | Auto-created, content container |
| MediaFolder | Slug | `Unique(organization, parent, slug)` | Named, nested hierarchy |
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

---

## 5. Schema Validation Engine

### 5.1 Architecture

Content validation is handled by a server-side **`SchemaValidator`** service class that takes a BlockTemplate's schema and validates a content JSONB against it. This is not a loose convention — it is a concrete, testable component.

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

The media library is a **centralized, folder-based asset management system** shared across the organization. All media references in block content point to media library files by UUID. **Files are stored by path/key in Supabase Storage — URLs are generated at read time, never stored.**

### 6.2 MediaFolder Model

| Field | Type | Description |
|---|---|---|
| _Base fields_ | — | UUID, slug, timestamps, created_by, updated_by |
| `organization` | ForeignKey → Organization | Owning organization |
| `name` | CharField | Folder display name |
| `parent` | ForeignKey → self (nullable) | Parent folder for nesting |
| `path` | CharField | Full materialized path (e.g., `/images/heroes/2026/`) |

**Slug Uniqueness:** `Unique(organization, parent, slug)`

**Constraints:**

- Unique together: `(organization, parent, name)` — no duplicate folder names at the same level
- Maximum nesting depth enforced at API level (recommended: 5 levels)

### 6.3 MediaFile Model

| Field | Type | Description |
|---|---|---|
| _Base fields_ | — | UUID, timestamps, created_by, updated_by |
| `organization` | ForeignKey → Organization | Owning organization |
| `folder` | ForeignKey → MediaFolder (nullable) | Containing folder (null = root) |
| `storage_key` | CharField | **Storage path/key in Supabase Storage** (e.g., `org-uuid/images/hero-banner.png`). This is the permanent reference — never a URL. |
| `original_filename` | CharField | Original upload filename |
| `mime_type` | CharField | MIME type (e.g., `image/png`, `application/pdf`) |
| `file_size` | PositiveIntegerField | Size in bytes |
| `width` | PositiveIntegerField (nullable) | Image/video width in pixels |
| `height` | PositiveIntegerField (nullable) | Image/video height in pixels |
| `alt_text` | CharField (nullable) | Default alt text |
| `title` | CharField (nullable) | Display title |
| `metadata` | JSONB (nullable) | EXIF data, custom tags, processing info |
| `is_tombstoned` | BooleanField | Default `false`. Set to `true` when admin deletes the file but it's still referenced by published content. |

**URL Generation:** The API generates signed URLs at read time using `storage_key` + Supabase Storage SDK. URLs are never stored in the database. This means tombstoned files remain accessible (their storage key still resolves) until the cleanup job removes them.

### 6.4 MediaUsage Tracking Model

Tracks where every media file is referenced, enabling safe deletion warnings and cascade cleanup.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `media_file` | ForeignKey → MediaFile | The referenced file |
| `block_placement` | ForeignKey → SectionBlockPlacement | The block placement containing the reference |
| `field_key` | CharField | Which field in the block's content references this file |
| `content_layer` | CharField | One of: `draft`, `published` — which content JSONB holds this reference |
| `created_at` | DateTimeField | When the reference was established |

**Behavior — Aligned with Draft/Publish Model:**

- **MediaUsage records are created/updated** whenever block placement content is saved (draft) or published. Both `draft_content` and `published_content` references are tracked separately via the `content_layer` field.
- **When a media file is deleted from the library**:
  - `draft_content` references are set to `null` across all block placements. This is safe because draft content is not live.
  - `published_content` references are **NOT immediately nulled**. The media file enters tombstoned state (`is_tombstoned=true`) — it remains in storage and its URL still resolves. On next publish, the SchemaValidator catches the tombstoned reference and forces the admin to replace it.
  - A pre-deletion check warns the admin how many block placements (draft and published) will be affected.
- **When a media reference is removed from a block field**: only the MediaUsage record is deleted. The file remains in the library untouched.
- **Tombstone cleanup job**: A periodic background task checks for tombstoned files that have zero `published` layer MediaUsage records (all affected pages have been re-published with replacement media). These files are permanently deleted from storage.
- **Lookup**: given a media file, query MediaUsage to find every block placement, field, and content layer that references it.

---

## 7. Permission Model & RBAC Integration

### 7.1 CMS Permission Set

The CMS defines the following permissions that integrate with the existing ARENA-Z RBAC system:

**Structural Permissions (Superuser / Developer):**

| Permission | Description |
|---|---|
| `cms.manage_sites` | Create, edit, delete Sites |
| `cms.manage_pages` | Create, edit, delete Pages and their structural placements |
| `cms.manage_section_templates` | Create, edit, delete SectionTemplates |
| `cms.manage_block_templates` | Create, edit, delete BlockTemplates and their schemas |
| `cms.manage_templates` | Full structural authority across all CMS template models |
| `cms.assign_to_organization` | Assign sites/pages to organizations |

**Content Permissions (Organization Admin):**

| Permission | Description |
|---|---|
| `cms.view_content` | View pages, placements, and their content |
| `cms.edit_content` | Edit draft_content values within assigned block placements |
| `cms.publish_content` | Publish pages (copy draft_content → published_content) |
| `cms.manage_media` | Upload, organize, and delete media files |
| `cms.toggle_visibility` | Hide/show non-required section and block placements |
| `cms.export_content` | Export page data as JSON |
| `cms.import_content` | Import page data from JSON (content-only) |
| `cms.view_history` | View content version history |
| `cms.rollback_content` | Rollback draft_content to a previous version |

### 7.2 Permission Enforcement

- **Django Admin panel**: Structural permissions are enforced through Django's built-in admin permission system combined with custom `ModelAdmin` configurations
- **API endpoints**: Every view checks the user's RBAC permissions before allowing the operation
- **Organization scoping**: Admins can only access content for sites belonging to their organization. The RBAC system verifies organization membership on every request
- **Field-level enforcement**: Even with `cms.edit_content`, the API validates that the user is only modifying `draft_content` JSONB values — never `schema`, `published_content`, `order`, `is_required`, or structural fields
- **Public API**: No authentication required for read-only access to `published_content`. Only the `/api/cms/public/` prefix is exposed to unauthenticated consumers.

### 7.3 Interaction Mode Summary

| Action | Superuser | Admin (with permissions) | Admin (without permissions) |
|---|---|---|---|
| Create Site | ✅ | ❌ | ❌ |
| Create Page | ✅ | ❌ | ❌ |
| Delete Page | ✅ | ❌ | ❌ |
| Create/edit/delete BlockTemplates | ✅ | ❌ | ❌ |
| Create/edit/delete SectionTemplates | ✅ | ❌ | ❌ |
| Define or modify block schema | ✅ | ❌ | ❌ |
| Modify field definitions (name, type, validation) | ✅ | ❌ | ❌ |
| Set required/nullable flags on fields | ✅ | ❌ | ❌ |
| Attach section placement to page | ✅ | ❌ | ❌ |
| Attach block placement to section | ✅ | ❌ | ❌ |
| Reorder placements | ✅ | ❌ | ❌ |
| Edit field **values** (draft_content only) | ✅ | ✅ | ❌ |
| Add/remove repeater items (within min/max) | ✅ | ✅ | ❌ |
| Toggle placement visibility | ✅ | ✅ (only if `is_required=false`) | ❌ |
| Save as draft | ✅ | ✅ | ❌ |
| Publish page | ✅ | ✅ | ❌ |
| Upload media | ✅ | ✅ | ❌ |
| Delete media from library | ✅ | ✅ | ❌ |
| Export JSON | ✅ | ✅ | ❌ |
| Import JSON (content-only) | ✅ | ✅ | ❌ |
| Import JSON (full structural) | ✅ | ❌ | ❌ |
| View content (admin API) | ✅ | ✅ | ✅ |
| View content (public API) | ✅ | ✅ | ✅ (published only) |
| View content history | ✅ | ✅ | ❌ |
| Rollback draft content | ✅ | ✅ | ❌ |

---

## 8. API Design

### 8.1 Design Principles

- **Public/Admin split**: Two endpoint prefixes with different authorization and data exposure rules
- **Every entity is independently accessible** via its own endpoint
- **Nested retrieval with depth control** allows fetching a full page tree in one request
- **Templates use slug-based access**, placements use **UUID-based access**
- **Organization-scoped**: admin API queries are automatically filtered by the requesting user's organization
- **RESTful conventions** with consistent response envelopes

### 8.2 Admin API Endpoints (`/api/cms/admin/`)

All admin endpoints require authentication. Organization scoping is enforced automatically.

**Sites:**

```
GET    /api/cms/admin/sites/                              → List sites (org-scoped)
POST   /api/cms/admin/sites/                              → Create site (superuser)
GET    /api/cms/admin/sites/{slug}/                        → Get site details
PATCH  /api/cms/admin/sites/{slug}/                        → Update site
DELETE /api/cms/admin/sites/{slug}/                        → Delete site (superuser)
```

**Pages:**

```
GET    /api/cms/admin/pages/                               → List pages (filterable by site, status)
POST   /api/cms/admin/pages/                               → Create page (superuser)
GET    /api/cms/admin/pages/{slug}/                        → Get page
GET    /api/cms/admin/pages/{slug}/?depth=sections         → Page + section placements
GET    /api/cms/admin/pages/{slug}/?depth=full             → Page + section placements + block placements + draft_content
PATCH  /api/cms/admin/pages/{slug}/                        → Update page metadata
DELETE /api/cms/admin/pages/{slug}/                        → Delete page (superuser)
POST   /api/cms/admin/pages/{slug}/publish/                → Validate & publish page (transactional)
POST   /api/cms/admin/pages/{slug}/unpublish/              → Revert to draft status
POST   /api/cms/admin/pages/{slug}/export/                 → Export page tree as JSON
POST   /api/cms/admin/pages/{slug}/import/                 → Import page content from JSON
```

**Templates (Superuser-only):**

```
GET    /api/cms/admin/templates/sections/                  → List section templates
POST   /api/cms/admin/templates/sections/                  → Create section template
GET    /api/cms/admin/templates/sections/{slug}/            → Get section template
PATCH  /api/cms/admin/templates/sections/{slug}/            → Update section template
DELETE /api/cms/admin/templates/sections/{slug}/            → Delete section template

GET    /api/cms/admin/templates/blocks/                    → List block templates
POST   /api/cms/admin/templates/blocks/                    → Create block template
GET    /api/cms/admin/templates/blocks/{slug}/              → Get block template (with schema)
PATCH  /api/cms/admin/templates/blocks/{slug}/              → Update block template/schema
DELETE /api/cms/admin/templates/blocks/{slug}/              → Delete block template
```

**Section Placements:**

```
GET    /api/cms/admin/section-placements/{uuid}/           → Get section placement details
PATCH  /api/cms/admin/section-placements/{uuid}/           → Update visibility/overrides (admin)
```

**Block Placements (content interaction):**

```
GET    /api/cms/admin/block-placements/{uuid}/             → Get block placement (draft_content + template schema)
PATCH  /api/cms/admin/block-placements/{uuid}/             → Update draft_content (admin)
GET    /api/cms/admin/block-placements/{uuid}/history/     → List content versions
POST   /api/cms/admin/block-placements/{uuid}/rollback/{version}/ → Rollback draft_content to version
```

**Media:**

```
GET    /api/cms/admin/media/folders/                       → List folders (nested tree)
POST   /api/cms/admin/media/folders/                       → Create folder
PATCH  /api/cms/admin/media/folders/{slug}/                → Rename/move folder
DELETE /api/cms/admin/media/folders/{slug}/                 → Delete folder (must be empty)
GET    /api/cms/admin/media/files/                         → List files (filterable by folder, type)
POST   /api/cms/admin/media/files/                         → Upload file
GET    /api/cms/admin/media/files/{uuid}/                  → Get file details + usage info + signed URL
PATCH  /api/cms/admin/media/files/{uuid}/                  → Update metadata
DELETE /api/cms/admin/media/files/{uuid}/                  → Delete file (tombstone if published refs exist)
GET    /api/cms/admin/media/files/{uuid}/usage/            → List all block placements referencing this file
```

### 8.3 Public API Endpoints (`/api/cms/public/`)

Public endpoints are read-only. They return `published_content` only. No `draft_content`, no template schemas (unless `?include_schema=true` for frontend rendering needs), no structural editing capabilities.

```
GET    /api/cms/public/sites/{slug}/                       → Get published site info
GET    /api/cms/public/pages/{slug}/                       → Get published page
GET    /api/cms/public/pages/{slug}/?depth=full            → Full published page tree (sections + blocks + published_content)
GET    /api/cms/public/media/files/{uuid}/url/             → Get signed URL for a media file
```

### 8.4 Depth Control Parameter

The `depth` query parameter controls how much related data is included in responses:

| Value | Behavior |
|---|---|
| _omitted_ | Returns only the requested model's fields |
| `sections` | (Pages only) Includes section placements with ordering |
| `blocks` | (Section placements only) Includes block placements with ordering |
| `full` | (Pages only) Includes sections → blocks → content, fully resolved |

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
- Standard pagination via `?page=1&page_size=20`

---

## 9. Draft & Publish Workflow

### 9.1 States

Every Page has a `status` field with these states:

```
draft ──── publish ────→ published
  ↑                          │
  └──── unpublish ───────────┘

published ── archive ──→ archived
                            │
  draft ←── unarchive ──────┘
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

**Publish Flow (single database transaction):**

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
   - If ANY errors exist → ABORT transaction, return structured error response

3. WRITE ALL (only if validation passed)
   - For each block placement:
     a. Copy draft_content → published_content
     b. Set status = 'published'
     c. Create ContentVersion (action=publish)
     d. Update MediaUsage records for published layer
   - Set Page.status = 'published'
   - Set Page.published_at = now()

4. COMMIT TRANSACTION
   - All changes are committed atomically
   - If any step fails, entire transaction rolls back — nothing changes

5. POST-COMMIT (outside transaction)
   - Invalidate cached published page tree (if caching is enabled)
   - Fire audit log entries
   - Trigger webhooks (future)
```

**Concurrency Guarantee:** If Admin A and Admin B both click "Publish" on the same page simultaneously, one will acquire the lock first and complete. The other will wait for the lock and then either succeed (if validation still passes) or fail (if the first publish changed something that invalidates their draft).

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
  "export_version": "3.0",
  "exported_at": "2026-02-25T14:30:00Z",
  "exported_by": "user-uuid",
  "source_site": "main-website",
  "source_organization": "org-uuid",
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

### 10.2 Import Behavior

- **Content-only import** (admin): Matches block placements by UUID and updates `draft_content` values only. Ignores structural differences. Validates against existing template schemas.
- **Full import** (superuser): Can create or update structural elements (templates, placements, schemas). Used for migrating page structures between environments (staging → production).
- **Conflict resolution**: UUID matches update existing entities. New UUIDs in full-import mode create new placements (superuser only).
- **Validation**: Import always validates content against template schema before applying. Rejected imports return a **structured, machine-readable error report**:

```json
{
  "import_errors": [
    {
      "block_placement_id": "uuid-of-block-placement",
      "field_key": "title",
      "error_type": "type_mismatch",
      "message": "Expected text, received number",
      "value": 42
    }
  ],
  "warnings": [
    {
      "type": "template_mismatch",
      "message": "Block template 'hero_text' schema has changed since export. 2 fields added, 1 removed."
    }
  ]
}
```

---

## 11. Django Admin Panel Configuration

### 11.1 Design Principles

The Django Admin panel is the **primary interface for superusers** to manage the CMS structure. It must be well-organized, intuitive, and prevent accidental destructive operations. Template models and placement models should be clearly separated in the admin navigation.

### 11.2 Admin Structure

**SiteAdmin:**
- Fieldsets: Basic Info (name, slug, domain), Organization, Settings (locale, metadata), Status
- Inlines: Pages list (read-only summary with links)
- List display: name, organization, domain, is_active, page count
- List filters: organization, is_active
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
- List display: display_name, section_type, placement count (how many placements reference this template)
- Search: name, display_name

**BlockTemplateAdmin:**
- Fieldsets: Basic Info (name, display_name, slug), Type, Schema (JSONB with pretty-print widget), Default Content, Metadata, UI Config
- List display: display_name, block_type, placement count
- Custom actions: "Export block schema", "Duplicate template"
- Search: name, display_name

**PageSectionPlacementAdmin:**
- Fieldsets: Page (read-only link), Template (read-only link), Order, Required, Visible, Config Overrides
- Inlines: `SectionBlockPlacementInline` — tabular inline showing block placements with order, template name, is_required, is_visible, status
- List display: page title, template display_name, order, is_visible
- List filters: page__site, template
- Search: page__title, label

**SectionBlockPlacementAdmin:**
- Fieldsets: Section Placement (read-only link), Template Info (read-only: template name, schema preview), Draft Content (editable JSONB), Published Content (read-only JSONB), Status, Order, Required, Visible
- Read-only fields for admin users: template, schema (via template), published_content, section_placement, order
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

### 12.1 Audited Operations

Every CMS mutation must generate an audit log entry through the existing ARENA-Z observability system:

| Category | Operations |
|---|---|
| **Structural** | Create/update/delete site, page, section template, block template, schema changes, placement creation/deletion |
| **Content** | Draft save, publish (transactional — all placements), unpublish, rollback, visibility toggle |
| **Media** | File upload, file delete/tombstone, tombstone cleanup, folder create/delete, media reference change |
| **Access** | Export triggered, import triggered, permission-denied attempts |

### 12.2 Audit Entry Data

Each audit entry should include:

- `action`: The operation performed
- `model`: Which CMS model was affected
- `object_id`: UUID of the affected object
- `user_id`: Who performed the action
- `organization_id`: Which organization context
- `timestamp`: When it happened
- `changes`: JSONB diff showing before/after for content changes
- `metadata`: Additional context (IP address, API endpoint, request ID)

### 12.3 Content Change Tracking

For content updates specifically, the audit system should capture a **diff** rather than a full snapshot (the full snapshot lives in ContentVersion). The diff format:

```json
{
  "field_key": "title",
  "old_value": "Welcome",
  "new_value": "Welcome to Arena-Z",
  "content_layer": "draft"
}
```

---

## 13. Indexing & Performance Considerations

### 13.1 Database Indexes

| Table | Index | Type | Purpose |
|---|---|---|---|
| Site | `(organization_id, slug)` | Unique composite | Slug unique per org |
| Page | `(site_id, slug)` | Unique composite | Slug unique per site |
| Page | `(site_id, path)` | Unique composite | Ensure unique paths within a site |
| Page | `(site_id, status)` | Composite | Filter published pages per site |
| SectionTemplate | `slug` | Unique | Globally unique template slug |
| BlockTemplate | `slug` | Unique | Globally unique template slug |
| PageSectionPlacement | `(page_id, order)` | Unique composite | One section per position |
| SectionBlockPlacement | `(section_placement_id, order)` | Unique composite | One block per position |
| SectionBlockPlacement | `template_id` | B-tree | Find all placements of a template |
| SectionBlockPlacement | `draft_content` | GIN | JSONB content search |
| SectionBlockPlacement | `published_content` | GIN | JSONB published content search |
| SectionBlockPlacement | `status` | B-tree | Filter by publish status |
| MediaFile | `(organization_id, folder_id)` | Composite | Folder browsing |
| MediaFile | `mime_type` | B-tree | Type filtering |
| MediaFile | `is_tombstoned` | B-tree | Filter tombstoned files |
| MediaUsage | `(media_file_id)` | B-tree | Reverse lookup: where is this file used? |
| MediaUsage | `(block_placement_id)` | B-tree | Forward lookup: what media does this block use? |
| ContentVersion | `(block_placement_id, version_number)` | Composite, descending | Latest version retrieval |

### 13.2 Query Optimization Notes

- The `?depth=full` endpoint on pages involves joins across Page → PageSectionPlacement → SectionBlockPlacement → BlockTemplate. Use `select_related` and `prefetch_related` aggressively. With the simplified model (no separate instance tables), this is only 3 joins deep — much more efficient than v2.
- JSONB GIN indexes on both `draft_content` and `published_content` enable efficient searching within content fields, but avoid unbounded JSONB queries in list endpoints — use them only for targeted searches.
- Media usage tracking via the `MediaUsage` table avoids expensive JSONB scans across all block placements when checking if a file is referenced.
- **Published page cache**: Cache the full `depth=full` public API response per page. Invalidate only on publish/unpublish. Since `published_content` only changes during the publish transaction, cache invalidation is deterministic and easy.
- Template queries (listing all block templates, section templates) are infrequent and small — no special optimization needed.

---

## 14. Risks & Edge Cases

### 14.1 Schema Change Breaking Existing Content

**Risk:** When a superuser modifies a BlockTemplate's schema (adding required fields, changing field types, removing fields), existing `draft_content` and `published_content` on placements using that template may become invalid. The next publish attempt would fail validation, potentially blocking admins from publishing unrelated changes on the same page.

**Mitigations:**

- **Schema versioning:** Add a `schema_version` integer field to BlockTemplate. Increment on every schema change. Each SectionBlockPlacement records the `schema_version` it was last validated against. When a schema changes, the system can identify all affected placements.
- **Compatibility rules:** Schema changes are classified as **backward-compatible** (adding optional fields, relaxing validation) or **breaking** (adding required fields, changing types, removing fields). Backward-compatible changes apply silently. Breaking changes trigger a warning in the Django Admin listing all affected placements.
- **Migration scripts:** For breaking changes, provide a management command or admin action that batch-updates affected `draft_content` — applying defaults for new required fields, transforming values for type changes, and pruning removed fields. This runs against draft only; published content remains stable until re-publish.
- **Publish-time fallback:** If `draft_content` references fields that no longer exist in the schema, the SchemaValidator ignores unknown fields (permissive) rather than rejecting. This prevents stale fields from blocking publish. The admin UI can flag these as "orphaned fields" for cleanup.

### 14.2 Large Repeater Payloads

**Risk:** Admins adding many items to repeater fields (100+ cards, team members, FAQ entries, etc.) causes large JSONB payloads. This degrades API response times, increases database I/O, and makes the admin editing UI sluggish.

**Mitigations:**

- **Enforce max_items limits:** Every repeater field schema already supports `max_items`. Superusers should set reasonable ceilings (e.g., 50) based on the use case. The SchemaValidator enforces this on both draft save and publish.
- **API payload size monitoring:** Log response sizes for `depth=full` requests. Alert when average payload exceeds a configurable threshold (e.g., 1MB).
- **Future: repeater pagination:** For repeaters that legitimately need many items (e.g., a product catalog block), support paginated sub-queries within the block placement API — returning items in batches rather than the full array.
- **Future: content chunking:** For extremely large pages, consider breaking `draft_content` into per-field or per-repeater storage rather than a single monolithic JSONB. This is a significant architectural change and should only be pursued if performance monitoring shows a real problem.

### 14.3 Concurrent Editing Conflict

**Risk:** Two admins editing the same block placement's `draft_content` simultaneously. With the current design, last save wins — the second admin's save overwrites the first admin's changes without warning.

**Current behavior (v1):** Last write wins. Acceptable for initial launch because concurrent editing of the same block placement is expected to be rare (most organizations have few content editors, and blocks are granular enough that collision is unlikely).

**Future mitigations (not in initial scope):**

- **Optimistic locking via `updated_at`:** On save, the API checks that the client's `updated_at` matches the current database value. If another save occurred in between, the API returns a `409 Conflict` response with both versions, letting the admin decide how to merge.
- **Edit presence indicators:** The admin UI shows a warning when another user is currently viewing/editing the same block placement (via WebSocket or polling).
- **Field-level merging:** Instead of overwriting the entire `draft_content` JSONB, the API accepts partial updates (only changed fields) and merges them. This reduces collision surface — two admins can edit different fields on the same block without conflict.

### 14.4 Tombstoned Media Accumulation

**Risk:** If admins frequently delete and replace media files, tombstoned files accumulate in storage. Without the cleanup job running reliably, storage costs grow indefinitely.

**Mitigations:**

- **Cleanup job reliability:** The tombstone cleanup job must be monitored via the existing observability system. Alert if it hasn't run successfully within its expected schedule (e.g., daily).
- **Tombstone age limit:** As a safety net, auto-delete tombstoned files older than a configurable threshold (e.g., 90 days) regardless of published reference status. This prevents indefinite accumulation in cases where pages are never re-published.
- **Admin visibility:** The MediaFile admin list shows tombstoned files with a clear visual indicator. Superusers can manually trigger cleanup or permanently delete specific tombstoned files.

### 14.5 ContentVersion Storage Growth

**Risk:** With full JSONB snapshots on every save, ContentVersion storage grows proportionally to content size × edit frequency. A block with a large repeater (e.g., 50 items) saved 50 times creates 50 copies of the full payload.

**Mitigations:**

- **Retention policy** (already specified): Default 50 versions per block placement. Oldest are pruned automatically.
- **Throttling** (already specified): Max 1 version per 30 seconds. Rapid edits update the latest version in-place.
- **Monitoring:** Track total ContentVersion storage size per site/org. Alert when growth rate exceeds expected thresholds.
- **Future: diff-based storage** (already noted in Future Considerations): Store only changed fields per version. Reconstruct full content by replaying diffs. Reduces storage by ~80-90% for typical edit patterns.

---

## 15. Future Considerations

The following are **not in scope for the initial build** but the architecture should not prevent them:

- **Multi-language / Localization**: Content JSONB could be keyed by locale (`{"en": {...}, "fa": {...}}`). The schema structure already supports this with minimal changes.
- **Visual Page Builder**: A frontend drag-and-drop interface for superusers to build page structures. The Template/Placement model supports this — the builder would create templates and wire up placements through the existing API.
- **Workflow Approvals**: A multi-step publish flow (editor → reviewer → publisher) built on top of the status system.
- **Component Marketplace**: Pre-built block templates (hero sections, pricing tables, FAQ accordions) that superusers can install into their CMS. The globally-scoped template model is designed for this.
- **A/B Testing**: Multiple content variants per block placement with traffic splitting logic. Could be modeled as additional JSONB fields on SectionBlockPlacement.
- **Webhooks**: Notify external systems on publish/unpublish events (post-commit hooks in the publish transaction).
- **Business Account CMS Access**: When the platform expands beyond the platform account, the site/organization scoping already supports multi-tenant content management.
- **Full Page Snapshots**: A `PagePublishSnapshot` model that stores the fully resolved page tree JSON at publish time, enabling point-in-time reconstruction. The current dual-content model is a stepping stone to this.
- **Diff-based ContentVersions**: Replace full JSONB snapshots with field-level diffs to reduce storage cost at scale.

---

## 16. Glossary

| Term | Definition |
|---|---|
| **Site** | A website container grouping pages under one organization. |
| **Page** | A routable page with a fixed structure of section and block placements. |
| **SectionTemplate** | A reusable, platform-wide layout definition (e.g., hero, features, footer). Holds no content. |
| **BlockTemplate** | A reusable, platform-wide schema definition for a content block. Holds field definitions and default content, but no live content. |
| **PageSectionPlacement** | A record attaching a SectionTemplate to a specific Page. Carries order, visibility, and config overrides. Belongs to exactly one page. |
| **SectionBlockPlacement** | The core content container. Attaches a BlockTemplate to a PageSectionPlacement and carries draft_content, published_content, and status. Belongs to exactly one section placement. |
| **Schema** | The JSONB definition on a BlockTemplate specifying what fields exist — types, constraints, flags. Immutable by admins. |
| **draft_content** | The working JSONB on a SectionBlockPlacement. Editable by admins. Served by the admin API. |
| **published_content** | The frozen JSONB on a SectionBlockPlacement. Set only during the publish transaction. Served by the public API. |
| **SchemaValidator** | The server-side validation engine that checks content JSONB against a BlockTemplate's schema. Runs permissively on draft save, strictly on publish. |
| **Repeater** | A field type that holds an ordered list of structured objects, each conforming to a sub-schema. |
| **Superuser** | A developer or platform administrator who defines CMS structure via templates and placements. Works through Django Admin. |
| **Admin** | An organization user who populates draft_content within fixed structures. Cannot modify templates, schemas, or structural placements. |
| **ContentVersion** | A historical snapshot of block placement draft_content, enabling rollback. Subject to retention limits and save throttling. |
| **MediaUsage** | A tracking record linking a media file to the block placement, field, and content layer that references it. |
| **Tombstoned** | A media file state indicating it has been deleted from the library but remains in storage because published content still references it. Cleaned up after re-publish. |
| **Publish Transaction** | The atomic database operation that validates all draft_content on a page and copies it to published_content. Uses row-level locking for concurrency safety. |
| **Schema Version** | An integer on BlockTemplate that increments on every schema change. Used to identify block placements affected by schema modifications. |
| **Optimistic Locking** | A future concurrency control strategy where the API checks `updated_at` timestamps on save to detect and reject conflicting concurrent edits. |

---

*This document serves as the authoritative specification for the ARENA-Z CMS system (v3.0). All implementation — models, serializers, views, admin configuration, and API endpoints — should conform to the architecture described here. This version incorporates the placement-as-instance architecture (eliminating content leakage by construction), transactional publish with row-level locking, public/admin API separation, UUID-based placement endpoints, concrete schema validation engine, storage-key-based media architecture, and ContentVersion cost controls.*
