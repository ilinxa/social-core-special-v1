# API Integration Test Plan

Comprehensive test scenarios for verifying all backend API endpoints against the Docker infrastructure stack (PostgreSQL 17 + Redis 7).

**Reference:** See [index.md](./index.md) for prerequisites, auth helpers, and error format.

---

## Part 1: Setup & Prerequisites

### 1.1 Environment Setup

```bash
# 1. Start Docker infrastructure
make dev-up
# Verify: docker ps shows dev_postgres (healthy) and dev_redis (healthy)

# 2. Run migrations (creates tables + seeds permissions, forms, platform)
make dev-migrate

# 3. Start Django development server
make dev
# Server runs at http://localhost:8000 with local_docker settings
# Rate limits relaxed: login 100/min, password_reset 100/hr (vs 5/min and 3/hr in production)

# 4. Run tests
make test-api
```

**Note:** No superuser or Celery worker is needed. Tests register their own users via the API and use `DBHelper` for out-of-band data (verification codes, password reset tokens, system form responses).

### 1.2 Data Seeded by Migrations

After `make dev-migrate`, the database contains:

**Platform Account** (from `organization.0002`):
- 1 PlatformAccount singleton (`is_configured=False` initially)

**Permissions** (from `rbac.0002`, `rbac.0003`, `rbac.0004`):

| Category | Permissions | Count |
|----------|------------|-------|
| Membership | `can_invite_member`, `can_remove_member`, `can_change_member_role`, `can_suspend_member`, `can_ban_member`, `can_approve_membership_request`, `can_view_members` | 7 |
| Roles | `can_create_role`, `can_edit_role`, `can_delete_role` | 3 |
| Settings | `can_edit_business`, `can_edit_profile`, `can_view_settings` | 3 |
| Platform | `can_suspend_business`, `can_remove_business_owner`, `can_transfer_business_ownership`, `can_view_businesses`, `can_approve_verification_request`, `can_approve_business_creation` | 6 |
| Audit | `can_view_audit_logs` | 1 |
| Forms | `can_create_form`, `can_edit_form`, `can_delete_form`, `can_view_responses`, `can_export_responses`, `can_process_response` | 6 |
| Transaction | `can_view_transactions`, `can_view_all_transactions` | 2 |
| CMS Structure | `can_create_cms_site`, `can_edit_cms_site`, `can_delete_cms_site`, `can_create_cms_page`, `can_edit_cms_page`, `can_delete_cms_page`, `can_create_cms_template`, `can_edit_cms_template`, `can_delete_cms_template`, `can_assign_cms_to_business`, `can_create_cms_api_key`, `can_revoke_cms_api_key` | 12 |
| CMS Content | `can_view_cms_content`, `can_edit_cms_content`, `can_publish_cms_content`, `can_toggle_cms_visibility`, `can_view_cms_history`, `can_rollback_cms_content`, `can_export_cms_content`, `can_import_cms_content` | 8 |
| CMS Media | `can_upload_cms_media`, `can_edit_cms_media`, `can_delete_cms_media` | 3 |
| **Total** | | **51** |

**System Forms** (from `forms.0003`):

| Slug | Fields | Used By |
|------|--------|---------|
| `system-business-verification` | 8 (legal_name, registration_number, tax_id, country, legal_address, business_license, tax_certificate, additional_documents) | `business_verification_request` transaction |
| `system-business-creation` | 6 (legal_name, display_name, country, business_type, description, website) | `business_creation_permission_request` transaction |
| `system-platform-staff-application` | 5 (motivation, experience, availability, linkedin_url, resume) | Future platform staff flow |

### 1.3 Test User Tiers

**All users are created via `POST /api/v1/auth/register/`** — no superuser needed:

| User | Email | Password | Intended Role |
|------|-------|----------|---------------|
| Alice | `alice@test.com` | `TestPass123!` | Platform admin, business owner |
| Bob | `bob@test.com` | `TestPass123!` | Platform member, business member |
| Carol | `carol@test.com` | `TestPass123!` | Business member with limited role |
| Nobody | `nobody@test.com` | `TestPass123!` | No memberships anywhere |

### 1.4 Transaction Types Reference

10 transaction types defined in `apps/transaction/types.py`:

| Type | Direction | Form Required | Auto-Approval | Notes |
|------|-----------|---------------|---------------|-------|
| `platform_membership_invitation` | Owner → Target | No | No | Platform invite |
| `platform_membership_request` | User → Platform | No | No | Request to join platform |
| `platform_ownership_transfer` | Owner → Target | No | No | Transfer platform ownership |
| `business_membership_invitation` | Owner → Target | No | No | Business invite |
| `business_membership_request` | User → Business | No | No | Request to join business |
| `business_verification_request` | Business → Platform | Yes (`system-business-verification`) | No | Business verification |
| `business_follow_request` | User → Business | No | **Yes** | Auto-approved follow |
| `business_ownership_transfer` | Owner → Target | No | No | Transfer business ownership |
| `business_creation_permission_request` | User → Platform | Yes (`system-business-creation`) | No | Request to create a business |
| `user_connection_request` | User → User | No | No | User-to-user connection |

---

## Part 2: Domain-Specific Test Scenarios

### 2.1 Auth Domain (17 endpoints)

**Base URL:** `POST/GET /api/v1/auth/`

#### Core Auth

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| A01 | Register new user with valid data | POST | `/register/` | 201, user object + access_token + refresh cookie |
| A02 | Register with duplicate email | POST | `/register/` | 409 conflict |
| A03 | Register with weak password | POST | `/register/` | 400 validation_error |
| A04 | Register with missing required fields | POST | `/register/` | 400 validation_error |
| A05 | Login with valid credentials | POST | `/login/` | 200, access_token + refresh cookie + has_session cookie |
| A06 | Login with wrong password | POST | `/login/` | 401 invalid_credentials |
| A07 | Login with non-existent email | POST | `/login/` | 401 invalid_credentials |
| A08 | Login with unverified email (if enforced) | POST | `/login/` | 401 account_not_verified |
| A09 | Refresh token (valid refresh cookie) | POST | `/refresh/` | 200, new access_token + new refresh cookie |
| A10 | Refresh token reuse detection (use old refresh) | POST | `/refresh/` | 401 token_already_used |
| A11 | Logout current session | POST | `/logout/` | 200, refresh cookie cleared |
| A12 | Logout all sessions | POST | `/logout-all/` | 200, all refresh tokens invalidated |
| A13 | Verify JTI blacklist after logout-all: login fresh, save tokens, call `POST /auth/logout-all/`, then use saved access token on `GET /users/me/` — expect 401 (JTI blacklisted in Redis) | GET | `/users/me/` | 401 (token blacklisted via JTI) |

