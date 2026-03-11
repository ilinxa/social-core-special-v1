# Form Builder System — Implementation Reference

**Version:** v2
**Last Updated:** 2026-02-24
**Status:** Implemented

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  API Layer (api/views.py)                                        │
│  13 views: TemplateList, TemplateDetail, Publish, Archive, Fork, │
│            PublicLibrary, FieldAdd, ResponseList, ResponseDetail, │
│            ResponseSubmit, ResponseProcess, ResponseVoid,         │
│            MyResponses                                            │
│  FormViewMixin → resolves Membership + ActorContext per policy    │
├──────────────────────────────────────────────────────────────────┤
│  Serializers (api/serializers.py)                                │
│  8 input + 6 output serializers                                  │
├──────────────────────────────────────────────────────────────────┤
│  Service Layer (services.py)                                     │
│  FormBuilderService: create, update, publish, archive, delete,   │
│                      fork, add_field + _create_new_version       │
│  FormResponseService: create, update, submit, process, void,     │
│                       create_and_submit, link_to_transaction,    │
│                       mark_info_requested, update_after_info_req │
├─────────────────────┬────────────────────────────────────────────┤
│  Policies            │  IndexService (indexing.py)                │
│  (policies.py)       │  extract_and_store, clear_indexes,         │
│  FormTemplatePolicy  │  rebuild_indexes, _coerce_value            │
│  (7 methods)         │  6 typed index tables                      │
│  FormResponsePolicy  │  INDEX_TABLE_MAP, FIELD_STORAGE_MAP        │
│  (4 methods)         │                                            │
├─────────────────────┴────────────────────────────────────────────┤
│  Selectors (selectors.py)                                        │
│  FormTemplateSelector (10) FormFieldSelector (4)                 │
│  FormResponseSelector (6)                                        │
├──────────────────────────────────────────────────────────────────┤
│  Managers (managers.py)                                          │
│  FormTemplateQuerySet (7 methods) + FormTemplateManager          │
│  FormResponseQuerySet (5 methods) + FormResponseManager          │
├──────────────────────────────────────────────────────────────────┤
│  Data Layer (models.py)                                          │
│  FormTemplate (UUID, audit, soft-delete, versioning)             │
│  FormField (UUID only, ordered, per-template unique key)         │
│  FormResponse (UUID, audit, soft-delete, state machine)          │
│  6 typed index tables (Text, Integer, Decimal, Boolean,          │
│                         Date, DateTime)                          │
├──────────────────────────────────────────────────────────────────┤
│  Constants                                                       │
│  core/constants.py: FormStatus, ResponseStatus, FieldType (22),  │
│                     StorageType (7), FormScope (2)                │
│  forms/constants.py: FIELD_STORAGE_MAP, INDEXABLE_STORAGE_TYPES, │
│                      MAX_INDEXED_FIELDS                          │
└──────────────────────────────────────────────────────────────────┘

External dependencies:
  → apps.rbac (RBACService, MembershipSelector, 6 form permissions)
  → apps.core (ActorContext, AuditService, exceptions, pagination)
  → apps.users (User model, FK references)
  → apps.transaction (TransactionSelector, TransactionStatus for cross-system queries)
