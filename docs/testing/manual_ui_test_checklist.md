# Manual UI Test Checklist

> Walk through each item as a real user. Check off items as you go.
> Each item includes **State** (your current context), **Action** (what to do), and **Expected** (what should happen).
>
> **Prefixes:** U = User scope, B = Business scope, P = Platform scope, X = Cross-scope

---

## Legend

| Symbol | Meaning |
|--------|---------|
| State | Your current logged-in status, role, and context before performing the action |
| Action | What you click, type, or navigate to |
| Expected | The observable outcome (page content, toast, redirect, error, visibility) |

**Actors used throughout:**
- **User A** — Primary test user (you)
- **User B** — Secondary test user (for invitations, connections)
- **User C** — Third test user (for quota/edge case tests)
- **Biz-X** — A business account (slug: `test-business`)
- **Platform** — The single platform account

---

# SCOPE 1: USER (U)

## 1.1 Registration

- [ ] **U-01** | State: _Not logged in_ | Action: Navigate to `/register` | Expected: Registration form appears with email, username, password fields and OAuth buttons (Google, Apple). Link to login page visible.

- [ ] **U-02** | State: _On register page_ | Action: Submit form with valid email, username (3+ chars), password (8+ chars) | Expected: Account created. Redirected to `/verify-email`. Success toast shown.

- [ ] **U-03** | State: _On register page_ | Action: Submit with already-used email | Expected: Error message "Email already registered" (or similar). Form stays on page.

- [ ] **U-04** | State: _On register page_ | Action: Submit with already-taken username | Expected: Error message about username unavailability.

- [ ] **U-05** | State: _On register page_ | Action: Submit with weak password (less than 8 chars) | Expected: Client-side validation error shown. Form not submitted.

- [ ] **U-06** | State: _On register page_ | Action: Submit with empty fields | Expected: Validation errors shown for each required field.

- [ ] **U-07** | State: _On register page_ | Action: Submit with invalid email format | Expected: Validation error for email field.

## 1.2 Email Verification

- [ ] **U-08** | State: _Registered but unverified, on `/verify-email`_ | Action: Enter the 6-digit code from email | Expected: Email verified. Success message. Redirected to `/home` (or login).

- [ ] **U-09** | State: _On verify-email page_ | Action: Enter wrong code | Expected: Error "Invalid code" shown. Can retry.

- [ ] **U-10** | State: _On verify-email page_ | Action: Enter wrong code 5 times | Expected: Account locked out from verification. Error message indicates lockout.

- [ ] **U-11** | State: _On verify-email page_ | Action: Click "Resend verification" | Expected: New code sent. Success toast "Verification email sent".

- [ ] **U-12** | State: _Not logged in_ | Action: Navigate to `/resend-verification`, enter email | Expected: Success message shown (always, even for non-existent emails to prevent enumeration).

## 1.3 Login

- [ ] **U-13** | State: _Not logged in, email verified_ | Action: Navigate to `/login`, enter valid email + password | Expected: Logged in. Redirected to `/home`. User menu shows username in topbar.

- [ ] **U-14** | State: _On login page_ | Action: Enter valid email + wrong password | Expected: Error "Invalid credentials". Form stays on page.

- [ ] **U-15** | State: _On login page_ | Action: Enter non-existent email | Expected: Same error "Invalid credentials" (no user enumeration).

- [ ] **U-16** | State: _On login page_ | Action: Attempt login 5+ times rapidly with wrong password | Expected: Rate limit hit. Error "Too many attempts, try again later".

- [ ] **U-17** | State: _On login page_ | Action: Click Google OAuth button | Expected: Redirected to Google consent screen. After consent, redirected back and logged in.

- [ ] **U-18** | State: _On login page_ | Action: Click Apple OAuth button | Expected: Redirected to Apple sign-in. After consent, redirected back and logged in.

- [ ] **U-19** | State: _On login page_ | Action: Click "Forgot password?" link | Expected: Navigated to `/forgot-password` page.

- [ ] **U-20** | State: _On login page_ | Action: Click "Register" link | Expected: Navigated to `/register` page.

## 1.4 Password Management

- [ ] **U-21** | State: _Not logged in_ | Action: Navigate to `/forgot-password`, enter registered email, submit | Expected: Success message "If an account exists, a reset link was sent" (always same message).

- [ ] **U-22** | State: _Not logged in_ | Action: On `/forgot-password`, enter non-existent email | Expected: Same success message (no user enumeration).

- [ ] **U-23** | State: _Have reset email_ | Action: Click reset link, navigate to `/reset-password?token=...` | Expected: New password form shown with password field.

- [ ] **U-24** | State: _On reset password page_ | Action: Enter new valid password and submit | Expected: Password reset success. Redirected to login.

- [ ] **U-25** | State: _On reset password page_ | Action: Use expired or invalid token | Expected: Error "Invalid or expired reset link".

- [ ] **U-26** | State: _Logged in as User A_ | Action: Navigate to settings/security, change password (enter current + new) | Expected: Password changed. All other sessions logged out. Success toast.

- [ ] **U-27** | State: _Logged in as User A_ | Action: Change password with wrong current password | Expected: Error "Current password is incorrect".

## 1.5 Session Management

- [ ] **U-28** | State: _Logged in as User A_ | Action: Navigate to `/sessions` | Expected: List of active sessions shown with device info, IP, last activity. Current session flagged.

- [ ] **U-29** | State: _On sessions page, logged in from 2 devices_ | Action: Click "Revoke" on another session | Expected: Session removed from list. That device is logged out.

- [ ] **U-30** | State: _On sessions page_ | Action: Try to revoke current session | Expected: Either not allowed or handled gracefully (logged out).

- [ ] **U-31** | State: _Logged in as User A_ | Action: Click "Logout" in user menu | Expected: Logged out. Redirected to `/login`. Access token cleared.

- [ ] **U-32** | State: _Logged in from 2+ devices_ | Action: Click "Logout all devices" | Expected: All sessions revoked. Logged out everywhere. Redirected to login.

## 1.6 User Profile — View & Edit

- [ ] **U-33** | State: _Logged in as User A_ | Action: Navigate to `/profile` | Expected: Own profile page shows username, display name, bio, avatar, country, city, tags.

- [ ] **U-34** | State: _On profile page_ | Action: Click "Edit Profile" (or navigate to `/profile/edit`) | Expected: Edit form with fields: first_name, last_name, bio, country, city, tags, timezone, language.

- [ ] **U-35** | State: _On edit profile page_ | Action: Update first_name, last_name, bio and save | Expected: Profile updated. Success toast. Changes reflected on profile page.

- [ ] **U-36** | State: _On edit profile page_ | Action: Select a country from dropdown | Expected: Country saved. City dropdown filters to cities in selected country.

- [ ] **U-37** | State: _On edit profile page_ | Action: Select a city using combobox | Expected: City saved. Shown on profile.

- [ ] **U-38** | State: _On edit profile page_ | Action: Add tags (type tag, press enter) | Expected: Tags added as chips. Saved to profile.

- [ ] **U-39** | State: _On edit profile page_ | Action: Change timezone and language | Expected: Preferences saved successfully.

## 1.7 Avatar

- [ ] **U-40** | State: _On profile/edit page_ | Action: Upload avatar image (JPEG, < 5MB) | Expected: Avatar uploaded immediately. Preview shown. Success toast.

- [ ] **U-41** | State: _On profile/edit page_ | Action: Upload file > 5MB | Expected: Error "File too large" (max 5MB).

- [ ] **U-42** | State: _On profile/edit page_ | Action: Upload non-image file (.pdf) | Expected: Error "Unsupported format".

- [ ] **U-43** | State: _Has avatar uploaded_ | Action: Click "Remove avatar" | Expected: Avatar removed. Default placeholder shown.

## 1.8 Username

- [ ] **U-44** | State: _Logged in as User A_ | Action: Navigate to settings, update username | Expected: Username changed. Success toast.

- [ ] **U-45** | State: _On settings page_ | Action: Enter already-taken username | Expected: Error "Username already taken".

- [ ] **U-46** | State: _On settings page_ | Action: Enter username with invalid characters | Expected: Validation error.

## 1.9 Privacy

- [ ] **U-47** | State: _Logged in as User A, profile is public_ | Action: Log in as User B, navigate to `/users/userA` | Expected: User A's public profile is visible.

- [ ] **U-48** | State: _Logged in as User A_ | Action: Set profile to private (is_public = false) | Expected: Setting saved.

- [ ] **U-49** | State: _User A profile is private_ | Action: Log in as User B, navigate to `/users/userA` | Expected: 404 or "Profile not found" (private profile hidden).

- [ ] **U-50** | State: _User A profile is private_ | Action: As User A, navigate to `/users/userA` | Expected: Own profile always visible regardless of privacy setting.

## 1.10 Navigation & Layout

- [ ] **U-51** | State: _Logged in, on `/home`_ | Action: Check sidebar (desktop) | Expected: Personal nav sections visible: Main (Home, Explore, Notifications, Activity), Account (Profile, Settings, Security).

- [ ] **U-52** | State: _Logged in, on `/home`, mobile viewport_ | Action: Check bottom navbar | Expected: Bottom navbar with Home, Explore, Notifications, Profile icons.

- [ ] **U-53** | State: _Logged in_ | Action: Click hamburger menu (mobile) | Expected: Mobile menu sheet opens with full navigation.

- [ ] **U-54** | State: _Logged in_ | Action: Click user menu in topbar | Expected: Dropdown with profile link, settings, logout option.

- [ ] **U-55** | State: _Logged in, no business memberships_ | Action: Open account switcher | Expected: Only personal context shown. No business or platform accounts listed.