#### Email Verification

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| A14 | Verify email with valid 6-digit code | POST | `/verify-email/` | 200, email verified |
| A15 | Verify email with invalid code | POST | `/verify-email/` | 400 |
| A16 | Verify email with expired code | POST | `/verify-email/` | 400 |
| A17 | Verify email via magic link (valid UUID) | GET | `/verify-email/<uuid>/` | 200 |
| A18 | Verify email via magic link (invalid UUID) | GET | `/verify-email/<uuid>/` | 400 |
| A19 | Resend verification email | POST | `/resend-verification/` | 200 |
| A20 | Resend verification for already verified | POST | `/resend-verification/` | 400 |

#### Password Management

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| A21 | Request password reset | POST | `/password/reset/` | 200 (always, even for non-existent email) |
| A22 | Confirm password reset with valid token | POST | `/password/reset/confirm/` | 200 |
| A23 | Confirm password reset with expired token | POST | `/password/reset/confirm/` | 400 |
| A24 | Change password (authenticated) | POST | `/password/change/` | 200 |
| A25 | Change password with wrong current password | POST | `/password/change/` | 400 |

#### Sessions

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| A26 | List active sessions | GET | `/sessions/` | 200, array of sessions with device info |
| A27 | Revoke specific session | DELETE | `/sessions/<uuid>/` | 200, session invalidated |
| A28 | Revoke non-existent session | DELETE | `/sessions/<uuid>/` | 404 |

#### OAuth

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| A29 | Start Google OAuth flow | GET | `/oauth/google/` | 302 redirect to Google |
| A30 | Google OAuth callback (valid) | GET | `/oauth/google/callback/` | 200, tokens + user |
| A31 | Start Apple OAuth flow | GET | `/oauth/apple/` | 302 redirect to Apple |

---

### 2.2 Users Domain (9 operations)

**Base URL:** `/api/v1/users/me/`

**Auth required:** All endpoints require `Authorization: Bearer <token>`

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| U01 | Get current user profile | GET | `/me/` | 200, user object with id, email, first_name, last_name |
| U02 | Update current user (first_name, last_name) | PATCH | `/me/` | 200, updated user |
| U03 | Get extended profile | GET | `/me/profile/` | 200, profile object |
| U04 | Update profile (bio, etc.) | PATCH | `/me/profile/` | 200, updated profile |
| U05 | Get avatar | GET | `/me/avatar/` | 200, avatar URL or null |
| U06 | Upload avatar | POST | `/me/avatar/` | 200, new avatar URL |
| U07 | Delete avatar | DELETE | `/me/avatar/` | 200/204 |
| U08 | List user's memberships (all accounts) | GET | `/me/memberships/` | 200, array of memberships |
| U09 | Get specific membership detail | GET | `/me/memberships/<uuid>/` | 200, membership with role/permissions |
| U10 | Get membership for non-existent ID | GET | `/me/memberships/<uuid>/` | 404 |
| U11 | Deactivate account | PATCH | `/me/` | 200, then verify login blocked (401 account_inactive) |

---

### 2.3 Platform Domain (5 operations)

**Base URL:** `/api/v1/platform/`

**Auth required:** All endpoints require authentication + platform membership

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| P01 | Get platform account (unconfigured) | GET | `/account/` | 200, platform with `is_configured=false` |
| P02 | Configure platform (first time) | POST | `/account/` | 200, initializes RBAC, creates owner membership |
| P03 | Configure platform (second time) | POST | `/account/` | 409 conflict (already configured) |
| P04 | Get platform profile | GET | `/profile/` | 200, profile object |
| P05 | Update platform profile | PATCH | `/profile/` | 200, updated profile |
| P06 | Update platform settings | PATCH | `/settings/` | 200, merged JSONB settings |
| P07 | Access platform as non-member | GET | `/account/` | 403 permission_denied |
| P08 | Update settings without permission | PATCH | `/settings/` | 403 permission_denied |
| P09 | Update profile without permission | PATCH | `/profile/` | 403 permission_denied |

---

### 2.4 Business Domain (13 operations)

**Base URL:** `/api/v1/business/`

**Auth required:** All endpoints require authentication

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| B01 | List all businesses | GET | `/` | 200, paginated list |
| B02 | Create business | POST | `/` | 201, new business + owner membership created |
| B03 | Create business with duplicate slug | POST | `/` | 409 conflict |
| B04 | List my businesses | GET | `/my/` | 200, only businesses where user is member |
| B05 | Get business by UUID | GET | `/id/<uuid>/` | 200, business object |
| B06 | Get business by slug | GET | `/<slug>/` | 200, business object |
| B07 | Update business by slug | PATCH | `/<slug>/` | 200, updated business |
| B08 | Delete business (soft delete) | DELETE | `/<slug>/` | 200/204, is_deleted=true |
| B09 | Get business profile | GET | `/<slug>/profile/` | 200, profile object |
| B10 | Update business profile | PATCH | `/<slug>/profile/` | 200, updated profile |
| B11 | Update business slug | PATCH | `/<slug>/slug/` | 200, slug changed + old slug returns redirect info |
| B12 | Suspend business (platform admin) | POST | `/<slug>/suspend/` | 200, status=suspended |
| B13 | Reactivate business (platform admin) | POST | `/<slug>/reactivate/` | 200, status=active |
| B14 | Archive business (owner) | POST | `/<slug>/archive/` | 200, status=archived |
| B15 | Access suspended business | GET | `/<slug>/` | 200 but with suspended status |
| B16 | Modify suspended business | PATCH | `/<slug>/` | 403 (business is suspended) |
| B17 | Non-member update business | PATCH | `/<slug>/` | 403 permission_denied |
| B18 | Non-owner archive business | POST | `/<slug>/archive/` | 403 permission_denied |

