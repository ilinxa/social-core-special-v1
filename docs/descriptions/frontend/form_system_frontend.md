# Form System — Frontend High-Level Description

> **Status:** Description (pre-plan)
> **Date:** 2026-03-04
> **Scope:** Frontend implementation for form management, library, form builder, and responses dashboard
> **Depends on:** Frontend Foundation, RBAC system, Member Quota system
> **Related (future):** Transaction UI (form-transaction assignment lives there, not here)

---

## 1. Overview

The Form System frontend provides organization members with tools to create, manage, and
analyze dynamic forms. It is built on top of a **complete backend** (22 field types, versioning,
forking, typed indexing, transaction integration) and leverages the existing **3-tier
authorization** infrastructure for permission-aware UI.

### Core Principles

| Principle | Implementation |
|-----------|---------------|
| **Solo accounts excluded** | Entire Forms section hidden when `max_members <= 1` via `minMembers: 2` on nav item |
| **Permission-aware everywhere** | Nav gating (Tier 1), API `_permissions` (Tier 1.5), Guards (Tier 2), Backend policies (Tier 3) |
| **Consistent with app patterns** | Uses existing guards, `<Can>` component, `useFilteredNav`, membership store |
| **Reusable form builder** | Single comprehensive component covering all 21 backend field types |

---

## 2. Routes

All routes exist in two contexts — business console and platform console:

| Route | Business Console | Platform Console |
|-------|-----------------|-----------------|
| Dashboard | `/bconsole/[slug]/forms/` | `/pconsole/forms/` |
| Templates list | `/bconsole/[slug]/forms/templates` | `/pconsole/forms/templates` |
| Template detail | `/bconsole/[slug]/forms/templates/[id]` | `/pconsole/forms/templates/[id]` |
| Create template | `/bconsole/[slug]/forms/templates/new` | `/pconsole/forms/templates/new` |
| Library | `/bconsole/[slug]/forms/library` | `/pconsole/forms/library` |
| Responses dashboard | `/bconsole/[slug]/forms/responses` | `/pconsole/forms/responses` |
| Response detail | `/bconsole/[slug]/forms/responses/[id]` | `/pconsole/forms/responses/[id]` |

### Route Protection

| Layer | Mechanism | Already Built |
|-------|-----------|--------------|
| Authentication | `AuthGuard` wraps all `(app)` routes | Yes |
| Account membership | `BusinessGuard` / `PlatformGuard` with retry-on-miss | Yes |
| Member quota | `minMembers: 2` on nav config hides section for solo accounts | Yes |
| Permission | `permission` field on nav items filters by RBAC codes | Yes |

---

## 3. Navigation Configuration

### Nav Item (in `navigation-config.ts`)

The Forms section is a **new nav section** with sub-items. The section-level item gates
the entire group:

```
Section: "Forms"
  minMembers: 2
  permission: (any form permission — see dashboard visibility logic)

  Items:
    - Templates    → /forms/templates      permission: can_create_form | can_edit_form | can_delete_form
    - Library      → /forms/library        permission: can_create_form
    - Responses    → /forms/responses      permission: can_view_responses
```

**Note:** The section-level visibility requires the user to have **any** of the 6 form
permissions (`can_create_form`, `can_edit_form`, `can_delete_form`, `can_view_responses`,
`can_export_responses`, `can_process_response`). The individual items within the section
are filtered by their specific permission gates.

---

## 4. Pages

### 4.1 Forms Dashboard (`/forms/`)

**Purpose:** Landing page with bento grid / card panel summarizing each sub-section.

**Visibility rule:** Each card is visible only if the user has the relevant permission.
Hidden cards are removed from the layout (not disabled), consistent with the rest of the app.

| Card | Visible When | Navigates To | Summary Content |
|------|-------------|--------------|-----------------|
| **Templates** | `can_create_form` OR `can_edit_form` OR `can_delete_form` | `/forms/templates` | Form count, active count, recent activity |
| **Library** | `can_create_form` | `/forms/library` | "Browse public templates" |
| **Responses** | `can_view_responses` | `/forms/responses` | Submission count, pending processing count |