```

---

## 2. Core Concepts & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Two-tier data storage | JSONB `data` field + typed index tables | All response data in JSONB for flexibility; indexed fields extracted to typed tables for efficient querying |
| Form versioning | Editing ACTIVE form creates new version; DRAFT edited in-place | Preserves response-to-schema fidelity — submitted responses always reference the exact version they were filled against |
| System form immutability | `owner_type=SYSTEM` blocks edit/delete/archive/fork via API | System forms (e.g., business verification) only modifiable via migrations |
| Max 5 indexed fields | Service-enforced limit per form template | Prevents index table bloat; covers primary query patterns |
| Hybrid service params | `actor_context` + `actor` (User) passed separately | ActorContext for permission checks and context JSON storage; User object for AuditService.log and FK fields |
| Selective indexing | Only TEXT, INTEGER, DECIMAL, BOOLEAN, DATE, DATETIME are indexable | JSON storage types (MULTISELECT, FILE, LOCATION, REPEATABLE) have no meaningful scalar index |
| Slug auto-generation | `slugify(name)` if no slug provided; collision auto-increment on fork | Ensures URL-friendly identifiers without manual input |
| FormField not AuditModel | FormField inherits only UUIDModel (no created_by/updated_by/soft-delete) | Fields are managed through their parent template's lifecycle — versioning copies fields |

---

## 3. Data Layer

### 3.1 FormTemplate

Location: `apps/forms/models.py`

Inherits: `UUIDModel` (UUID pk) + `AuditModel` (timestamps, created_by, updated_by, soft-delete)

| Field | Type | Notes |
|-------|------|-------|
| `name` | CharField(255) | Display name |
| `slug` | SlugField(100) | URL-friendly identifier, part of unique constraint |
| `description` | TextField | Optional, blank default |
| `owner_type` | CharField(20, choices=OwnerType) | SYSTEM, PLATFORM, BUSINESS; indexed |
| `owner_id` | UUIDField(null, blank) | NULL for system forms; indexed |
| `scope` | CharField(20, choices=FormScope) | PLATFORM or BUSINESS; indexed |
| `creator_context` | JSONField | `ActorContext.to_dict()` snapshot at creation |
| `status` | CharField(20, choices=FormStatus) | DRAFT → ACTIVE → ARCHIVED / DELETED; indexed |
| `version` | PositiveIntegerField | Starts at 1, incremented on versioning |
| `is_current` | BooleanField | Only one version per owner+slug is current; indexed |
| `parent_version` | FK(self, SET_NULL) | Links to previous version |
| `is_template_public` | BooleanField | If true, visible in public library; indexed |
| `forked_from` | FK(self, SET_NULL) | Links to source template |
| `settings` | JSONField | Form-level config (expiry, notifications) |

Constraints:
- `UniqueConstraint(owner_type, owner_id, slug, version)` — prevents duplicate versions
- 4 composite indexes for common query patterns

Managers:
- `objects` = `FormTemplateManager` (soft-delete + QuerySet delegation)
- `all_objects` = default Django Manager (includes soft-deleted)

Properties:
- `is_system_form` → `owner_type == OwnerType.SYSTEM`
- `is_editable` → not system AND status in [DRAFT, ACTIVE]
- `accepts_responses` → status == ACTIVE AND is_current == True

### 3.2 FormField

Location: `apps/forms/models.py`

Inherits: `UUIDModel` only

| Field | Type | Notes |
|-------|------|-------|
| `form_template` | FK(FormTemplate, CASCADE) | related_name="fields" |
| `field_key` | CharField(100) | Machine-readable identifier |
| `field_type` | CharField(50, choices=FieldType) | 22 types (text, email, integer, date, etc.) |
| `label` | CharField(255) | Display label |
| `description` | TextField | Help text |
| `placeholder` | CharField(255) | Input placeholder |
| `order` | PositiveIntegerField | Display order (lower first) |
| `step_tag` | CharField(50) | Groups fields into wizard steps |
| `section_tag` | CharField(50) | Visual grouping within a step |
| `options` | JSONField(default=list) | For select/radio/checkbox fields |
| `validation_rules` | JSONField(default=dict) | min_length, max_value, etc. |
| `ui_config` | JSONField(default=dict) | width, layout_hint, etc. |
| `default_value` | JSONField(null) | Default or dynamic token |
| `is_required` | BooleanField | Must have value on submit |
| `is_indexed` | BooleanField | Extracted to typed index table; indexed |
| `is_hidden` | BooleanField | System/internal field |
| `is_readonly` | BooleanField | Display-only field |

Constraints:
- `UniqueConstraint(form_template, field_key)` — unique key per form
- Default ordering: `[order]`

### 3.3 FormResponse

Location: `apps/forms/models.py`

Inherits: `UUIDModel` + `AuditModel`

| Field | Type | Notes |
|-------|------|-------|
| `form_template` | FK(FormTemplate, PROTECT) | Cannot delete template with responses |
| `form_version` | PositiveIntegerField | Captures version at submission time |
| `submitted_by` | FK(User, PROTECT) | Cannot delete user with responses |
| `submitter_context` | JSONField | ActorContext snapshot, refreshed on submit |
| `data` | JSONField | Complete response data |
| `status` | CharField(choices=ResponseStatus) | DRAFT → SUBMITTED → PROCESSED / VOID |
| `submitted_at` | DateTimeField(null) | Set on submit |
| `processed_at` | DateTimeField(null) | Set on process |
| `processed_by` | FK(User, SET_NULL, null) | Who processed |
| `processor_notes` | TextField | Notes from processor |
| `transaction_id` | UUIDField(null, blank, indexed) | Linked transaction UUID |
| `context_type` | CharField(20, blank) | Context type: platform, business, or user |
| `context_id` | UUIDField(null, blank) | Context account UUID |
| `revision` | PositiveIntegerField(default=1) | Revision number for info-request updates |
| `revision_history` | JSONField(default=list) | Previous revision snapshots |
| `info_requested_at` | DateTimeField(null, blank) | When additional info was last requested |

Properties:
- `is_editable` → status in [DRAFT, SUBMITTED]

### 3.4 Typed Index Tables

6 tables, all inheriting from `BaseFieldIndex(UUIDModel)`:

| Table | Value Type | Used By Field Types |
|-------|-----------|---------------------|
| `TextFieldIndex` | TextField | text, textarea, email, url, phone, select, radio, time |
| `IntegerFieldIndex` | BigIntegerField | integer, rating |
| `DecimalFieldIndex` | DecimalField(19,4) | decimal, currency |
| `BooleanFieldIndex` | BooleanField | boolean, checkbox |
| `DateFieldIndex` | DateField | date |
| `DateTimeFieldIndex` | DateTimeField | datetime |

Each has indexes on `(response, field_key)` and `(field_key, value)`.

### Migrations

- `core/0004_alter_auditlog_action.py` — Adds 16 form audit actions to AuditLog.Action choices
- `forms/0001_initial.py` — Creates all form models (3 core + 6 index tables) with constraints and indexes
- `forms/0002_add_transaction_integration.py` — Adds transaction_id, context_type, context_id, revision, revision_history, info_requested_at to FormResponse
- `forms/0003_seed_system_forms.py` — Seeds 3 system forms (system-business-verification, system-business-creation, system-platform-staff-application) with fields

---

## 4. Service Layer

### 4.1 FormBuilderService

Location: `apps/forms/services.py`

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `create_form_template` | actor_context, actor, name, slug?, description?, owner_type, owner_id?, scope, settings? | FormTemplate | Validates no system creation, auto-slug, uniqueness check. `@transaction.atomic` |
| `update_form_template` | form_template, updated_by, name?, description?, settings? | FormTemplate | If ACTIVE → creates new version; if DRAFT → updates in-place. `@transaction.atomic` |
| `publish_form` | form_template, published_by | FormTemplate | DRAFT → ACTIVE |
| `archive_form` | form_template, archived_by | FormTemplate | ACTIVE → ARCHIVED; blocks system forms |
| `delete_form` | form_template, deleted_by | FormTemplate | Sets DELETED status + soft_delete(); blocks system forms |
| `fork_template` | source_template, actor_context, actor, new_owner_type, new_owner_id, new_name?, new_slug? | FormTemplate | Copies fields, auto-resolves slug collisions; blocks non-public and system forms |
| `add_field` | form_template, added_by, field_key, field_type, label, order, ... | FormField | Validates editability, key uniqueness, indexing constraints |
| `_create_new_version` | form_template, updated_by, name?, description?, settings? | FormTemplate | Internal: marks old as not-current, creates v+1, copies all fields |

### 4.2 FormResponseService

Location: `apps/forms/services.py`

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `create_response` | form_template, actor_context, actor, data | FormResponse | Validates `accepts_responses`; status=DRAFT |
| `update_response` | response, updated_by, data | FormResponse | Validates `is_editable` |
| `submit_response` | response, actor_context, actor | FormResponse | Validates required fields, refreshes context, calls IndexService |
| `process_response` | response, processed_by, notes? | FormResponse | SUBMITTED → PROCESSED |
| `void_response` | response, voided_by, reason? | FormResponse | DRAFT/SUBMITTED → VOID |
| `create_and_submit` | form_template, data, context_type?, context_id?, actor_context, actor | FormResponse | Atomic create+submit for transaction-linked forms; validates required fields, extracts indexes |
| `link_to_transaction` | response_id, transaction_id | FormResponse | Sets bidirectional link; raises ConflictError if already linked to different txn |
| `mark_info_requested` | response_id, actor | FormResponse | Sets info_requested_at timestamp |
| `update_after_info_request` | response_id, data, actor_context, actor | FormResponse | Validates linked txn is INFO_REQUESTED, validates submitter, saves revision history, re-extracts indexes |

### 4.3 IndexService

Location: `apps/forms/indexing.py`

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `extract_and_store` | response | int (count) | Reads indexed fields from form_template, coerces values, creates typed index entries |
| `clear_indexes` | response | None | Deletes all index entries for a response across all 6 tables |
| `rebuild_indexes` | response | int (count) | Clears then re-extracts |
| `_coerce_value` | value, storage_type, field_key | coerced value or None | Handles TEXT→str, INTEGER→int, DECIMAL→Decimal, BOOLEAN→bool, DATE→date, DATETIME→datetime |

### 4.4 Selectors

Location: `apps/forms/selectors.py`

**FormTemplateSelector (10):**

| Method | Returns | Notes |
|--------|---------|-------|
| `get_by_id(form_template_id)` | FormTemplate | Raises NotFound |
| `get_by_id_or_none(form_template_id)` | Optional[FormTemplate] | |
| `get_by_slug(owner_type, owner_id, slug, current_only=True)` | FormTemplate | Raises NotFound |
| `get_by_slug_or_none(owner_type, owner_id, slug, current_only=True)` | Optional[FormTemplate] | Like get_by_slug but returns None |
| `get_current_version(form_template_id)` | FormTemplate | Follows version chain to current |
| `list_by_owner(owner_type, owner_id, status?, current_only=True)` | QuerySet | |
| `list_public_templates(scope?)` | QuerySet | Uses manager's `public_templates()` |
| `list_system_forms(scope?)` | QuerySet | |
| `get_with_fields(form_template_id)` | FormTemplate | prefetch_related("fields") |
| `count_indexed_fields(form_template_id)` | int | |

**FormFieldSelector:**

| Method | Returns | Notes |
|--------|---------|-------|
| `get_by_id(field_id)` | FormField | select_related("form_template") |
| `list_by_form(form_template_id, step_tag?)` | QuerySet | Ordered by `order` |
| `list_indexed_fields(form_template_id)` | QuerySet | |
| `get_step_tags(form_template_id)` | List[str] | Distinct, ordered by first occurrence |

**FormResponseSelector (6):**

| Method | Returns | Notes |
|--------|---------|-------|
| `get_by_id(response_id)` | FormResponse | select_related("form_template", "submitted_by") |
| `get_by_id_or_none(response_id)` | Optional[FormResponse] | |
| `list_by_form(form_template_id, status?)` | QuerySet | |
| `list_by_submitter(user_id, form_template_id?)` | QuerySet | select_related("form_template") |
| `exists_for_user_and_form(user_id, form_template_id, status?)` | bool | |
| `get_by_transaction_id(transaction_id)` | Optional[FormResponse] | select_related("form_template") |

---

## 5. API Layer

### 5.1 Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/{acct_type}/{acct_id}/templates/` | GET | IsAuthenticated + membership | List form templates for account |
| `/{acct_type}/{acct_id}/templates/` | POST | + can_create_form | Create form template |
| `/templates/{form_id}/` | GET | IsAuthenticated + membership (or public) | Get template detail with fields |
| `/templates/{form_id}/` | PATCH | + can_edit_form | Update template (versioning if active) |
| `/templates/{form_id}/` | DELETE | + can_delete_form | Soft-delete template |
| `/templates/{form_id}/publish/` | POST | + can_edit_form | DRAFT → ACTIVE |
| `/templates/{form_id}/archive/` | POST | + can_edit_form | ACTIVE → ARCHIVED |
| `/templates/{form_id}/fork/` | POST | + can_create_form | Fork public template to own account |
| `/templates/{form_id}/fields/` | POST | + can_edit_form | Add field to template |
| `/templates/library/` | GET | IsAuthenticated | Browse public template library |
| `/templates/{form_id}/responses/` | GET | + can_view_responses | List responses for form |
| `/templates/{form_id}/responses/` | POST | IsAuthenticated + membership | Create draft response |
| `/responses/{id}/` | GET | Owner or + can_view_responses | Get response detail |
| `/responses/{id}/` | PATCH | Owner only | Update response data |
| `/responses/{id}/submit/` | POST | Owner + membership | Submit response |
| `/responses/{id}/process/` | POST | + can_process_response | SUBMITTED → PROCESSED |
| `/responses/{id}/void/` | POST | Owner or + can_process_response | DRAFT/SUBMITTED → VOID |
| `/me/responses/` | GET | IsAuthenticated | List own responses across forms |