- [ ] **U-56** | State: _Logged in, member of Biz-X_ | Action: Open account switcher | Expected: Personal context + Biz-X listed. Can switch to business console.

- [ ] **U-57** | State: _Not logged in_ | Action: Try to navigate to `/home` | Expected: Redirected to `/login?callbackUrl=/home`.

- [ ] **U-58** | State: _Not logged in_ | Action: Navigate to `/explore` | Expected: Explore page loads (public access). "Users" tab may be auth-gated.

## 1.11 Explore / Discovery

- [ ] **U-59** | State: _On `/explore`_ | Action: Type a search query in search bar | Expected: Results shown in "All" tab (businesses + users combined). Results update as you type or on submit.

- [ ] **U-60** | State: _On `/explore`, "Businesses" tab_ | Action: Search for a business name | Expected: Business cards shown with name, tagline, industry, location, tags.

- [ ] **U-61** | State: _On explore, Businesses tab_ | Action: Apply country filter | Expected: Results filtered to businesses in selected country. URL params updated.

- [ ] **U-62** | State: _On explore, Businesses tab_ | Action: Apply city filter (after selecting country) | Expected: Results filtered to businesses in selected city.

- [ ] **U-63** | State: _On explore, Businesses tab_ | Action: Apply industry filter | Expected: Results filtered by industry.

- [ ] **U-64** | State: _On explore, Businesses tab_ | Action: Apply company_size filter | Expected: Results filtered by company size range.

- [ ] **U-65** | State: _On explore, Businesses tab_ | Action: Apply multiple filters simultaneously | Expected: All filters applied together (AND logic). Filter indicator badge shows count.

- [ ] **U-66** | State: _On explore, Businesses tab_ | Action: Add tags filter | Expected: Tag autocomplete from `/explore/tags/` endpoint. Results filtered by tags.

- [ ] **U-67** | State: _On explore, Businesses tab, many results_ | Action: Scroll to bottom of results | Expected: Infinite scroll triggers. Next page loads. Loading indicator shown.

- [ ] **U-68** | State: _On explore_ | Action: Apply filters, then reload page | Expected: Filters restored from URL query params. Same results shown.

- [ ] **U-69** | State: _On explore_ | Action: Search with no results | Expected: Empty state message "No results found" or similar.

- [ ] **U-70** | State: _Logged in, on explore, "Users" tab_ | Action: Search for a user | Expected: User cards shown with display name, avatar, country, tags.

- [ ] **U-71** | State: _Not logged in, on explore_ | Action: Click "Users" tab | Expected: Tab is auth-gated. Prompted to log in or tab disabled.

- [ ] **U-72** | State: _On explore, Users tab_ | Action: Apply country + city filter | Expected: Users filtered by location.

- [ ] **U-73** | State: _On explore, Businesses tab_ | Action: Click on a business card | Expected: Navigated to `/business/[slug]` public profile page.

- [ ] **U-74** | State: _On explore_ | Action: Change ordering to "name" or "newest" | Expected: Results re-sorted accordingly.

## 1.12 Public Pages

- [ ] **U-75** | State: _Not logged in_ | Action: Navigate to `/` (root) | Expected: Landing/home page shown with platform info.

- [ ] **U-76** | State: _Not logged in_ | Action: Navigate to `/about` | Expected: About page loads.

- [ ] **U-77** | State: _Not logged in_ | Action: Navigate to `/contact` | Expected: Contact page loads.

- [ ] **U-78** | State: _Not logged in_ | Action: Navigate to `/business/test-business` | Expected: Public business profile page. Shows display name, tagline, description, logo, industry, location. No edit buttons.

- [ ] **U-79** | State: _Not logged in_ | Action: On public business page, check for "Join" button | Expected: If business has `open_member_request=true`, "Request to Join" button visible. If false, no join button.

- [ ] **U-80** | State: _Logged in, not member of Biz-X, open_member_request=true_ | Action: Click "Request to Join" on public business page | Expected: Join request transaction created. Success toast. Button changes to "Request Pending" or similar.

- [ ] **U-81** | State: _Logged in, already member of Biz-X_ | Action: Visit `/business/test-business` | Expected: "Request to Join" button not shown (already a member). May show "Go to Console" link instead.

- [ ] **U-82** | State: _Not logged in_ | Action: Navigate to `/platform/profile` | Expected: Public platform profile page shown (platform name, description, logo).

## 1.13 User Transactions (Receiving)

- [ ] **U-83** | State: _Logged in as User A, not member of Biz-X. Biz-X owner sent invitation_ | Action: Navigate to `/activity` or check transactions | Expected: Pending invitation visible in transaction list.

- [ ] **U-84** | State: _Viewing pending business invitation_ | Action: Click on invitation to view detail | Expected: Transaction detail page shows: initiator info, business name, role offered, message, timeline, action buttons (Accept, Deny).

- [ ] **U-85** | State: _Viewing business invitation detail_ | Action: Click "Accept" | Expected: Transaction → ACCEPTED. Membership created (ACTIVE). Redirected or toast "You joined [business]". Business now in account switcher.

- [ ] **U-86** | State: _Viewing business invitation detail_ | Action: Click "Deny" | Expected: Transaction → DENIED. Removed from active list. Toast "Invitation denied".

- [ ] **U-87** | State: _Viewing business invitation with required form_ | Action: Click "Accept" | Expected: Form dialog opens. Must fill required fields. Submit form, then accept completes. Transaction → PENDING_REVIEW. Membership → PENDING_APPROVAL.

- [ ] **U-88** | State: _Accepted invitation with form, status PENDING_REVIEW_ | Action: Check membership status | Expected: Membership shows as PENDING_APPROVAL. Limited or no console access. Guard shows "Pending Review" state.

- [ ] **U-89** | State: _Logged in as User A. User B sent connection request_ | Action: Navigate to `/activity`, view connection request transaction | Expected: Transaction detail shows User B's info, note (if any), Accept/Deny buttons. _(See also U-109..U-120 for ConnectButton CTA tests)_

- [ ] **U-90** | State: _Viewing connection request in activity_ | Action: Accept connection | Expected: Transaction → ACCEPTED. Connection record created. User B appears in My Network → Connections tab.

- [ ] **U-91** | State: _Viewing connection request in activity_ | Action: Deny connection | Expected: Transaction → DENIED. No connection record created.

- [ ] **U-92** | State: _Logged in as User A_ | Action: Send connection request to User B (via ConnectButton on `/users/e2e_user_b`) | Expected: Transaction created (PENDING). Button changes to "Cancel Request". Visible in sent transactions.

- [ ] **U-93** | State: _Sent connection request to User B, on `/users/e2e_user_b`_ | Action: Click "Cancel Request" | Expected: Transaction → CANCELLED. Button reverts to "Connect". Toast "Request cancelled".

## 1.14 Activity & Notifications (Placeholders)

- [ ] **U-94** | State: _Logged in_ | Action: Navigate to `/activity` | Expected: Activity page loads (placeholder content or empty state).

- [ ] **U-95** | State: _On activity page_ | Action: Click on an activity item (if any) | Expected: Navigated to `/activity/[id]` detail page.

- [ ] **U-96** | State: _Logged in_ | Action: Navigate to `/notifications` | Expected: Notifications page loads (placeholder content or empty state).

## 1.15 Account Deactivation

- [ ] **U-97** | State: _Logged in as User A_ | Action: Navigate to settings, click "Deactivate Account" | Expected: Confirmation dialog appears. Warns about consequences.

- [ ] **U-98** | State: _On deactivation confirmation_ | Action: Confirm deactivation | Expected: Account soft-deleted. Logged out. Redirected to login.

- [ ] **U-99** | State: _Account deactivated_ | Action: Try to log in with old credentials | Expected: Login fails or shows "Account deactivated" message.

## 1.16 Network (Follow & Connect)

### 1.16a Follow Business

- [ ] **U-100** | State: _Logged in as User A, on `/business/e2e-test-business`_ | Action: Check for Follow button | Expected: "Follow" button visible next to "Request to Join" in the action buttons area.

- [ ] **U-101** | State: _On business page, not following_ | Action: Click "Follow" | Expected: Follow created (business is public → direct follow via transaction). Button changes to "Following". Toast "Followed successfully".

- [ ] **U-102** | State: _On business page, now following_ | Action: Hover over "Following" button | Expected: Button text changes to "Unfollow", button variant changes to destructive (red outline/text).

- [ ] **U-103** | State: _Hovering "Unfollow" button_ | Action: Click "Unfollow" | Expected: Follow removed. Button reverts to "Follow". Toast "Unfollowed".

- [ ] **U-104** | State: _Not logged in, on `/business/e2e-test-business`_ | Action: Check for Follow button | Expected: Follow button NOT visible (unauthenticated users cannot follow).

### 1.16b Follow Platform

- [ ] **U-105** | State: _Logged in as User A, on `/platform/profile`_ | Action: Check for Follow button | Expected: "Follow" button visible below platform profile header.

- [ ] **U-106** | State: _On platform page, not following_ | Action: Click "Follow" | Expected: Follow auto-approved (platform_follow_request uses AUTO_APPROVAL). Button changes to "Following". Toast "Followed successfully".

- [ ] **U-107** | State: _On platform page, now following_ | Action: Hover "Following" → Click "Unfollow" → Confirm dialog | Expected: Button reverts to "Follow". Toast "Unfollowed". Same cycle as business follow.

### 1.16c User Connections

- [ ] **U-108** | State: _Logged in as User A, on `/users/e2e_user_b` (public profile)_ | Action: Check for Connect button | Expected: "Connect" button visible in profile header (not own profile).

- [ ] **U-109** | State: _On User B's profile, not connected_ | Action: Click "Connect" | Expected: Dialog opens: "Send Connection Request" with optional "Note" textarea (`#confirm-reason`).