**Data source:** Lightweight API calls (template list count, response list count) or
single dashboard summary endpoint (to be determined at plan phase).

### 4.2 Templates List (`/forms/templates`)

**Purpose:** Browse and manage the organization's form templates.

**Permission gate:** `can_create_form` OR `can_edit_form` OR `can_delete_form`

**Layout:**
- Tab bar: **All** | **Active** | **Archived** (filters by `status`)
- Each row shows: name, status badge, version, scope, created date, updated date
- "New Form" button (visible if `can_create_form`) → navigates to `/forms/templates/new`
- Row click → navigates to `/forms/templates/[id]`

**Backend endpoint:** `GET /api/v1/forms/<account_type>/<account_id>/templates/`

**API fields returned (FormTemplateListOutput):**

| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary key |
| `name` | string | Display name |
| `slug` | string | URL-safe identifier |
| `description` | string | Short description |
| `owner_type` | enum | `business` / `platform` / `system` |
| `scope` | enum | `business` / `platform` |
| `status` | enum | `draft` / `active` / `archived` / `deleted` |
| `version` | integer | Version number |
| `is_current` | boolean | Whether this is the latest version |
| `is_template_public` | boolean | Whether visible in public library |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |

### 4.3 Template Detail (`/forms/templates/[id]`)

**Purpose:** View and edit a single form template — metadata, fields, lifecycle actions.

**Permission gate:** Any form permission (read access). Write actions gated by `_permissions`.

**Backend endpoint:** `GET /api/v1/forms/templates/<form_id>/`

**Permission-Aware Response (Tier 1.5):**

The GET response includes `_permissions` dict:

```json
{
  "id": "...",
  "name": "My Form",
  "fields": [...],
  "_permissions": {
    "can_edit": true,
    "can_delete": false,
    "can_publish": true,
    "can_archive": false
  }
}
```

**UI actions gated by `_permissions`:**

| Action | Gated by | Backend endpoint | Condition |
|--------|----------|-----------------|-----------|
| Edit name/description/settings | `can_edit` | `PATCH /templates/<id>/` | Status is DRAFT or ACTIVE |
| Add/edit/reorder/remove fields | `can_edit` | `POST /templates/<id>/fields/` | Status is DRAFT or ACTIVE |
| Publish (DRAFT → ACTIVE) | `can_publish` | `POST /templates/<id>/publish/` | Status is DRAFT |
| Archive (ACTIVE → ARCHIVED) | `can_archive` | `POST /templates/<id>/archive/` | Status is ACTIVE |
| Delete | `can_delete` | `PATCH /templates/<id>/` (soft) | Not a system form |
| Toggle public visibility | `can_edit` | `PATCH /templates/<id>/` | — |
| Read-only view | Always | — | Fallback when no write permissions |

**Versioning behavior:**
- Editing an **ACTIVE** form creates a new version automatically (backend handles this)
- The UI should display the version number and optionally link to parent version
- `is_current` indicates the live version; non-current versions are historical

**API fields returned (FormTemplateDetailOutput):**

All list fields, plus: `owner_id`, `parent_version`, `forked_from`, `forked_from_name`,
`settings` (JSON), `fields` (nested array of FormFieldOutput)

### 4.4 Create Form (`/forms/templates/new`)

**Purpose:** Create a new form template with the form builder.

**Permission gate:** `can_create_form`

**Backend endpoint:** `POST /api/v1/forms/<account_type>/<account_id>/templates/`

**Flow:**
1. Enter metadata: name, description, scope (business/platform)
2. Build fields using the **Form Builder Component** (Section 6)
3. Save as DRAFT
4. Optionally publish immediately

**Input fields (FormTemplateCreateInput):**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | |
| `slug` | string | No | Auto-generated from name if omitted |
| `description` | string | No | |
| `owner_type` | enum | Yes | `business` or `platform` (set from context) |
| `owner_id` | UUID | No | Set from current account context |
| `scope` | enum | Yes | `business` or `platform` |
| `settings` | JSON | No | Form-level metadata |