---

### 2.5 RBAC Platform Domain (14 operations)

**Base URL:** `/api/v1/platform/`

**Auth required:** All endpoints require authentication + platform membership

#### Roles

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| RP01 | List platform roles | GET | `/roles/` | 200, array of roles with permissions |
| RP02 | Create custom role | POST | `/roles/` | 201, new role |
| RP03 | Create role with duplicate name | POST | `/roles/` | 409 conflict |
| RP04 | Get role detail | GET | `/roles/<uuid>/` | 200, role with permissions array |
| RP05 | Update role (name, level) | PATCH | `/roles/<uuid>/` | 200, updated role |
| RP06 | Delete custom role | DELETE | `/roles/<uuid>/` | 200/204 |
| RP07 | Assign permission to role | POST | `/roles/<uuid>/permissions/` | 200, permission added |
| RP08 | Remove permission from role | DELETE | `/roles/<uuid>/permissions/` | 200, permission removed |

#### Members

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| RP09 | List platform members | GET | `/members/` | 200, array of memberships |
| RP10 | Get member detail | GET | `/members/<uuid>/` | 200, membership with role |
| RP11 | Change member role | PATCH | `/members/<uuid>/role/` | 200, role updated |
| RP12 | Suspend member | POST | `/members/<uuid>/suspend/` | 200, membership suspended |
| RP13 | Remove member | POST | `/members/<uuid>/remove/` | 200, membership removed |
| RP14 | Leave platform (self) | POST | `/members/leave/` | 200, own membership removed |

---

### 2.6 RBAC Business Domain (14 operations)

**Base URL:** `/api/v1/business/<slug>/`

**Auth required:** All endpoints require authentication + business membership

#### Roles

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| RB01 | List business roles | GET | `/roles/` | 200, array of roles |
| RB02 | Create custom role | POST | `/roles/` | 201, new role |
| RB03 | Get role detail | GET | `/roles/<uuid>/` | 200, role detail |
| RB04 | Update role | PATCH | `/roles/<uuid>/` | 200 |
| RB05 | Delete role | DELETE | `/roles/<uuid>/` | 200/204 |
| RB06 | Assign permission to role | POST | `/roles/<uuid>/permissions/` | 200 |
| RB07 | Remove permission from role | DELETE | `/roles/<uuid>/permissions/` | 200 |

#### Members

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| RB08 | List business members | GET | `/members/` | 200 |
| RB09 | Get member detail | GET | `/members/<uuid>/` | 200 |
| RB10 | Change member role | PATCH | `/members/<uuid>/role/` | 200 |
| RB11 | Suspend member | POST | `/members/<uuid>/suspend/` | 200 |
| RB12 | Remove member | POST | `/members/<uuid>/remove/` | 200 |
| RB13 | Ban member | POST | `/members/<uuid>/ban/` | 200 |
| RB14 | Owner attempts to leave (blocked) | POST | `/members/leave/` | 400 business_rule_violation (owner cannot leave) |

---

### 2.7 RBAC Shared Domain (1 operation)

**Base URL:** `/api/v1/rbac/`

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| RS01 | List all available permissions | GET | `/permissions/` | 200, array of 51 permissions with code, name, category, applicable_scopes |

---

### 2.8 Transaction Domain (12 URL paths, ~13 operations)

**Base URL:** `/api/v1/transactions/`

**Auth required:** All endpoints require authentication