- [ ] **U-110** | State: _On connect dialog_ | Action: Type optional note, click "Send Request" | Expected: Connection request created (transaction). Button changes to "Cancel Request". Toast "Connection request sent". Dialog closes.

- [ ] **U-111** | State: _On User B's profile, pending request (User A is initiator)_ | Action: Click "Cancel Request" | Expected: Request cancelled. Button reverts to "Connect". Toast "Request cancelled".

- [ ] **U-112** | State: _Logged in as User B, User A sent connection request. Navigate to `/users/e2e_user_a`_ | Action: Check buttons | Expected: "Accept" + "Decline" buttons visible (viewer_role = target).

- [ ] **U-113** | State: _On User A's profile as User B (target)_ | Action: Click "Accept" | Expected: Connection accepted. Buttons change to single "Connected" button. Toast "Connection accepted".

- [ ] **U-114** | State: _On User A's profile as User B, connected_ | Action: Hover over "Connected" button | Expected: Button text changes to "Disconnect", variant changes to destructive (red).

- [ ] **U-115** | State: _Hovering "Disconnect" button_ | Action: Click "Disconnect" | Expected: Connection removed. Button reverts to "Connect". Toast "Disconnected".

- [ ] **U-116** | State: _Logged in as User A, on `/users/e2e_user_c` (private/limited profile)_ | Action: Check for Connect button | Expected: "Connect" button visible even on limited/private profile views.

- [ ] **U-117** | State: _On own profile `/users/e2e_user_a`_ | Action: Check for Connect button | Expected: Connect button NOT visible (cannot connect with yourself).

- [ ] **U-118** | State: _Logged in as User B, User A sent request. Navigate to `/users/e2e_user_a`_ | Action: Click "Decline" | Expected: Request declined. Buttons revert to "Connect". Toast "Request declined".

### 1.16d My Network Page

- [ ] **U-119** | State: _Logged in as User A, connected with User B, following e2e-test-business_ | Action: Navigate to `/network` | Expected: "My Network" page loads. Header shows stats (e.g., "1 connections · 1 following"). Default tab is "Connections".

- [ ] **U-120** | State: _On My Network page, Connections tab_ | Action: Check connections list | Expected: User B shown in connections list with display name, username, "Connected" status badge, connected date.

- [ ] **U-121** | State: _On My Network page_ | Action: Click "Following" tab | Expected: Tab switches. Following list shows "E2E Test Business" with type badge "business", followed since date.

- [ ] **U-122** | State: _On My Network page, Connections tab_ | Action: Type User B's name in search input | Expected: List filters to show only matching connections.

- [ ] **U-123** | State: _On My Network page, Connections tab_ | Action: Search for non-existent name | Expected: Empty state: "No connections match your search."

- [ ] **U-124** | State: _On My Network page, no connections at all_ | Action: Check empty state | Expected: "No connections yet." message shown.

- [ ] **U-125** | State: _On My Network page, Following tab_ | Action: Check unfollow action | Expected: "Unfollow" button visible on each following card. Click → confirmation → item removed from list.

### 1.16e Navigation

- [ ] **U-126** | State: _Logged in, check sidebar_ | Action: Find Network nav item | Expected: "Network" item visible in Main section (between Explore and Notifications) with Users2 icon.

- [ ] **U-127** | State: _On sidebar_ | Action: Click "Network" | Expected: Navigated to `/network`. Nav item highlighted as active.

---

# SCOPE 2: BUSINESS (B)

## 2.1 Create Business Account

- [ ] **B-01** | State: _Logged in as User A, no businesses_ | Action: Find "Create Business" option (account switcher or nav) | Expected: Create business form shown with fields: legal_name, country, slug (optional), business_type, registration_number, tax_id.

- [ ] **B-02** | State: _On create business form_ | Action: Fill in legal_name + country, submit | Expected: Business created. Slug auto-generated from legal_name. Redirected to `/bconsole/[slug]/dashboard`. User A is now Owner.

- [ ] **B-03** | State: _Just created Biz-X_ | Action: Check account switcher | Expected: Biz-X appears in account list.

- [ ] **B-04** | State: _Just created Biz-X_ | Action: Check member list | Expected: Only User A listed as Owner. Member count = 1.

- [ ] **B-05** | State: _Just created Biz-X_ | Action: Check roles list | Expected: 2 system roles: "Business Owner" (level 0) and "Base Member" (level 10). Both marked as system roles.

- [ ] **B-06** | State: _On create business form_ | Action: Submit with slug that already exists | Expected: Error "Slug already taken" or auto-suggestion.

## 2.2 Business Profile

- [ ] **B-07** | State: _Logged in as User A (Owner of Biz-X), on `/bconsole/[slug]/profile`_ | Action: View profile page | Expected: Edit form visible (has `can_edit_profile` permission). Fields: display_name, tagline, description, logo, cover_image, website, social_links, industry, company_size, tags, is_public.

- [ ] **B-08** | State: _On business profile edit_ | Action: Update display_name and tagline, save | Expected: Profile updated. Success toast. Changes reflected.

- [ ] **B-09** | State: _On business profile edit_ | Action: Update description (long text) | Expected: Description saved. Rendered on public profile.

- [ ] **B-10** | State: _On business profile edit_ | Action: Upload logo image | Expected: Logo uploaded (deferred until form save). Preview shown. After save, logo visible on profile.

- [ ] **B-11** | State: _On business profile edit_ | Action: Upload cover image | Expected: Cover image uploaded and displayed.

- [ ] **B-12** | State: _On business profile edit_ | Action: Add social links (Twitter, LinkedIn) | Expected: Social links saved. Shown on profile/public page.

- [ ] **B-13** | State: _On business profile edit_ | Action: Add tags | Expected: Tags saved (JSONField). Shown on profile. Searchable in explore.

- [ ] **B-14** | State: _On business profile edit_ | Action: Set company_size, industry, founded_year | Expected: Fields saved. Shown on public profile.

- [ ] **B-15** | State: _On business profile edit_ | Action: Set website URL | Expected: Website URL saved and displayed.

- [ ] **B-16** | State: _On business profile edit_ | Action: Toggle is_public OFF | Expected: Business profile hidden from public explore. Direct URL still accessible to members.

- [ ] **B-17** | State: _Logged in as Base Member of Biz-X (no `can_edit_profile` permission)_ | Action: Navigate to `/bconsole/[slug]/profile` | Expected: Read-only profile view shown. No edit form. No save button.

- [ ] **B-18** | State: _Not logged in_ | Action: Navigate to `/business/[slug]` for private business | Expected: 404 or "Business not found" (profile not public).

## 2.3 Business Account Management

- [ ] **B-19** | State: _Logged in as Owner of Biz-X_ | Action: Change business slug | Expected: Slug updated. Old slug redirects (301) to new slug. URL updated.

- [ ] **B-20** | State: _Logged in as non-owner member of Biz-X_ | Action: Try to change slug | Expected: Option not visible or 403 error ("Only owner can change slug").

- [ ] **B-21** | State: _Logged in as Owner of Biz-X_ | Action: Update business account fields (legal_name, business_type, country) | Expected: Account updated. Success toast.

- [ ] **B-22** | State: _Platform admin_ | Action: Suspend Biz-X | Expected: Business suspended. Members lose access. Status shown as suspended.

- [ ] **B-23** | State: _Platform admin, Biz-X is suspended_ | Action: Reactivate Biz-X | Expected: Business reactivated. Members regain access.

- [ ] **B-24** | State: _Owner of Biz-X_ | Action: Archive business | Expected: Business archived. No longer active. Confirmation dialog shown first.

- [ ] **B-25** | State: _Logged in_ | Action: Access business by UUID via `/business/id/[uuid]` | Expected: Business detail page loads with correct data.

- [ ] **B-26** | State: _Biz-X slug changed from `old-slug` to `new-slug`_ | Action: Navigate to `/business/old-slug` | Expected: 301 redirect to `/business/new-slug`.

## 2.4 Role Management

- [ ] **B-27** | State: _Logged in as Owner of Biz-X, on `/bconsole/[slug]/roles`_ | Action: View roles list | Expected: All roles listed with name, level, member_count. System roles (Owner, Base Member) shown.

- [ ] **B-28** | State: _On roles page_ | Action: Click "Create Role" | Expected: Dialog/form opens with fields: name, level (1-9), description.

- [ ] **B-29** | State: _On create role dialog_ | Action: Create role "Admin" at level 2 | Expected: Role created. Appears in list. Member count = 0.

- [ ] **B-30** | State: _On create role dialog_ | Action: Try to create role at level 0 | Expected: Error "Level 0 is reserved for owner".

- [ ] **B-31** | State: _On create role dialog_ | Action: Try to create role at level 10 (same as Base Member) | Expected: Role created at level 10 (valid). OR error if level must be unique — verify behavior.

- [ ] **B-32** | State: _On role detail page for "Admin" role_ | Action: Edit role name and description | Expected: Role updated. Success toast.

- [ ] **B-33** | State: _On role detail for "Admin" role_ | Action: Add permissions (e.g., can_invite_member, can_view_members) | Expected: Permissions added. Listed on role detail. Success toast.

- [ ] **B-34** | State: _On role detail for "Admin" role_ | Action: Remove a permission | Expected: Permission removed from role.

- [ ] **B-35** | State: _On role detail for system role (Owner or Base Member)_ | Action: Try to edit name/description | Expected: Edit disabled. System roles cannot be modified. UI shows message or buttons hidden.

- [ ] **B-36** | State: _On role detail for system role_ | Action: Try to delete system role | Expected: Delete button hidden or disabled. Cannot delete system roles.

