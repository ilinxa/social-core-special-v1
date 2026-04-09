# L3 Persona Scenario Catalog

> **8 files** | **199 tests** | Project: `scenarios`
>
> Full user journey simulations. Each persona starts from scratch and progresses through 17-37 steps that build on previous state.

## Configuration

| Setting | Value |
|---------|-------|
| Project | `scenarios` |
| Workers | 1 (serial execution) |
| Retries | 0 (must pass on first try) |
| Timeout | 30s per step |
| Viewport | 1280x720 |
| Artifacts | Video ON, trace ON, screenshot ON (full recording) |
| Pattern | `test.describe.serial()` — steps execute in order |

---

## Persona Summary

| Persona | File | Steps | Systems | Focus |
|---------|------|-------|---------|-------|
| Alice | `persona-alice-newcomer.spec.ts` | 36 | Auth, Users, Explore, Network, Transaction, Organization, Chat | Complete newcomer onboarding |
| Bob | `persona-bob-entrepreneur.spec.ts` | 37 | Auth, Organization, Forms, RBAC, Transaction | Business creation to full management |
| Eve | `persona-eve-adversarial.spec.ts` | 29 | Auth, Users, Organization, Security | Security testing, XSS, injection, lockout |
| Carol | `persona-carol-admin.spec.ts` | 17 | Auth, Platform, Organization, CMS, Forms | Platform administrator tasks |
| Dave | `persona-dave-social.spec.ts` | 20 | Auth, Network, Chat, Explore | Social features, real-time chat |
| Frank | `persona-frank-multi-context.spec.ts` | 21 | Auth, Organization, RBAC | 3 business contexts, scope isolation |
| Gary | `persona-gary-cms.spec.ts` | 18 | Auth, CMS, Platform | CMS lifecycle management |
| Multi | `multi-persona-interaction.spec.ts` | 21 | Auth, Organization, Network, Chat, Transaction | 5 actors interacting simultaneously |

**Total: 199 steps/tests**

---

## Alice: The Newcomer (36 steps)

A brand-new user discovers the platform, registers, explores, follows a business, requests to join, and starts chatting.

### Phases

1. **Anonymous Discovery** (Steps 1-6): Landing page, about page, explore (anonymous), business profile
2. **Registration** (Steps 7-9): Register, verify email, first login
3. **Profile Setup** (Steps 10-11): Edit profile, view own profile
4. **Exploration** (Steps 12-14): Authenticated explore, search businesses, follow business
5. **Organization Join** (Steps 15-21): Follow business, request to join, owner accepts, access console
6. **Chat** (Steps 22-28): Create DM, send messages, receive reply, group chat, reactions
7. **Network** (Steps 29-33): Connection request, accept, network page, following list
8. **Final State** (Steps 34-36): Return to home, verify all state persists

### Feature Gates
- `isSystemEnabled('network')` for Steps 15, 29-33
- `isSystemEnabled('chat')` for Steps 22-28
- `getOrgMode() !== 'user_only'` for Steps 17-21

---

## Bob: The Entrepreneur (37 steps)

A business owner creates a business from scratch, sets up forms, manages members with RBAC, handles transactions, and tests quota enforcement.

### Phases

1. **Setup** (Steps 1-4): Register, verify, grant business creation, create business
2. **Business Configuration** (Steps 5-8): Update settings, create form template, add fields, publish template
3. **Member Management** (Steps 9-15): Invite 3 members, accept invitations, verify member list, role assignment
4. **RBAC Testing** (Steps 16-20): Create custom role, assign to member, verify permission changes
5. **Transaction Management** (Steps 21-25): View transactions, form mapping, join request with form
6. **Quota Testing** (Steps 26-30): Set quota, fill to limit, over-quota error, remove member, re-invite
7. **Ownership Transfer** (Steps 31-34): Transfer to member, verify new owner permissions
8. **Final State** (Steps 35-37): Verify all state, return to home

### Feature Gates
- `getOrgMode() !== 'user_only'` for Steps 4+
- `isSystemEnabled('forms')` for Steps 6-8, 23-25

---

## Eve: The Adversarial User (29 steps)

An adversarial user tests security boundaries: XSS injection, SQL injection, account lockout, unauthorized access, and account deactivation.

### Phases

1. **Registration** (Steps 1-2): Register, verify email
2. **XSS Testing** (Steps 3-5): XSS in profile fields (bio, display name) — verify sanitized
3. **SQL Injection** (Steps 6-8): SQL in search, login, registration — verify rejected
4. **Authorization** (Steps 9-12): Access business console without membership, access platform console without admin, access other user's settings
5. **Account Lockout** (Steps 13-16): 10 failed login attempts → locked → wait → unlock
6. **CSRF/Session** (Steps 17-19): Manipulate tokens, expired session handling
7. **Business Boundary** (Steps 20-24): Create business, try actions beyond role, try actions in other business
8. **Account Deactivation** (Steps 25-29): Deactivate account, verify session cleared, verify profile hidden

### Feature Gates
- `getOrgMode() !== 'user_only'` for Steps 20-24

