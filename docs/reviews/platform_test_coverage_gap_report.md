# Platform Test Coverage Gap Report

**Date:** 2026-03-09
**Scope:** pconsole (platform console) — business-like features only (gconsole excluded)
**Methodology:** Compared platform test coverage against business test coverage across all backend apps
**Total backend tests:** 3,134 unit tests

---

## Executive Summary

Platform test coverage is **critically uneven** across apps. RBAC and CMS have adequate-to-excellent platform coverage, but **Transaction** and **Forms** apps have near-zero platform-specific tests despite supporting platform context. The Organization (platform) tests exist but have significant gaps compared to their business counterparts.

| App | Platform Tests | Business Tests | Total Tests | Platform % | Status |
|-----|---------------|---------------|-------------|-----------|--------|
| Organization | ~59 | ~131 | ~205 | 29% | Gaps |
| RBAC | 30 | 69 | 257 | 12% | Adequate |
| Transaction | 12 | 15 | 375 | 3% | **Critical Gap** |
| Forms | 0 | 9 | 354 | 0% | **Critical Gap** |
| CMS | 5 | 0 | 165 | 3% | OK (platform-only by design) |

**Priority:** Transaction > Organization > Forms > RBAC

---

## 1. Organization App

### Current Coverage

| Module | Platform | Business | Gap |
|--------|----------|----------|-----|
| test_models.py | 123 lines | 184 lines | Minor |
| test_policies.py | 194 lines | 312 lines | Moderate |
| test_selectors.py | **MISSING** | 64 lines | **Full gap** |
| test_services.py | 162 lines | 278 lines | Moderate |
| test_views.py | 306 lines | 644 lines | Significant |
| **Total** | **785 lines** | **1,482 lines** | **47% smaller** |

### Specific Gaps

#### 1.1 Missing: `test_selectors.py` for Platform
Business has `test_selectors.py` (64 lines) testing `BusinessAccountSelector`. Platform has `PlatformSelector` in `platform/selectors.py` but **zero selector tests**.

**Tests needed:**
- `test_get_platform_account` — singleton retrieval
- `test_get_platform_account_unconfigured` — returns None or raises when not configured
- `test_get_platform_profile` — profile retrieval

#### 1.2 Gap: Policy Tests (194 vs 312 lines)
Business policies test 37 scenarios across 5 test classes. Platform policies test ~20 scenarios.

**Missing platform policy tests:**
- `can_manage_members` — platform owner/admin vs base member/global mod
- `can_manage_roles` — role hierarchy enforcement
- `can_view_audit_log` — audit log access
- Negative tests: anonymous user, non-member, suspended member
- `get_viewer_permissions` edge cases: no membership, deleted membership

#### 1.3 Gap: Service Tests (162 vs 278 lines)
Business services test lifecycle operations (create, update, soft delete, reactivate). Platform services are simpler (singleton, no create/delete), but gaps exist.

**Missing platform service tests:**
- Profile update with file uploads (logo, banner)
- Settings merge edge cases (partial update, null values)
- Configuration validation (required fields check)
- Error cases: update unconfigured platform, invalid settings data

#### 1.4 Gap: View Tests (306 vs 644 lines)
Business views test 48 scenarios including relationship injection, slug lookup, list endpoints, and permission-aware responses.

**Missing platform view tests:**
- `_relationship` injection on platform detail (RelationshipInjectMixin)
- Anonymous access: correct `_permissions` shape (all False except `can_view`)
- PATCH with file uploads (logo, banner) — multipart form data
- Error cases: invalid settings payload, unauthorized PATCH
- Pagination/filtering (if applicable to platform sub-resources)

---

## 2. RBAC App

### Current Coverage

| Module | Platform Tests | Notes |
|--------|---------------|-------|
| test_actor_scenarios.py | 17 | Cross-account authority, suspension rules |
| test_policies.py | 4 | Global permission, cross-account, invincibility |
| test_services.py | 3 | Platform initialization, membership creation |
| test_views.py | 6 | Role CRUD, member suspension |
| test_models.py | 0 | Business-only role/permission tests |
| test_selectors.py | 0 | Business-only selector tests |
| **Total** | **30** | 12% of 257 total |

### Status: Adequate (with minor gaps)

RBAC has the best platform coverage outside CMS. Actor scenarios (17 tests) thoroughly validate the two-plane authority model. However:

### Specific Gaps

#### 2.1 Gap: Platform Selector Tests (0 platform-specific)
`test_selectors.py` (42 tests) only tests business context. Missing:
- `get_memberships_for_account(account_type="platform", ...)` — platform member listing
- `count_active_members` for platform context
- `get_role_hierarchy` for platform roles (3 roles: Owner L0, Admin L2, Global Mod L5)
- Platform member search/filter (by status, role, search query)

#### 2.2 Gap: Platform Model Tests (0 platform-specific)
`test_models.py` (25 tests) only tests business roles/permissions. Missing:
- Platform role constraints (unique name per platform)
- Platform permission assignment
- Platform membership status transitions