- [ ] **B-37** | State: _On role detail for custom role with 0 members_ | Action: Delete the role | Expected: Role deleted. Removed from list. Success toast.

- [ ] **B-38** | State: _On role detail for custom role with 1+ active members_ | Action: Try to delete the role | Expected: Error "Cannot delete role with active members". Must reassign members first.

- [ ] **B-39** | State: _Logged in as Base Member (no `can_manage_roles` permission)_ | Action: Navigate to `/bconsole/[slug]/roles` | Expected: Roles list visible (read-only). No "Create Role" button. No edit/delete options.

- [ ] **B-40** | State: _On roles list_ | Action: Verify member_count annotation | Expected: Each role shows correct count of active members assigned to it.

- [ ] **B-41** | State: _Owner of Biz-X_ | Action: Create role "Moderator" at level 5, add permissions | Expected: Role created with permissions. Ready for member assignment.

- [ ] **B-42** | State: _Viewing role detail_ | Action: Check `_permissions` in response | Expected: Role detail shows `can_edit`, `can_delete`, `can_modify_permissions` booleans matching viewer's authority.

## 2.5 Member Management

- [ ] **B-43** | State: _Owner of Biz-X (has members), on `/bconsole/[slug]/members`_ | Action: View member list | Expected: All members listed with name, avatar, role, status, joined date. Paginated (20 per page).

- [ ] **B-44** | State: _On member list_ | Action: Search by member name | Expected: List filtered to matching members.

- [ ] **B-45** | State: _On member list_ | Action: Filter by status = "active" | Expected: Only active members shown.

- [ ] **B-46** | State: _On member list_ | Action: Filter by status = "suspended" | Expected: Only suspended members shown.

- [ ] **B-47** | State: _On member list_ | Action: Filter by role = "Base Member" | Expected: Only members with Base Member role shown.

- [ ] **B-48** | State: _On member list_ | Action: Change ordering to "name" / "newest" | Expected: List re-sorted accordingly.

- [ ] **B-49** | State: _On member list, 25+ members_ | Action: Navigate to page 2 | Expected: Next page of members loaded. Pagination controls work.

- [ ] **B-50** | State: _On member list_ | Action: Click on a member card | Expected: Navigated to member detail page `/bconsole/[slug]/members/[id]`.

### Member Detail & Actions

- [ ] **B-51** | State: _Owner, viewing Base Member (User B) detail_ | Action: Check available actions | Expected: Actions dropdown visible with: Change Role, Suspend, Remove, Ban. (Based on `_permissions`: can_change_role, can_suspend, can_remove, can_ban all true.)

- [ ] **B-52** | State: _Owner, viewing User B (Base Member) detail_ | Action: Change role to "Admin" | Expected: Role changed. Member detail updated. Success toast.

- [ ] **B-53** | State: _Owner, viewing User B (now Admin) detail_ | Action: Change role back to "Base Member" | Expected: Role changed back successfully.

- [ ] **B-54** | State: _Owner, viewing User B detail_ | Action: Suspend member | Expected: Member status → SUSPENDED. Member card shows "Suspended" status. Success toast.

- [ ] **B-55** | State: _Owner, User B is suspended_ | Action: Reactivate member | Expected: Member status → ACTIVE. Success toast.

- [ ] **B-56** | State: _Owner, viewing User B detail_ | Action: Remove member | Expected: Member status → REMOVED. Member still in list with "Removed" status. Success toast.

- [ ] **B-57** | State: _Owner, User B is removed_ | Action: Reactivate member | Expected: Member status → ACTIVE. Fully reinstated.

- [ ] **B-58** | State: _Owner, viewing User B detail_ | Action: Ban member | Expected: Member status → BANNED. Confirmation dialog first. Cannot be reactivated via normal flow.

- [ ] **B-59** | State: _Owner, viewing own member detail_ | Action: Check available actions | Expected: No action buttons on own membership (cannot act on yourself). Or only "Leave" option.

### Dominance & Invincibility Rules

- [ ] **B-60** | State: _Admin (level 2), viewing Base Member (level 10) detail_ | Action: Check actions | Expected: Can change role, suspend, remove, ban (admin outranks base member: 2 < 10).

- [ ] **B-61** | State: _Admin (level 2), viewing another Admin (level 2) detail_ | Action: Check actions | Expected: NO action buttons (same level, cannot act on peers).

- [ ] **B-62** | State: _Admin (level 2), viewing Owner (level 0) detail_ | Action: Check actions | Expected: NO action buttons (owner is invincible within same account).

- [ ] **B-63** | State: _Base Member (no permissions), viewing any member detail_ | Action: Check actions | Expected: No action buttons. Read-only view.

### Leave Business

- [ ] **B-64** | State: _Logged in as User B (Base Member of Biz-X)_ | Action: Click "Leave Business" | Expected: Confirmation dialog. After confirm: membership → LEFT. Redirected away from bconsole. Business removed from account switcher.

- [ ] **B-65** | State: _Logged in as Owner of Biz-X (sole owner)_ | Action: Try to "Leave Business" | Expected: Error "Owner cannot leave. Transfer ownership first." Leave button hidden or disabled.

### Member States Visibility

- [ ] **B-66** | State: _Owner of Biz-X, User B is SUSPENDED_ | Action: Log in as User B, try to access `/bconsole/[slug]/` | Expected: BusinessGuard blocks access. Shows "Your membership is suspended" message.

- [ ] **B-67** | State: _Owner of Biz-X, User B is REMOVED_ | Action: Log in as User B, try to access `/bconsole/[slug]/` | Expected: BusinessGuard blocks access. Business not in account switcher.

- [ ] **B-68** | State: _Owner of Biz-X, User B has PENDING_APPROVAL membership_ | Action: Log in as User B, try to access `/bconsole/[slug]/` | Expected: BusinessGuard shows "Pending Review" state. Limited/no console access.

## 2.6 Member Quota

- [ ] **B-69** | State: _Biz-X has max_members=1, 1 active member (Owner)_ | Action: As Owner, try to create invitation | Expected: Error "Member quota exceeded". Cannot invite.

- [ ] **B-70** | State: _Biz-X has max_members=1_ | Action: As external user, try to send join request | Expected: Error "Member quota exceeded".

- [ ] **B-71** | State: _Admin increases Biz-X max_members to 5_ | Action: Create invitation for User B | Expected: Invitation created successfully (quota allows).

- [ ] **B-72** | State: _Biz-X has max_members=3, 3 active members_ | Action: Try to create invitation | Expected: Error "Member quota exceeded".

- [ ] **B-73** | State: _Biz-X has max_members=3, 2 active + 1 PENDING_APPROVAL_ | Action: Try to create invitation | Expected: Error "Member quota exceeded" (PENDING_APPROVAL counts toward quota).

- [ ] **B-74** | State: _Biz-X has max_members=0 (unlimited)_ | Action: Create multiple invitations | Expected: All invitations created successfully. No quota limit.

- [ ] **B-75** | State: _Biz-X at quota, 1 member suspended_ | Action: Try to create invitation | Expected: Suspended members may NOT count toward quota (verify behavior). If they don't count, invitation succeeds.

- [ ] **B-76** | State: _Biz-X at quota_ | Action: Remove a member, then try to invite | Expected: After removal, quota has room. Invitation succeeds.

## 2.7 Open Member Request

- [ ] **B-77** | State: _Owner of Biz-X, open_member_request=false_ | Action: As external User B, try to send join request | Expected: Error "This organization is not accepting membership requests".

- [ ] **B-78** | State: _Owner of Biz-X_ | Action: Toggle open_member_request to true (in settings) | Expected: Setting saved. Success toast.

- [ ] **B-79** | State: _Biz-X open_member_request=true_ | Action: As User B, send join request | Expected: Request created (PENDING). Visible in business transactions.

- [ ] **B-80** | State: _Owner_ | Action: Toggle open_member_request back to false | Expected: Setting saved. New requests blocked.

- [ ] **B-81** | State: _Biz-X open_member_request=false AND max_members quota exceeded_ | Action: As User B, try to send join request | Expected: Error "This organization is not accepting membership requests" (closed check runs BEFORE quota check).

- [ ] **B-82** | State: _Biz-X open_member_request=true AND max_members quota exceeded_ | Action: As User B, try to send join request | Expected: Error "Member quota exceeded" (quota check runs after open check).

## 2.8 Transactions — Invitations (Business → User)

- [ ] **B-83** | State: _Owner of Biz-X, max_members > current count_ | Action: Navigate to transactions, click "Create Invitation" | Expected: Invitation form shown. Fields: target (email/username/user_id), role selection, message.

- [ ] **B-84** | State: _On invitation form_ | Action: Enter User B's username, select "Base Member" role, add message, submit | Expected: Invitation created (PENDING). Appears in invitations list. Success toast.

- [ ] **B-85** | State: _On invitation form_ | Action: Enter User B's email instead of username | Expected: Invitation created. Target resolved by email.

- [ ] **B-86** | State: _Invitation to User B is PENDING_ | Action: View invitation detail | Expected: Detail page shows: target info, role, message, status=PENDING, timeline, action buttons (Cancel).

- [ ] **B-87** | State: _Owner viewing PENDING invitation_ | Action: Cancel the invitation | Expected: Transaction → CANCELLED. Status updated in list.

- [ ] **B-88** | State: _Owner creates invitation for User B who is already an active member_ | Action: Submit invitation | Expected: Error "User is already a member of this business".

- [ ] **B-89** | State: _Owner creates invitation for User B while another PENDING invitation exists for User B_ | Action: Submit | Expected: Error "Duplicate active transaction" — cannot have two pending invitations for same target.

