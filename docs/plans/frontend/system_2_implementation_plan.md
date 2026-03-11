# Implementation Plan: Forms, Transactions, and Member Management Frontend Systems

## Context

Three description documents define what needs to be built for the frontend:
- `docs/descriptions/frontend/form_system_frontend.md`
- `docs/descriptions/frontend/transaction_system_frontend.md`
- `docs/descriptions/frontend/role_member_management_frontend.md`

The backend is largely complete but has gaps that must be fixed first. The frontend foundation (auth, guards, nav, API layer, permissions, stores) is complete with 541 tests.

**Current state:** All three systems have stub pages ("coming soon"). No feature folders exist yet for `members/`, `forms/`, or `transactions/`.

**Verified against code (2026-03-05):** All backend gaps confirmed real. `BusinessReactivateView` exists but is for business ACCOUNT reactivation, NOT member reactivation — member reactivate endpoint is genuinely missing.

**Recommended approach: Backend-first, then frontend.**
- Complete Phase 0 backend gaps first (~15-20 files, each testable)
- Then build frontend Phases 1-7 with APIs ready
- Phases 1-2 (types + shared components) can start alongside backend — no API dependency

**Build order:** Members first (no cross-deps) → Forms (provides FormBuilder) → Transactions (consumes FormBuilder + RolePicker)

---

## Phase 0: Backend Prerequisites

### 0A. Critical Fixes (Block workflows)

**0A.1 — Add Platform Base Member role**
- File: `backend/apps/rbac/services.py` → `initialize_platform_account()` — add Base Member role (level 10)
- New migration to backfill existing platform accounts
- Without this, platform membership invitations/requests crash

**0A.2 — Add `role_id` to platform invitation payload schema**
- File: `backend/apps/transaction/types.py` → `platform_membership_invitation` config
- Add `payload_schema` with required `role_id` (UUID) + optional `message`
- Verified: currently has no `payload_schema` (empty default)

**0A.3 — Accept endpoint must accept request body**
- File: `backend/apps/transaction/api/serializers.py` → new `AcceptTransactionInputSerializer` (optional `role_id`)
- File: `backend/apps/transaction/api/views.py` → `AcceptTransactionView.post()` — parse body (verified: currently `request=None`)
- File: `backend/apps/transaction/services.py` → `accept()` — forward acceptance payload to outcome handler
- File: `backend/apps/transaction/outcome_handlers.py` → `handle_request_approved()` — use acceptance-time `role_id`

**0A.4 — Add role level validation to transaction flows**
- File: `backend/apps/transaction/services.py` → `create_invitation()` — validate inviter level < assigned role level
- File: `backend/apps/transaction/services.py` → `accept()` — validate approver level < assigned role level
- Reuse `MembershipPolicy.validate_role_assignment()` logic

### 0B. High Priority (Block features)

**0B.1 — Add `_permissions` to TransactionDetailView**
- File: `backend/apps/transaction/policies.py` → add `get_viewer_permissions()` returning: `can_accept`, `can_deny`, `can_cancel`, `can_dismiss`, `can_request_info`, `can_resubmit`, `can_view_form`
- File: `backend/apps/transaction/api/views.py` → add `PermissionInjectMixin` to `TransactionDetailView`
- Verified: currently no `PermissionInjectMixin` on this view

**0B.2 — Add `_permissions` to Member and Role detail views**
- File: `backend/apps/rbac/policies.py` → `MembershipPolicy.get_viewer_permissions()` returning: `can_change_role`, `can_suspend`, `can_remove`, `can_ban`, `can_reactivate`
- File: `backend/apps/rbac/policies.py` → `RolePolicy.get_viewer_permissions()` returning: `can_edit`, `can_delete`, `can_modify_permissions`
- File: `backend/apps/rbac/api/views.py` → add `PermissionInjectMixin` to `Business/PlatformMemberDetailView` and `Business/PlatformRoleDetailView`
- Verified: currently no `PermissionInjectMixin` on any RBAC view

**0B.3 — Extend MemberUserOutputSerializer**
- File: `backend/apps/rbac/api/serializers.py` → add `display_name`, `avatar_url` via SerializerMethodField
- Verified: currently only exposes `id`, `email`, `username`