### 4.5 Library (`/forms/library`)

**Purpose:** Browse publicly shared form templates from other organizations. Fork templates
into your own org as a starting point.

**Permission gate:** `can_create_form` (forking requires create permission)

**Backend endpoint:** `GET /api/v1/forms/templates/library/`

**Layout:**
- Search/filter by scope, name
- Card or list view showing template name, description, scope, owner
- "Fork" button on each template → creates copy as DRAFT in your org
- Fork endpoint: `POST /api/v1/forms/templates/<form_id>/fork/`

**Fork input (ForkTemplateInput):**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `new_owner_type` | enum | Yes | `business` or `platform` |
| `new_owner_id` | UUID | Yes | Target account ID |
| `new_name` | string | No | Override name (defaults to source name) |
| `new_slug` | string | No | Override slug (auto-deduplicates) |

### 4.6 Responses Dashboard (`/forms/responses`)

**Purpose:** Browse, filter, and manage form submissions across all org forms.

**Permission gate:** `can_view_responses`

**Backend endpoints:**
- `GET /api/v1/forms/templates/<form_id>/responses/` — responses for a specific form
- `GET /api/v1/forms/responses/<response_id>/` — single response detail

**Combinable Filters:**

| Filter | Type | Source | Notes |
|--------|------|--------|-------|
| Form template | Select dropdown | Org's form templates | Primary filter |
| Transaction type | Select dropdown | Transaction types enum | Filter by linked transaction type |
| Submitter (user) | Search / autocomplete | User lookup | Filter by who submitted |
| Status | Multi-select | `draft` / `submitted` / `processed` / `void` / `expired` | |
| Date range | Date picker (from/to) | `submitted_at` or `created_at` | |
| **Indexed field values** | Dynamic (varies by field type) | Selected form's indexed fields | **Appears after form template is selected** |

**Dynamic indexed field filters:**

When a form template is selected, the dashboard queries its indexed fields and renders
appropriate filter inputs based on field type:

| Storage Type | Filter UI | Index Table |
|-------------|-----------|-------------|
| TEXT | Text search input | `TextFieldIndex` |
| INTEGER | Number range (min/max) | `IntegerFieldIndex` |
| DECIMAL | Number range (min/max) | `DecimalFieldIndex` |
| BOOLEAN | Checkbox / toggle | `BooleanFieldIndex` |
| DATE | Date range picker | `DateFieldIndex` |
| DATETIME | DateTime range picker | `DateTimeFieldIndex` |

**Maximum 5 indexed fields per form** (backend enforced). Non-indexable types (JSON storage:
multiselect, checkbox_group, file, image, location, repeatable) cannot be filtered.

**Response list fields (FormResponseListOutput):**

| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary key |
| `form_template` | UUID | Form template ID |
| `form_name` | string | Denormalized form name |
| `form_version` | integer | Version at submission time |
| `submitted_by` | UUID | Submitter user ID |
| `submitter_email` | string | Denormalized submitter email |
| `status` | enum | Current response status |
| `submitted_at` | datetime | When submitted |
| `processed_at` | datetime | When processed (null if pending) |
| `created_at` | datetime | When draft was created |

**In-page action permissions:**

| Action | Gated by | Backend endpoint |
|--------|----------|-----------------|
| View response detail | `can_view_responses` | `GET /responses/<id>/` |
| Process response | `can_process_response` | `POST /responses/<id>/process/` |
| Void response | `can_process_response` | `POST /responses/<id>/void/` |
| Export responses | `can_export_responses` | (future — not yet built) |

### 4.7 Response Detail (`/forms/responses/[id]`)

**Purpose:** View a single form response — submitted data, revision history, processing.

**Backend endpoint:** `GET /api/v1/forms/responses/<response_id>/`

**Response detail fields (FormResponseDetailOutput):**

| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary key |
| `form_template` | UUID | Form template ID |
| `form_name` | string | Denormalized form name |
| `form_version` | integer | Version at submission time |
| `submitted_by` | UUID | Submitter user ID |
| `submitter_email` | string | Denormalized |
| `submitter_context` | JSON | ActorContext snapshot |
| `data` | JSON | Complete response data (field_key → value) |
| `status` | enum | Current status |
| `submitted_at` | datetime | |
| `processed_at` | datetime | |
| `processed_by` | UUID | Processor user ID |
| `processor_email` | string | Denormalized |
| `processor_notes` | string | Processing notes |
| `created_at` | datetime | |
| `updated_at` | datetime | |

**Display:** The response data should be rendered using the form template's field definitions
to show proper labels, types, and formatting — not raw JSON.

**Revision history:** If the response has `revision > 1`, show revision history (previous
submissions for INFO_REQUESTED workflow).

---

## 5. Form Statuses & Lifecycles

### 5.1 Form Template Lifecycle

```
  ┌───────┐     publish      ┌────────┐     archive     ┌──────────┐
  │ DRAFT │ ───────────────► │ ACTIVE │ ──────────────► │ ARCHIVED │
  └───────┘                  └────────┘                  └──────────┘
      │                          │                            │
      │         delete           │         delete             │    delete
      ▼                          ▼                            ▼
  ┌─────────┐              ┌─────────┐                  ┌─────────┐
  │ DELETED │              │ DELETED │                  │ DELETED │
  └─────────┘              └─────────┘                  └─────────┘
```

- **DRAFT:** Editable, not accepting responses
- **ACTIVE:** Accepting responses, editing creates new version (immutability)
- **ARCHIVED:** Read-only, not accepting responses, existing responses preserved
- **DELETED:** Soft-deleted, hidden from all views

### 5.2 Form Response Lifecycle

```
  ┌───────┐     submit       ┌───────────┐     process     ┌───────────┐
  │ DRAFT │ ───────────────► │ SUBMITTED │ ──────────────► │ PROCESSED │
  └───────┘                  └───────────┘                  └───────────┘
      │                          │
      │           void           │         void
      ▼                          ▼
  ┌──────┐                  ┌──────┐
  │ VOID │                  │ VOID │
  └──────┘                  └──────┘

  Special: SUBMITTED ──(info_requested)──► revision cycle ──► SUBMITTED (updated)
  Special: any ──(expiry)──► EXPIRED
```

- **DRAFT:** Being filled out, editable by submitter
- **SUBMITTED:** Awaiting processing, triggers index extraction
- **PROCESSED:** Handled by authorized member, with processor notes
- **VOID:** Rejected/cancelled
- **EXPIRED:** Time-expired (system-managed)

---

## 6. Form Builder Component (Reusable)

### 6.1 Purpose

A comprehensive, reusable component that covers **all 21 backend field types**. Used in:
- Create form page (`/forms/templates/new`)
- Edit form page (`/forms/templates/[id]` when `can_edit`)
- Response rendering (read-only mode for viewing submitted data)
- Response filling (input mode for submitters — used by transaction flows)

### 6.2 Field Types (22 total)

The form builder must support rendering and configuring all field types:

#### Text Input Fields (8 types)

| Field Type | Input Component | Indexable | Storage |
|-----------|----------------|-----------|---------|
| `text` | Text input | Yes | TEXT |
| `textarea` | Multi-line textarea | Yes | TEXT |
| `email` | Email input (with validation) | Yes | TEXT |
| `url` | URL input (with validation) | Yes | TEXT |
| `phone` | Phone input (with formatting) | Yes | TEXT |
| `select` | Select dropdown | Yes | TEXT |
| `radio` | Radio button group | Yes | TEXT |
| `time` | Time picker | Yes | TEXT |

#### Numeric Fields (4 types)

