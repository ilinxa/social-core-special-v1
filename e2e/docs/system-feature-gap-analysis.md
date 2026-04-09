# System Feature Gap Analysis — E2E Test Coverage

> **Generated**: 2026-03-27
> **Method**: Deep-dive code audit of every backend model, service, endpoint, frontend route, component, and business rule — cross-referenced against `architecture.md` L1/L2/L3 catalogs.
> **Purpose**: Feature-by-feature assessment of what the E2E architecture covers vs what it misses.

---

## Reading Guide

**Coverage status legend:**

| Symbol | Meaning |
|--------|---------|
| `[L1]` | Covered by L1 smoke test |
| `[L2]` | Covered by L2 workflow |
| `[L3]` | Covered by L3 persona scenario |
| `[GAP]` | **Not covered anywhere** — must be added |
| `[PARTIAL]` | Partially covered — key aspects missing |

---

## 1. AUTH SYSTEM

### 1.1 Backend: 5 models, 4 services, 17+ endpoints

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **Registration** | Valid registration | `[L1]` register.spec.ts | OK |
| | Duplicate email rejection | `[L1]` register.spec.ts | OK |
| | Invalid fields validation | `[L1]` register.spec.ts | OK |
| | Username auto-generation | `[GAP]` | Registration requires `username` field — not tested |
| | `referred_by` parameter | `[GAP]` | Referral tracking on registration not tested |
| | Deployment limit `max_users` | `[GAP]` | VG limit on user creation not tested |
| **Login** | Valid login → redirect | `[L1]` login.spec.ts | OK |
| | Invalid credentials → error | `[L1]` login.spec.ts | OK |
| | Empty fields validation | `[L1]` login.spec.ts | OK |
| | LoginRateThrottle (5/min) | `[L3]` Eve step 3 | Partially via account lockout |
| **Logout** | Single device logout | `[L1]` logout.spec.ts | OK |
| | Logout-all (all sessions) | `[GAP]` | API exists, UI button exists — not tested |
| **Email Verification** | Code-based verification | `[GAP]` *(Appendix D flagged)* | 3 routes exist, zero L1 tests |
| | Magic link verification | `[GAP]` | GET endpoint — not tested |
| | Resend verification | `[GAP]` | Separate route/API — not tested |
| | Verification success page | `[GAP]` | Route exists — not tested |
| | Rate limiting (3/hour) | `[GAP]` | PasswordResetRateThrottle on resend |
| **Password Reset** | Request reset email | `[L1]` password-reset.spec.ts | OK |
| | Confirm reset + login | `[L1]` password-reset.spec.ts | OK |
| | Rate limiting | `[GAP]` | PasswordResetRateThrottle not tested from UI |
| **Password Change** | Change while logged in | `[GAP]` *(Appendix D flagged)* | API + component exists |
| | Current password verification | `[GAP]` | Service validates current password |
| | Logout other sessions option | `[GAP]` | Optional flag on password change |
| **Session Management** | List active sessions | `[L1]` session-management.spec.ts | OK |
| | Session info display | `[L1]` session-management.spec.ts | OK |
| | Revoke specific session | `[GAP]` | DELETE endpoint exists, not tested |
| | Max 5 sessions enforcement | `[GAP]` | Oldest auto-revoked — never tested |
| | New device notification | `[GAP]` | Email sent on new device login |
| **OAuth (Google)** | Start Google OAuth flow | `[GAP]` *(Appendix D flagged)* | Full API + redirect flow exists |
| | Google callback → auth | `[GAP]` | PKCE + state verification |
| | Auto-verify from Google | `[GAP]` | Email auto-verified if Google verified |
| **OAuth (Apple)** | Start Apple Sign In | `[GAP]` | Full API exists |
| | Apple callback (POST!) | `[GAP]` | Form-encoded callback, not JSON |
| | Apple first-login user data | `[GAP]` | Apple only sends name on first sign-in |
| **Account Lockout** | 10 failed attempts → lockout | `[L3]` Eve step 3 | OK |
| | Lockout expiry (15 min) | `[L3]` Eve step 4 | OK |
| | Retry-After header display | `[L3]` Eve step 3 | OK |
| **Token Security** | JWT access (15min) + refresh (7day) | `[PARTIAL]` | Implicitly tested via login/refresh |
| | Token rotation on refresh | `[GAP]` | Rotation + old token invalidation |
| | Reuse detection → logout_all | `[GAP]` | Critical security feature |
| | JTI blacklist (Redis) | `[GAP]` | Immediate revocation mechanism |
| | Token expiry → silent refresh | `[L3]` Eve step 16 | OK |

### 1.2 Frontend: 7 auth routes

| Route | Coverage | Notes |
|-------|----------|-------|
| `/login` | `[L1]` | OK |
| `/register` | `[L1]` | OK |
| `/verify-email` | `[GAP]` | *(Appendix D flagged)* |
| `/verify-success` | `[GAP]` | *(Appendix D flagged)* |
| `/forgot-password` | `[L1]` | OK |
| `/reset-password` | `[L1]` | OK |
| `/resend-verification` | `[GAP]` | *(Appendix D flagged)* |

### 1.3 Auth Gap Summary

**Existing coverage**: 5 L1 + W1 + Alice/Eve persona steps = login, register, logout, reset, lockout
**Gaps**: 23 features uncovered. Critical: email verification flow (3 routes), OAuth (2 providers), session revocation, logout-all, token reuse detection, password change.

---

## 2. USERS SYSTEM

### 2.1 Backend: 2 models (User + UserProfile), 14 service methods, 13 endpoints

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **Profile View** | Own profile page | `[L1]` profile-view.spec.ts | OK |
| | Avatar display | `[L1]` profile-view.spec.ts | OK |
| | Bio and details | `[L1]` profile-view.spec.ts | OK |
| **Profile Edit** | Edit fields → save | `[L1]` profile-edit.spec.ts | OK |
| | Cancel → no changes | `[L1]` profile-edit.spec.ts | OK |
| | All 10 profile fields | `[PARTIAL]` | Doc says "edit fields" but doesn't list all: first_name, last_name, phone, timezone, language, bio, country, city, tags, is_public |
| **Avatar Upload** | Upload avatar image | `[PARTIAL]` | Mentioned in Bob step 3, not L1 |
| | Delete avatar | `[GAP]` | DELETE endpoint exists |
| | Max 5MB enforcement | `[GAP]` | MIME whitelist + size limit |
| | Invalid file type rejection | `[L3]` Eve step 10 | OK |
| **Cover Image** | Upload cover image | `[GAP]` *(Appendix D flagged)* | Separate API + component |
| | Delete cover image | `[GAP]` | DELETE endpoint exists |
| **Username** | Change username | `[GAP]` *(Appendix D flagged)* | Real-time validation component exists |
| | Check availability (debounced) | `[GAP]` | useUsernameCheck hook |
| | Reserved name rejection | `[GAP]` | 40+ reserved names |
| | Format validation (5-30 chars) | `[GAP]` | Alphanumeric + underscores only |
| **Email Change** | Change email → unverified | `[GAP]` | API exists, re-verification required |
| **Other User Profile** | View `/users/[username]` | `[GAP]` *(Appendix D flagged)* | Different from `/profile` (self) |
| | Public vs private profile | `[L3]` Alice step 12 | Visibility tiers tested |
| | `_permissions` injection | `[GAP]` | can_connect, can_disconnect in response |
| | `_relationship` injection | `[GAP]` | membership_status, follow_status, etc. |
| | Limited profile (is_public=False) | `[GAP]` | Returns only username, avatar, display_name |
| | Inactive user → 404 | `[GAP]` | Deactivated users return 404 |
| **Account Deactivation** | Deactivate account | `[GAP]` *(Appendix D flagged)* | Sets is_active=False, revokes sessions |
| | Reactivate account | `[GAP]` | Sets is_active=True, is_verified stays False |
| **Settings** | Settings page | `[L1]` settings.spec.ts | OK |
| | Notification preferences | `[L1]` settings.spec.ts | OK |
| | Changes persist re-login | `[L1]` settings.spec.ts | OK |
| **Home Feed** | `/home` renders | `[GAP]` *(Appendix D flagged)* | Primary landing page |
| **Activity Feed** | `/activity` list | `[GAP]` *(Appendix D flagged)* | Full feature |
| | `/activity/[id]` detail | `[GAP]` *(Appendix D flagged)* | Activity detail page |
| **Social Links** | Social links editor | `[GAP]` *(Appendix D flagged)* | SocialLinksEditor component |