**0B.4 — Add search/filter/pagination to member list**
- File: `backend/apps/rbac/api/views.py` → `Business/PlatformMemberListView` — add `StandardPagination`, query params `?search=`, `?status=`, `?role_id=`, `?ordering=`
- File: `backend/apps/rbac/selectors.py` → add filter/search/ordering to `get_memberships_for_account()`
- Verified: currently extends `APIView` with no pagination, returns data directly

**0B.5 — Add member reactivate endpoint**
- File: `backend/apps/rbac/api/views.py` → new `Business/PlatformMemberReactivateView` calling `RBACService.update_membership_status(new_status=ACTIVE)`
- File: `backend/apps/rbac/api/urls.py` + org URLs → `POST members/{id}/reactivate/`
- Verified: no member reactivate endpoint exists (only business account reactivate at `/business/<slug>/reactivate/`)

**0B.6 — Expand TransactionListSerializer**
- File: `backend/apps/transaction/api/serializers.py` → add `initiator_name`, `initiator_email`, `target_name`, `target_email`, `category`

**0B.7 — Add `category` to TransactionTypeConfig**
- File: `backend/apps/transaction/types.py` → add `category: str` to dataclass, set on all 10 types (membership, ownership, verification, permission, social)
- Verified: no `category` field exists on `TransactionTypeConfig`

**0B.8 — Add transaction list filters**
- File: `backend/apps/transaction/api/views.py` → `TransactionListView` — add `?mode=`, `?context_type=`, `?context_id=`, `?status=`, `?transaction_type=`
- Verified: currently only supports `?role=` param

**0B.9 — Seed `can_configure_transactions` permission**
- New migration in `backend/apps/rbac/migrations/`
- Verified: permission does not exist in any migration

**0B.10 — Create TransactionFormMapping model + CRUD**
- File: `backend/apps/transaction/models.py` → new `TransactionFormMapping` model (account_type, account_id, transaction_type, form_template FK, is_required)
- New migration + services + selectors + serializers + views + URLs
- Verified: model does not exist

**0B.11 — Add transaction types list endpoint**
- File: `backend/apps/transaction/api/views.py` → new `TransactionTypeListView`
- File: `backend/apps/transaction/api/urls.py` → `GET /transactions/types/`
- Verified: no list endpoint exists (only single-type form schema view)

**0B.12 — Add form field update/delete/reorder endpoints**
- File: `backend/apps/forms/api/views.py` → `FormFieldDetailView` (PATCH/DELETE), `FormFieldReorderView` (bulk PATCH)
- File: `backend/apps/forms/api/serializers.py` → input serializers
- File: `backend/apps/forms/api/urls.py` → URL patterns
- Verified: only `FormFieldAddView` (POST) exists — no PATCH/DELETE/reorder

**0B.13 — Add member count annotation to role list**
- File: `backend/apps/rbac/api/serializers.py` → `RoleOutputSerializer` + `member_count`
- File: `backend/apps/rbac/selectors.py` → annotate with `Count('memberships')`

### 0C. Backend Tests
- Each change gets tests per `docs/implementations/backend/test-standards.md`
- Pattern: `backend/apps/{app}/tests/`

---

## Phase 1: Shared Types and Query Keys

No backend dependency — start immediately alongside Phase 0.

### 1.1 — Create `frontend/src/types/members.ts`
Types matching `backend/apps/rbac/api/serializers.py`:
- `MemberUser` (id, email, username, display_name, avatar_url)
- `MemberListItem` (id, user, role_name, role_level, is_owner, status, joined_at)
- `MemberDetail` (full membership with nested Role)
- `MemberPermissions` = `{ can_change_role, can_suspend, can_remove, can_ban, can_reactivate }`
- `MemberDetailWithPerms` = `MemberDetail & WithPermissions<MemberPermissions>`
- `RoleListItem` (RoleOutputSerializer + member_count)
- `RoleDetail` (with nested role_permissions)
- `RolePermissions` = `{ can_edit, can_delete, can_modify_permissions }`
- `RoleDetailWithPerms` = `RoleDetail & WithPermissions<RolePermissions>`
- `Permission` (id, code, name, description, category, applicable_scopes)
- Input types: `CreateRoleInput`, `UpdateRoleInput`, `AddPermissionInput`, `RemovePermissionInput`, `ChangeRoleInput`, `MemberActionInput`
- Reuse: `AccountType`, `MembershipStatus`, `Role` from `src/types/rbac.ts`; `WithPermissions` from `src/types/api.ts`