All endpoints prefixed with `/api/v1/forms/`.

### 5.2 Serializers

Location: `apps/forms/api/serializers.py`

**Input Serializers:**

| Serializer | Key Fields |
|------------|------------|
| `FormTemplateCreateInputSerializer` | name, slug?, description?, owner_type, owner_id?, scope, settings? |
| `FormTemplateUpdateInputSerializer` | name?, description?, settings? |
| `FormFieldCreateInputSerializer` | field_key, field_type, label, order, + 10 optional fields |
| `FormResponseCreateInputSerializer` | data (JSONField) |
| `FormResponseUpdateInputSerializer` | data (JSONField) |
| `FormResponseProcessInputSerializer` | notes? |
| `FormResponseVoidInputSerializer` | reason? |
| `ForkTemplateInputSerializer` | new_owner_type, new_owner_id, new_name?, new_slug? |

**Output Serializers:**

| Serializer | Key Fields |
|------------|------------|
| `FormFieldOutputSerializer` | All field attributes |
| `FormTemplateListOutputSerializer` | id, name, slug, status, version, is_current, timestamps |
| `FormTemplateDetailOutputSerializer` | All list fields + nested fields, settings, forked_from_name |
| `FormResponseListOutputSerializer` | id, form_name, submitter_email, status, timestamps |
| `FormResponseDetailOutputSerializer` | All list fields + data, processor_email, processor_notes |