#### 2.3 Gap: Platform View Endpoint Tests
`test_views.py` has 6 platform tests but business has more comprehensive coverage:
- **Missing:** Platform member list with search/filter/pagination
- **Missing:** Platform member detail with `_permissions`
- **Missing:** Platform role detail with `_permissions`
- **Missing:** Platform member reactivate endpoint
- **Missing:** Platform member ban/unban endpoints
- **Missing:** Error cases: invalid role level, duplicate role name

---

## 3. Transaction App — **CRITICAL GAP**

### Current Coverage

| Module | Platform Tests | Business Tests | Total | Platform % |
|--------|---------------|---------------|-------|-----------|
| test_policies.py | 5 | 0 | 40 | 13% |
| test_open_member_request.py | 3 | 2 | 9 | 33% |
| test_models.py | 2 | 2 | 43 | 5% |
| test_types.py | 1 | 2 | 15 | 7% |
| test_constants.py | 1 | 0 | 35 | 3% |
| test_services.py | **0** | 7 | 76 | **0%** |
| test_views.py | **0** | 1 | 44 | **0%** |
| test_selectors.py | **0** | 0 | 45 | **0%** |
| test_pending_review.py | **0** | 0 | 13 | **0%** |
| test_form_integration.py | **0** | 0 | 24 | **0%** |
| test_outcome_handlers.py | 0 | 1 | 15 | 0% |
| test_rate_limits.py | 0 | 0 | 5 | 0% |
| test_tasks.py | 0 | 0 | 11 | 0% |
| **Total** | **12** | **15** | **375** | **3.2%** |

### Why This Is Critical

Platform supports **4 transaction types** (mirror of business):
- `platform_membership_invitation` — platform owner/admin invites a user
- `platform_membership_request` — user requests to join platform
- `platform_ownership_transfer` — transfer platform ownership
- `platform_role_change` — change a member's role

These share the same service methods (`create_invitation`, `create_request`, `accept`, `deny`, `cancel`) as business transactions but with `account_type="platform"` context. **None of these flows are tested end-to-end for platform context.**

### Specific Gaps (Priority Order)

#### 3.1 MISSING: Platform Transaction Service Tests
`test_services.py` has 76 tests — **all business-scoped**. Need platform equivalents:

**Must-have tests:**
- `test_create_platform_invitation_happy_path` — owner invites user
- `test_create_platform_request_happy_path` — user requests to join
- `test_accept_platform_invitation` — invited user accepts
- `test_accept_platform_request` — owner accepts request
- `test_deny_platform_invitation` — owner denies
- `test_cancel_platform_request` — requester cancels
- `test_platform_duplicate_active_raises_conflict` — conflict detection
- `test_platform_cross_type_conflict` — invitation+request conflict guard
- `test_platform_member_quota_check` — quota enforcement
- `test_platform_open_member_request_check` — closed requests blocked

#### 3.2 MISSING: Platform Transaction View Tests
`test_views.py` has 44 tests — **0 platform-scoped**. Need:

**Must-have tests:**
- `test_create_platform_invitation_via_api` — POST /transactions/
- `test_create_platform_request_via_api` — POST /transactions/
- `test_list_platform_transactions` — GET /transactions/?context_type=platform
- `test_platform_transaction_detail` — GET /transactions/{id}/
- `test_platform_transaction_detail_permissions` — `_permissions` in response
- `test_accept_platform_transaction_via_api` — POST /transactions/{id}/accept/
- `test_deny_platform_transaction_via_api` — POST /transactions/{id}/deny/
- `test_cancel_platform_transaction_via_api` — POST /transactions/{id}/cancel/
- `test_platform_transaction_forbidden_for_non_member` — 403
- `test_platform_transaction_list_filter_by_status` — ?status=pending
- `test_platform_transaction_list_filter_by_type` — ?type=platform_membership_invitation

#### 3.3 MISSING: Platform Pending Review Tests
`test_pending_review.py` has 13 tests — **all business-scoped**. Need:

**Must-have tests:**
- `test_platform_accept_with_required_form_enters_pending_review`
- `test_platform_approve_pending_review_activates_membership`
- `test_platform_deny_pending_review_deletes_membership`
- `test_platform_cancel_from_pending_review`

#### 3.4 MISSING: Platform Form-Transaction Integration Tests
`test_form_integration.py` has 24 tests — **all context-agnostic but business fixtures**. Need:

**Must-have tests:**
- `test_platform_transaction_form_mapping_enforcement`
- `test_platform_info_requested_flow`
- `test_platform_resubmit_flow`

#### 3.5 MISSING: Platform Selector Tests
`test_selectors.py` has 45 tests — **context-agnostic but need platform verification**:

**Should-have tests:**
- `test_get_transactions_for_platform_context` — filter by context_type=platform
- `test_has_active_in_conflict_group_platform` — cross-type conflict for platform types