### 1.2 — Create `frontend/src/types/forms.ts`
- `FormStatus`, `ResponseStatus`, `FieldType` (22 values)
- `FormField` (17 fields), `FormTemplateList`, `FormTemplateDetail`
- `FormTemplatePermissions` = `{ can_edit, can_delete, can_publish, can_archive }`
- `FormTemplateDetailWithPerms`
- `FormResponseList`, `FormResponseDetail`
- Input types: `CreateTemplateInput`, `CreateFieldInput`, `UpdateFieldInput`, `ForkTemplateInput`

### 1.3 — Create `frontend/src/types/transactions.ts`
- `TransactionStatus` (9 values), `TransactionMode`, `TransactionCategory`
- `TransactionLog`, `TransactionListItem`, `TransactionDetail`
- `TransactionPermissions` = `{ can_accept, can_deny, can_cancel, can_dismiss, can_request_info, can_resubmit, can_view_form }`
- `TransactionDetailWithPerms`, `TransactionTypeInfo`, `TransactionFormMapping`
- Input types: `CreateInvitationInput`, `CreateRequestInput`, `DenyInput`, `AcceptInput`

### 1.4 — Extend `frontend/src/lib/query-keys.ts`
Add to existing keys:
- `members: { all, list(accountType, slug), detail(id), formResponses(id) }`
- `roles: { all, list(accountType, slug), detail(id) }`
- `transactions: { ...existing, types(contextType?), formMappings(accountType, accountId), formResponse(id) }`
- `forms: { ...existing, responses(formId, params), responseDetail(id), myResponses() }`

---

## Phase 2: Shared Components

No backend dependency — start immediately.

### 2.1 — `frontend/src/components/common/RolePicker.tsx` + test
Reused by: Member Management (role change), Transactions (invitation create, request accept)
- Props: `accountType`, `slug?`, `actorRoleLevel`, `value`, `onChange`, `required`, `disabled`
- Fetch roles → filter out Owner (level 0) + roles ≤ actor level → sort by level ascending
- Pattern: `src/components/common/ComboboxField.tsx`

### 2.2 — `frontend/src/components/common/ConfirmActionDialog.tsx` + test
- Props: `open`, `onOpenChange`, `title`, `description`, `confirmLabel`, `variant`, `showReasonField`, `reasonRequired`, `onConfirm(reason?)`, `isLoading`
- Uses shadcn `AlertDialog`

### 2.3 — `frontend/src/components/common/StatusBadge.tsx` + test
Generic badge with config map (label, color, icon per status).

### 2.4 — `frontend/src/components/common/QuotaBar.tsx` + test
Member quota progress bar. Props: `current`, `max` (0=unlimited), `label?`

---

## Phase 3: Member Management System (6 routes)

**Backend deps:** 0B.2, 0B.3, 0B.4, 0B.5, 0B.13

### 3A. API Layer

**3A.1 — `frontend/src/features/members/api/members-api.ts` + test**
- `fetchMembersApi`, `fetchMemberDetailApi`, `changeMemberRoleApi`, `suspendMemberApi`, `removeMemberApi`, `banMemberApi`, `reactivateMemberApi`, `leaveMemberApi`
- Helper: `buildMemberUrl(accountType, slug?, membershipId?, action?)`
- Pattern: `src/features/business/api/business-api.ts`

**3A.2 — `frontend/src/features/members/api/roles-api.ts` + test**
- `fetchRolesApi`, `fetchRoleDetailApi`, `createRoleApi`, `updateRoleApi`, `deleteRoleApi`, `addPermissionToRoleApi`, `removePermissionFromRoleApi`, `fetchAllPermissionsApi`

### 3B. Hooks

**3B.1 — `use-member-queries.ts` + test** — `useMemberList`, `useMemberDetail`
**3B.2 — `use-member-mutations.ts` + test** — `useChangeMemberRole`, `useSuspendMember`, `useRemoveMember`, `useBanMember`, `useReactivateMember`, `useLeaveMember`
**3B.3 — `use-role-queries.ts` + test** — `useRoleList`, `useRoleDetail`, `useAllPermissions`
**3B.4 — `use-role-mutations.ts` + test** — `useCreateRole`, `useUpdateRole`, `useDeleteRole`, `useAddPermission`, `useRemovePermission`