---

## 6. Types & Constants

**Core enums** (`apps/core/constants.py`):

| Enum | Values |
|------|--------|
| `FormStatus` | DRAFT, ACTIVE, ARCHIVED, DELETED |
| `ResponseStatus` | DRAFT, SUBMITTED, PROCESSED, VOID, EXPIRED |
| `FieldType` | 22 types: text, textarea, email, url, phone, integer, decimal, currency, rating, boolean, checkbox, date, datetime, time, select, radio, multiselect, checkbox_group, file, image, location, repeatable |
| `StorageType` | TEXT, INTEGER, DECIMAL, BOOLEAN, DATE, DATETIME, JSON |
| `FormScope` | PLATFORM, BUSINESS |

**Forms constants** (`apps/forms/constants.py`):

| Constant | Description |
|----------|-------------|
| `FIELD_STORAGE_MAP` | Maps each FieldType → StorageType (22 entries) |
| `INDEXABLE_STORAGE_TYPES` | frozenset of TEXT, INTEGER, DECIMAL, BOOLEAN, DATE, DATETIME |
| `MAX_INDEXED_FIELDS` | 5 (per form template) |

---

## 7. Key Flows

### Flow 1: Create Form Template
1. View validates input, resolves membership + ActorContext
2. `FormTemplatePolicy.can_create_form()` checks permission
3. `FormBuilderService.create_form_template()` validates no system creation, generates slug, checks uniqueness
4. Creates FormTemplate with status=DRAFT, version=1, captures creator_context
5. AuditService logs FORM_TEMPLATE_CREATED