| Field Type | Input Component | Indexable | Storage |
|-----------|----------------|-----------|---------|
| `integer` | Number input (whole numbers) | Yes | INTEGER |
| `decimal` | Number input (decimal places) | Yes | DECIMAL |
| `currency` | Currency input (with symbol) | Yes | DECIMAL |
| `rating` | Star/number rating | Yes | INTEGER |

#### Boolean Fields (2 types)

| Field Type | Input Component | Indexable | Storage |
|-----------|----------------|-----------|---------|
| `boolean` | Toggle switch | Yes | BOOLEAN |
| `checkbox` | Single checkbox | Yes | BOOLEAN |

#### Date/Time Fields (2 types)

| Field Type | Input Component | Indexable | Storage |
|-----------|----------------|-----------|---------|
| `date` | Date picker | Yes | DATE |
| `datetime` | DateTime picker | Yes | DATETIME |

#### Multi-Value Fields (2 types — NOT indexable)

| Field Type | Input Component | Indexable | Storage |
|-----------|----------------|-----------|---------|
| `multiselect` | Multi-select dropdown | No | JSON |
| `checkbox_group` | Checkbox group | No | JSON |

#### File Fields (2 types — NOT indexable)

| Field Type | Input Component | Indexable | Storage |
|-----------|----------------|-----------|---------|
| `file` | File upload | No | JSON |
| `image` | Image upload (with preview) | No | JSON |

#### Complex Fields (1 type — NOT indexable)

| Field Type | Input Component | Indexable | Storage |
|-----------|----------------|-----------|---------|
| `location` | Location picker / coordinates | No | JSON |

#### Structural Fields (1 type — NOT indexable)

| Field Type | Input Component | Indexable | Storage |
|-----------|----------------|-----------|---------|
| `repeatable` | Repeatable field group | No | JSON |

### 6.3 Field Configuration (per field)

Each field in the builder has these configurable properties:

| Property | Type | Purpose |
|----------|------|---------|
| `field_key` | string | Machine-readable key (unique per form) |
| `field_type` | enum (21 types) | Determines input component |
| `label` | string | Human-readable label shown to users |
| `description` | string | Help text shown below field |
| `placeholder` | string | Placeholder text in input |
| `order` | integer | Display position (drag-and-drop reorder) |
| `step_tag` | string | Groups fields into wizard steps |
| `section_tag` | string | Visual grouping within a step |
| `options` | JSON array | Choices for select/radio/multiselect/checkbox_group |
| `validation_rules` | JSON | Rules: min_length, max_length, min_value, max_value, pattern, etc. |
| `ui_config` | JSON | Layout hints: width, columns, custom styling |
| `default_value` | JSON | Pre-filled value |
| `is_required` | boolean | Enforced at submit time |
| `is_indexed` | boolean | Stored in typed index table (max 5 per form, indexable types only) |
| `is_hidden` | boolean | System/internal field, not shown in UI |
| `is_readonly` | boolean | Displayed but not editable by submitter |

### 6.4 Builder Modes

The form builder component operates in **four modes**:

| Mode | Context | Behavior |
|------|---------|----------|
| **Design** | Template create/edit | Add, configure, reorder, remove fields. Full field config panel. |
| **Preview** | Template detail (read-only) | Shows field layout as end users would see it. No interaction. |
| **Fill** | Response creation (submitter) | Interactive inputs for filling out the form. Validates on submit. |
| **View** | Response detail (viewer) | Shows submitted data with field labels. Read-only. |

### 6.5 Structural Features

**Step support (`step_tag`):**
- Fields with the same `step_tag` are grouped into a wizard step
- Step navigation: next/previous/step indicator
- If no `step_tag` on any field → single-page form (no wizard)

**Section support (`section_tag`):**
- Fields with the same `section_tag` within a step are visually grouped
- Rendered with a section header / card wrapper
- If no `section_tag` → flat field list

**Field ordering:**
- In **Design** mode: drag-and-drop reorder (updates `order` field)
- In all other modes: fields rendered in `order` sequence

### 6.6 Validation