### 3C. Validations
**3C.1 — `frontend/src/lib/validations/role.ts`** — `createRoleSchema`, `updateRoleSchema`

### 3D. Constants
**3D.1 — `frontend/src/features/members/constants/member-statuses.ts`** — status config map (colors, icons)

### 3E. Components (each with test)

| # | Component | Purpose |
|---|-----------|---------|
| 3E.1 | `MemberCard.tsx` | Row: avatar, name, email, role badge, status badge, joined date |
| 3E.2 | `MemberList.tsx` | Table + status tabs + role filter + search + pagination |
| 3E.3 | `RoleCard.tsx` | Card: name, level, system indicator, member count, actions |
| 3E.4 | `RoleList.tsx` | Role cards grid + "Create Role" button (permission-gated) |
| 3E.5 | `CreateRoleDialog.tsx` | Dialog: name, level (filtered by actor), description |
| 3E.6 | `MemberProfile.tsx` | User info + membership info on detail page |
| 3E.7 | `MemberActions.tsx` | Buttons gated by `_permissions`: Change Role, Suspend, Remove, Ban, Reactivate |
| 3E.8 | `PermissionsEditor.tsx` | Searchable checklist by category; toggle + scope selector; immediate save |
| 3E.9 | `MemberDashboardPage.tsx` | QuotaBar + "Invite Member" + MemberList + RoleList |
| 3E.10 | `MemberDetailPage.tsx` | MemberProfile + MemberActions |
| 3E.11 | `RoleDetailPage.tsx` | Role header (editable) + PermissionsEditor |

### 3F. Route Pages

**Business console:**
- Replace `app/(app)/bconsole/[slug]/members/page.tsx` → `MemberDashboardPage`
- Create `.../members/[id]/page.tsx` → `MemberDetailPage`
- Create `.../members/roles/[id]/page.tsx` → `RoleDetailPage`
- Redirect `app/(app)/bconsole/[slug]/roles/page.tsx` → `/bconsole/{slug}/members`

**Platform console:** Mirror above under `app/(app)/pconsole/`

### 3G. Navigation Config
- `biz-members` / `plat-members` already correct (`permission: "can_view_members"`, `minMembers: 2`)
- Remove `biz-roles` / `plat-roles` (roles are sub-route of members, not separate sidebar items)

---

## Phase 4: Form System (14 routes)

**Backend deps:** 0B.12 (field update/delete/reorder)

### 4A. API Layer
**4A.1 — `frontend/src/features/forms/api/forms-api.ts` + test**

Templates: `fetchTemplatesApi`, `createTemplateApi`, `fetchTemplateDetailApi`, `updateTemplateApi`, `publishTemplateApi`, `archiveTemplateApi`, `forkTemplateApi`, `fetchLibraryApi`

Fields: `addFieldApi`, `updateFieldApi`, `deleteFieldApi`, `reorderFieldsApi`

Responses: `fetchResponsesApi`, `createResponseApi`, `fetchResponseDetailApi`, `updateResponseApi`, `submitResponseApi`, `processResponseApi`, `voidResponseApi`, `fetchMyResponsesApi`

### 4B. Hooks
**4B.1 — `use-form-queries.ts` + test** — `useTemplateList`, `useTemplateDetail`, `useLibrary`, `useResponseList`, `useResponseDetail`, `useMyResponses`
**4B.2 — `use-form-mutations.ts` + test** — Template/field/response mutations (15 total)

### 4C. Validations
**4C.1 — `frontend/src/lib/validations/form-template.ts`** — `createTemplateSchema`, `createFieldSchema`, `forkTemplateSchema`

### 4D. Constants
**4D.1 — `field-types.ts`** — metadata for 22 types (label, icon, category, indexable)
**4D.2 — `form-statuses.ts`** — template + response status configs

### 4E. Form Builder (Core Reusable Component)

**4E.1 — Field components** (`features/forms/components/form-builder/fields/`)
22 field components grouped by category:
- Text (5): TextField, TextareaField, EmailField, UrlField, PhoneField — share `BaseTextField`
- Choice (2): SelectField, RadioField
- Multi-value (2): MultiselectField, CheckboxGroupField
- Numeric (4): IntegerField, DecimalField, CurrencyField, RatingField
- Boolean (2): BooleanField, CheckboxField
- Temporal (3): DateField, DateTimeField, TimeField
- File (2): FileField, ImageField
- Complex (2): LocationField, RepeatableField