- [ ] **B-90** | State: _User B logged in, has PENDING invitation from Biz-X_ | Action: Accept invitation | Expected: Transaction → ACCEPTED. Membership created (ACTIVE, Base Member role). Biz-X appears in account switcher.

- [ ] **B-91** | State: _User B, has PENDING invitation_ | Action: Deny invitation | Expected: Transaction → DENIED. No membership created.

- [ ] **B-92** | State: _Owner creates invitation with role "Admin" (level 2)_ | Action: User B accepts | Expected: Membership created with Admin role. User B has admin-level permissions.

### Invitation with Required Form (Two-Phase)

- [ ] **B-93** | State: _Biz-X has TransactionFormMapping for `business_membership_invitation` with is_required=true_ | Action: User B receives invitation and clicks "Accept" | Expected: Form dialog opens. User B must fill required form fields.

- [ ] **B-94** | State: _User B filling required form in accept dialog_ | Action: Fill all required fields, submit form, then accept | Expected: Transaction → PENDING_REVIEW. Membership created as PENDING_APPROVAL. Toast "Accepted, pending business review".

- [ ] **B-95** | State: _Transaction in PENDING_REVIEW, User B has PENDING_APPROVAL membership_ | Action: As Owner, view transaction detail | Expected: Detail shows PENDING_REVIEW status. "Approve" and "Deny" buttons visible. Form response viewable.

- [ ] **B-96** | State: _Owner viewing PENDING_REVIEW transaction_ | Action: Click "Approve" | Expected: Transaction → ACCEPTED. Membership → ACTIVE. User B gains full console access.

- [ ] **B-97** | State: _Owner viewing PENDING_REVIEW transaction_ | Action: Click "Deny" | Expected: Transaction → DENIED. PENDING_APPROVAL membership soft-deleted. User B loses provisional access.

- [ ] **B-98** | State: _Owner viewing PENDING_REVIEW transaction with form_ | Action: Click "Request Info" | Expected: Transaction → INFO_REQUESTED. User B notified to update form submission.

- [ ] **B-99** | State: _User B, invitation in INFO_REQUESTED state_ | Action: Update form response, click "Resubmit" | Expected: Transaction → PENDING_REVIEW (back to review). Owner can re-review.

- [ ] **B-100** | State: _Transaction in PENDING_REVIEW_ | Action: User B (target) clicks "Cancel" | Expected: Transaction → CANCELLED. PENDING_APPROVAL membership soft-deleted.

## 2.9 Transactions — Requests (User → Business)

- [ ] **B-101** | State: _Logged in as User B, not member of Biz-X, Biz-X has open_member_request=true_ | Action: Send join request (from explore or public page) | Expected: Request created (PENDING). Appears in User B's transactions.

- [ ] **B-102** | State: _User B sent join request_ | Action: As Owner of Biz-X, navigate to transactions → Requests | Expected: User B's request visible in requests list.

- [ ] **B-103** | State: _Owner viewing User B's join request detail_ | Action: Click "Accept" (select role for new member) | Expected: Transaction → ACCEPTED. User B's membership created (ACTIVE) with selected role. Toast "Request accepted".

- [ ] **B-104** | State: _Owner viewing join request_ | Action: Click "Deny" with reason | Expected: Transaction → DENIED. Reason recorded. User B notified.

- [ ] **B-105** | State: _Owner viewing join request_ | Action: Click "Dismiss" | Expected: Transaction → DISMISSED.

- [ ] **B-106** | State: _User B, request is PENDING_ | Action: Cancel own request | Expected: Transaction → CANCELLED.

- [ ] **B-107** | State: _User B previously denied, cooldown active (7 days)_ | Action: Try to send another join request | Expected: Error "Resubmission cooldown active" (7-day cooldown for business_membership_request).

### Request with Required Form (Two-Phase)

- [ ] **B-108** | State: _Biz-X has TransactionFormMapping for `business_membership_request` with is_required=true_ | Action: User B sends join request | Expected: Must provide form_response_id with request. Form filling required before/during request creation.

- [ ] **B-109** | State: _User B submitted request with form_ | Action: Owner views request detail | Expected: Form response visible. Can review submitted data.

- [ ] **B-110** | State: _Owner viewing request with form_ | Action: Accept request | Expected: Transaction → PENDING_REVIEW (if form is required). Membership → PENDING_APPROVAL.

- [ ] **B-111** | State: _Request in PENDING_REVIEW_ | Action: Owner approves | Expected: Transaction → ACCEPTED. Membership → ACTIVE.

- [ ] **B-112** | State: _Owner viewing request with form_ | Action: Request info | Expected: Transaction → INFO_REQUESTED. User B can update form and resubmit.

## 2.10 Transaction Settings (Form Mappings)

- [ ] **B-113** | State: _Owner of Biz-X, on `/bconsole/[slug]/transactions/settings`_ | Action: View transaction settings page | Expected: List of transaction types. Form mappings shown (if any).

- [ ] **B-114** | State: _On transaction settings_ | Action: Create form mapping: attach a form template to `business_membership_request` | Expected: Mapping created. Form now associated with that transaction type.

- [ ] **B-115** | State: _Form mapping created_ | Action: Toggle `is_required` to true | Expected: Setting updated. Requests of this type now require form completion.

- [ ] **B-116** | State: _Form mapping exists_ | Action: Delete the form mapping | Expected: Mapping removed. Transaction type no longer requires form.

- [ ] **B-117** | State: _On transaction settings_ | Action: Create mapping for `business_membership_invitation` | Expected: Mapping created. Invitations now have associated form.

- [ ] **B-118** | State: _Logged in as Base Member (no `can_configure_transactions` permission)_ | Action: Navigate to transaction settings | Expected: Page not visible in nav (permission-gated) or access denied.

- [ ] **B-119** | State: _On transaction settings_ | Action: Check available transaction types list | Expected: `/transactions/types/` endpoint returns configurable types for this context.

- [ ] **B-120** | State: _Form mapping set with a published form_ | Action: Archive the mapped form template | Expected: Mapping still exists but form is archived. Verify behavior — new transactions may fail if form unavailable.

## 2.11 Forms

### Template Management

- [ ] **B-121** | State: _Owner of Biz-X (has `can_create_form`), on `/bconsole/[slug]/forms/templates`_ | Action: View templates list | Expected: List of form templates (if any). Filter by status (draft/active/archived). "Create" button visible.

- [ ] **B-122** | State: _On templates list_ | Action: Click "Create New Form" | Expected: Navigated to `/bconsole/[slug]/forms/templates/new`. Form builder in design mode. Fields: title, description.

- [ ] **B-123** | State: _On form builder (new template)_ | Action: Set title "Membership Application", save | Expected: Template created as DRAFT. Saved. Success toast.

- [ ] **B-124** | State: _On form builder, editing draft template_ | Action: Add a "text" field (label: "Full Name", required) | Expected: Field added to form. Shown in field list.

- [ ] **B-125** | State: _On form builder_ | Action: Add "email" field, "select" field with options, "textarea" field | Expected: All fields added. Correct field type icons shown.

- [ ] **B-126** | State: _On form builder_ | Action: Add "file" field | Expected: File upload field added with config for allowed types, max size.

- [ ] **B-127** | State: _On form builder with 3+ fields_ | Action: Reorder fields (drag or reorder button) | Expected: Fields reordered. New display_order saved.

- [ ] **B-128** | State: _On form builder_ | Action: Configure a field (edit label, set required, add placeholder) | Expected: Field config updated. Changes reflected in preview.

- [ ] **B-129** | State: _On form builder_ | Action: Delete a field | Expected: Field removed. Confirmation prompt first.

- [ ] **B-130** | State: _On form builder_ | Action: Switch to "Preview" mode | Expected: Form shown as end-user would see it. Fields rendered with proper types, labels, placeholders.

- [ ] **B-131** | State: _On form builder, template is DRAFT_ | Action: Click "Publish" | Expected: Template → ACTIVE. New version created (version 1). Form now usable for responses/mappings.

- [ ] **B-132** | State: _Template is ACTIVE (published)_ | Action: Click "Edit" (create edit draft) | Expected: New draft version created (copy). Original stays ACTIVE. Editing the draft doesn't affect live version.

- [ ] **B-133** | State: _Editing draft of published form_ | Action: Add new field, then publish | Expected: New version published (version 2). Old version → is_current=false. New version → is_current=true.

- [ ] **B-134** | State: _Template is ACTIVE_ | Action: Click "Archive" | Expected: Template → ARCHIVED. No longer visible in active list. Not usable for new responses.

- [ ] **B-135** | State: _Template is ARCHIVED_ | Action: Click "Unarchive" | Expected: Template → ACTIVE again.

- [ ] **B-136** | State: _On form library page `/bconsole/[slug]/forms/library`_ | Action: Browse public templates | Expected: List of public form templates from platform library.

- [ ] **B-137** | State: _On library page_ | Action: Fork a template to Biz-X | Expected: Copy created in Biz-X's templates as DRAFT. `forked_from` set.

### Form Responses

- [ ] **B-138** | State: _Template is ACTIVE with fields_ | Action: Navigate to responses list | Expected: List of responses for this form. Filter by status.

- [ ] **B-139** | State: _On form template detail_ | Action: Switch to "Fill" mode (or create response) | Expected: Empty form shown in fill mode. Fields rendered for input.

- [ ] **B-140** | State: _Filling form_ | Action: Fill all required fields with valid data, save as draft | Expected: Response created (DRAFT). Saved successfully.

- [ ] **B-141** | State: _Response is DRAFT_ | Action: Edit response, update answers | Expected: Response updated. Changes saved.

- [ ] **B-142** | State: _Response is DRAFT, all required fields filled_ | Action: Click "Submit" | Expected: Response → SUBMITTED. No longer editable. Validation passes.