**Design-time validation (builder):**
- `field_key` must be unique per form
- `is_indexed` only allowed on indexable storage types
- Max 5 indexed fields per form
- `options` required for select/radio/multiselect/checkbox_group

**Submit-time validation (response filling):**
- `is_required` fields must have non-empty values
- Type-specific validation from `validation_rules` (min/max length, patterns, etc.)
- Client-side validation mirrors backend rules for immediate feedback

---

## 7. Permission Matrix

### 7.1 RBAC Permissions (Backend — 6 codes)

| Code | Name | Category | Scopes |
|------|------|----------|--------|
| `can_create_form` | Create Form | forms | business, platform_only |
| `can_edit_form` | Edit Form | forms | business, platform_only, global_only |
| `can_delete_form` | Delete Form | forms | business, platform_only, global_only |
| `can_view_responses` | View Responses | forms | business, platform_only, global_only |
| `can_export_responses` | Export Responses | forms | business, platform_only, global_only |
| `can_process_response` | Process Response | forms | business, platform_only, global_only |

### 7.2 Frontend Permission Usage

| Feature | Tier | Mechanism | Permission(s) |
|---------|------|-----------|---------------|
| Forms nav section visible | Tier 1 | `useFilteredNav` + `minMembers: 2` | Any form permission |
| Templates nav item visible | Tier 1 | `useFilteredNav` permission gate | `can_create_form` OR `can_edit_form` OR `can_delete_form` |
| Library nav item visible | Tier 1 | `useFilteredNav` permission gate | `can_create_form` |
| Responses nav item visible | Tier 1 | `useFilteredNav` permission gate | `can_view_responses` |
| Dashboard card visibility | Tier 1 | `<Can>` or conditional render | Same as respective nav items |
| Edit/Publish/Archive buttons | Tier 1.5 | `<Can allowed={_permissions.can_edit}>` | Via `_permissions` from API |
| Delete button | Tier 1.5 | `<Can allowed={_permissions.can_delete}>` | Via `_permissions` from API |
| Process/Void response | Tier 1.5 | `<Can>` + permission check | `can_process_response` |
| Export button | Tier 1.5 | `<Can>` + permission check | `can_export_responses` |
| Route access | Tier 2 | BusinessGuard / PlatformGuard | Membership required |
| All write operations | Tier 3 | Backend policy enforcement | RBAC permission checks |

### 7.3 Visibility Summary by Role

| Feature | Owner | Admin (all form perms) | Member (view_responses only) | Member (no form perms) |
|---------|-------|----------------------|----------------------------|----------------------|
| Forms nav section | Visible | Visible | Visible | Hidden |
| Dashboard | Visible | Visible | Visible (1 card) | Hidden |
| Templates card | Visible | Visible | Hidden | Hidden |
| Library card | Visible | Visible | Hidden | Hidden |
| Responses card | Visible | Visible | Visible | Hidden |
| Create form | Yes | Yes | No | No |
| Edit form | Yes | Yes | No | No |
| Delete form | Yes | Yes | No | No |
| Publish/Archive | Yes | Yes | No | No |
| Fork from library | Yes | Yes | No | No |
| View responses | Yes | Yes | Yes | No |
| Process responses | Yes | Yes | No | No |
| Export responses | Yes | Yes | No | No |

---

## 8. Backend API Reference

### 8.1 Endpoints (13 total)

#### Template Management

| Method | Endpoint | View | Purpose |
|--------|----------|------|---------|
| `POST` | `/api/v1/forms/<account_type>/<account_id>/templates/` | FormTemplateListView | Create template |
| `GET` | `/api/v1/forms/<account_type>/<account_id>/templates/` | FormTemplateListView | List org templates |
| `GET` | `/api/v1/forms/templates/library/` | PublicTemplateLibraryView | Browse public templates |
| `GET` | `/api/v1/forms/templates/<form_id>/` | FormTemplateDetailView | Get template detail + `_permissions` |
| `PATCH` | `/api/v1/forms/templates/<form_id>/` | FormTemplateDetailView | Update template |
| `POST` | `/api/v1/forms/templates/<form_id>/publish/` | FormTemplatePublishView | Publish draft |
| `POST` | `/api/v1/forms/templates/<form_id>/archive/` | FormTemplateArchiveView | Archive active form |
| `POST` | `/api/v1/forms/templates/<form_id>/fork/` | FormTemplateForkView | Fork public template |
| `POST` | `/api/v1/forms/templates/<form_id>/fields/` | FormFieldAddView | Add field to template |