#### 3.6 Conftest Gap
Transaction `conftest.py` has platform fixtures (`platform`, `platform_owner_role`, `platform_membership`) but they're minimal. Need:
- `platform_admin_membership` — admin role member
- `platform_base_member_membership` — base member (no special perms)
- `platform_invitation` — pre-created invitation fixture
- `platform_request` — pre-created request fixture

---

## 4. Forms App — **CRITICAL GAP**

### Current Coverage

| Module | Platform Tests | Business Tests | Total |
|--------|---------------|---------------|-------|
| test_models.py | 0 | 0 | 27 |
| test_policies.py | 0 | 0 | 27 |
| test_selectors.py | 0 | 0 | 32 |
| test_services.py | 0 | 8 | 40 |
| test_views.py | 0 | 1 | 42 |
| test_validators.py | 0 | 0 | 162 |
| test_indexing.py | 0 | 0 | 23 |
| test_transaction_integration.py | 0 | 0 | 23 |
| **Total** | **0** | **9** | **354** |

### Why This Matters

Forms are used as **transaction pre-requisites** (TransactionFormMapping). When a platform transaction type requires a form (e.g., platform membership request requires a verification form), the form system operates in platform context. While forms are largely account-agnostic (templates are owned by `created_by` user, not by account), the **policy checks and view permissions** depend on the requesting user's membership context.

### Specific Gaps

#### 4.1 Platform Context in Form Policies
`FormTemplatePolicy` checks membership permissions. Need to verify:
- Platform member can create/view/edit form templates
- Platform admin can manage all templates
- Non-platform-member is denied

#### 4.2 Platform Form Views
Form CRUD endpoints need platform context validation:
- `test_create_form_template_as_platform_member`
- `test_list_form_templates_platform_context`
- `test_form_template_detail_permissions_platform`

#### 4.3 Platform TransactionFormMapping
- `test_create_mapping_for_platform_transaction_type`
- `test_list_mappings_platform_context`
- `test_delete_mapping_platform_context`

#### 4.4 Conftest Gap
Forms `conftest.py` has **no platform fixtures**. Need:
- `platform` fixture
- `platform_membership` fixture for authenticated platform member
- `platform_form_template` fixture

---

## 5. CMS App — OK

### Current Coverage

CMS is **100% platform-scoped by design**. All 165 tests operate in platform context. Sites are owned by `OwnerType.PLATFORM` — no business CMS.

**Status:** No gaps for pconsole. CMS is already platform-first.

---

## 6. Priority Action Plan

### Phase 1: Transaction App (Critical — ~50 new tests)

| Priority | Test Module | Est. Tests | Effort |
|----------|------------|-----------|--------|
| P0 | Platform service tests (create/accept/deny/cancel flows) | 15 | High |
| P0 | Platform view tests (API endpoints) | 15 | High |
| P1 | Platform pending review tests | 5 | Medium |
| P1 | Platform form-transaction integration | 5 | Medium |
| P2 | Platform selector tests | 5 | Low |
| P2 | Conftest fixtures expansion | — | Low |

### Phase 2: Organization Platform App (~25 new tests)

| Priority | Test Module | Est. Tests | Effort |
|----------|------------|-----------|--------|
| P1 | Platform selector tests (new file) | 5 | Low |
| P1 | Platform view tests (relationship, uploads, errors) | 10 | Medium |
| P2 | Platform policy tests (expand) | 5 | Low |
| P2 | Platform service tests (expand) | 5 | Low |

### Phase 3: Forms App (~15 new tests)

| Priority | Test Module | Est. Tests | Effort |
|----------|------------|-----------|--------|
| P1 | Platform form policies | 5 | Low |
| P1 | Platform form views | 5 | Medium |
| P2 | Platform form-mapping CRUD | 5 | Low |

### Phase 4: RBAC App (~15 new tests)

| Priority | Test Module | Est. Tests | Effort |
|----------|------------|-----------|--------|
| P2 | Platform selector tests | 5 | Low |
| P2 | Platform model tests | 5 | Low |
| P2 | Platform view endpoint expansion | 5 | Low |

---

## 7. Estimated Total New Tests

| Phase | App | New Tests | Lines (est.) |
|-------|-----|----------|-------------|
| 1 | Transaction | ~50 | ~1,500 |
| 2 | Organization | ~25 | ~600 |
| 3 | Forms | ~15 | ~400 |
| 4 | RBAC | ~15 | ~400 |
| **Total** | | **~105** | **~2,900** |

This would bring platform test parity from **current ~3% (transaction)** to **~15-20%** across all apps, matching the ratio of platform:business transaction types (4:5).

---

## 8. Key Principle

> **Platform tests should mirror business tests for every shared feature.**
> If business has a test for `create_invitation` → platform needs `create_platform_invitation`.
> If business has a test for `accept with required form` → platform needs the same.
> The goal is **feature parity**, not line-count parity.

The platform is a **singleton account** (no slug-based routing, no list endpoint), so some business tests don't apply (e.g., business list, slug lookup). But all **member management, transaction lifecycle, form integration, and RBAC enforcement** features must be tested in platform context.