**4E.2 — `FieldRenderer.tsx`** — maps field_type → component
**4E.3 — `FieldConfigPanel.tsx`** — design-mode field configuration panel
**4E.4 — `StepNavigation.tsx`** — wizard steps (grouped by step_tag)
**4E.5 — `SectionWrapper.tsx`** — visual grouping by section_tag
**4E.6 — `FormBuilder.tsx` + test** — main component (4 modes: design/preview/fill/view)

### 4F. Page Components (each with test)

| # | Component | Purpose |
|---|-----------|---------|
| 4F.1 | `FormsDashboardPage.tsx` | Bento grid: Templates, Library, Responses (permission-gated) |
| 4F.2 | `TemplateListPage.tsx` | Tabs (All/Active/Archived) + "New Form" + template table |
| 4F.3 | `TemplateDetailPage.tsx` | FormBuilder (preview/design) + actions (Publish/Archive/Delete) |
| 4F.4 | `CreateTemplatePage.tsx` | Metadata form + FormBuilder design mode |
| 4F.5 | `LibraryPage.tsx` | Browse public templates + fork |
| 4F.6 | `ResponsesDashboardPage.tsx` | Form selector + filters + response table |
| 4F.7 | `ResponseDetailPage.tsx` | FormBuilder view mode + Process/Void actions |

### 4G. Route Pages

**Business console (7 routes):**
- Replace stub `.../forms/page.tsx` → `FormsDashboardPage`
- Create `.../forms/templates/page.tsx`, `.../new/page.tsx`, `.../[id]/page.tsx`
- Create `.../forms/library/page.tsx`
- Create `.../forms/responses/page.tsx`, `.../responses/[id]/page.tsx`

**Platform console (7 routes):** Mirror above under `app/(app)/pconsole/forms/`

---

## Phase 5: Transaction System (12 routes)

**Backend deps:** 0A.* (critical), 0B.1, 0B.6-0B.11
**Frontend deps:** Phase 2 (RolePicker), Phase 4E (FormBuilder)

### 5A. API Layer
**5A.1 — `frontend/src/features/transactions/api/transactions-api.ts` + test**

CRUD: `fetchTransactionsApi`, `fetchTransactionDetailApi`, `createInvitationApi`, `createRequestApi`, `acceptTransactionApi`, `denyTransactionApi`, `cancelTransactionApi`, `dismissTransactionApi`, `requestInfoApi`, `resubmitTransactionApi`

Form: `fetchTransactionFormResponseApi`, `updateTransactionFormResponseApi`, `fetchTransactionFormSchemaApi`

Types/Mappings: `fetchTransactionTypesApi`, `fetchFormMappingsApi`, `createFormMappingApi`, `deleteFormMappingApi`

### 5B. Hooks
**5B.1 — `use-transaction-queries.ts` + test**
**5B.2 — `use-transaction-mutations.ts` + test**

### 5C. Validations
**5C.1 — `frontend/src/lib/validations/transaction.ts`** — `createInvitationSchema`, `denySchema`, `requestInfoSchema`, `acceptSchema`

### 5D. Constants
**5D.1 — `transaction-statuses.ts`** — 9 statuses with colors/icons
**5D.2 — `transaction-categories.ts`** — 5 categories

### 5E. Components (each with test)