#### Response Management

| Method | Endpoint | View | Purpose |
|--------|----------|------|---------|
| `GET` | `/api/v1/forms/templates/<form_id>/responses/` | FormResponseListView | List responses for form |
| `GET` | `/api/v1/forms/responses/<response_id>/` | FormResponseDetailView | Get response detail |
| `PATCH` | `/api/v1/forms/responses/<response_id>/` | FormResponseDetailView | Update response data |
| `POST` | `/api/v1/forms/responses/<response_id>/submit/` | FormResponseSubmitView | Submit response |
| `POST` | `/api/v1/forms/responses/<response_id>/process/` | FormResponseProcessView | Process response |
| `POST` | `/api/v1/forms/responses/<response_id>/void/` | FormResponseVoidView | Void response |
| `GET` | `/api/v1/forms/me/responses/` | MyResponsesView | User's own responses |

### 8.2 Missing Endpoints (May Need Backend Work)

| Feature | Current State | Needed For |
|---------|--------------|------------|
| Field update (`PATCH` field) | Not exposed — fields added via `POST`, no update endpoint | Field editing in builder |
| Field delete | Not exposed | Removing fields in builder |
| Field reorder (bulk) | Not exposed | Drag-and-drop reorder |
| Response filtering by index values | Not exposed as query params | Responses Dashboard indexed field filters |
| Dashboard summary (counts) | Not exposed | Dashboard cards showing counts |
| Template search/filter | Not exposed as query params on list | Library search, templates list filtering |

> **Note:** These gaps should be addressed during the planning phase. The backend service
> layer supports most of these operations — they just need API endpoints exposed.

---

## 9. Frontend Architecture

### 9.1 Feature Folder Structure (Proposed)

```
frontend/src/features/forms/
├── api/
│   ├── forms-api.ts              # API functions (typed wrappers)
│   └── forms-api.test.ts
├── hooks/
│   ├── use-form-queries.ts       # TanStack Query hooks
│   ├── use-form-mutations.ts     # Mutation hooks (create, update, publish, etc.)
│   └── *.test.ts
├── components/
│   ├── form-builder/             # Reusable form builder (Section 6)
│   │   ├── FormBuilder.tsx       # Main builder component (4 modes)
│   │   ├── FieldRenderer.tsx     # Maps field_type → input component
│   │   ├── FieldConfigPanel.tsx  # Side panel for field settings
│   │   ├── StepNavigation.tsx    # Wizard step navigation
│   │   ├── SectionWrapper.tsx    # Visual section grouping
│   │   ├── fields/               # One component per field type
│   │   │   ├── TextField.tsx
│   │   │   ├── TextareaField.tsx
│   │   │   ├── EmailField.tsx
│   │   │   ├── SelectField.tsx
│   │   │   ├── RadioField.tsx
│   │   │   ├── DateField.tsx
│   │   │   ├── FileField.tsx
│   │   │   ├── RatingField.tsx
│   │   │   ├── LocationField.tsx
│   │   │   ├── RepeatableField.tsx
│   │   │   └── ... (all 21 types)
│   │   └── form-builder.test.tsx
│   ├── TemplateCard.tsx          # Card for template list/library
│   ├── ResponseRow.tsx           # Row for response list
│   ├── ResponseFilters.tsx       # Combinable filter panel
│   ├── IndexedFieldFilter.tsx    # Dynamic filter per indexed field type
│   └── DashboardCard.tsx         # Bento grid card
├── types/
│   └── forms.ts                  # TypeScript types matching backend serializers
└── validations/
    └── form-template.ts          # Zod schemas for client-side validation
```