#### Transaction Creation

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| T01 | List user's transactions | GET | `/` | 200, paginated list with filters |
| T02 | Create invitation (platform_membership_invitation) | POST | `/invitation/` | 201, transaction in PENDING state |
| T03 | Create invitation with non-member target | POST | `/invitation/` | 201 (target doesn't need to be member yet) |
| T04 | Create request (business_membership_request) | POST | `/request/` | 201, transaction in PENDING state |
| T05 | Create duplicate transaction | POST | `/invitation/` | 409 conflict |
| T06 | Get form schema for transaction type | GET | `/types/<type>/form/` | 200, form template with fields |
| T07 | Get form schema for type without form | GET | `/types/platform_membership_invitation/form/` | 404 (no form required) |

#### Transaction Lifecycle

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| T08 | Get transaction detail | GET | `/<uuid>/` | 200, full transaction object |
| T09 | Accept transaction (target user) | POST | `/<uuid>/accept/` | 200, state → ACCEPTED, membership created |
| T10 | Deny transaction (target user) | POST | `/<uuid>/deny/` | 200, state → DENIED |
| T11 | Cancel transaction (initiator) | POST | `/<uuid>/cancel/` | 200, state → CANCELLED |
| T12 | Dismiss transaction (any party) | POST | `/<uuid>/dismiss/` | 200, state → DISMISSED |
| T13 | Accept already-accepted transaction | POST | `/<uuid>/accept/` | 400 business_rule_violation |

#### Form-Linked Transactions

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| T14 | Create verification request without form | POST | `/request/` | 400 (form_response_id required) |
| T15 | Create verification request with form response (system form response created via `DBHelper.create_system_form_response()` since system-owned forms can't be created via the forms API) | POST | `/request/` | 201, form_response linked |
| T16 | Request additional info (INFO_REQUESTED) | POST | `/<uuid>/request-info/` | 200, state → INFO_REQUESTED, form response unlocked |
| T17 | Resubmit after info request | POST | `/<uuid>/resubmit/` | 200, state → PENDING again |
| T18 | Get form response for transaction | GET | `/<uuid>/form-response/` | 200, form response object |

#### Auto-Approval

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| T19 | Create auto-approval transaction (business_follow_request) | POST | `/request/` | 201, state immediately ACCEPTED |

---

### 2.9 Forms Domain (13 URL paths, ~17 operations)

**Base URL:** `/api/v1/forms/`

**Auth required:** All endpoints require authentication

#### Template Management

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| F01 | Browse public template library | GET | `/templates/library/` | 200, published templates |
| F02 | List account-scoped templates | GET | `/<account_type>/<account_id>/templates/` | 200, templates for account |
| F03 | Create template (within account) | POST | `/<account_type>/<account_id>/templates/` | 201, new draft template |
| F04 | Get template detail | GET | `/templates/<uuid>/` | 200, template with fields |
| F05 | Update template (draft only) | PATCH | `/templates/<uuid>/` | 200, updated template |
| F06 | Delete template | DELETE | `/templates/<uuid>/` | 200/204 |
| F07 | Publish template (draft → active) | POST | `/templates/<uuid>/publish/` | 200, status=active, version incremented |
| F08 | Archive template (active → archived) | POST | `/templates/<uuid>/archive/` | 200, status=archived |
| F09 | Fork template (create editable copy) | POST | `/templates/<uuid>/fork/` | 201, new draft template based on source |
| F10 | Add field to template | POST | `/templates/<uuid>/fields/` | 201, new field added |

#### Response Lifecycle

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| F11 | List responses for template | GET | `/templates/<uuid>/responses/` | 200, paginated responses |
| F12 | Create response (draft) | POST | `/templates/<uuid>/responses/` | 201, status=draft |
| F13 | Get response detail | GET | `/responses/<uuid>/` | 200, response with data |
| F14 | Update response (draft) | PATCH | `/responses/<uuid>/` | 200, data updated |
| F15 | Submit response (draft → submitted) | POST | `/responses/<uuid>/submit/` | 200, status=submitted, validation enforced |
| F16 | Process response (submitted → processed) | POST | `/responses/<uuid>/process/` | 200 |
| F17 | Void response (Bob — confirmed business member via accepted invitation) | POST | `/responses/<uuid>/void/` | 200, status=voided |
| F18 | List my own responses | GET | `/me/responses/` | 200, only responses by current user |

---

### 2.10 CMS Admin Domain (17 URL paths, ~27 operations)

**Base URL:** `/api/v1/cms/admin/`

**Auth required:** Authentication + platform membership + CMS RBAC permissions

#### Sites

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| C01 | List sites | GET | `/sites/` | 200, sites for platform |
| C02 | Create site | POST | `/sites/` | 201, new site |
| C03 | Create site with duplicate slug | POST | `/sites/` | 409 conflict |
| C04 | Get site detail | GET | `/sites/<slug>/` | 200 |
| C05 | Update site | PATCH | `/sites/<slug>/` | 200 |
| C06 | Delete site | DELETE | `/sites/<slug>/` | 200/204 |

#### Pages

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| C07 | List pages for site | GET | `/pages/` | 200, pages filtered by site |
| C08 | Create page | POST | `/pages/` | 201, new draft page |
| C09 | Get page detail | GET | `/pages/<slug>/` | 200, page with metadata |
| C10 | Update page | PATCH | `/pages/<slug>/` | 200 |
| C11 | Delete page | DELETE | `/pages/<slug>/` | 200/204 |
| C12 | Publish page (draft → published) | POST | `/pages/<slug>/publish/` | 200, validates all required blocks have published_content |
| C13 | Unpublish page (published → draft) | POST | `/pages/<slug>/unpublish/` | 200 |
| C14 | Export page as JSON | GET | `/pages/<slug>/export/` | 200, full page tree as JSON |
| C15 | Import page from JSON | POST | `/pages/<slug>/import/` | 200, content restored from JSON |

#### Templates

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| C16 | List section templates | GET | `/templates/sections/` | 200 |
| C17 | Create section template | POST | `/templates/sections/` | 201 |
| C18 | List block templates | GET | `/templates/blocks/` | 200 |
| C19 | Create block template with schema | POST | `/templates/blocks/` | 201, schema validated |
| C20 | Create block template with invalid schema | POST | `/templates/blocks/` | 400 validation_error |

#### Block Placements (Content)

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| C21 | Get block placement detail | GET | `/block-placements/<uuid>/` | 200, placement with draft_content + published_content |
| C22 | Update draft content (valid schema) | PATCH | `/block-placements/<uuid>/` | 200, draft_content updated, version created |
| C23 | Update draft content (invalid schema) | PATCH | `/block-placements/<uuid>/` | 400, permissive draft validation (warns but saves) |
| C24 | View content version history | GET | `/block-placements/<uuid>/history/` | 200, list of versions |
| C25 | Rollback to previous version | POST | `/block-placements/<uuid>/rollback/<version>/` | 200, draft_content restored |
| C26 | Rollback to non-existent version | POST | `/block-placements/<uuid>/rollback/999/` | 404 |

#### Media

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| C27 | List media files | GET | `/media/files/` | 200, paginated files |
| C28 | Upload media file | POST | `/media/files/` | 201, file metadata saved |
| C29 | Get media file detail | GET | `/media/files/<uuid>/` | 200 |
| C30 | Delete media file (tombstone) | DELETE | `/media/files/<uuid>/` | 200, tombstoned (not soft-deleted) |

#### API Keys

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| C31 | List API keys for site | GET | `/api-keys/` | 200, keys (hash only, no raw key) |
| C32 | Create API key | POST | `/api-keys/` | 201, returns raw key (only time it's visible), `cmsk_` prefix |
| C33 | Get API key detail | GET | `/api-keys/<uuid>/` | 200, key metadata (no raw key) |
| C34 | Revoke (delete) API key | DELETE | `/api-keys/<uuid>/` | 200/204 |

---

### 2.11 CMS Public Domain (2 URL paths)

**Base URL:** `/api/v1/cms/public/`

**Auth:** API key via `X-CMS-API-Key: cmsk_...` header (CMSApiKeyMiddleware)

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| CP01 | Get public site data (valid API key) | GET | `/sites/<slug>/` | 200, site metadata |
| CP02 | Get public site data (no API key) | GET | `/sites/<slug>/` | 401 |
| CP03 | Get public site data (invalid API key) | GET | `/sites/<slug>/` | 401 |
| CP04 | Get public site data (revoked API key) | GET | `/sites/<slug>/` | 401 |
| CP05 | Get published page (valid API key) | GET | `/pages/<slug>/` | 200, page with published_content only |
| CP06 | Get draft page via public API | GET | `/pages/<slug>/` | 404 (only published pages are visible) |
| CP07 | Get published page with full content tree | GET | `/pages/<slug>/` | 200, sections + blocks + published_content |
| CP08 | Verify origin header check (if configured) | GET | `/pages/<slug>/` | Depends on site's `allowed_origins` config |

---

### 2.12 Notifications Domain (4 URL paths, ~6 operations)

**Base URL:** `/api/v1/notifications/`

**Auth required:** All endpoints require authentication

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| N01 | Get notification preferences | GET | `/preferences/` | 200, user's preference list |
| N02 | Update preferences (bulk) | PATCH | `/preferences/` | 200 |
| N03 | Get specific preference | GET | `/preferences/<type>/` | 200 |
| N04 | Update specific preference | PATCH | `/preferences/<type>/` | 200 |
| N05 | Delete specific preference (reset to default) | DELETE | `/preferences/<type>/` | 200/204 |
| N06 | List notification history | GET | `/history/` | 200, paginated notifications |
| N07 | List configurable notification types | GET | `/types/` | 200, `{"types": [...], "count": N}` (11 configurable types) |
| N08 | Update preference for invalid type | PATCH | `/preferences/invalid_type/` | 404 |

---

### 2.13 Email Domain (1 endpoint)

**Base URL:** `/api/v1/email/`

**Auth:** AWS SNS signature verification (no JWT)

| ID | Test Case | Method | Endpoint | Expected |
|----|-----------|--------|----------|----------|
| E01 | SES webhook — delivery notification | POST | `/webhooks/ses/` | 200, delivery status logged |
| E02 | SES webhook — bounce notification | POST | `/webhooks/ses/` | 200, bounce recorded |
| E03 | SES webhook — complaint notification | POST | `/webhooks/ses/` | 200, complaint recorded |

---

## Part 3: Cross-Domain Integration Scenarios

### 3.1 Full User Lifecycle

**Goal:** Verify the complete user journey from registration through deactivation.

| Step | Action | Domain | Expected Outcome |
|------|--------|--------|------------------|
| 1 | Register Alice | Auth (A01) | 201, user created, unverified |
| 2 | Login Alice (before verification) | Auth (A08) | 401 account_not_verified (if enforced) |
| 3 | Verify Alice's email (6-digit code) | Auth (A14) | 200, email verified |
| 4 | Login Alice | Auth (A05) | 200, tokens issued |
| 5 | Get current user | Users (U01) | 200, Alice's profile |
| 6 | Update profile (bio, avatar) | Users (U04, U06) | 200, profile updated |
| 7 | List memberships (empty) | Users (U08) | 200, empty array |
| 8 | Change password | Auth (A24) | 200 |
| 9 | Login with old password | Auth (A06) | 401 invalid_credentials |
| 10 | Login with new password | Auth (A05) | 200, tokens issued |
| 11 | Deactivate account | Users (U11) | 200 |
| 12 | Login after deactivation | Auth | 401 account_inactive |

---

### 3.2 Business Lifecycle with RBAC

**Goal:** Full business creation, member management, and lifecycle operations.

**Prerequisites:** Alice is a registered, verified user. Platform is configured with Alice as owner.

| Step | Action | Domain | Expected Outcome |
|------|--------|--------|------------------|
| 1 | Alice creates business "test-biz" | Business (B02) | 201, business created, Alice is owner |
| 2 | Verify Alice is owner | RBAC Business (RB08) | 200, Alice listed with owner role |
| 3 | Alice creates custom role "editor" | RBAC Business (RB02) | 201, role created |
| 4 | Alice assigns permissions to "editor" | RBAC Business (RB06) | 200, permissions added |
| 5 | Alice invites Bob to business | Transaction (T02) | 201, invitation pending |
| 6 | Bob accepts invitation | Transaction (T09) | 200, membership created |
| 7 | Verify Bob is member | RBAC Business (RB08) | 200, Bob listed with default role |
| 8 | Alice changes Bob's role to "editor" | RBAC Business (RB10) | 200, role changed |
| 9 | Bob accesses business with editor permissions | Business (B07) | 200 (if editor has `can_edit_business`) |
| 10 | Bob tries operation without permission | Business (B14) | 403 permission_denied |
| 11 | Alice suspends Bob | RBAC Business (RB11) | 200, Bob's membership suspended |
| 12 | Bob tries to access business | Business (B06) | 403 (membership suspended) |
| 13 | Alice removes Bob | RBAC Business (RB12) | 200, Bob's membership removed |
| 14 | Bob no longer listed in members | RBAC Business (RB08) | 200, Bob not in list |
| 15 | Alice updates business slug | Business (B11) | 200, slug changed |
| 16 | Old slug returns redirect info | Business (B06) | 301/200 with new slug |

---

### 3.3 Transaction + Form Integration

**Goal:** Verify the complete form-linked transaction workflow including INFO_REQUESTED.

**Prerequisites:** Alice is platform admin. Bob has a business that needs verification.

| Step | Action | Domain | Expected Outcome |
|------|--------|--------|------------------|
| 1 | Get form schema for business_verification_request | Transaction (T06) | 200, system-business-verification template with 8 fields |
| 2 | Create form response (draft) | Forms (F12) | 201, draft response |
| 3 | Fill form data (legal_name, registration_number, etc.) | Forms (F14) | 200, data saved |
| 4 | Submit form response | Forms (F15) | 200, status=submitted, validation passes |
| 5 | Create verification request with form_response_id | Transaction (T15) | 201, transaction PENDING, form response linked |
| 6 | Platform admin (Alice) views transaction with form | Transaction (T08, T18) | 200, transaction + form response visible |
| 7 | Alice requests additional info | Transaction (T16) | 200, state → INFO_REQUESTED |
| 8 | Form response is unlocked for editing | Forms (F14) | 200, can update data |
| 9 | Bob updates form data | Forms (F14) | 200 |
| 10 | Bob resubmits transaction | Transaction (T17) | 200, state → PENDING again |
| 11 | Alice approves verification | Transaction (T09) | 200, state → ACCEPTED |

---

### 3.4 CMS Publish Flow

**Goal:** Full CMS content creation through public API consumption.

**Prerequisites:** Alice is platform owner with full CMS permissions (from Phase 03). A fresh user will NOT work — CMS endpoints require platform membership with CMS RBAC permissions.

| Step | Action | Domain | Expected Outcome |
|------|--------|--------|------------------|
| 1 | Create site "main-site" | CMS Admin (C02) | 201, site created |
| 2 | Create section template "hero" | CMS Admin (C17) | 201 |
| 3 | Create block template "text-block" with schema | CMS Admin (C19) | 201, schema defined |
| 4 | Create page "home" | CMS Admin (C08) | 201, draft page |
| 5 | Verify page has section + block placements | CMS Admin (C09) | 200, structural tree |
| 6 | Edit block placement draft_content | CMS Admin (C22) | 200, draft saved, version 1 created |
| 7 | Edit draft_content again | CMS Admin (C22) | 200, version 2 created (if > 30s) |
| 8 | View content history | CMS Admin (C24) | 200, version list |
| 9 | Rollback to version 1 | CMS Admin (C25) | 200, draft restored |
| 10 | Publish page | CMS Admin (C12) | 200, draft_content → published_content |
| 11 | Create API key for site | CMS Admin (C32) | 201, returns raw key `cmsk_...` |
| 12 | Public API: get page (valid key) | CMS Public (CP05) | 200, published_content visible |
| 13 | Public API: verify no draft content exposed | CMS Public (CP05) | Response only contains published_content |
| 14 | Unpublish page | CMS Admin (C13) | 200, page status → draft |
| 15 | Public API: get unpublished page | CMS Public (CP06) | 404 (not published) |

---

### 3.5 Permission Boundaries

**Goal:** Verify that authorization is consistently enforced across all domains.

**Prerequisites:** Nobody is a registered user with no memberships.

| Step | Action | Domain | Expected Outcome |
|------|--------|--------|------------------|
| 1 | Nobody accesses platform account | Platform (P07) | 403 |
| 2 | Nobody accesses business detail | Business | 200 (public read may be allowed) |
| 3 | Nobody tries to update business | Business (B17) | 403 |
| 4 | Nobody tries to list business members | RBAC Business | 403 |
| 5 | Nobody tries to create a form template | Forms | 403 |
| 6 | Nobody tries to access CMS admin | CMS Admin | 403 |
| 7 | Use expired access token on any endpoint | Any | 401 token_expired |
| 8 | Use malformed JWT on any endpoint | Any | 401 token_invalid |
| 9 | Use blacklisted token (after logout) | Any | 401 |
| 10 | Use token from deactivated account | Any | 401 account_inactive |

---

### 3.6 Ownership Transfer

**Goal:** Verify ownership transfer for business accounts.

**Prerequisites:** Alice owns "test-biz", Bob is a member.

| Step | Action | Domain | Expected Outcome |
|------|--------|--------|------------------|
| 1 | Alice creates ownership transfer to Bob | Transaction | 201, business_ownership_transfer pending |
| 2 | Bob accepts transfer | Transaction (T09) | 200, ownership transferred |
| 3 | Verify Bob is now owner | RBAC Business (RB09) | 200, Bob has owner role |
| 4 | Verify Alice is demoted to member | RBAC Business (RB09) | 200, Alice has member role |
| 5 | Alice tries to leave business | RBAC Business | 200 (Alice can leave since she's no longer owner) |

---

### 3.7 Platform Admin Lifecycle

**Goal:** Full platform membership, role management, and CMS access flow.

**Prerequisites:** Platform is configured. Admin (superuser) is platform owner.

| Step | Action | Domain | Expected Outcome |
|------|--------|--------|------------------|
| 1 | Admin invites Alice to platform | Transaction (T02) | 201, platform_membership_invitation |
| 2 | Alice accepts invitation | Transaction (T09) | 200, platform membership created |
| 3 | Verify Alice is platform member | RBAC Platform (RP09) | 200, Alice listed |
| 4 | Admin creates "cms-editor" role | RBAC Platform (RP02) | 201, role created |
| 5 | Admin assigns CMS permissions to role | RBAC Platform (RP07) | 200 (can_create_cms_site, can_edit_cms_content, etc.) |
| 6 | Admin assigns Alice the "cms-editor" role | RBAC Platform (RP11) | 200 |
| 7 | Alice creates CMS site | CMS Admin (C02) | 201, authorized via role permissions |
| 8 | Alice creates page and edits content | CMS Admin (C08, C22) | 201, 200 |
| 9 | Admin suspends Alice's membership | RBAC Platform (RP12) | 200 |
| 10 | Alice tries to access CMS admin | CMS Admin | 403 (membership suspended) |
| 11 | Admin removes Alice from platform | RBAC Platform (RP13) | 200 |

---

## Part 4: Negative Testing

### 4.1 Authentication Failures

| ID | Test Case | Expected |
|----|-----------|----------|
| NEG-A01 | Request without Authorization header | 401 |
| NEG-A02 | Request with `Authorization: Bearer` (no token) | 401 |
| NEG-A03 | Request with malformed JWT (invalid base64) | 401 token_invalid |
| NEG-A04 | Request with expired access token | 401 token_expired |
| NEG-A05 | Request with token signed by wrong secret | 401 token_invalid |
| NEG-A06 | Request with blacklisted token (after logout) | 401 |
| NEG-A07 | Refresh with expired refresh token | 401 token_expired |
| NEG-A08 | Refresh with already-used refresh token | 401 token_already_used |
| NEG-A09 | Request from deactivated account | 401 account_inactive |
| NEG-A10 | Request from unverified account (where enforced) | 401 account_not_verified |

### 4.2 Authorization Failures

| ID | Test Case | Expected |
|----|-----------|----------|
| NEG-B01 | Non-member accesses business management endpoints | 403 permission_denied |
| NEG-B02 | Member without `can_edit_business` updates business | 403 permission_denied |
| NEG-B03 | Non-owner tries to archive business | 403 permission_denied |
| NEG-B04 | Non-owner tries to transfer ownership | 403 permission_denied |
| NEG-B05 | Non-platform-member accesses platform endpoints | 403 permission_denied |
| NEG-B06 | Member without CMS permissions accesses CMS admin | 403 permission_denied |
| NEG-B07 | Suspended member accesses any protected endpoint | 403 permission_denied |
| NEG-B08 | Banned member accesses any protected endpoint | 403 permission_denied |

### 4.3 Validation Failures

| ID | Test Case | Expected |
|----|-----------|----------|
| NEG-V01 | Create business with empty name | 400 validation_error with field details |
| NEG-V02 | Create business with slug > 50 chars | 400 validation_error |
| NEG-V03 | Update profile with invalid URL | 400 validation_error |
| NEG-V04 | Create form template with invalid field_type | 400 validation_error |
| NEG-V05 | Submit form response with missing required fields | 400 validation_error |
| NEG-V06 | Create CMS block template with invalid JSON schema | 400 validation_error |
| NEG-V07 | Publish page with blocks missing published_content | 400 business_rule_violation |
| NEG-V08 | Upload media file exceeding size limit | 400 validation_error |

### 4.4 Conflict Scenarios

| ID | Test Case | Expected |
|----|-----------|----------|
| NEG-C01 | Create business with existing slug | 409 conflict |
| NEG-C02 | Create user with existing email | 409 conflict |
| NEG-C03 | Accept already-accepted transaction | 400 business_rule_violation |
| NEG-C04 | Accept already-denied transaction | 400 business_rule_violation |
| NEG-C05 | Configure platform twice | 409 conflict |
| NEG-C06 | Create duplicate role name in same account | 409 conflict |
| NEG-C07 | Invite user who is already an active member of the business | 409 conflict (membership existence check) |

### 4.5 Resource Not Found

| ID | Test Case | Expected |
|----|-----------|----------|
| NEG-N01 | Get business with non-existent slug | 404 not_found |
| NEG-N02 | Get transaction with random UUID | 404 not_found |
| NEG-N03 | Get form template with random UUID | 404 not_found |
| NEG-N04 | Get CMS page with non-existent slug | 404 not_found |
| NEG-N05 | Rollback to non-existent version number | 404 not_found |
| NEG-N06 | Get membership with random UUID | 404 not_found |

### 4.6 Rate Limiting

| ID | Test Case | Expected |
|----|-----------|----------|
| NEG-R01 | Rapid login attempts (brute force) | 429 rate_limit_exceeded after threshold |
| NEG-R02 | Rapid password reset requests | 429 rate_limit_exceeded |

---

## Part 5: PostgreSQL-Specific Verification

### 5.1 JSONB Operations

| ID | Test Case | Verification |
|----|-----------|--------------|
| PG-J01 | Platform settings merge (PATCH) | Old keys preserved, new keys added, nested merge works |
| PG-J02 | Business settings merge (PATCH) | Same as PG-J01 |
| PG-J03 | Form response data storage | Complex nested data stored/retrieved correctly |
| PG-J04 | Form response indexed fields | Indexed values queryable via GIN index |
| PG-J05 | CMS block placement draft_content | Complex content JSON stored, schema validated |
| PG-J06 | CMS block placement published_content | Published content accurately copies draft |
| PG-J07 | Transaction payload/metadata JSONB | Nested objects with varied types |
| PG-J08 | Notification preferences JSONB | Key-value preferences merge correctly |

### 5.2 UUID FK Integrity

| ID | Test Case | Verification |
|----|-----------|--------------|
| PG-F01 | Create transaction with valid target_user_id | FK resolved, no error |
| PG-F02 | Create transaction with non-existent user UUID | 400 or IntegrityError handled gracefully |
| PG-F03 | Create form response for non-existent template | 404 |
| PG-F04 | Create CMS page for non-existent site | 400 or 404 |
| PG-F05 | Reference soft-deleted resource as FK | Appropriate error (not dangling ref) |

### 5.3 Unique Constraints with Soft-Delete

| ID | Test Case | Verification |
|----|-----------|--------------|
| PG-U01 | Create business, delete, create with same slug | Should succeed (unique constraint excludes soft-deleted) |
| PG-U02 | Create role, delete, create with same name | Should succeed |
| PG-U03 | Create CMS site, delete, create with same slug | Should succeed |
| PG-U04 | Register user, deactivate, register same email | Depends on implementation (may or may not allow) |

### 5.4 Transaction Isolation

| ID | Test Case | Verification |
|----|-----------|--------------|
| PG-T01 | Concurrent page publish (same page) | Only one succeeds, other gets conflict |
| PG-T02 | Concurrent transaction accept (same invitation) | Only one creates membership |
| PG-T03 | Concurrent slug change (same business) | No duplicate slugs |
| PG-T04 | Concurrent content version creation | Version numbers are sequential, no duplicates |

---

## Part 6: Redis-Specific Verification

### 6.1 Permission Caching

| ID | Test Case | Verification |
|----|-----------|--------------|
| RD-P01 | First permission check (cache miss) | Permission fetched from DB, cached in Redis |
| RD-P02 | Second permission check (cache hit) | Permission served from Redis (verify with Redis CLI) |
| RD-P03 | Role change invalidates cache | After changing role, old permissions not served |
| RD-P04 | Permission removal invalidates cache | After removing permission from role, access denied |
| RD-P05 | Cache TTL expiry | After TTL, permissions re-fetched from DB |

### 6.2 JTI Blacklist

| ID | Test Case | Verification |
|----|-----------|--------------|
| RD-J01 | Logout adds JTI to Redis blacklist | `redis-cli GET jti:<jti>` returns entry |
| RD-J02 | Logout-all blacklists all JTIs | All session JTIs present in Redis |
| RD-J03 | Blacklisted token rejected | Request with blacklisted JTI returns 401 |
| RD-J04 | JTI TTL matches token expiry | Redis TTL on JTI key ≈ remaining token lifetime |
| RD-J05 | Expired JTI auto-cleaned by Redis | After token expiry, JTI key no longer in Redis |

### 6.3 Rate Limiting

| ID | Test Case | Verification |
|----|-----------|--------------|
| RD-R01 | Rate limit counter in Redis | `redis-cli KEYS *rate*` shows rate limit keys |
| RD-R02 | Counter increments per request | Value increases with each request |
| RD-R03 | Window reset after TTL | Counter resets after rate limit window expires |
| RD-R04 | Per-IP isolation | Different IPs have separate counters |

### 6.4 Celery Task Execution

| ID | Test Case | Verification |
|----|-----------|--------------|
| RD-C01 | Email verification triggers Celery task | Task appears in Celery logs, email logged |
| RD-C02 | Password reset triggers Celery task | Task executed, email logged |
| RD-C03 | Notification triggers Celery task | Notification created asynchronously |
| RD-C04 | Failed task retries | Task retried per retry policy |

---

## Appendix A: Test Case Summary

| Part | Category | Planned | Implemented | IDs |
|------|----------|---------|-------------|-----|
| 2.1 | Auth | 31 | 31 | A01–A31 |
| 2.2 | Users | 11 | 11 | U01–U11 |
| 2.3 | Platform | 9 | 10 | P01–P09 (+P10) |
| 2.4 | Business | 18 | 32 | B01–B18 (+RB tests combined in Phase 04) |
| 2.5 | RBAC Platform | 14 | 15 | RP01–RP14 (+RS01) |
| 2.6 | RBAC Business | 14 | — | (combined into Phase 04) |
| 2.7 | RBAC Shared | 1 | — | (combined into Phase 05) |
| 2.8 | Transaction | 19 | 19 | T01–T19 |
| 2.9 | Forms | 18 | 18 | F01–F18 |
| 2.10 | CMS Admin | 34 | 42 | C01–C34 (+CP tests combined in Phase 08) |
| 2.11 | CMS Public | 8 | — | (combined into Phase 08) |
| 2.12 | Notifications | 8 | 11 | N01–N08 (+E01–E03) |
| 2.13 | Email | 3 | — | (combined into Phase 09) |
| 3 | Cross-Domain (7 workflows) | ~80 steps | 7 | WF1–WF7 |
| 4 | Negative Testing | 32 | 41 | NEG-A01–NEG-R02 (expanded) |
| 5 | PostgreSQL | 19 | 39 | PG + Redis combined in Phase 12 |
| 6 | Redis | 14 | — | (combined into Phase 12) |
| **Total** | | **~253 + ~80 steps** | **276 tests** | **275 passed, 1 skipped (A27)** |

**Note:** The implemented test suite consolidates some planned phases (e.g., RBAC Business tests are in Phase 04 alongside Business tests, CMS Public tests are in Phase 08). Total implemented: 276 tests across 12 phase files.

## Appendix B: Execution Order Recommendation

1. **Phase 1 — Auth + Users** (A01–A31, U01–U11)
   - Register test users, verify auth flows work before anything else

2. **Phase 2 — Platform** (P01–P09, RP01–RP14)
   - Configure platform, create roles, establish admin access

3. **Phase 3 — Business + RBAC** (B01–B18, RB01–RB14, RS01)
   - Create businesses, manage members, verify permission enforcement

4. **Phase 4 — Transaction** (T01–T19)
   - Test all transaction types, state machine transitions

5. **Phase 5 — Forms** (F01–F18)
   - Template management, response lifecycle

6. **Phase 6 — CMS** (C01–C34, CP01–CP08)
   - Full CMS workflow including public API

7. **Phase 7 — Notifications + Email** (N01–N08, E01–E03)
   - Preference management, webhook handling

8. **Phase 8 — Cross-Domain Workflows** (Part 3)
   - Run 7 integration scenarios after individual domains pass

9. **Phase 9 — Negative Testing** (Part 4)
   - Systematic error path validation

10. **Phase 10 — Infrastructure** (Parts 5–6)
    - PostgreSQL JSONB, unique constraints, Redis caching verification

---

## Appendix C: Implementation Notes & Gotchas

Lessons learned during 10 test runs across 4 sessions (see `test_execution_report.md` for full details).

### Rate Limiting

DRF throttle rates (`LoginRateThrottle` 5/min, `PasswordResetRateThrottle` 3/hr) are hit during test sequences because many auth tests run within seconds. The `local_docker.py` settings override these to 100/min and 100/hr respectively.

### System-Owned Forms

The 3 system forms (`system-business-verification`, `system-business-creation`, `system-platform-staff-application`) have `owner_type="system"` and `owner_id=None`. The forms API's membership check (`get_membership_or_403()`) cannot resolve `account_type="system"`, so form responses for system forms must be created via `DBHelper.create_system_form_response()` — direct PostgreSQL inserts.

### CMS API Key Header

The CMS public API uses `X-CMS-API-Key` (not `X-API-Key`) for authentication. API keys use `cmsk_` prefix and SHA-256 hashing.

### Notification Types Response Format

`GET /notifications/types/` returns `{"types": [...], "count": N}` — the top-level key is `types`, not `results`.

### User Membership Requirements

- **F17 (void form response):** Must use Bob (accepted invitation in T09), not Carol (denied in T10 — not a member).
- **WF4 (CMS publish workflow):** Must use Alice (platform owner from Phase 03), not a fresh user (no platform membership = 403).
- **NEG-C07 (duplicate invitation):** `create_invitation()` now checks `MembershipSelector.get_active_membership_for_user_account()` before creating — returns 409 if target is already an active member.

### PostgreSQL vs SQLite Differences

5 production bugs were invisible to unit tests (SQLite) but surfaced in integration tests (PostgreSQL):
1. `select_for_update()` + nullable FK → `NotSupportedError` (PostgreSQL enforces JOIN types, SQLite ignores)
2. UUID not JSON-serializable in JWT (Python `uuid.UUID` objects)
3. `@transaction.atomic` rollback behavior (PostgreSQL commits differ from SQLite)
4. Missing `log.save()` (data persistence timing)
5. Wrong `AuditLog.Action` enum name — masked by monkey-patch in unit tests

### Deactivation Endpoint

User deactivation uses `DELETE /users/me/` (not `PATCH` or `POST`). After deactivation, login returns 401 `account_inactive`.
