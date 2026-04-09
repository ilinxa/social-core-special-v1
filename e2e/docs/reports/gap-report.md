# E2E Gap Report

> Auto-generated on 2026-03-27 by `scripts/generate-gap-report.ts`
> Cross-references 125 test files against expected feature areas.

## Summary

| Status | Count | % |
|--------|-------|---|
| Covered | 76 | 84.4% |
| Partial | 8 | 8.9% |
| Missing | 6 | 6.7% |
| **Total** | **90** | **100%** |

## Auth (8/8)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Login (valid/invalid) | partial | Partially covered by related test file |
| Registration | covered |  |
| Logout | covered |  |
| Password reset | covered |  |
| Email verification | covered |  |
| Password change | covered |  |
| Session management | covered |  |
| OAuth redirect | covered |  |

## Users (7/7)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Profile view | covered |  |
| Profile edit | covered |  |
| Settings/preferences | partial | Partially covered by related test file |
| Home feed | covered |  |
| Activity feed | covered |  |
| Other user profile | covered |  |
| Username change | covered |  |

## Organization (11/11)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Business creation | covered |  |
| Business dashboard | partial | Partially covered by related test file |
| Member management | covered |  |
| Role management | covered |  |
| Business settings | covered |  |
| Business lifecycle | covered |  |
| Member actions (suspend/ban) | partial | Partially covered by related test file |
| Business visibility | covered |  |
| Business network | covered |  |
| Business transactions | covered |  |
| Business audit | covered |  |

## Platform (7/7)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Platform dashboard | partial | Partially covered by related test file |
| Platform management | covered |  |
| Platform businesses | covered |  |
| Platform CMS | covered |  |
| Platform forms | covered |  |
| Platform transactions | covered |  |
| Platform audit | covered |  |

## RBAC (1/3)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Role assignment | partial | Partially covered by related test file |
| Permission changes | **MISSING** |  |
| Custom roles | **MISSING** |  |

## Chat (13/13)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Conversation list | covered |  |
| Send message | covered |  |
| Group chat | covered |  |
| Attachments | covered |  |
| Reactions | covered |  |
| Search messages | covered |  |
| Chat requests | covered |  |
| Message edit/delete | covered |  |
| Presence indicators | covered |  |
| Delivery status | covered |  |
| Group admin | covered |  |
| Chat mute | covered |  |
| Entity sender badge | covered |  |

## Network (6/6)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Follow business | covered |  |
| Connect user | covered |  |
| Network page | covered |  |
| Following list | covered |  |
| Connection list | covered |  |
| Disconnect | covered |  |

## Transaction (7/7)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Membership invitation | covered |  |
| Join request | covered |  |
| Ownership transfer | covered |  |
| Transaction list | covered |  |
| Transaction deny/cancel | covered |  |
| Transaction pages | covered |  |
| Form mapping settings | covered |  |

## Forms (6/6)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Template builder | covered |  |
| Form submission | covered |  |
| Form responses | covered |  |
| Template lifecycle | covered |  |
| Field CRUD | covered |  |
| Field types (all 14+) | partial | Partially covered by related test file |

## CMS (5/5)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Site management | covered |  |
| Page publish | covered |  |
| Content editing | covered |  |
| Media library | covered |  |
| API keys | covered |  |

## Notifications (3/3)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Notification center | covered |  |
| Notification preferences | covered |  |
| Notification history | covered |  |

## Explore (3/3)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Search businesses | covered |  |
| Search users | covered |  |
| Filters | covered |  |

## Feature Gates (1/1)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Feature gate 403 + UI degradation | covered |  |

## Visibility (1/2)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Tier 2 visibility settings | partial | Partially covered by related test file |
| Public view changes | **MISSING** |  |

## Limits (3/3)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Member quota | covered |  |
| Rate limits | covered |  |
| Field length limits | covered |  |

## Navigation (1/1)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Account switcher | covered |  |

## Public (1/1)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| Landing pages | covered |  |

## Security (0/3)

| Feature Area | Status | Notes |
|-------------|--------|-------|
| XSS injection | **MISSING** |  |
| Account lockout | **MISSING** |  |
| Unauthorized access | **MISSING** |  |

## Action Items

- [ ] **RBAC**: Permission changes
- [ ] **RBAC**: Custom roles
- [ ] **Visibility**: Public view changes
- [ ] **Security**: XSS injection
- [ ] **Security**: Account lockout
- [ ] **Security**: Unauthorized access