- [ ] **B-143** | State: _Response is DRAFT, missing required fields_ | Action: Try to submit | Expected: Validation error "Required fields missing". Submit blocked.

- [ ] **B-144** | State: _Response is SUBMITTED_ | Action: As reviewer (with `can_process_response`), click "Process" → Approve | Expected: Response → PROCESSED. Status updated.

- [ ] **B-145** | State: _Response is SUBMITTED_ | Action: As reviewer, void the response | Expected: Response → VOID with reason.

- [ ] **B-146** | State: _On `/bconsole/[slug]/forms/responses`_ | Action: View all responses across forms | Expected: Paginated list with form name, submitter, status, date.

- [ ] **B-147** | State: _On response detail_ | Action: Switch to "View" mode | Expected: Read-only view of submitted data. All fields and answers displayed.

- [ ] **B-148** | State: _Base Member without `can_create_form` permission_ | Action: Navigate to forms section | Expected: "Forms" nav item hidden (permission-gated). Direct URL → access denied.

## 2.12 Ownership Transfer

- [ ] **B-149** | State: _Owner of Biz-X, User B is Admin member_ | Action: Create ownership transfer invitation for User B | Expected: Transaction created (PENDING). Type: `business_ownership_transfer`.

- [ ] **B-150** | State: _User B received ownership transfer invitation_ | Action: Accept | Expected: Transaction → ACCEPTED. User B → Owner (level 0). User A → demoted (to Admin or Base Member). Atomic swap.

- [ ] **B-151** | State: _After transfer, User A is no longer owner_ | Action: As User A, check role | Expected: User A is now regular member (no owner privileges). Cannot access owner-only actions.

- [ ] **B-152** | State: _After transfer_ | Action: As User B (new owner), verify full owner access | Expected: User B has all owner permissions. Can manage all settings, members, etc.

- [ ] **B-153** | State: _Logged in as Admin (not owner)_ | Action: Try to initiate ownership transfer | Expected: Option not visible or 403 error. Only owner can transfer ownership.

- [ ] **B-154** | State: _Owner, transfer invitation PENDING_ | Action: Cancel the transfer | Expected: Transaction → CANCELLED. No ownership change.

- [ ] **B-155** | State: _Owner creates transfer invitation for non-member User C_ | Action: Submit | Expected: Verify behavior — may require target to be existing member, or invitation handles it.

## 2.13 Business Verification Request

- [ ] **B-156** | State: _Owner of Biz-X_ | Action: Submit business verification request (type: `business_verification_request`) | Expected: Transaction created with required system form. Sent to platform for review.

- [ ] **B-157** | State: _Verification request PENDING_ | Action: As platform admin, view and approve | Expected: Transaction → ACCEPTED. Business verification_status updated.

- [ ] **B-158** | State: _Verification denied_ | Action: Check cooldown | Expected: 30-day resubmission cooldown before requesting again.

## 2.14 Navigation & Guards (Business Context)

- [ ] **B-159** | State: _Logged in as Owner of Biz-X_ | Action: Check sidebar in bconsole | Expected: All nav items visible: Dashboard, Profile, Members, Forms, Content, Media, Transactions, Audit Log, Settings.

- [ ] **B-160** | State: _Logged in as Base Member (minimal permissions)_ | Action: Check sidebar in bconsole | Expected: Only Dashboard and Profile visible. Permission-gated items (Members, Forms, Transactions, etc.) hidden.

- [ ] **B-161** | State: _Biz-X has max_members=1_ | Action: Check sidebar | Expected: "Members" nav item hidden (minMembers: 2 requirement not met).

- [ ] **B-162** | State: _Biz-X has max_members=5_ | Action: Check sidebar | Expected: "Members" nav item visible (minMembers: 2 requirement met).

- [ ] **B-163** | State: _Not logged in_ | Action: Navigate to `/bconsole/test-business/dashboard` | Expected: Redirected to `/login?callbackUrl=...`. AuthGuard intercepts.

- [ ] **B-164** | State: _Logged in as User C (not member of Biz-X)_ | Action: Navigate to `/bconsole/test-business/dashboard` | Expected: BusinessGuard shows "Access Denied" — no membership. Retry-on-miss logic runs but finds no membership.

- [ ] **B-165** | State: _In bconsole for Biz-X_ | Action: Click account switcher, switch to personal | Expected: Navigated to `/home`. Sidebar shows personal nav items.

## 2.15 Network Management (Business)

### 2.15a Business Followers Management

- [ ] **B-166** | State: _Logged in as User B (Owner of e2e-test-business), User A follows the business. Navigate to `/bconsole/e2e-test-business/network/followers`_ | Action: View followers page | Expected: "Followers" page loads. User A shown in list with avatar, display name, username, followed since date.

- [ ] **B-167** | State: _On followers page, has `can_manage_followers` permission_ | Action: Check "Remove" button | Expected: "Remove" button visible on each follower card.

- [ ] **B-168** | State: _On followers page_ | Action: Click "Remove" on User A | Expected: Confirmation dialog (destructive variant). After confirm: follower removed. Toast notification. User A no longer in followers list.

- [ ] **B-169** | State: _Logged in as Base Member (no `can_manage_followers` permission)_ | Action: Navigate to followers page | Expected: "Remove" button NOT visible on follower cards (permission-gated).

- [ ] **B-170** | State: _On followers page with multiple followers_ | Action: Type in search input | Expected: List filters by display name.

### 2.15b Business Connections Management

- [ ] **B-171** | State: _Owner on `/bconsole/e2e-test-business/network/connections`_ | Action: View connections page | Expected: "Connections" page loads. Account connections listed (if any). Empty state if none.

- [ ] **B-172** | State: _On connections page, has `can_manage_connections` permission_ | Action: Check "Disconnect" button | Expected: "Disconnect" button visible on each connection card.

### 2.15c Business Network Navigation

- [ ] **B-173** | State: _Owner in bconsole, check sidebar_ | Action: Find Network section | Expected: "Network" section visible with "Followers" (Heart icon) and "Connections" (Users2 icon) sub-items.

- [ ] **B-174** | State: _Owner in bconsole_ | Action: Click "Followers" in sidebar | Expected: Navigated to `/bconsole/e2e-test-business/network/followers`. Nav item highlighted.

- [ ] **B-175** | State: _Base Member without network permissions (`can_manage_followers`, `can_manage_connections`)_ | Action: Check sidebar | Expected: "Followers" and "Connections" nav items NOT visible (permission-gated).

---

# SCOPE 3: PLATFORM (P)

## 3.1 Platform Setup

- [ ] **P-01** | State: _Logged in as superuser, no platform configured_ | Action: POST to create platform account (name, settings) | Expected: Platform account created (singleton). Superuser becomes Platform Owner. 3 system roles created (Owner, Admin, Moderator).

- [ ] **P-02** | State: _Platform already configured_ | Action: Try to create again | Expected: Error — singleton constraint. Platform already exists.

- [ ] **P-03** | State: _Logged in as Platform Owner_ | Action: Navigate to `/pconsole/dashboard` | Expected: Platform console dashboard loads. Sidebar shows platform nav items.

- [ ] **P-04** | State: _Logged in as regular user (non-platform-member)_ | Action: Navigate to `/pconsole/dashboard` | Expected: PlatformGuard blocks access. "Access Denied" or redirect.

## 3.2 Platform Profile

- [ ] **P-05** | State: _Platform Owner, on `/pconsole/profile`_ | Action: View profile page | Expected: Edit form visible (has `can_edit_profile`). Fields: name, tagline, description, logo, favicon, primary_color, secondary_color, contact_email, contact_phone, address, social_links.

- [ ] **P-06** | State: _On platform profile edit_ | Action: Update name and tagline, save | Expected: Profile updated. Success toast.

- [ ] **P-07** | State: _On platform profile edit_ | Action: Upload logo | Expected: Logo uploaded (deferred). After save, logo shown on profile.

- [ ] **P-08** | State: _On platform profile edit_ | Action: Upload favicon | Expected: Favicon uploaded and saved.

- [ ] **P-09** | State: _On platform profile edit_ | Action: Set primary_color to `#FF5500` | Expected: Color saved (hex validation). Applied to platform branding.