### Flow 2: Edit Active Form (Versioning)
1. View resolves form, membership, ActorContext
2. `FormTemplatePolicy.can_edit_form()` checks permission + not system
3. `FormBuilderService.update_form_template()` detects status=ACTIVE
4. Calls `_create_new_version()`: marks old as `is_current=False`, creates v+1 as ACTIVE
5. Copies all FormField records to new version
6. AuditService logs FORM_TEMPLATE_VERSIONED

### Flow 3: Submit Response
1. `FormResponsePolicy.can_edit_response()` checks ownership + editability
2. View resolves membership + ActorContext
3. `FormResponseService.submit_response()` validates status=DRAFT
4. Validates all required fields have values in response data
5. Refreshes submitter_context, sets status=SUBMITTED + submitted_at
6. `IndexService.extract_and_store()` extracts indexed field values to typed tables
7. AuditService logs FORM_RESPONSE_SUBMITTED

### Flow 4: Fork Public Template
1. Source template must be `is_template_public=True` and not system
2. `FormTemplatePolicy.can_fork_template()` checks can_create_form permission
3. `FormBuilderService.fork_template()` auto-resolves slug collisions (appends -1, -2, etc.)
4. Creates new DRAFT template with `forked_from` FK, copies all fields
5. AuditService logs FORM_TEMPLATE_FORKED