### 9.2 Type Definitions (Matching Backend Serializers)

```typescript
// Form Template types
type FormStatus = "draft" | "active" | "archived" | "deleted";
type OwnerType = "system" | "platform" | "business";
type FormScope = "business" | "platform";
type ResponseStatus = "draft" | "submitted" | "processed" | "void" | "expired";

type FieldType =
  | "text" | "textarea" | "email" | "url" | "phone"
  | "integer" | "decimal" | "currency" | "rating"
  | "boolean" | "checkbox"
  | "date" | "datetime" | "time"
  | "select" | "radio" | "multiselect" | "checkbox_group"
  | "file" | "image"
  | "location" | "repeatable";

// Permission type for Tier 1.5
type FormTemplatePermissions = {
  can_edit: boolean;
  can_delete: boolean;
  can_publish: boolean;
  can_archive: boolean;
};
```

### 9.3 State Management Pattern

| Concern | Tool | Pattern |
|---------|------|---------|
| Server data (templates, responses) | TanStack Query | Query + mutation hooks |
| Current membership / permissions | Zustand (membership-store) | Already built |
| Form builder local state | React state (useState/useReducer) | Component-local |
| URL state (filters, tabs) | URL search params | Consistent with Explore system |

---

## 10. Cross-System Dependencies

### 10.1 What This System Uses (Already Built)

| System | What We Use | How |
|--------|------------|-----|
| **Auth** | `AuthGuard`, access token | Route protection, API calls |
| **RBAC** | Permission codes, membership store | Nav gating, `<Can>` component |
| **Organization** | Account context (business/platform) | Scope for form ownership |
| **Member Quota** | `minMembers` nav filter | Hide entire Forms section for solo accounts |
| **Frontend Foundation** | Guards, nav config, API layer, error handling | All infrastructure |

### 10.2 What Uses This System (Future)

| System | What They Use | How |
|--------|-------------|-----|
| **Transaction UI** | Form builder (Fill mode) | Submitters fill forms during transaction flow |
| **Transaction UI** | Form-Transaction assignment | Config panel to connect forms to transaction types |
| **Transaction UI** | Response viewer (View mode) | Reviewers see submitted form data |
| **Member Management UI** | Response viewer (View mode) | Member detail page shows submitted form responses |

### 10.3 Backend Gaps to Address Before/During Planning

| Gap | Impact | Suggested Resolution |
|-----|--------|---------------------|
| No field update/delete endpoints | Can't edit existing fields in builder | Add `PATCH`/`DELETE` on `/fields/<field_id>/` |
| No field reorder endpoint | Can't drag-and-drop reorder | Add bulk `PATCH` for field ordering |
| No response index filtering | Responses Dashboard can't filter by field values | Add query params on response list endpoint |
| No dashboard summary endpoint | Dashboard cards need counts | Add lightweight summary endpoint or use list with `?limit=0` |
| No template search/filter params | Library search, template list filtering | Add `?search=`, `?status=`, `?scope=` query params |

---

## 11. Relationship to Transaction UI (Future — Not In Scope Here)

The Form-Transaction assignment feature lives in the **Transaction UI**, not in the Forms section.
It is documented here only to clarify the boundary.

**What the Transaction UI will need from the Form system:**
- Form builder in **Fill** mode — for submitters to fill forms during transaction flows
- Form builder in **View** mode — for reviewers to see submitted data
- Form template selector — for the assignment config panel
- Form response status tracking — to show form completion state within transaction detail

**What requires new backend work (for Transaction UI):**
- `TransactionFormMapping` model — per-account configuration of which form is used for which
  transaction type (currently hard-coded in `TransactionTypeConfig` dataclass)
- API endpoints for CRUD on form-transaction mappings
- Validation that provided form matches configured transaction type

This will be described in the **Transaction UI high-level description** (next document).