### Security Parameters
- P11 (Security), P13 (Error Handling) throughout

---

## Carol: The Platform Admin (17 steps)

A platform administrator manages the platform: dashboard, business oversight, CMS content, forms, and audit.

### Phases

1. **Login** (Steps 1-2): Login as platform admin, view dashboard
2. **Business Oversight** (Steps 3-5): View business list, business detail, member management
3. **CMS Management** (Steps 6-10): Create site, create page, publish, unpublish, re-publish
4. **Forms** (Steps 11-13): Create platform template, add fields, view responses
5. **Navigation** (Steps 14-17): Switch between platform sections, return to personal context

### Feature Gates
- `isSystemEnabled('cms')` for Steps 6-10
- `isSystemEnabled('forms')` for Steps 11-13

---

## Dave: The Social Butterfly (20 steps)

A socially active user focuses on network features, chat, and real-time interactions.

### Phases

1. **Setup** (Steps 1-3): Register, verify, setup profile
2. **Discovery** (Steps 4-6): Explore, search for businesses and users
3. **Following** (Steps 7-9): Follow 3 businesses, verify following list
4. **Connections** (Steps 10-13): Send 2 connection requests, accept responses, verify connections list
5. **Chat** (Steps 14-17): Create DM, send messages, group chat, reactions
6. **Verification** (Steps 18-20): Network page shows all connections, following list accurate, chat history persists

### Feature Gates
- `isSystemEnabled('network')` for Steps 7-13
- `isSystemEnabled('chat')` for Steps 14-17

---

## Frank: The Multi-Context User (21 steps)

A user who is a member of 3 different businesses, testing scope isolation and context switching.

### Phases

1. **Setup** (Steps 1-4): Register Frank, create 3 businesses (different owners), invite Frank to all 3, accept all
2. **Context Switching** (Steps 5-8): Login, navigate to each business dashboard
3. **Scope Isolation** (Steps 9-12): Verify correct member count in each business, view public profiles
4. **Settings** (Steps 13-15): View settings in business 1 and 2 (not owner — limited), return home
5. **Rapid Switching** (Steps 16-19): Navigate between all 3 businesses rapidly, back to home, explore, profile
6. **Final State** (Steps 20-21): Multi-context journey complete, all 3 businesses still have correct state

### Feature Gates
- `getOrgMode() !== 'user_only'` (entire test)

---

## Gary: The CMS Manager (18 steps)

A platform admin focused on CMS: creates sites, manages pages, publishes content, creates API keys.

### Phases

1. **Site Management** (Steps 1-3): Login, create CMS site, verify in list
2. **Page Creation** (Steps 4-7): Create 2 pages, publish both
3. **Content Versioning** (Steps 8-9): Unpublish page 2, re-publish
4. **API Keys** (Steps 10-11): Create API key, verify `cmsk_` prefix
5. **Platform Console** (Steps 12-13): View CMS section, navigate dashboard
6. **Cleanup** (Steps 14-18): Unpublish/republish page 1, verify site list, return home

### Feature Gates
- `isSystemEnabled('cms')` (entire test)

---

## Multi-Persona Interaction (21 steps)

5 actors (Alpha, Beta, Gamma, Delta, Echo) interact simultaneously across multiple systems.

### Phases

1. **Register All** (Step 1): Register all 5 actors
2. **Business Setup** (Steps 2-6): Alpha creates business, invites Beta+Gamma, both accept, verify 3 members
3. **Network** (Steps 7-8): Delta and Echo follow the business
4. **Connections** (Steps 9-13): Delta↔Alpha connection, Echo↔Beta connection, verify
5. **Group Chat** (Steps 14-17): Alpha creates group chat with Beta+Gamma, all exchange messages
6. **Browser Verification** (Steps 18-19): Alpha and Beta open chat in browser, verify UI
7. **Final State** (Steps 20-21): All 5 actors can still log in, business has correct member count

### Feature Gates
- `getOrgMode() !== 'user_only'` for Steps 2-8
- `isSystemEnabled('network')` for Steps 7-13
- `isSystemEnabled('chat')` for Steps 14-19

---

## Design Patterns

### Serial Execution

All L3 tests use `test.describe.serial()`:

```typescript
test.describe.serial('Alice: The Newcomer', () => {
  // Shared state across steps
  let aliceEmail: string;
  let aliceId: string;

  test('Step 1: Visit landing page', async ({ page }) => { /* ... */ });
  test('Step 2: Navigate to register', async ({ page }) => { /* ... */ });
  // Each step builds on the previous
});
```

### Hybrid Data Setup

L3 tests use a mix of API-driven and browser-driven interactions:
- **API**: Registration, email verification, business creation, invitations
- **Browser**: Navigation, form filling, visual verification, chat UI

### Feature Gate Skipping

Steps that depend on optional systems use conditional skips:

```typescript
test('Step 15: Follow the business', async ({ apiClient }) => {
  test.skip(!isSystemEnabled('network'), 'Network disabled');
  // ...
});
```

Steps that depend on organization mode:

```typescript
test.skip(getOrgMode() === 'user_only', 'Organization disabled');
```