### 2.2 Frontend Routes

| Route | Coverage | Notes |
|-------|----------|-------|
| `/profile` | `[L1]` | OK |
| `/profile/edit` | `[L1]` | *(Note: doc treats as same, they are separate routes)* |
| `/users/[username]` | `[GAP]` | *(Appendix D flagged)* |
| `/sessions` | `[L1]` | OK |
| `/settings` | `[L1]` | OK |
| `/home` | `[GAP]` | *(Appendix D flagged)* |
| `/activity` | `[GAP]` | *(Appendix D flagged)* |
| `/activity/[id]` | `[GAP]` | *(Appendix D flagged)* |

### 2.3 Users Gap Summary

**Existing coverage**: 3 L1 + W1 + persona steps for profile
**Gaps**: 21 features uncovered. Critical: home feed, activity feed, other user profiles, username change, avatar/cover management, account deactivation, email change.

---

## 3. ORGANIZATION — BUSINESS

### 3.1 Backend: BusinessAccount model (20+ fields), BusinessProfile, 10+ service methods

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **Business Creation** | Create via form | `[L1]` create-business.spec.ts | OK |
| | Required fields enforced | `[L1]` create-business.spec.ts | OK |
| | Slug generation/uniqueness | `[GAP]` | Auto-slug from legal_name |
| | `can_create_business` permission | `[GAP]` | User flag controls creation ability |
| | VG limit `max_businesses` | `[GAP]` | Deployment limit |
| | VG limit `max_businesses_per_user` | `[GAP]` | Per-user limit |
| **Business Profile** | Public view (anonymous) | `[L1]` profile-public.spec.ts | OK |
| | Public fields visible | `[L1]` profile-public.spec.ts | OK |
| | Private fields hidden | `[L1]` profile-public.spec.ts | OK |
| | `_permissions` injection | `[L1]` profile-public.spec.ts | OK |
| | `_relationship` injection | `[GAP]` | membership_status + active_transaction + follow_status |
| | T2 visibility (contact_email, contact_phone) | `[GAP]` | Configurable per-field visibility |
| | Visibility settings configuration | `[GAP]` *(Appendix D flagged)* | PATCH visibility overrides |
| **Console Dashboard** | Renders with stats | `[L1]` console-dashboard.spec.ts | OK |
| | Navigation works | `[L1]` console-dashboard.spec.ts | OK |
| **Business Update** | Update legal_name, description, etc. | `[L1]` business-settings.spec.ts | OK |
| | Update slug | `[GAP]` | Owner-only, separate endpoint |
| | Slug history tracking | `[GAP]` | BusinessSlugHistory model |
| **Business Lifecycle** | Suspend (staff action) | `[GAP]` *(Appendix D flagged)* | Status transition, members blocked |
| | Reactivate (staff action) | `[GAP]` *(Appendix D flagged)* | Restore from suspended |
| | Archive (owner action) | `[GAP]` *(Appendix D flagged)* | Preserve data, deactivate |
| | Delete (soft) | `[GAP]` | Superuser/owner only |
| | Suspended business → member access blocked | `[GAP]` | Critical user experience |
| **Business Verification** | Verify (staff action) | `[GAP]` | Staff/superuser only |
| | Verification badge display | `[GAP]` | is_verified field in UI |
| **Member Management** | Member list renders | `[L1]` member-management.spec.ts | OK |
| | Role badges shown | `[L1]` member-management.spec.ts | OK |
| | Member count accurate | `[L1]` member-management.spec.ts | OK |
| | Member detail page | `[GAP]` | `/bconsole/[slug]/members/[id]` route exists |
| | `_permissions` on member detail | `[GAP]` | can_change_role, can_suspend, etc. |
| **Member Actions** | Suspend member | `[GAP]` *(Appendix D flagged)* | POST endpoint + status transition |
| | Ban member | `[GAP]` *(Appendix D flagged)* | POST endpoint + status transition |
| | Remove member | `[L2]` W15 step 5 | Partially (quota context) |
| | Reactivate member | `[GAP]` *(Appendix D flagged)* | POST endpoint + status transition |
| **Role Management** | List roles | `[L1]` role-management.spec.ts | OK |
| | Create custom role | `[L2]` W10, `[L3]` Bob step 6 | OK |
| | Edit role | `[GAP]` | PATCH endpoint exists |
| | Delete role | `[GAP]` | DELETE endpoint, must have no members |
| | Permission checkboxes | `[L1]` role-management.spec.ts | OK |
| | Dominance rule enforcement | `[GAP]` | actor.level < target.level |
| | Owner invincibility | `[GAP]` | Cannot act on owner |
| **Approved Creators** | Platform approved creators list | `[GAP]` *(Appendix D flagged)* | Platform feature |
| | Business creation request | `[GAP]` | useBusinessCreationRequest hook |

### 3.2 Frontend: 29 business console routes

| Route Group | Covered | Missing |
|-------------|---------|---------|
| Dashboard (2) | `[L1]` dashboard, profile | — |
| Members (3) | `[L1]` list only | member detail, role assignment |
| Roles (1) | `[L1]` | — |
| Network (2) | `[GAP]` both | followers page, connections page |
| Content (3) | `[GAP]` all 3 | CMS content, media, forms overview |
| Forms (6) | `[L1]` 1 of 6 | templates/new, templates/[id], library, responses, responses/[id] |
| Transactions (6) | `[L1]` 1 of 6 | requests, requests/[id], invitations, invitations/[id], settings |
| Chat (1) | `[L1]` via chat tests | — |
| Operations (2) | `[GAP]` both | audit, settings |

### 3.3 Business Gap Summary

**Existing coverage**: 6 L1 + W2/W4/W6/W10/W13-W15 + Bob/Frank personas
**Gaps**: 28 features uncovered. Critical: business lifecycle (suspend/reactivate/archive), member actions (suspend/ban/reactivate), member detail page, business network management pages, audit log, visibility settings, slug management, approved creators.

---

## 4. ORGANIZATION — PLATFORM

### 4.1 Backend: PlatformAccount (singleton), PlatformProfile, 3 service methods

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **Platform Configure** | One-time setup | `[GAP]` | POST endpoint, superuser only |
| | Creates singleton + roles | `[GAP]` | PlatformAccountService.configure() |
| **Platform Profile** | Public view | `[L1]` platform profile-public.spec.ts | OK |
| | Update profile | `[GAP]` | PATCH name, tagline, logo, colors, etc. |
| | Logo/favicon upload | `[GAP]` | Image upload fields |
| | Social links | `[GAP]` | JSONField social links |
| **Platform Settings** | Update settings | `[L3]` Carol step 9 | OK |
| | open_member_request toggle | `[GAP]` | Controls platform join requests |
| **Console Dashboard** | Dashboard renders | `[L1]` console-dashboard.spec.ts | OK |
| | Stats accurate | `[L1]` console-dashboard.spec.ts | OK |
| **Business Management** | List all businesses | `[L1]` platform-management.spec.ts | OK |
| | View business detail | `[L3]` Carol step 4 | OK |
| | Suspend business (cross-entity) | `[GAP]` | Platform admin suspends business |
| | Reactivate business | `[GAP]` | Platform admin action |
| **Platform Members** | Member list | `[L1]` platform-management.spec.ts | OK |
| | Member detail | `[GAP]` | `/pconsole/members/[id]` route |
| | Create platform role | `[L3]` Carol step 6 | OK |
| | Platform role assignment | `[GAP]` | `/pconsole/members/roles/[id]` |
| **Approved Creators** | List approved creators | `[GAP]` *(Appendix D flagged)* | `/pconsole/approved-creators` |
| | Grant/revoke business creation | `[GAP]` | Platform governance feature |