- [ ] **P-10** | State: _On platform profile edit_ | Action: Set invalid color (e.g., "red") | Expected: Validation error — must be hex format (#RRGGBB).

- [ ] **P-11** | State: _On platform profile edit_ | Action: Add social links | Expected: Social links saved and displayed.

- [ ] **P-12** | State: _On platform profile edit_ | Action: Update contact info (email, phone, address) | Expected: Contact info saved.

- [ ] **P-13** | State: _Logged in as Platform Admin (has `can_edit_profile`)_ | Action: Edit platform profile | Expected: Can edit (permission granted). Changes saved.

- [ ] **P-14** | State: _Logged in as Global Moderator (no `can_edit_profile`)_ | Action: Navigate to profile page | Expected: Read-only view. No edit controls.

## 3.3 Platform Settings

- [ ] **P-15** | State: _Platform Owner (superuser)_ | Action: Navigate to platform settings, update settings JSON | Expected: Settings merged and saved.

- [ ] **P-16** | State: _Platform Owner_ | Action: Toggle open_member_request to true | Expected: Platform now accepts membership requests from users.

- [ ] **P-17** | State: _Platform Owner_ | Action: Toggle open_member_request to false | Expected: Platform no longer accepts membership requests.

- [ ] **P-18** | State: _Logged in as Platform Admin (not superuser)_ | Action: Try to update platform settings | Expected: Depends on permissions — if has `can_edit_business`, may succeed. Otherwise 403.

## 3.4 Role Management (Platform)

- [ ] **P-19** | State: _Platform Owner, on `/pconsole/roles`_ | Action: View roles list | Expected: 3 system roles listed: Platform Owner (level 0), Platform Admin (level 2), Global Moderator (level 5). Each shows member_count.

- [ ] **P-20** | State: _On roles list_ | Action: Verify NO "Base Member" role exists | Expected: Platform has only 3 system roles (unlike business which has Owner + Base Member).

- [ ] **P-21** | State: _On roles page_ | Action: Create custom role "Content Manager" at level 7 | Expected: Role created. Appears in list with member_count = 0.

- [ ] **P-22** | State: _On custom role detail_ | Action: Add permissions (e.g., can_create_form, can_view_cms_content) | Expected: Permissions added to role.

- [ ] **P-23** | State: _On custom role detail_ | Action: Edit role name and description | Expected: Role updated.

- [ ] **P-24** | State: _On custom role detail (0 members)_ | Action: Delete role | Expected: Role deleted. Removed from list.

- [ ] **P-25** | State: _On system role (Platform Admin)_ | Action: Try to edit or delete | Expected: Cannot modify system roles. Edit/delete buttons hidden or disabled.

- [ ] **P-26** | State: _Platform Admin (level 2)_ | Action: Try to create role at level 1 (higher than own) | Expected: Error — cannot create role above own level.

- [ ] **P-27** | State: _Platform Admin_ | Action: Create role at level 3 (below own) | Expected: Role created successfully.

- [ ] **P-28** | State: _On roles list_ | Action: Verify member_count annotation | Expected: Each role shows correct count of active platform memberships.

## 3.5 Member Management (Platform)

- [ ] **P-29** | State: _Platform Owner, on `/pconsole/members`_ | Action: View member list | Expected: All platform members listed. Search, filter, pagination available.

- [ ] **P-30** | State: _On member list_ | Action: Search by name | Expected: Filtered results shown.

- [ ] **P-31** | State: _On member list_ | Action: Filter by status (active/suspended) | Expected: Correctly filtered.

- [ ] **P-32** | State: _On member list_ | Action: Filter by role | Expected: Members with selected role shown.

- [ ] **P-33** | State: _Owner, viewing Platform Admin member detail_ | Action: Check actions | Expected: Can change role, suspend, remove, ban (owner outranks admin: 0 < 2).

- [ ] **P-34** | State: _Owner, viewing another Owner_ | Action: Check actions | Expected: No actions available (platform owner is ALWAYS invincible).

- [ ] **P-35** | State: _Platform Admin, viewing Global Moderator_ | Action: Check actions | Expected: Can act on moderator (2 < 5). Actions available.

- [ ] **P-36** | State: _Platform Admin, viewing another Platform Admin_ | Action: Check actions | Expected: No actions (same level, cannot act on peers).

- [ ] **P-37** | State: _Owner, viewing member_ | Action: Change role from Moderator to Admin | Expected: Role changed. Member now has admin permissions.

- [ ] **P-38** | State: _Owner, viewing member_ | Action: Suspend member | Expected: Member → SUSPENDED. Loses platform console access.

- [ ] **P-39** | State: _Owner, member is suspended_ | Action: Reactivate member | Expected: Member → ACTIVE. Regains access.

- [ ] **P-40** | State: _Owner, viewing member_ | Action: Remove member | Expected: Member → REMOVED.

- [ ] **P-41** | State: _Owner, viewing member_ | Action: Ban member | Expected: Member → BANNED. Confirmation dialog. Permanent.

- [ ] **P-42** | State: _Logged in as Platform Member_ | Action: Click "Leave Platform" | Expected: Confirmation dialog. After confirm: membership → LEFT. Loses platform console access.

- [ ] **P-43** | State: _Platform Owner (sole owner)_ | Action: Try to leave platform | Expected: Error "Owner cannot leave. Transfer ownership first."

- [ ] **P-44** | State: _Platform member is SUSPENDED_ | Action: Log in as that user, try to access `/pconsole/` | Expected: PlatformGuard blocks. Shows "Membership suspended" message.

## 3.6 Transactions — Invitations (Platform)

- [ ] **P-45** | State: _Platform Owner, max_members > current count_ | Action: Create platform membership invitation for User B | Expected: Transaction created (PENDING). Type: `platform_membership_invitation`. Requires role_id in payload.

- [ ] **P-46** | State: _Invitation created_ | Action: View in invitations list | Expected: Invitation visible with target info, role, status.

- [ ] **P-47** | State: _User B logged in_ | Action: View and accept invitation | Expected: Transaction → ACCEPTED. Platform membership created (ACTIVE). `/pconsole` accessible.

- [ ] **P-48** | State: _User B logged in_ | Action: Deny invitation | Expected: Transaction → DENIED.

- [ ] **P-49** | State: _Platform Owner_ | Action: Cancel pending invitation | Expected: Transaction → CANCELLED.

- [ ] **P-50** | State: _Platform Owner, invitation has required form mapping_ | Action: User B accepts invitation | Expected: Form dialog appears. User B fills form. Transaction → PENDING_REVIEW. Membership → PENDING_APPROVAL.

- [ ] **P-51** | State: _Transaction in PENDING_REVIEW_ | Action: Platform Owner approves | Expected: Transaction → ACCEPTED. Membership → ACTIVE.

- [ ] **P-52** | State: _Transaction in PENDING_REVIEW_ | Action: Platform Owner denies | Expected: Transaction → DENIED. PENDING_APPROVAL membership soft-deleted.

- [ ] **P-53** | State: _Transaction in PENDING_REVIEW_ | Action: Platform Owner requests info | Expected: Transaction → INFO_REQUESTED.

- [ ] **P-54** | State: _Transaction INFO_REQUESTED_ | Action: User B updates form, resubmits | Expected: Transaction → PENDING_REVIEW.

- [ ] **P-55** | State: _Platform at max_members quota_ | Action: Try to create invitation | Expected: Error "Member quota exceeded".

- [ ] **P-56** | State: _Existing active member_ | Action: Try to invite them again | Expected: Error "User is already a member".

## 3.7 Transactions — Requests (User → Platform)

- [ ] **P-57** | State: _Platform open_member_request=true, User B not a member_ | Action: User B sends platform join request | Expected: Request created (PENDING). Type: `platform_membership_request`.

- [ ] **P-58** | State: _Platform open_member_request=false_ | Action: User B tries to send join request | Expected: Error "This organization is not accepting membership requests".

- [ ] **P-59** | State: _Request PENDING_ | Action: Platform admin/owner views request list | Expected: User B's request visible.

- [ ] **P-60** | State: _Viewing request detail_ | Action: Accept (with role selection) | Expected: Transaction → ACCEPTED. User B → platform member.

- [ ] **P-61** | State: _Viewing request_ | Action: Deny with reason | Expected: Transaction → DENIED.

- [ ] **P-62** | State: _Viewing request_ | Action: Dismiss | Expected: Transaction → DISMISSED.

- [ ] **P-63** | State: _User B, request PENDING_ | Action: Cancel own request | Expected: Transaction → CANCELLED.

- [ ] **P-64** | State: _User B denied, within 7-day cooldown_ | Action: Try to re-request | Expected: Error "Resubmission cooldown active".

- [ ] **P-65** | State: _Platform has form mapping for `platform_membership_request` (is_required=true)_ | Action: User B sends request | Expected: Must fill form. After form + acceptance → PENDING_REVIEW.

- [ ] **P-66** | State: _Request in PENDING_REVIEW_ | Action: Owner approves | Expected: Transaction → ACCEPTED. Membership → ACTIVE.

## 3.8 Ownership Transfer (Platform)

- [ ] **P-67** | State: _Platform Owner_ | Action: Create ownership transfer invitation for existing platform member | Expected: Transaction created (PENDING). Type: `platform_ownership_transfer`.

- [ ] **P-68** | State: _Target accepts transfer_ | Action: Accept | Expected: Ownership transferred. Old owner demoted. New owner at level 0.

- [ ] **P-69** | State: _Non-owner platform member_ | Action: Try to initiate ownership transfer | Expected: Error — owner_only action. Not allowed.

- [ ] **P-70** | State: _Transfer PENDING_ | Action: Owner cancels | Expected: Transaction → CANCELLED. No ownership change.

## 3.9 Forms (Platform)

- [ ] **P-71** | State: _Platform member with `can_create_form`, on `/pconsole/forms/templates`_ | Action: View templates list | Expected: Platform-scoped form templates listed.

- [ ] **P-72** | State: _On templates page_ | Action: Create new platform form template | Expected: Form builder opens. Can add fields, configure, save as draft.

- [ ] **P-73** | State: _Draft template_ | Action: Publish | Expected: Template → ACTIVE. Versioned.

- [ ] **P-74** | State: _On form library_ | Action: View public templates | Expected: Library of public templates. Can fork to platform.

- [ ] **P-75** | State: _On responses page_ | Action: View platform form responses | Expected: All responses for platform forms listed.

- [ ] **P-76** | State: _On transaction settings `/pconsole/transactions/settings`_ | Action: Create form mapping for `platform_membership_request` | Expected: Mapping created. Platform requests now require/include this form.

- [ ] **P-77** | State: _On transaction settings_ | Action: Toggle mapping `is_required` | Expected: Setting updated.

- [ ] **P-78** | State: _Member without form permissions_ | Action: Try to access forms | Expected: Nav item hidden. Direct URL → access denied.

## 3.10 CMS (Placeholder Pages)

- [ ] **P-79** | State: _Platform member with CMS permissions_ | Action: Navigate to `/cconsole/sites` | Expected: Page loads (placeholder or empty state). "Sites" section exists.

- [ ] **P-80** | State: _On CMS templates page_ | Action: Navigate to `/cconsole/templates` | Expected: Page loads (placeholder or empty state).

- [ ] **P-81** | State: _On API keys page_ | Action: Navigate to `/cconsole/api-keys` | Expected: Page loads (placeholder or empty state).

- [ ] **P-82** | State: _On media page_ | Action: Navigate to `/pconsole/media` | Expected: Page loads (placeholder or empty state).

## 3.11 Navigation & Guards (Platform Context)

- [ ] **P-83** | State: _Platform Owner_ | Action: Check pconsole sidebar | Expected: All sections visible: Overview (Dashboard, Profile), Management (Businesses, Members), CMS (Sites, Templates, API Keys, Media), Operations (Transactions, Audit Log, Settings).

- [ ] **P-84** | State: _Platform Moderator (limited permissions)_ | Action: Check sidebar | Expected: Only items matching permissions visible. Management/CMS items may be hidden.

- [ ] **P-85** | State: _In pconsole_ | Action: Switch to personal context via account switcher | Expected: Navigated to `/home`. Personal sidebar shown.

---

# SCOPE 4: CROSS-SCOPE SCENARIOS (X)

## 4.1 Full User Journey

- [ ] **X-01** | State: _Not logged in_ | Action: Register → verify email → log in | Expected: Complete onboarding flow. Ends on `/home`. Personal nav visible. No business/platform memberships.

- [ ] **X-02** | State: _Logged in, no memberships_ | Action: Navigate to `/explore` → search for a business → click business card → view public page → click "Request to Join" | Expected: Full discovery-to-request flow works end-to-end. Request created.

- [ ] **X-03** | State: _Request PENDING_ | Action: Business owner accepts request | Expected: User becomes member. Business appears in account switcher. Can navigate to bconsole.

- [ ] **X-04** | State: _New business member (Base Member)_ | Action: Navigate to `/bconsole/[slug]/dashboard` | Expected: Business console loads. Sidebar shows items based on Base Member permissions.

- [ ] **X-05** | State: _Business member_ | Action: Owner changes user's role to Admin | Expected: More sidebar items become visible. User can now manage members, forms, etc.

- [ ] **X-06** | State: _Business Admin_ | Action: Leave business → back to personal context | Expected: Membership → LEFT. Business removed from switcher. Personal nav shown.

## 4.2 Multi-Account Switching

- [ ] **X-07** | State: _User is member of Biz-A AND Biz-B_ | Action: Open account switcher | Expected: Both businesses listed. Personal context also listed.

- [ ] **X-08** | State: _In Biz-A console_ | Action: Switch to Biz-B via account switcher | Expected: Navigated to `/bconsole/biz-b/dashboard`. Sidebar shows Biz-B nav items.

- [ ] **X-09** | State: _User is member of Biz-A AND platform_ | Action: Switch from business to platform | Expected: Navigated to `/pconsole/dashboard`. Platform sidebar shown.

- [ ] **X-10** | State: _In platform console_ | Action: Switch to personal context | Expected: Navigated to `/home`. Personal sidebar shown.

- [ ] **X-11** | State: _In platform console_ | Action: Switch to business console | Expected: Navigated to `/bconsole/[slug]/dashboard`. Business sidebar shown.

- [ ] **X-12** | State: _User is owner of Biz-A, admin in Biz-B_ | Action: Check sidebar in each | Expected: Biz-A shows all owner items. Biz-B shows admin-level items. Correct permission filtering per account.

## 4.3 Permission Changes in Real-Time

- [ ] **X-13** | State: _User B is Base Member of Biz-X, viewing bconsole_ | Action: While User B is logged in, Owner changes User B's role to Admin | Expected: On next navigation/refresh, User B sees additional nav items. New actions available.

- [ ] **X-14** | State: _User B is Admin of Biz-X_ | Action: Owner suspends User B's membership | Expected: On next page load, BusinessGuard blocks access. Shows "Membership suspended".

- [ ] **X-15** | State: _User B is Admin, Owner removes a permission from Admin role_ | Action: User B refreshes page | Expected: Affected nav items disappear. Actions gated by that permission are hidden.

- [ ] **X-16** | State: _User B is active member, Owner bans User B_ | Action: User B tries to access bconsole | Expected: Access denied. Business removed from account switcher.

## 4.4 Quota + Closed Requests Combined

- [ ] **X-17** | State: _Biz-X: open_member_request=false, max_members=3, 2 active members_ | Action: User C sends join request | Expected: Error "This organization is not accepting membership requests" (closed check first, before quota).

- [ ] **X-18** | State: _Biz-X: open_member_request=true, max_members=3, 3 active members_ | Action: User C sends join request | Expected: Error "Member quota exceeded".

- [ ] **X-19** | State: _Biz-X: open_member_request=true, max_members=3, 2 active + 1 PENDING_APPROVAL_ | Action: User C sends join request | Expected: Error "Member quota exceeded" (PENDING_APPROVAL counts).

- [ ] **X-20** | State: _Biz-X: invitation sent to User C, User C has PENDING invitation. Owner also invites User D_ | Action: User C accepts invitation. Then User D tries to accept | Expected: If accepting User C fills quota, User D's acceptance fails with quota error (validated at acceptance time).

## 4.5 Business Creation Permission

- [ ] **X-21** | State: _User A without `can_create_business` flag (if restricted)_ | Action: Try to create a business | Expected: Depends on platform config — may require `business_creation_permission_request` transaction first.

- [ ] **X-22** | State: _User A submits business creation permission request_ | Action: Platform admin approves | Expected: `can_create_business` flag set. User A can now create businesses.

## 4.6 Form-Transaction End-to-End

- [ ] **X-23** | State: _Biz-X owner creates a form template "Application Form" with 3 fields_ | Action: Publish the form | Expected: Form → ACTIVE.

- [ ] **X-24** | State: _Owner creates form mapping: `business_membership_request` → "Application Form" (is_required=true)_ | Action: Save mapping | Expected: Mapping created.

- [ ] **X-25** | State: _User B sends join request to Biz-X_ | Action: Fill "Application Form" and submit request | Expected: Request created with form_response_id. Form response linked to transaction.

- [ ] **X-26** | State: _Owner views User B's request_ | Action: View form response within transaction detail | Expected: Form data visible. Can review submitted answers.

- [ ] **X-27** | State: _Owner accepts the request_ | Action: Accept → PENDING_REVIEW | Expected: Transaction → PENDING_REVIEW. Membership → PENDING_APPROVAL.

- [ ] **X-28** | State: _Owner requests more info_ | Action: Click "Request Info" with message | Expected: Transaction → INFO_REQUESTED. User B notified.

- [ ] **X-29** | State: _User B updates form response_ | Action: Edit answers, resubmit | Expected: Transaction → PENDING_REVIEW. Revision incremented.

- [ ] **X-30** | State: _Owner approves_ | Action: Click "Approve" | Expected: Transaction → ACCEPTED. Membership → ACTIVE. User B has full access.

## 4.7 Network End-to-End

- [ ] **X-31** | State: _User A logged in_ | Action: Follow e2e-test-business (from `/business/e2e-test-business`) → navigate to `/network` → click "Following" tab | Expected: "E2E Test Business" appears in Following tab with type badge "business" and correct followed date.

- [ ] **X-32** | State: _User A logged in_ | Action: Send connection request to User B (from `/users/e2e_user_b`) → switch to User B → accept → switch back to User A → navigate to `/network` → Connections tab | Expected: User B appears in Connections tab with display name, username, and "Connected" status.

- [ ] **X-33** | State: _User A follows e2e-test-business. User B (owner) logs in_ | Action: Navigate to `/bconsole/e2e-test-business/network/followers` | Expected: User A appears in followers list. Follower count reflects User A's follow.

- [ ] **X-34** | State: _User B removes User A as follower from bconsole (B-168)_ | Action: User A visits `/business/e2e-test-business` again | Expected: Follow button shows "Follow" (not "Following") — the follow was removed by the business owner.

- [ ] **X-35** | State: _User A connected with User B. User A navigates to `/network` → Connections tab_ | Action: Click "Disconnect" on User B's connection card → confirm | Expected: User B removed from User A's connections. User B's My Network also no longer shows User A.

---

# TEST SUMMARY

| Scope | Items | Coverage |
|-------|-------|----------|
| **User (U)** | U-01 to U-127 | Auth, profile, explore, public pages, transactions, deactivation, **network (follow/connect/my network)** |
| **Business (B)** | B-01 to B-175 | Account, profile, RBAC, members, quota, transactions, forms, ownership, **network (followers/connections management)** |
| **Platform (P)** | P-01 to P-85 | Setup, profile, settings, RBAC, members, transactions, forms, CMS |
| **Cross-Scope (X)** | X-01 to X-35 | Full journeys, multi-account, permission changes, quota+closed, form-transaction e2e, **network e2e** |
| **TOTAL** | **422 items** | |

---

# NOTES FOR TESTER

1. **Prerequisites**: Docker running (PostgreSQL + Redis), backend server running, frontend dev server running
2. **Test Users**: Create User A, User B, User C before starting. Keep credentials handy.
3. **Platform Setup**: Platform must be configured (P-01) before testing platform scope
4. **Business Setup**: Create at least one business (B-01/B-02) before testing business scope
5. **Order**: Start with User scope (U), then Business (B), then Platform (P), then Cross-Scope (X)
6. **Gaps Found**: Document any unexpected behavior, missing UI elements, or errors in a separate "Issues" list with the checklist item ID
7. **max_members**: Default is 1 for new businesses. Increase via admin or API to test multi-member features
8. **open_member_request**: Default is false. Toggle via business settings (B-78) to test request flows