### Flow 5: Index Extraction
1. Called during `submit_response()` after status transition
2. `IndexService.extract_and_store()` queries all `is_indexed=True` fields for the form
3. For each indexed field with a non-null value in response data:
   - Looks up StorageType via `FIELD_STORAGE_MAP`
   - Coerces value to correct Python type (`_coerce_value`)
   - Creates entry in the appropriate typed index table
4. Returns count of entries created; logs warnings for coercion failures

### Flow 6: Transaction-Linked Form (Info Request Cycle)
1. User creates a form response via `FormResponseService.create_and_submit()` (atomic create + submit)
2. User creates a transaction (e.g., business_verification_request) with form_response_id
3. `TransactionService._validate_form_requirement()` validates template slug matches config
4. `TransactionService._link_form_response()` sets bidirectional link (FormResponse.transaction_id)
5. Reviewer requests more info → `TransactionService.request_info()` transitions PENDING → INFO_REQUESTED
6. Transaction service calls `FormResponseService.mark_info_requested()` on the linked response
7. User updates form data via `FormResponseService.update_after_info_request()`:
   - Validates transaction is INFO_REQUESTED
   - Validates original submitter
   - Saves current data to revision_history
   - Increments revision, re-extracts indexes
8. User calls `TransactionService.resubmit_after_info_request()` → INFO_REQUESTED → PENDING

---

## 8. Permissions & Authorization