### 4.2 Frontend: 28 platform console routes

| Route Group | Covered | Missing |
|-------------|---------|---------|
| Dashboard (2) | `[L1]` both | — |
| Management (4+) | `[L1]` list only | businesses detail, approved-creators, member detail, role assignment |
| CMS (4) | `[GAP]` all 4 | sites, templates, api-keys, media |
| Forms (6+) | `[GAP]` all | All platform form routes |
| Transactions (6) | `[GAP]` all | All platform transaction routes |
| Chat (1) | `[L1]` via chat tests | — |
| Operations (2) | `[GAP]` both | audit, settings |

### 4.3 Platform Gap Summary

**Existing coverage**: 3 L1 + W13 + Carol persona
**Gaps**: 18 features uncovered. Critical: platform CMS management (4 routes), platform forms, platform transactions, approved creators, platform profile update, member detail pages.

---

## 5. RBAC SYSTEM

### 5.1 Backend: 4 models, 49 seeded permissions, 10+ service methods

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **Roles** | List roles for account | `[L1]` role-management.spec.ts | OK |
| | Create custom role | `[L2]` W10, `[L3]` Bob | OK |
| | Update role name/description | `[GAP]` | PATCH endpoint exists |
| | Delete role (no members check) | `[GAP]` | Validates no active members |
| | Role level hierarchy | `[GAP]` | Level 0-10, ordering tested nowhere |
| | System roles immutability | `[GAP]` | Cannot modify system roles |
| | VG limit `max_roles` | `[GAP]` | Per-account role cap |
| | FG gate `custom_roles` | `[GAP]` | Feature gate toggle |
| **Permissions** | List all permissions | `[GAP]` | GET /permissions/ endpoint |
| | Permission categories | `[GAP]` | Filter by category |
| | Add permission to role | `[L2]` W10 (implied) | Via role creation |
| | Remove permission from role | `[GAP]` | DELETE endpoint |
| | Scope validation | `[GAP]` | Scope must be in permission.applicable_scopes |
| **Memberships** | Create membership | `[L2]` W2/W3 | Via transaction outcome |
| | Change member role | `[L2]` W10 step 6 | OK |
| | Suspend member | `[GAP]` | Status transition |
| | Ban member | `[GAP]` | Status transition |
| | Remove member | `[L2]` W15 | OK (quota context) |
| | Reactivate member | `[GAP]` | Status transition |
| | Member leave | `[GAP]` | Voluntary leave (owner blocked) |
| | Restore soft-deleted membership | `[GAP]` | Restore from is_deleted=True |
| | Reactivate REMOVED membership | `[GAP]` | create_membership reactivates |
| | PENDING_APPROVAL status | `[L2]` W5 | Two-phase acceptance |
| **Ownership Transfer** | Transfer ownership | `[L2]` W14, `[L3]` Bob | OK |
| | Old owner downgraded | `[L2]` W14, `[L3]` Bob | OK |
| | New owner gets level 0 | `[L2]` W14 | OK |
| **Authorization Rules** | Dominance rule (same account) | `[GAP]` | actor.level < target.level |
| | Owner invincibility | `[GAP]` | Cannot act on owner |
| | Cross-account (global scope only) | `[GAP]` | Platform admin → business member |
| | Owner cannot leave | `[GAP]` | BusinessRuleViolation |
| **Permission Injection** | `_permissions` in detail responses | `[L1]` business profile | Partially |
| | `_permissions` per-member detail | `[GAP]` | can_change_role, can_suspend, etc. |
| | `_permissions` per-role detail | `[GAP]` | can_edit, can_delete |
| **Permission Caching** | 5-min cache TTL | `[GAP]` | Cache invalidation on role change |
| | Cache invalidation on role perm change | `[GAP]` | Bulk invalidation |

### 5.2 RBAC Gap Summary

**Existing coverage**: Integrated into business/platform L1 + W2/W3/W5/W10/W14/W15 + Bob/Carol/Frank personas
**Gaps**: 22 features uncovered. Critical: member lifecycle actions (suspend/ban/leave/reactivate), role CRUD beyond create, dominance rule, owner invincibility, cross-account authorization, permission scope validation.

---

## 6. TRANSACTION SYSTEM

### 6.1 Backend: 14 types, 10 statuses, 8 outcome handlers, 40+ transitions

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **Transaction Types** | | | |
| | business_membership_invitation | `[L1]` + `[L2]` W2/W3 | OK |
| | business_membership_request | `[L1]` + `[L2]` W4 | OK |
| | platform_membership_invitation | `[GAP]` | Platform-specific |
| | platform_membership_request | `[GAP]` | Platform-specific |
| | business_verification_request | `[GAP]` | Verification workflow |
| | business_ownership_transfer | `[L2]` W14 | OK |
| | platform_ownership_transfer | `[GAP]` | Platform-specific |
| | business_creation_request | `[GAP]` | Request to create business |
| | business_follow_request | `[L2]` W6 (implied) | Via network follow |
| | business_follow_approval_request | `[GAP]` | Follow requires approval |
| | platform_follow_request | `[GAP]` | Platform follow |
| | user_connection_request | `[L2]` W9/W11 | OK |
| | business_connection_request | `[GAP]` | Business-to-business |
| | business_platform_connection_request | `[GAP]` | Business-to-platform |
| **Status Transitions** | | | |
| | PENDING → ACCEPTED | `[L2]` W2-W4 | OK |
| | PENDING → DENIED | `[GAP]` | Deny with reason |
| | PENDING → CANCELLED | `[GAP]` | Initiator cancels |
| | PENDING → EXPIRED | `[GAP]` | Auto-expire task |
| | PENDING → DISMISSED | `[GAP]` | Target dismisses |
| | PENDING → INFO_REQUESTED | `[GAP]` | Request additional info |
| | INFO_REQUESTED → RESUBMITTED | `[GAP]` | Target updates and resubmits |
| | PENDING_REVIEW → APPROVED | `[L2]` W5 | OK |
| | PENDING_REVIEW → DENIED | `[GAP]` | Deny after form review |
| | Auto-expire (Celery task) | `[GAP]` | expire_transactions_task |
| | Expiration reminder (24-48h) | `[GAP]` | send_expiration_reminder_task |
| **Conflict Detection** | | | |
| | Same-type duplicate prevention | `[GAP]` | Conflict guard |
| | Cross-type conflict groups | `[GAP]` | conflict_group field |
| | `_relationship` in detail response | `[GAP]` | active_transaction injection |
| **Form Integration** | | | |
| | TransactionFormMapping CRUD | `[GAP]` *(Appendix D flagged)* | Settings page exists |
| | Required form on join request | `[L2]` W4 | OK |
| | Form response in request detail | `[L2]` W4 step 7, `[L3]` Bob step 29 | OK |
| | INFO_REQUESTED → update → resubmit | `[GAP]` | Full revision workflow |
| | Two-phase acceptance (PENDING_REVIEW) | `[L2]` W5 | OK |
| **Transaction Views** | | | |
| | Transaction list | `[L1]` transaction-list.spec.ts | OK |
| | Transaction detail | `[L1]` (implied) | OK |
| | Filter by status/type | `[L1]` transaction-list.spec.ts | OK |
| | Separate requests page | `[GAP]` | `/bconsole/[slug]/transactions/requests` |
| | Request detail page | `[GAP]` | `/bconsole/[slug]/transactions/requests/[id]` |
| | Invitations list page | `[GAP]` | `/bconsole/[slug]/transactions/invitations` |
| | Invitation detail page | `[GAP]` | `/bconsole/[slug]/transactions/invitations/[id]` |
| | Transaction settings page | `[GAP]` *(Appendix D flagged)* | Form mappings config |
| **Outcome Handlers** | | | |
| | MembershipOutcomeHandler | `[L2]` W2-W4 | OK (via acceptance) |
| | VerificationOutcomeHandler | `[GAP]` | Verification status transitions |
| | OwnershipOutcomeHandler | `[L2]` W14 | OK |
| | PermissionOutcomeHandler | `[GAP]` | Grants can_create_business |
| | NetworkFollowOutcomeHandler | `[L2]` W6 (implied) | OK |
| | NetworkConnectionOutcomeHandler | `[L2]` W9 | OK |
| **Notifications** | | | |
| | 8 transaction notification types | `[PARTIAL]` | Only invitation_received tested |