| # | Component | Purpose |
|---|-----------|---------|
| 5E.1 | `TransactionStatusBadge.tsx` | StatusBadge with transaction config |
| 5E.2 | `CategoryBadge.tsx` | Category icon + label |
| 5E.3 | `TransactionFilters.tsx` | Category, type, status, date, user (URL-synced) |
| 5E.4 | `TransactionCard.tsx` | List row with parties, status, dates |
| 5E.5 | `TransactionTimeline.tsx` | Status change log timeline |
| 5E.6 | `DenyDialog.tsx` | ConfirmActionDialog + reason field |
| 5E.7 | `RequestInfoDialog.tsx` | Message + field checkboxes |
| 5E.8 | `AcceptDialog.tsx` | Membership: RolePicker + quota. Non-membership: confirm |
| 5E.9 | `ActionButtons.tsx` | Accept/Deny/Cancel/Dismiss/RequestInfo (gated by `_permissions`) |
| 5E.10 | `InvitationCreateForm.tsx` | Multi-step: type → target → payload (RolePicker) → form (FormBuilder fill) |
| 5E.11 | `FormMappingCard.tsx` | Per-type: system form (read-only) + custom form (editable) |
| 5E.12 | `FormMappingList.tsx` | Cards grouped by category |
| 5E.13 | `TransactionsDashboardPage.tsx` | Bento grid: Requests, Invitations, Settings |
| 5E.14 | `RequestsListPage.tsx` | Filtered incoming requests list |
| 5E.15 | `RequestDetailPage.tsx` | Detail + FormBuilder view + timeline + actions |
| 5E.16 | `InvitationsListPage.tsx` | Filtered list + "New Invitation" button |
| 5E.17 | `InvitationDetailPage.tsx` | Detail + FormBuilder view + timeline + cancel |
| 5E.18 | `TransactionSettingsPage.tsx` | FormMappingList (gate: `can_configure_transactions`) |

### 5F. Route Pages

**Business console (6 routes):**
- Replace stub `.../transactions/page.tsx` → `TransactionsDashboardPage`
- Create `.../transactions/requests/page.tsx`, `.../requests/[id]/page.tsx`
- Create `.../transactions/invitations/page.tsx`, `.../invitations/[id]/page.tsx`
- Create `.../transactions/settings/page.tsx`

**Platform console (6 routes):** Mirror above under `app/(app)/pconsole/transactions/`

---

## Phase 6: Cross-System Integration

### 6.1 — Member Dashboard "Invite Member" button
Navigate to `/bconsole/{slug}/transactions/invitations?create=true&type=business_membership_invitation`. `InvitationsListPage` reads `?create=true` and auto-opens `InvitationCreateForm`.

### 6.2 — Transaction Accept quota check
In `AcceptDialog` for membership transactions: read `account_max_members` from membership store, check member count, disable Accept if quota full.

### 6.3 — Transaction Detail FormBuilder
If `_permissions.can_view_form` && `form_response` exists → render FormBuilder in view mode.

### 6.4 — Invitation Create form resolution
Select type → fetch form schema → if form exists, render FormBuilder fill mode → create response first, then transaction with `form_response_id`.

### 6.5 — Navigation `minMembers: 2` gates
Add `minMembers: 2` to `biz-forms`, `biz-transactions`, and platform equivalents (currently missing).

---

## Phase 7: Testing and Documentation

### 7.1 — Test targets
- All API functions, hooks, components get tests
- Backend: each Phase 0 change gets tests per test-standards.md
- Run: `cd frontend && npm run test` + backend pytest + `make test-api`

### 7.2 — Documentation
- Progress entries in `progress/` per phase
- Update `MEMORY.md` with new test counts

---

## File Summary

| Category | Count | Location |
|----------|-------|----------|
| Type files | 3 new | `src/types/{members,forms,transactions}.ts` |
| Query keys | 1 modified | `src/lib/query-keys.ts` |
| Validations | 3 new | `src/lib/validations/{role,form-template,transaction}.ts` |
| Shared components | 4 new (+tests) | `src/components/common/` |
| Feature: members | ~15 files (+tests) | `src/features/members/` |
| Feature: forms | ~35 files (+tests) | `src/features/forms/` |
| Feature: transactions | ~25 files (+tests) | `src/features/transactions/` |
| Route pages | 32 total | `src/app/(app)/bconsole/` + `pconsole/` |
| Nav config | 1 modified | `src/lib/navigation-config.ts` |
| Backend changes | ~15-20 files | `backend/apps/{rbac,transaction,forms}/` |

## Open Design Questions (resolve during implementation)

| Question | Default Decision |
|----------|-----------------|
| Dual forms per transaction (system + custom) | Defer — current backend supports 1 form per transaction |
| Invitation creation UX | Multi-step wizard within InvitationsListPage |
| Nav multi-permission gate for Forms | Keep single `can_create_form` for simplicity |
| Dismissed transactions visibility | Show with muted style in list |
| Transaction expiry UI | Static display with visual warning near expiry |