| Action | RBAC Permission | Audit Action | Notes |
|--------|----------------|--------------|-------|
| Create form | `can_create_form` | `FORM_TEMPLATE_CREATED` | Business scope |
| Edit form | `can_edit_form` | `FORM_TEMPLATE_UPDATED` / `VERSIONED` | Also checks system form guard |
| Delete form | `can_delete_form` | `FORM_TEMPLATE_DELETED` | System forms blocked |
| Publish form | `can_edit_form` | `FORM_TEMPLATE_PUBLISHED` | System forms blocked |
| Archive form | `can_edit_form` | `FORM_TEMPLATE_ARCHIVED` | System forms blocked |
| Fork template | `can_create_form` | `FORM_TEMPLATE_FORKED` | Source must be public |
| Add field | `can_edit_form` | `FORM_FIELD_ADDED` | Form must be editable |
| View responses | `can_view_responses` | — | Form-level permission |
| Process response | `can_process_response` | `FORM_RESPONSE_PROCESSED` | |
| Export responses | `can_export_responses` | — | Not yet wired to a view |
| Create response | Membership required | `FORM_RESPONSE_CREATED` | No specific perm needed |
| Submit response | Response owner | `FORM_RESPONSE_SUBMITTED` | Membership for context |
| Update response | Response owner | `FORM_RESPONSE_UPDATED` | Must be editable |
| Void response | Owner or `can_process_response` | `FORM_RESPONSE_VOIDED` | Dual-path auth |
| Info request on txn | — | `TRANSACTION_INFO_REQUESTED` | Cross-system (triggered by TransactionService) |
| Resubmit after info | — | `TRANSACTION_RESUBMITTED` | Cross-system (triggered by TransactionService) |

---

## 9. Configuration & Gotchas

### Gotchas
- **Custom manager delegation**: `FormTemplateManager` overrides `get_queryset()`, which means Django does NOT auto-proxy QuerySet methods. Every QuerySet method used externally must be explicitly delegated on the manager class.
- **soft_delete() scope**: `soft_delete()` only persists `is_deleted`, `deleted_at`, `deleted_by`. Any other field changes (like `status=DELETED`) must be saved separately before calling `soft_delete()`.
- **FormTemplate.fields name collision**: The `FormTemplateDetailOutputSerializer` declares a field called `fields` which collides with DRF's `Meta.fields`. DRF resolves this correctly (declared fields take precedence), but it can be confusing to read.
- **Required field validation**: `submit_response` checks `not response.data.get(key)` which means empty string `""` and `0` and `False` are treated as missing. This is intentional for form submissions but worth noting.
- **Versioning on edit**: Editing an ACTIVE form creates a new version transparently. The old version becomes `is_current=False` but is NOT deleted — responses reference it via `form_version`.

---

## 10. Testing

| Module | Tests | Coverage |
|--------|-------|----------|
| test_models.py | 27 | Models, properties, constraints, soft-delete, index tables |
| test_selectors.py | 32 | All 3 selector classes, filters, edge cases |
| test_services.py | 40 | All service methods, state transitions, error paths |
| test_policies.py | 27 | All policy methods, permission/denial/system-form guards |
| test_indexing.py | 23 | Extraction, coercion, clear/rebuild, all 6 types |
| test_views.py | 27 | All 13 views, RBAC integration, status codes |
| test_transaction_integration.py | 23 | create_and_submit, link_to_transaction, mark_info_requested, update_after_info_request, new selectors |
| **Total** | **199** | **All passing** |

Factories: `apps/forms/tests/factories.py` — FormTemplateFactory, ActiveFormTemplateFactory, ArchivedFormTemplateFactory, SystemFormTemplateFactory, PublicFormTemplateFactory, FormFieldFactory, FormResponseFactory, SubmittedFormResponseFactory

---

## 11. File Summary

### New Files