### 6.2 Transaction Gap Summary

**Existing coverage**: 4 L1 + W2-W6/W12/W14/W15 + persona steps
**Gaps**: 30 features uncovered. Critical: 7 of 14 transaction types never tested, deny/cancel/dismiss/expire transitions, INFO_REQUESTED workflow, form mapping CRUD, conflict detection, dedicated list/detail pages for requests and invitations.

---

## 7. FORMS SYSTEM

### 7.1 Backend: 4 core models + 6 index tables, 14+ field types, 22+ service methods

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **Template Lifecycle** | | | |
| | Create template | `[L1]` template-builder.spec.ts | OK |
| | Update metadata | `[GAP]` | PATCH name, description |
| | Publish (DRAFT → ACTIVE) | `[GAP]` *(Appendix D flagged)* | Critical workflow step |
| | Archive (ACTIVE → ARCHIVED) | `[GAP]` *(Appendix D flagged)* | Status transition |
| | Unarchive (ARCHIVED → DRAFT) | `[GAP]` *(Appendix D flagged)* | Status transition |
| | Create edit draft (from ACTIVE) | `[GAP]` *(Appendix D flagged)* | Versioning workflow |
| | Fork public template | `[GAP]` *(Appendix D flagged)* | Cross-account reuse |
| | Delete template | `[GAP]` | Soft delete |
| | Version numbering | `[GAP]` | Auto-increment on new version |
| | Template library (public) | `[GAP]` | Browse + fork public templates |
| | System forms (by slug) | `[GAP]` | GET /forms/system/{slug}/ |
| **Field Management** | | | |
| | Add fields (14+ types) | `[L1]` template-builder.spec.ts | OK (text, select, date, etc.) |
| | Update field properties | `[GAP]` *(Appendix D flagged)* | PATCH label, validation, etc. |
| | Delete field | `[GAP]` *(Appendix D flagged)* | DELETE + auto-reorder |
| | Reorder fields (drag-drop) | `[GAP]` *(Appendix D flagged)* | Two-pass reorder logic |
| | Max 5 indexed fields | `[GAP]` | Validation rule |
| | All 14+ field types rendering | `[PARTIAL]` | L1 tests "text, select, date, checkbox" — but 10+ more types exist |
| | Field validation rules | `[GAP]` | Required, regex, range, etc. |
| | Conditional logic | `[GAP]` | Field visibility conditions |
| | File upload field | `[GAP]` | FormFileUploadView, 10MB limit |
| **Response Lifecycle** | | | |
| | Create draft response | `[GAP]` | POST creates DRAFT |
| | Update response data | `[GAP]` | PATCH data |
| | Submit response | `[L1]` form-submission.spec.ts | OK |
| | Required fields validation | `[L1]` form-submission.spec.ts | OK |
| | Process response (admin) | `[GAP]` | SUBMITTED → PROCESSED |
| | Void response | `[GAP]` | DRAFT/SUBMITTED → VOID |
| | My responses list | `[GAP]` | User's own submissions |
| **Response List** | Response list renders | `[L1]` form-responses.spec.ts | OK |
| | Response detail view | `[L1]` form-responses.spec.ts | OK |
| | Filter by status | `[GAP]` | Query param filtering |
| **Index Tables** | Typed indexing (6 types) | `[GAP]` | TextFieldIndex, IntegerFieldIndex, etc. |
| **Form-Transaction Integration** | Required form on request | `[L2]` W4 | OK |
| | INFO_REQUESTED → revision | `[GAP]` | Revision history, re-extraction |
| | Two-phase acceptance | `[L2]` W5 | OK |

### 7.2 Frontend: 7 business + 7 platform form routes

| Route | Coverage | Notes |
|-------|----------|-------|
| `/bconsole/[slug]/forms` | `[L1]` (implied) | Forms overview |
| `/bconsole/[slug]/forms/templates` | `[L1]` template list | OK |
| `/bconsole/[slug]/forms/templates/new` | `[GAP]` | Create template page |
| `/bconsole/[slug]/forms/templates/[id]` | `[GAP]` | Edit template page |
| `/bconsole/[slug]/forms/templates/[id]/builder` | `[L1]` builder | OK |
| `/bconsole/[slug]/forms/library` | `[GAP]` | Public template library |
| `/bconsole/[slug]/forms/responses` | `[L1]` responses list | OK |
| `/bconsole/[slug]/forms/responses/[id]` | `[L1]` response detail | OK |
| All `/pconsole/forms/*` (7 routes) | `[GAP]` | All platform form routes |

### 7.3 Forms Gap Summary

**Existing coverage**: 3 L1 + W4/W5 + Bob step 8-10
**Gaps**: 25 features uncovered. Critical: template lifecycle (publish/archive/unarchive/fork/edit-draft), field CRUD beyond add, field reorder, response lifecycle (process/void), all platform form routes, file upload field, template library.

---

## 8. CHAT SYSTEM

### 8.1 Backend: 6 models, 33 service methods, 23 REST + 12 WS events

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **Conversations** | | | |
| | Conversation list | `[L1]` conversation-list.spec.ts | OK |
| | Latest message preview | `[L1]` conversation-list.spec.ts | OK |
| | Unread indicators | `[L1]` conversation-list.spec.ts | OK |
| | Create DM | `[L2]` W7/W8/W11 | OK |
| | Create group | `[L1]` group-chat.spec.ts | OK |
| | Update group name/description | `[GAP]` | PATCH endpoint + ConversationSettings component |
| | Conversation detail + `_permissions` | `[GAP]` | Tier 1.5 permission injection |
| | Scope isolation (global/business/platform) | `[L3]` Frank steps 13-16 | OK |
| | VG limit max_groups | `[GAP]` | Per-user/scope group cap |
| **Messages** | | | |
| | Send text message | `[L1]` send-message.spec.ts | OK |
| | Message timestamp/sender | `[L1]` send-message.spec.ts | OK |
| | Edit message | `[GAP]` *(Appendix D flagged)* | EditMessageMode component, 15-min window |
| | Delete message | `[GAP]` *(Appendix D flagged)* | Soft delete, content cleared |
| | Edit window enforcement (15 min) | `[GAP]` | VG tunable |
| | System messages (join, leave, promote) | `[GAP]` | SystemMessage component |
| | Max message length (5000 chars) | `[L3]` Eve step 13 | OK |
| | DM request message limit (3) | `[GAP]` | Before acceptance |
| | Message sequence ordering | `[L2]` W8 step 5 | OK |
| **Real-Time (WebSocket)** | | | |
| | Real-time message delivery | `[L2]` W8 | OK |
| | Typing indicators | `[L2]` W8 step 2 | OK |
| | Presence (online/offline) | `[GAP]` | PresenceDot component |
| | Seen watermarks (✓✓) | `[GAP]` | DeliveryStatus component |
| | Delivered watermarks (✓) | `[GAP]` | DeliveryStatus component |
| | Connection banner (disconnect/reconnect) | `[L2]` W8 steps 6-7 | OK |
| | Optimistic updates | `[GAP]` | Send → show immediately → sync |
| **Chat Requests** | | | |
| | Request list renders | `[L1]` chat-requests.spec.ts | OK |
| | Accept request | `[L1]` chat-requests.spec.ts | OK |
| | Ignore request | `[L1]` chat-requests.spec.ts | OK |
| | Request banner in conversation | `[GAP]` | RequestBanner component |
| | Request expiry (30 days) | `[GAP]` | expire_stale_chat_requests task |
| | Rate limiting (1 per 5 min) | `[GAP]` | Redis-backed rate limit |
| **Attachments** | | | |
| | Upload image | `[L1]` attachments.spec.ts | OK |
| | Preview shown | `[L1]` attachments.spec.ts | OK |
| | Lightbox opens | `[L1]` attachments.spec.ts | OK |
| | MIME type validation | `[GAP]` | Extension + MIME whitelist |
| | File size limit (10 MB) | `[GAP]` | VG tunable |
| | Max attachments per message (10) | `[GAP]` | VG limit |
| | Media gallery | `[GAP]` *(Appendix D flagged)* | Separate cursor-based gallery endpoint |
| | Orphan cleanup (24h) | `[GAP]` | cleanup_orphan_attachments task |
| **Reactions** | | | |
| | Add reaction | `[L1]` reactions.spec.ts | OK |
| | Remove reaction | `[L1]` reactions.spec.ts | OK |
| | Reaction count updates | `[L1]` reactions.spec.ts | OK |
| | 6 preset emoji types | `[GAP]` | LIKE, HEART, LAUGH, WOW, SAD, ANGRY |
| | Reaction notification to author | `[GAP]` | chat_reaction_received notification |
| **Search** | | | |
| | Search query → results | `[L1]` search-messages.spec.ts | OK |
| | Click result → navigate | `[L1]` search-messages.spec.ts | OK |
| | FTS + trigram fallback | `[GAP]` | PostgreSQL-specific behavior |
| **Blocking** | | | |
| | Block user | `[L3]` Dave step 13 | OK |
| | Unblock user | `[L3]` Dave step 14 | OK |
| | Block list page | `[GAP]` | Separate blocks endpoint |
| | Blocked user can't message | `[GAP]` | Bidirectional blocking |
| **Group Management** | | | |
| | Add participant | `[L2]` W7 step 3 | OK |
| | Remove participant | `[GAP]` *(Appendix D flagged)* | Admin removes member |
| | Promote to admin | `[GAP]` *(Appendix D flagged)* | Group admin management |
| | Demote from admin | `[GAP]` *(Appendix D flagged)* | Last admin protection |
| | Leave conversation | `[L2]` W7 step 7 | OK |
| | Admin succession (last admin leaves) | `[GAP]` | Auto-promote oldest member |
| | Group size limit (100) | `[GAP]` | VG tunable |
| | Participant list display | `[L1]` group-chat.spec.ts | OK |
| **Entity Chat** | | | |
| | Business as participant | `[L2]` W16 | OK |
| | Message attributed to business | `[L2]` W16 step 4 | OK |
| | Entity inbox | `[L2]` W16 step 6 | OK |
| | EntitySenderBadge | `[GAP]` | Visual indicator component |
| | Platform as participant | `[GAP]` | Platform entity chat |
| | `can_manage_chat` RBAC check | `[GAP]` | Permission enforcement |
| **Mute/Unmute** | Mute conversation | `[GAP]` *(Appendix D flagged)* | MuteToggle component |
| | Unmute conversation | `[GAP]` | MuteToggle component |
| **Feature Gates** | 20+ chat feature gates | `[GAP]` | Not tested from E2E |
| **Notifications** | 5 chat notification types | `[PARTIAL]` | Only implicitly tested |

### 8.2 Chat Gap Summary

**Existing coverage**: 7 L1 + W7/W8/W16 + Alice/Dave/Frank personas
**Gaps**: 38 features uncovered. Critical: edit/delete messages, presence indicators, delivery/seen watermarks, group admin management (promote/demote/remove), media gallery, mute/unmute, entity sender badge, DM request limits, all chat feature gates, platform entity chat.

---

## 9. NETWORK SYSTEM