| File | Description |
|------|-------------|
| `apps/forms/__init__.py` | App init |
| `apps/forms/apps.py` | FormsConfig |
| `apps/forms/admin.py` | Admin with FormField inline |
| `apps/forms/constants.py` | FIELD_STORAGE_MAP, INDEXABLE_STORAGE_TYPES, MAX_INDEXED_FIELDS |
| `apps/forms/models.py` | FormTemplate, FormField, FormResponse, 6 index tables |
| `apps/forms/managers.py` | FormTemplateManager/QuerySet, FormResponseManager/QuerySet |
| `apps/forms/selectors.py` | FormTemplateSelector, FormFieldSelector, FormResponseSelector |
| `apps/forms/policies.py` | FormTemplatePolicy (7), FormResponsePolicy (4) |
| `apps/forms/services.py` | FormBuilderService (8), FormResponseService (5) |
| `apps/forms/indexing.py` | IndexService, INDEX_TABLE_MAP |
| `apps/forms/signals.py` | on_response_submitted (placeholder) |
| `apps/forms/api/__init__.py` | API package init |
| `apps/forms/api/serializers.py` | 8 input + 6 output serializers |
| `apps/forms/api/views.py` | FormViewMixin + 13 API views |
| `apps/forms/api/urls.py` | URL routing, app_name="forms" |
| `apps/forms/migrations/0001_initial.py` | Initial migration |
| `apps/forms/tests/` | 8 test files (factories, conftest, 6 test modules) |
| `apps/forms/migrations/0002_add_transaction_integration.py` | Transaction integration fields |
| `apps/forms/migrations/0003_seed_system_forms.py` | System forms seed data |
| `apps/forms/tests/test_transaction_integration.py` | 23 integration tests |

### Modified Files

| File | Change |
|------|--------|
| `apps/core/constants.py` | Added FormStatus, ResponseStatus, FieldType (22), StorageType (7) enums |
| `apps/core/observability/audit/models.py` | Added 16 form audit actions |
| `apps/core/migrations/0004_alter_auditlog_action.py` | Migration for new audit actions |
| `backend_core/settings/base.py` | Added `"apps.forms"` to INSTALLED_APPS |
| `backend_core/urls.py` | Added forms URL include |
| `apps/forms/models.py` | Added transaction_id, context_type, context_id, revision, revision_history, info_requested_at fields |
| `apps/forms/selectors.py` | Added get_by_slug_or_none, get_by_transaction_id selectors |
| `apps/forms/services.py` | Added create_and_submit, link_to_transaction, mark_info_requested, update_after_info_request methods |

---

## 12. Known Limitations

1. **No field update/remove**: `FormBuilderService` has `add_field()` but no `update_field()` or `remove_field()`. Fields are managed through template versioning.
2. **No GIN index on FormResponse.data**: JSONB containment queries (`__contains`) will be slow on large datasets. The typed index tables cover primary query patterns.
3. **No export view**: `can_export_responses` permission exists but no export endpoint is wired yet.

---

## 13. vNext TODOs

| Item | Context | Priority |
|------|---------|----------|
| Add field update/remove service methods | Currently fields are immutable after creation | P1 |
| Wire export endpoint | Permission exists, need CSV/JSON export view | P2 |
| Add GIN index on FormResponse.data | Requires PostgreSQL; skip for SQLite tests | P2 |
| Add form response expiration | ResponseStatus.EXPIRED exists but no expiration logic | P3 |

---

## 14. Changelog

### v2 (2026-02-24)
- Form-Transaction integration: bidirectional linking, INFO_REQUESTED workflow, revision tracking
- 4 new FormResponseService methods (create_and_submit, link_to_transaction, mark_info_requested, update_after_info_request)
- 2 new selectors (get_by_slug_or_none, get_by_transaction_id)
- 3 system forms seeded via migration (business-verification, business-creation, platform-staff-application)
- 23 new integration tests (199 total)
- Updated version to v2, last updated to 2026-02-24

### v1 (2026-02-23)
- Initial implementation: models, services, selectors, policies, indexing, views, tests
- 176 tests, all passing
- 2 bugs found and fixed during testing (manager delegation, soft_delete field persistence)