### 9.1 Backend: 2 models (Follow + Connection), 13 endpoints, 6 outcome handlers

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **Follow** | Follow business | `[L1]` follow-business.spec.ts | OK |
| | Unfollow business | `[L1]` follow-business.spec.ts | OK |
| | Following list (user's follows) | `[GAP]` | GET /network/following/ |
| | Follow via transaction (approval required) | `[GAP]` | business_follow_approval_request type |
| | Platform follow | `[GAP]` | platform_follow_request type |
| | VG limit max_follows | `[GAP]` | Per-user follow cap |
| | VG limit max_followers (business) | `[GAP]` | Per-business cap |
| **Connections (User↔User)** | Send connection request | `[L1]` connect-user.spec.ts | OK |
| | Accept connection (via API) | `[L2]` W9 | OK |
| | Disconnect user | `[GAP]` | DELETE endpoint |
| | Connection list | `[GAP]` | GET /network/connections/ |
| | Mutual connections | `[GAP]` | get_mutual_connections selector |
| | Canonical ordering | `[GAP]` | user_a.id <= user_b.id |
| | VG limit max_connections | `[GAP]` | Per-user cap |
| **Connections (Account↔Account)** | Business connection request | `[GAP]` | Business-to-business |
| | Business-platform connection | `[GAP]` | Cross-entity type |
| | Account connection list | `[GAP]` | Business connections page |
| **Business Network Pages** | Followers list page | `[GAP]` | `/bconsole/[slug]/network/followers` |
| | Remove follower | `[GAP]` | Requires can_manage_followers |
| | Connections list page | `[GAP]` | `/bconsole/[slug]/network/connections` |
| **Network Stats** | User stats (counts) | `[L1]` network-page.spec.ts | OK |
| | Business stats (counts) | `[GAP]` | GET /network/business/{slug}/stats/ |
| **Network Page** | Renders correctly | `[L1]` network-page.spec.ts | OK |
| | Follower/following/connection counts | `[L1]` network-page.spec.ts | OK |
| **Outcome Handlers** | Follow outcome → Follow record | `[L2]` W6 (implied) | OK |
| | Connection outcome → Connection record | `[L2]` W9 | OK |
| **Notifications** | 5 social notification types | `[PARTIAL]` | Only connection_request in W9 |

### 9.2 Network Gap Summary

**Existing coverage**: 3 L1 + W6/W9/W11 + Alice/Dave personas
**Gaps**: 17 features uncovered. Critical: following list, connection list, disconnect, business network pages (followers + connections), account-to-account connections, follow approval flow, VG limits.

---

## 10. EXPLORE SYSTEM

### 10.1 Backend: 1 model (SuggestedTag), 3 search methods, 5 endpoints

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **Business Search** | Query → results | `[L1]` search-businesses.spec.ts | OK |
| | Result cards render | `[L1]` search-businesses.spec.ts | OK |
| | Click → navigate to profile | `[L1]` search-businesses.spec.ts | OK |
| | 11 filter parameters | `[PARTIAL]` | L1 filters.spec.ts tests "single + multiple + clear" but not all 11 |
| | FTS + trigram fallback | `[GAP]` | PostgreSQL-specific behavior |
| | Ordering: relevance, name, newest | `[GAP]` | Only default tested |
| | include_private (auth users) | `[GAP]` | Auth users see private businesses too |
| | Pagination (next page) | `[GAP]` | Infinite scroll in frontend |
| **User Search** | Auth required | `[L1]` search-users.spec.ts | OK |
| | Results display | `[L1]` search-users.spec.ts | OK |
| | Empty state | `[L1]` search-users.spec.ts | OK |
| | 5 filter parameters | `[GAP]` | country, city, language, verified, tags |
| | FG gate `user.explore.search_users` | `[GAP]` | Feature gate |
| | FG gate `user.explore.is_discoverable` | `[GAP]` | Discovery toggle |
| **Combined Search** | Top 6 businesses + top 6 users | `[GAP]` | Combined endpoint |
| **Tag Suggestions** | Tag autocomplete | `[GAP]` | GET /explore/tags/ |
| | Category filter (user/business) | `[GAP]` | Filter by tag category |
| **City List** | Cities for country | `[GAP]` | GET /explore/cities/ |
| | Country selection → city dropdown | `[GAP]` | CityCombobox component |
| **VG Config** | Min search length | `[GAP]` | explore.min_search_length |

### 10.2 Explore Gap Summary

**Existing coverage**: 3 L1 + W6/W11 + Alice/Dave personas
**Gaps**: 14 features uncovered. Key: all specific filter parameters, ordering options, pagination, tag suggestions, city selection, combined search endpoint, feature gates.

---

## 11. NOTIFICATIONS SYSTEM

### 11.1 Backend: 2 models, 32 notification types, 6 endpoints

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **Notification Center** | List renders | `[L1]` notification-center.spec.ts | OK |
| | Unread badge count | `[L1]` notification-center.spec.ts | OK |
| | Mark as read | `[L1]` notification-center.spec.ts | OK |
| | Click → navigate to source | `[L1]` notification-center.spec.ts | OK |
| **Preferences** | | | |
| | List all preferences | `[GAP]` | GET /notifications/preferences/ |
| | Get single preference | `[GAP]` | GET /notifications/preferences/{type}/ |
| | Update preference (email/push/sms) | `[L1]` settings.spec.ts | Partially (in settings) |
| | Reset to defaults | `[GAP]` | DELETE preference |
| | Mandatory types (non-configurable) | `[GAP]` | verify_email, password_reset, etc. |
| | Configurable types list | `[GAP]` | GET /notifications/types/ |
| **Notification Types** | | | |
| | AUTH types (4) | `[GAP]` | verify_email, welcome, password_reset, password_changed |
| | SECURITY types (2) | `[GAP]` | new_login, suspicious_activity |
| | TRANSACTIONAL types (8) | `[PARTIAL]` | Only invitation_received implicitly tested |
| | SOCIAL types (5) | `[PARTIAL]` | Only connection_request in W9 |
| | CHAT types (5) | `[GAP]` | chat_message_received, request_received, etc. |
| | MARKETING types (2) | `[GAP]` | newsletter, promotions |
| **Delivery** | | | |
| | Email delivery | `[GAP]` | Channel routing |
| | Push delivery | `[GAP]` | Channel routing |
| | Notification history | `[GAP]` | GET /notifications/history/ |
| | Multi-channel dispatch | `[GAP]` | Same notification to email + push + sms |
| **Feature Gates** | Deployment-level channel override | `[GAP]` | notifications.email_enabled, etc. |

### 11.2 Notifications Gap Summary

**Existing coverage**: 1 L1 + W3/W9/W12 + persona steps
**Gaps**: 17 features uncovered. Critical: preference management UI, specific notification types verification, notification history, channel routing, mandatory vs configurable types.

---

## 12. CMS SYSTEM

### 12.1 Backend: 11 models, 26 service methods, 17 API endpoints

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **Sites** | Create site | `[GAP]` | Platform admin creates CMS site |
| | List sites | `[GAP]` | `/cconsole/sites` route |
| | Update site | `[GAP]` | PATCH name, domain, metadata |
| | Delete site | `[GAP]` | Soft-delete |
| **Pages** | Create page | `[GAP]` | Within site |
| | Publish page | `[GAP]` | DRAFT → PUBLISHED (atomic) |
| | Unpublish page | `[GAP]` | Revert to draft |
| | Export/Import page | `[GAP]` | JSON export/import |
| | Page ordering | `[GAP]` | Reorder within site |
| **Templates** | Create section template | `[GAP]` | Global section templates |
| | Create block template | `[GAP]` | Block schema definition |
| | Schema versioning | `[GAP]` | Auto-increment on change |
| **Content Editing** | Edit draft content | `[GAP]` | Update block draft |
| | Publish (draft → published) | `[GAP]` | Copy draft_content to published_content |
| | Rollback to version | `[GAP]` | Restore previous content version |
| | Toggle block visibility | `[GAP]` | is_visible (non-required blocks) |
| | Content version history | `[GAP]` | Max 50 versions, 30s throttle |
| | Schema validation | `[GAP]` | JSON schema validation |
| | Rich text sanitization (nh3) | `[GAP]` | HTML sanitization |
| **Media** | Upload media file | `[GAP]` | MIME whitelist, storage |
| | Update file metadata | `[GAP]` | alt_text, title, folder |
| | Delete file (tombstoning) | `[GAP]` | Tombstone if published refs |
| | Media folders (5-level depth) | `[GAP]` | Folder organization |
| | Cleanup tombstoned files | `[GAP]` | Celery task |
| **API Keys** | Create API key | `[GAP]` | SHA-256, `cmsk_` prefix, plaintext once |
| | Revoke API key | `[GAP]` | Soft-delete |
| | API key rate limiting | `[GAP]` | Default 60/min |
| **Public API** | Public site view | `[GAP]` | AllowAny + API key auth |
| | Public page view | `[GAP]` | Published pages only |
| **RBAC** | 23 CMS permissions | `[GAP]` | All permission enforcement |

### 12.2 CMS Gap Summary

**Existing coverage**: Only vague mention in Carol scenario step 12 ("if UI exists")
**Gaps**: ALL 30 features uncovered. The CMS system has zero E2E test coverage. 6 platform console routes, 17 API endpoints, 11 models — completely untested.

---

## 13. CONTENT VISIBILITY SYSTEM

### 13.1 Backend: 3-tier model, 4 field registries, resolver logic

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **T1 (Always Public)** | Public fields visible to anonymous | `[L1]` business profile-public.spec.ts | OK |
| | 14 user profile T1 fields | `[PARTIAL]` | Tested generically, not per-field |
| | 19 business account T1 fields | `[PARTIAL]` | Tested generically |
| **T2 (Configurable)** | Business contact_email visibility | `[GAP]` | Default: FOLLOWERS |
| | Business contact_phone visibility | `[GAP]` | Default: FOLLOWERS |
| | Visibility override configuration | `[GAP]` *(Appendix D flagged)* | PATCH visibility_overrides |
| | Different visibility for different viewers | `[GAP]` | Member sees more than follower |
| | `is_authenticated=False` blocks T2 | `[GAP]` | Anonymous users never see T2 |
| **T3 (Members-only + RBAC)** | Business T3 fields (registration_number, tax_id, etc.) | `[GAP]` | Requires can_view_legal_info |
| | User T3 fields (phone, timezone, language) | `[GAP]` | Only connections or self |
| | RBAC permission gate on T3 | `[GAP]` | Different permissions per field |
| **Frontend Integration** | `<Can>` component gating | `[PARTIAL]` | Tested in some contexts |
| | `WithPermissions<T>` type usage | `[GAP]` | Type-level testing |

### 13.2 Visibility Gap Summary

**Existing coverage**: Implicitly tested in business profile L1 + Alice persona
**Gaps**: 9 features uncovered. Critical: T2 per-field configuration, T3 RBAC-gated fields, visibility settings page, different viewer experiences.

---

## 14. FEATURE GATE SYSTEM

### 14.1 Backend: 123 config fields, 3-tier gates, 98 enforcement points

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **System Gates (SG)** | System disabled → URLs not registered | `[GAP]` | Fixed at startup |
| | Chat system toggle | `[GAP]` | systems.chat |
| | Network system toggle | `[GAP]` | systems.network |
| | CMS system toggle | `[GAP]` | systems.cms |
| | Forms system toggle | `[GAP]` | systems.forms |
| | Transaction system toggle | `[GAP]` | systems.transaction |
| | Explore system toggle | `[GAP]` | systems.explore |
| **Feature Gates (FG)** | 403 FeatureDisabled response | `[GAP]` | Error handling in frontend |
| | Frontend reactive UI hide | `[GAP]` | useSyncExternalStore polling |
| | View-level gate enforcement | `[GAP]` | FeatureRequired("path") class |
| | Service-level gate enforcement | `[GAP]` | raise FeatureDisabled |
| | Celery task guard | `[GAP]` | Skip if system disabled |
| **Value Gates (VG)** | Limit enforcement (check_limit) | `[PARTIAL]` | max_members in W15 |
| | effective_limit (dual-source) | `[GAP]` | config + model limit |
| | Config values (get_value) | `[GAP]` | Tunable constants |
| **Org Mode** | `user_only` mode | `[GAP]` | No business, no platform |
| | `user_and_platform` mode | `[GAP]` | No business |
| | `full` mode (current) | Implicit | All tests use full mode |
| **Runtime Reload** | Config reload without restart | `[GAP]` | FG/VG change at runtime |

### 14.2 Feature Gate Gap Summary

**Existing coverage**: Only max_members limit tested in W15. Architecture mentions "future" gate-aware testing but has no concrete tests.
**Gaps**: ALL gate-specific testing uncovered. This is the architecture's stated "day 1: all enabled, variants later" approach, but even basic 403-on-disabled testing is missing.

---

## 15. EMAIL SYSTEM

### 15.1 Backend: 2 models, email lifecycle, retry mechanism, webhooks

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **Email Sending** | Template rendering | `[GAP]` | Django template variables |
| | Context validation | `[GAP]` | Schema validation before render |
| | Async dispatch (Celery) | `[GAP]` | E2E uses CELERY_TASK_ALWAYS_EAGER |
| **Email Lifecycle** | pending → sent → delivered | `[GAP]` | Full status tracking |
| | Retry on failure | `[GAP]` | Exponential backoff |
| | Bounce/complaint handling | `[GAP]` | SES webhook integration |
| **Email Types** | Verification email sent | `[GAP]` | Critical: part of registration flow |
| | Welcome email after verify | `[GAP]` | Post-verification |
| | Password reset email | `[GAP]` | Part of reset flow |
| | New device login email | `[GAP]` | Security notification |

### 15.2 Email Gap Summary

**Existing coverage**: Zero. Email system is internal-only (no public endpoints) but its effects are user-visible (verification codes, reset links). E2E tests need to either intercept emails or use API shortcuts to verify email content.

---

## 16. CORE INFRASTRUCTURE

### 16.1 Cross-Cutting Features

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **Error Handling** | 404 page | `[L3]` Eve step 20 | OK |
| | 403 (PermissionDenied) | `[L3]` Eve steps 5-6 | OK |
| | 400 (ValidationError) | `[L3]` Eve step 11 | OK |
| | 401 (AuthenticationError) | `[GAP]` | Token expired, invalid |
| | 409 (ConflictError) | `[GAP]` | Duplicate operations |
| | 429 (RateLimitExceeded) | `[L1]` rate-limits.spec.ts | OK |
| | 503 (ServiceUnavailable) | `[GAP]` | Backend down scenario |
| **Health Check** | `GET /health/` | `[GAP]` | Used in CI pipeline but not tested |
| **Pagination** | Standard pagination (20/page) | `[PARTIAL]` | Some tests mention "pagination works" |
| | Page size parameter | `[GAP]` | page_size query param |
| | max 100 per page | `[GAP]` | Limit enforcement |
| **Audit Trail** | Audit log page (business) | `[GAP]` *(Appendix D flagged)* | `/bconsole/[slug]/audit` |
| | Audit log page (platform) | `[GAP]` *(Appendix D flagged)* | `/pconsole/audit` |
| | 60+ audit actions tracked | `[GAP]` | Verification of logged actions |

---

## 17. FRONTEND INFRASTRUCTURE

### 17.1 Navigation & Guards

| Feature | Sub-Feature | Coverage | Notes |
|---------|------------|----------|-------|
| **AuthGuard** | Redirect unauthenticated → login | `[L3]` Alice step 3 | OK |
| | Preserve callbackUrl | `[L3]` Alice step 3 | OK |
| **BusinessGuard** | Validate membership | `[L3]` Eve step 5 | OK |
| | Access Denied card | `[L3]` Eve step 5 | OK |
| | Pending Review card | `[GAP]` | PENDING_APPROVAL UI |
| **PlatformGuard** | Validate platform membership | `[L3]` Eve step 6 | OK |
| | Access Denied card | `[L3]` Eve step 6 | OK |
| **AdminGuard** | Check is_staff/is_superuser | `[GAP]` | Admin route protection |
| **Account Switcher** | Switch personal/business/platform | `[L3]` Frank | OK |
| | Rapid switching (no stale data) | `[L3]` Frank step 17 | OK |
| | New business appears after join | `[L3]` Frank step 10 | OK |
| **Navigation** | Sidebar renders correctly | `[L1]` navigation-mobile.spec.ts | Mobile variant |
| | Permission-based nav filtering | `[GAP]` | useFilteredNav hook |
| | Active state highlighting | `[GAP]` | isNavActive logic |
| **Responsive** | Mobile bottom navbar | `[L1]` navigation-mobile.spec.ts | OK |
| | Desktop sidebar | `[GAP]` | Desktop navigation not explicitly tested |
| | Breakpoint transitions | `[GAP]` | md: (768px) breakpoint |

### 17.2 Public Routes

| Route | Coverage | Notes |
|-------|----------|-------|
| `/` (landing) | `[GAP]` *(Appendix D flagged)* | First thing users see |
| `/about` | `[GAP]` *(Appendix D flagged)* | Public page |
| `/contact` | `[GAP]` *(Appendix D flagged)* | Public page |
| `/explore` | `[L1]` search tests | OK |
| `/business/[slug]` | `[L1]` business profile | OK |
| `/platform/profile` | `[L1]` platform profile | OK |

---

## CONSOLIDATED GAP STATISTICS

### By System

| System | Total Features Audited | Covered | Gaps | Coverage % |
|--------|----------------------|---------|------|-----------|
| Auth | 37 | 14 | 23 | 38% |
| Users | 29 | 8 | 21 | 28% |
| Business (Org) | 37 | 9 | 28 | 24% |
| Platform (Org) | 22 | 4 | 18 | 18% |
| RBAC | 34 | 12 | 22 | 35% |
| Transaction | 44 | 14 | 30 | 32% |
| Forms | 33 | 8 | 25 | 24% |
| Chat | 55 | 17 | 38 | 31% |
| Network | 26 | 9 | 17 | 35% |
| Explore | 20 | 6 | 14 | 30% |
| Notifications | 20 | 3 | 17 | 15% |
| CMS | 30 | 0 | 30 | **0%** |
| Visibility | 12 | 3 | 9 | 25% |
| Feature Gates | 19 | 1 | 18 | **5%** |
| Email | 10 | 0 | 10 | **0%** |
| Core/Infra | 13 | 5 | 8 | 38% |
| Frontend Nav | 15 | 7 | 8 | 47% |
| **TOTAL** | **426** | **120** | **306** | **28%** |

### By Severity (Top Gaps)

| Priority | Gap | System | Impact |
|----------|-----|--------|--------|
| **P0** | Email verification flow (3 routes, 0 tests) | Auth | Registration is broken without it |
| **P0** | CMS system (30 features, 0 tests) | CMS | Entire system untested |
| **P0** | Home feed (primary landing page, 0 tests) | Users | Users land here after login |
| **P0** | Feature gate 403 handling (98 enforcement points) | Feature Gates | Platform usability on restricted deployments |
| **P1** | OAuth (Google + Apple, 0 tests) | Auth | Major auth pathway |
| **P1** | Business lifecycle (suspend/reactivate/archive) | Business | Critical admin operations |
| **P1** | Member discipline (suspend/ban/reactivate) | RBAC | Team management |
| **P1** | Transaction deny/cancel/expire transitions | Transaction | Half the state machine untested |
| **P1** | Form template lifecycle (publish/archive/fork) | Forms | Core builder workflow |
| **P1** | Chat edit/delete messages | Chat | Basic messaging operations |
| **P1** | Chat watermarks + presence | Chat | Real-time status features |
| **P1** | All platform console feature routes (~20) | Platform | Admin management pages |
| **P2** | Activity feed (2 routes) | Users | User engagement feature |
| **P2** | Network lists + disconnect | Network | Social features |
| **P2** | Notification preferences UI | Notifications | User configuration |
| **P2** | Business transaction detail pages | Transaction | List/detail separation |
| **P2** | Audit log pages (2 routes) | Core | Compliance feature |
| **P2** | Username change/check | Users | Profile management |
| **P2** | Account deactivation | Users | Account lifecycle |
| **P2** | INFO_REQUESTED workflow | Transaction | Form revision cycle |

---

## RECOMMENDED ADDITIONS TO ARCHITECTURE.MD

### New L1 Tests Required (beyond Appendix D's 16)

Based on this deep analysis, the following additional L1 tests are needed **on top of** the 16 already identified in Appendix D:

```
tests/smoke/
  auth/
    + oauth-redirect.spec.ts           # OAuth initiation + redirect (Google/Apple)
    + session-revocation.spec.ts       # Revoke specific session
    + logout-all.spec.ts               # Logout from all devices
  user/
    + username-change.spec.ts          # Change username + availability check
    + avatar-management.spec.ts        # Upload + delete avatar
    + cover-image.spec.ts              # Upload + delete cover image
    + account-deactivation.spec.ts     # Deactivate account
  business/
    + business-lifecycle.spec.ts       # Suspend/reactivate/archive states
    + member-actions.spec.ts           # Suspend/ban/reactivate member
    + member-detail.spec.ts            # Member detail page + permissions
    + business-slug.spec.ts            # Update slug (owner only)
    + business-verification.spec.ts    # Verification badge display
    + business-visibility.spec.ts      # T2 visibility configuration
  chat/
    + message-edit-delete.spec.ts      # Edit + delete messages
    + presence-indicators.spec.ts      # Online/offline status dots
    + delivery-status.spec.ts          # Sent/delivered/seen indicators
    + group-admin.spec.ts              # Promote/demote/remove participants
    + chat-mute.spec.ts                # Mute/unmute conversations
    + entity-sender-badge.spec.ts      # Business/platform sender indicator
  forms/
    + template-lifecycle.spec.ts       # Publish/archive/unarchive/fork
    + field-crud.spec.ts               # Add/update/delete/reorder fields
    + field-types-all.spec.ts          # All 14+ field types
    + template-library.spec.ts         # Browse + fork public templates
  transaction/
    + transaction-deny-cancel.spec.ts  # Deny + cancel transitions
    + transaction-pages.spec.ts        # Requests/invitations list+detail pages
    + form-mapping-settings.spec.ts    # Transaction form mapping config
  network/
    + following-list.spec.ts           # User's following list
    + connection-list.spec.ts          # User's connections list
    + disconnect.spec.ts               # Disconnect from user/account
  notification/
    + notification-preferences.spec.ts # Full preference management
    + notification-history.spec.ts     # Delivery history
  cms/
    + cms-site-management.spec.ts      # CRUD sites
    + cms-page-publish.spec.ts         # Create + publish page
    + cms-content-editing.spec.ts      # Edit block content
    + cms-media-library.spec.ts        # Upload + manage media
    + cms-api-keys.spec.ts             # Create + revoke API keys
```

**Additional L1 tests: 36 more files**
**Revised total L1: 61 (Appendix D) + 36 = 97 test files**

### New L2 Workflows Required (beyond Appendix D's 6)

```
W23: OAuth Registration Flow
    Google OAuth → account created → auto-verified → home page

W24: Full Notification Lifecycle
    Action → notification created → appears in center → click → navigate → mark read

W25: Chat Request → DM → Block Flow
    Stranger sends DM → request appears → accept → chat → block → unblock

W26: Form Builder Complete Lifecycle
    Create template → add 5+ field types → reorder → publish → submit response → process

W27: Business Network Management
    Business gets followers → manage followers page → remove follower → manage connections

W28: Feature Gate Degradation
    Disable chat feature → verify 403 → verify UI hides feature → re-enable → verify restored
```

**Additional L2 workflows: 6 more**
**Revised total L2: 22 (Appendix D) + 6 = 28 workflows**

### L3 Persona Additions (new steps within existing personas)

**Alice**: Add email verification steps (register → verify → login). Add home feed page visit. Add activity feed browsing.

**Bob**: Add form template publish flow (create → add fields → publish). Add business visibility settings. Add audit log verification. Add member suspend/reactivate flow.

**Carol**: Make CMS testing explicit (create site → create page → edit content → publish → verify public). Add platform forms management. Add platform transactions management. Add approved creators management. Add platform audit log.

**Dave**: Add chat edit/delete messages. Add delivery status verification. Add presence indicator check. Add following/connection list browsing.

**Eve**: Add OAuth bypass attempts. Add account deactivation abuse. Add concurrent session tests (5 tabs). Add feature gate 403 handling verification. Add conflict detection (duplicate transactions).

**Frank**: Add notification scope isolation. Add activity feed across contexts.

**New Persona G: Gary the CMS Content Manager** (optional but recommended)
    Platform admin focused on CMS: Create site → configure templates → build pages → edit content → publish → verify public view → rollback → media management → API key management.

---

## SUMMARY

The current architecture.md covers **28% of audited features** (120 of 426). After applying Appendix D fixes, coverage rises to approximately **35%**. This deep analysis identifies an additional **~200 features** that need E2E test coverage, primarily in:

1. **CMS** — 0% coverage (30 features, entire system)
2. **Feature Gates** — 5% coverage (18 gaps, critical for multi-deployment)
3. **Email** — 0% coverage (10 features, affects registration flow)
4. **Notifications** — 15% coverage (17 gaps)
5. **Platform console** — 18% coverage (18 gaps, admin management)
6. **Forms lifecycle** — 24% coverage (25 gaps)
7. **Business org** — 24% coverage (28 gaps)

The document should be updated to reach **70%+ feature coverage** before implementation begins, targeting all P0 and P1 gaps.

---

*End of analysis. Cross-reference source: 7 deep-dive system audits against architecture.md sections 9-12 and Appendix D.*
