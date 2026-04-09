# E2E Parameter Checklist

> Auto-generated on 2026-03-27 by `scripts/generate-coverage-matrix.ts`

## P1 — Render Integrity

**103 files, 420 tests**

| File | Layer | Systems | Tests |
|------|-------|---------|-------|
| scenarios/multi-persona-interaction.spec.ts | L3 | Auth, Organization, Network, Chat, Transaction | 21 |
| scenarios/persona-alice-newcomer.spec.ts | L3 | Auth, Users, Explore, Network, Transaction, Organization, Chat | 36 |
| scenarios/persona-bob-entrepreneur.spec.ts | L3 | Auth, Organization, Forms, RBAC, Transaction | 37 |
| scenarios/persona-carol-admin.spec.ts | L3 | Auth, Platform, Organization, CMS, Forms | 17 |
| scenarios/persona-dave-social.spec.ts | L3 | Auth, Network, Chat, Explore | 20 |
| scenarios/persona-eve-adversarial.spec.ts | L3 | Auth, Users, Organization, Security | 29 |
| scenarios/persona-frank-multi-context.spec.ts | L3 | Auth, Organization, RBAC | 21 |
| scenarios/persona-gary-cms.spec.ts | L3 | Auth, CMS, Platform | 18 |
| smoke/auth/login.spec.ts | L1 | Auth | 10 |
| smoke/auth/register.spec.ts | L1 | Auth | 7 |
| smoke/auth/session-management.spec.ts | L1 | Auth | 2 |
| smoke/business/business-audit.spec.ts | L1 | Organization | 1 |
| smoke/business/business-network.spec.ts | L1 | Network | 2 |
| smoke/business/business-settings.spec.ts | L1 | Organization | 5 |
| smoke/business/business-transactions-detail.spec.ts | L1 | Transaction | 3 |
| smoke/business/business-visibility.spec.ts | L1 | Visibility | 3 |
| smoke/business/console-dashboard.spec.ts | L1 | Organization | 5 |
| smoke/business/member-detail.spec.ts | L1 | RBAC | 1 |
| smoke/business/member-management.spec.ts | L1 | RBAC | 4 |
| smoke/business/profile-public.spec.ts | L1 | Organization | 5 |
| smoke/business/role-management.spec.ts | L1 | RBAC | 3 |
| smoke/chat/attachments.spec.ts | L1 | Chat | 1 |
| smoke/chat/chat-mute.spec.ts | L1 | Chat | 1 |
| smoke/chat/chat-requests.spec.ts | L1 | Chat | 1 |
| smoke/chat/conversation-list.spec.ts | L1 | Chat | 4 |
| smoke/chat/delivery-status.spec.ts | L1 | Chat | 1 |
| smoke/chat/entity-sender-badge.spec.ts | L1 | Chat | 2 |
| smoke/chat/group-admin.spec.ts | L1 | Chat | 1 |
| smoke/chat/group-chat.spec.ts | L1 | Chat | 2 |
| smoke/chat/message-edit-delete.spec.ts | L1 | Chat | 2 |
| smoke/chat/presence-indicators.spec.ts | L1 | Chat | 1 |
| smoke/chat/reactions.spec.ts | L1 | Chat | 1 |
| smoke/chat/search-messages.spec.ts | L1 | Chat | 2 |
| smoke/chat/send-message.spec.ts | L1 | Chat | 2 |
| smoke/cms/cms-api-keys.spec.ts | L1 | CMS | 2 |
| smoke/cms/cms-content-editing.spec.ts | L1 | CMS | 1 |
| smoke/cms/cms-media-library.spec.ts | L1 | CMS | 2 |
| smoke/cms/cms-page-publish.spec.ts | L1 | CMS | 2 |
| smoke/cms/cms-site-management.spec.ts | L1 | CMS | 2 |
| smoke/explore/filters.spec.ts | L1 | Explore | 2 |
| smoke/explore/search-businesses.spec.ts | L1 | Explore | 5 |
| smoke/explore/search-users.spec.ts | L1 | Explore | 2 |
| smoke/feature-gates/feature-gate-403.spec.ts | L1 | Feature Gates | 3 |
| smoke/forms/field-crud.spec.ts | L1 | Forms | 2 |
| smoke/forms/field-types-all.spec.ts | L1 | Forms | 2 |
| smoke/forms/form-responses.spec.ts | L1 | Forms | 2 |
| smoke/forms/form-submission.spec.ts | L1 | Forms | 2 |
| smoke/forms/template-builder.spec.ts | L1 | Forms | 3 |
| smoke/forms/template-lifecycle.spec.ts | L1 | Forms | 2 |
| smoke/limits/field-length-limits.spec.ts | L1 | Auth, Organization, Limits | 3 |
| smoke/limits/member-quota.spec.ts | L1 | Organization, Limits | 3 |
| smoke/limits/rate-limits.spec.ts | L1 | Auth, Limits | 2 |
| smoke/navigation/account-switcher.spec.ts | L1 | Navigation | 5 |
| smoke/network/connect-user.spec.ts | L1 | Network | 1 |
| smoke/network/connection-list.spec.ts | L1 | Network | 1 |
| smoke/network/disconnect.spec.ts | L1 | Network | 1 |
| smoke/network/follow-business.spec.ts | L1 | Network | 2 |
| smoke/network/following-list.spec.ts | L1 | Network | 1 |
| smoke/network/network-page.spec.ts | L1 | Network | 3 |
| smoke/notifications/notification-center.spec.ts | L1 | Notifications | 2 |
| smoke/notifications/notification-history.spec.ts | L1 | Notifications | 1 |
| smoke/notifications/notification-preferences.spec.ts | L1 | Notifications | 1 |
| smoke/platform/console-dashboard.spec.ts | L1 | Organization | 2 |
| smoke/platform/platform-audit.spec.ts | L1 | Organization | 1 |
| smoke/platform/platform-businesses.spec.ts | L1 | Organization | 2 |
| smoke/platform/platform-cms.spec.ts | L1 | CMS | 4 |
| smoke/platform/platform-forms.spec.ts | L1 | Forms | 2 |
| smoke/platform/platform-management.spec.ts | L1 | RBAC | 3 |
| smoke/platform/platform-transactions.spec.ts | L1 | Transaction | 2 |
| smoke/platform/profile-public.spec.ts | L1 | Organization | 1 |
| smoke/public/landing-pages.spec.ts | L1 | Public | 11 |
| smoke/responsive/auth-mobile.spec.ts | L1 | Auth | 6 |
| smoke/transactions/form-mapping-settings.spec.ts | L1 | Transaction | 2 |
| smoke/transactions/join-request.spec.ts | L1 | Transaction | 2 |
| smoke/transactions/membership-invitation.spec.ts | L1 | Transaction | 2 |
| smoke/transactions/ownership-transfer.spec.ts | L1 | Transaction | 1 |
| smoke/transactions/transaction-deny-cancel.spec.ts | L1 | Transaction | 1 |
| smoke/transactions/transaction-list.spec.ts | L1 | Transaction | 3 |
| smoke/transactions/transaction-pages.spec.ts | L1 | Transaction | 2 |
| smoke/user/activity-feed.spec.ts | L1 | Users | 3 |
| smoke/user/home-feed.spec.ts | L1 | Users | 3 |
| smoke/user/other-user-profile.spec.ts | L1 | Users | 2 |
| smoke/user/profile-edit.spec.ts | L1 | Users | 3 |
| smoke/user/profile-view.spec.ts | L1 | Users | 5 |
| smoke/user/settings.spec.ts | L1 | Users | 6 |
| workflows/auth-to-profile.spec.ts | L2 | Auth, Users | 1 |
| workflows/business-creation-to-first-member.spec.ts | L2 | Auth, Organization, Transaction, RBAC | 1 |
| workflows/business-follow-to-join.spec.ts | L2 | Network, Transaction, Organization | 1 |
| workflows/business-member-rbac-flow.spec.ts | L2 | RBAC, Organization, Auth | 1 |
| workflows/business-status-lifecycle.spec.ts | L2 | Organization, Platform, Auth | 1 |
| workflows/chat-request-dm-block-flow.spec.ts | L2 | Chat, Network | 1 |
| workflows/entity-chat-business-context.spec.ts | L2 | Chat, Organization, RBAC | 1 |
| workflows/explore-to-interaction.spec.ts | L2 | Explore, Network, Organization | 1 |
| workflows/full-notification-lifecycle.spec.ts | L2 | Notifications | 1 |
| workflows/member-discipline-flow.spec.ts | L2 | Organization, RBAC, Auth | 1 |
| workflows/member-invitation-full-cycle.spec.ts | L2 | Transaction, Organization, RBAC | 1 |
| workflows/network-follow-connect-flow.spec.ts | L2 | Network, Transaction, Auth | 1 |
| workflows/notification-triggered-actions.spec.ts | L2 | Notifications | 1 |
| workflows/oauth-registration-flow.spec.ts | L2 | Auth | 2 |
| workflows/ownership-transfer-workflow.spec.ts | L2 | Transaction, Organization, RBAC | 1 |
| workflows/platform-business-management.spec.ts | L2 | Platform, Organization | 1 |
| workflows/registration-email-verification.spec.ts | L2 | Auth | 2 |
| workflows/two-user-chat-realtime.spec.ts | L2 | Chat, Auth | 1 |

## P2 — User Interaction

**51 files, 233 tests**

| File | Layer | Systems | Tests |
|------|-------|---------|-------|
| scenarios/persona-alice-newcomer.spec.ts | L3 | Auth, Users, Explore, Network, Transaction, Organization, Chat | 36 |
| scenarios/persona-bob-entrepreneur.spec.ts | L3 | Auth, Organization, Forms, RBAC, Transaction | 37 |
| scenarios/persona-carol-admin.spec.ts | L3 | Auth, Platform, Organization, CMS, Forms | 17 |
| scenarios/persona-frank-multi-context.spec.ts | L3 | Auth, Organization, RBAC | 21 |
| smoke/auth/email-verification.spec.ts | L1 | Auth | 4 |
| smoke/auth/login.spec.ts | L1 | Auth | 10 |
| smoke/auth/logout.spec.ts | L1 | Auth | 2 |
| smoke/auth/oauth-redirect.spec.ts | L1 | Auth | 3 |
| smoke/auth/password-change.spec.ts | L1 | Auth | 1 |
| smoke/auth/password-reset.spec.ts | L1 | Auth | 4 |
| smoke/auth/register.spec.ts | L1 | Auth | 7 |
| smoke/auth/session-management.spec.ts | L1 | Auth | 2 |
| smoke/business/business-lifecycle.spec.ts | L1 | Organization | 1 |
| smoke/business/business-settings.spec.ts | L1 | Organization | 5 |
| smoke/business/create-business.spec.ts | L1 | Organization | 3 |
| smoke/business/member-actions.spec.ts | L1 | RBAC | 1 |
| smoke/business/member-management.spec.ts | L1 | RBAC | 4 |
| smoke/business/role-management.spec.ts | L1 | RBAC | 3 |
| smoke/chat/attachments.spec.ts | L1 | Chat | 1 |
| smoke/chat/chat-mute.spec.ts | L1 | Chat | 1 |
| smoke/chat/group-admin.spec.ts | L1 | Chat | 1 |
| smoke/chat/message-edit-delete.spec.ts | L1 | Chat | 2 |
| smoke/chat/reactions.spec.ts | L1 | Chat | 1 |
| smoke/chat/send-message.spec.ts | L1 | Chat | 2 |
| smoke/cms/cms-api-keys.spec.ts | L1 | CMS | 2 |
| smoke/cms/cms-content-editing.spec.ts | L1 | CMS | 1 |
| smoke/cms/cms-media-library.spec.ts | L1 | CMS | 2 |
| smoke/cms/cms-page-publish.spec.ts | L1 | CMS | 2 |
| smoke/cms/cms-site-management.spec.ts | L1 | CMS | 2 |
| smoke/forms/field-crud.spec.ts | L1 | Forms | 2 |
| smoke/forms/template-builder.spec.ts | L1 | Forms | 3 |
| smoke/forms/template-lifecycle.spec.ts | L1 | Forms | 2 |
| smoke/navigation/account-switcher.spec.ts | L1 | Navigation | 5 |
| smoke/network/connect-user.spec.ts | L1 | Network | 1 |
| smoke/network/disconnect.spec.ts | L1 | Network | 1 |
| smoke/network/follow-business.spec.ts | L1 | Network | 2 |
| smoke/notifications/notification-preferences.spec.ts | L1 | Notifications | 1 |
| smoke/platform/platform-management.spec.ts | L1 | RBAC | 3 |
| smoke/responsive/business-console-mobile.spec.ts | L1 | Organization | 6 |
| smoke/responsive/navigation-mobile.spec.ts | L1 | Navigation | 6 |
| smoke/transactions/form-mapping-settings.spec.ts | L1 | Transaction | 2 |
| smoke/transactions/join-request.spec.ts | L1 | Transaction | 2 |
| smoke/transactions/membership-invitation.spec.ts | L1 | Transaction | 2 |
| smoke/transactions/ownership-transfer.spec.ts | L1 | Transaction | 1 |
| smoke/transactions/transaction-deny-cancel.spec.ts | L1 | Transaction | 1 |
| smoke/user/activity-feed.spec.ts | L1 | Users | 3 |
| smoke/user/profile-edit.spec.ts | L1 | Users | 3 |
| smoke/user/settings.spec.ts | L1 | Users | 6 |
| smoke/user/username-change.spec.ts | L1 | Users | 1 |
| workflows/auth-to-profile.spec.ts | L2 | Auth, Users | 1 |
| workflows/business-creation-to-first-member.spec.ts | L2 | Auth, Organization, Transaction, RBAC | 1 |

## P3 — Navigation

**35 files, 118 tests**

| File | Layer | Systems | Tests |
|------|-------|---------|-------|
| scenarios/persona-alice-newcomer.spec.ts | L3 | Auth, Users, Explore, Network, Transaction, Organization, Chat | 36 |
| smoke/auth/oauth-redirect.spec.ts | L1 | Auth | 3 |
| smoke/business/business-network.spec.ts | L1 | Network | 2 |
| smoke/business/business-transactions-detail.spec.ts | L1 | Transaction | 3 |
| smoke/business/console-dashboard.spec.ts | L1 | Organization | 5 |
| smoke/chat/chat-requests.spec.ts | L1 | Chat | 1 |
| smoke/chat/conversation-list.spec.ts | L1 | Chat | 4 |
| smoke/chat/delivery-status.spec.ts | L1 | Chat | 1 |
| smoke/chat/entity-sender-badge.spec.ts | L1 | Chat | 2 |
| smoke/chat/group-chat.spec.ts | L1 | Chat | 2 |
| smoke/chat/presence-indicators.spec.ts | L1 | Chat | 1 |
| smoke/chat/search-messages.spec.ts | L1 | Chat | 2 |
| smoke/chat/send-message.spec.ts | L1 | Chat | 2 |
| smoke/explore/filters.spec.ts | L1 | Explore | 2 |
| smoke/explore/search-businesses.spec.ts | L1 | Explore | 5 |
| smoke/explore/search-users.spec.ts | L1 | Explore | 2 |
| smoke/forms/form-responses.spec.ts | L1 | Forms | 2 |
| smoke/forms/form-submission.spec.ts | L1 | Forms | 2 |
| smoke/navigation/account-switcher.spec.ts | L1 | Navigation | 5 |
| smoke/network/connect-user.spec.ts | L1 | Network | 1 |
| smoke/network/connection-list.spec.ts | L1 | Network | 1 |
| smoke/network/follow-business.spec.ts | L1 | Network | 2 |
| smoke/network/following-list.spec.ts | L1 | Network | 1 |
| smoke/network/network-page.spec.ts | L1 | Network | 3 |
| smoke/notifications/notification-center.spec.ts | L1 | Notifications | 2 |
| smoke/notifications/notification-history.spec.ts | L1 | Notifications | 1 |
| smoke/platform/console-dashboard.spec.ts | L1 | Organization | 2 |
| smoke/public/landing-pages.spec.ts | L1 | Public | 11 |
| smoke/transactions/transaction-list.spec.ts | L1 | Transaction | 3 |
| smoke/transactions/transaction-pages.spec.ts | L1 | Transaction | 2 |
| smoke/user/home-feed.spec.ts | L1 | Users | 3 |
| workflows/auth-to-profile.spec.ts | L2 | Auth, Users | 1 |
| workflows/business-member-rbac-flow.spec.ts | L2 | RBAC, Organization, Auth | 1 |
| workflows/member-discipline-flow.spec.ts | L2 | Organization, RBAC, Auth | 1 |
| workflows/ownership-transfer-workflow.spec.ts | L2 | Transaction, Organization, RBAC | 1 |

## P4 — Data Accuracy

**20 files, 42 tests**

| File | Layer | Systems | Tests |
|------|-------|---------|-------|
| smoke/auth/email-verification.spec.ts | L1 | Auth | 4 |
| smoke/auth/password-reset.spec.ts | L1 | Auth | 4 |
| smoke/business/business-lifecycle.spec.ts | L1 | Organization | 1 |
| smoke/business/create-business.spec.ts | L1 | Organization | 3 |
| smoke/business/member-management.spec.ts | L1 | RBAC | 4 |
| smoke/forms/field-types-all.spec.ts | L1 | Forms | 2 |
| smoke/limits/rate-limits.spec.ts | L1 | Auth, Limits | 2 |
| smoke/user/activity-feed.spec.ts | L1 | Users | 3 |
| smoke/user/other-user-profile.spec.ts | L1 | Users | 2 |
| smoke/user/profile-edit.spec.ts | L1 | Users | 3 |
| smoke/user/profile-view.spec.ts | L1 | Users | 5 |
| smoke/user/username-change.spec.ts | L1 | Users | 1 |
| workflows/business-creation-to-first-member.spec.ts | L2 | Auth, Organization, Transaction, RBAC | 1 |
| workflows/business-follow-to-join.spec.ts | L2 | Network, Transaction, Organization | 1 |
| workflows/join-request-with-form.spec.ts | L2 | Transaction, Forms, Organization | 1 |
| workflows/member-invitation-full-cycle.spec.ts | L2 | Transaction, Organization, RBAC | 1 |
| workflows/member-quota-enforcement.spec.ts | L2 | Organization, Transaction, RBAC | 1 |
| workflows/network-follow-connect-flow.spec.ts | L2 | Network, Transaction, Auth | 1 |
| workflows/ownership-transfer-workflow.spec.ts | L2 | Transaction, Organization, RBAC | 1 |
| workflows/transaction-form-approval-workflow.spec.ts | L2 | Transaction, Forms, Organization, RBAC | 1 |

## P5 — Auth & Authz

**105 files, 395 tests**

| File | Layer | Systems | Tests |
|------|-------|---------|-------|
| scenarios/multi-persona-interaction.spec.ts | L3 | Auth, Organization, Network, Chat, Transaction | 21 |
| scenarios/persona-alice-newcomer.spec.ts | L3 | Auth, Users, Explore, Network, Transaction, Organization, Chat | 36 |
| scenarios/persona-bob-entrepreneur.spec.ts | L3 | Auth, Organization, Forms, RBAC, Transaction | 37 |
| scenarios/persona-carol-admin.spec.ts | L3 | Auth, Platform, Organization, CMS, Forms | 17 |
| scenarios/persona-dave-social.spec.ts | L3 | Auth, Network, Chat, Explore | 20 |
| scenarios/persona-eve-adversarial.spec.ts | L3 | Auth, Users, Organization, Security | 29 |
| scenarios/persona-frank-multi-context.spec.ts | L3 | Auth, Organization, RBAC | 21 |
| scenarios/persona-gary-cms.spec.ts | L3 | Auth, CMS, Platform | 18 |
| smoke/auth/email-verification.spec.ts | L1 | Auth | 4 |
| smoke/auth/login.spec.ts | L1 | Auth | 10 |
| smoke/auth/logout.spec.ts | L1 | Auth | 2 |
| smoke/auth/password-change.spec.ts | L1 | Auth | 1 |
| smoke/auth/password-reset.spec.ts | L1 | Auth | 4 |
| smoke/auth/register.spec.ts | L1 | Auth | 7 |
| smoke/auth/session-management.spec.ts | L1 | Auth | 2 |
| smoke/business/business-audit.spec.ts | L1 | Organization | 1 |
| smoke/business/business-lifecycle.spec.ts | L1 | Organization | 1 |
| smoke/business/business-network.spec.ts | L1 | Network | 2 |
| smoke/business/business-settings.spec.ts | L1 | Organization | 5 |
| smoke/business/business-transactions-detail.spec.ts | L1 | Transaction | 3 |
| smoke/business/business-visibility.spec.ts | L1 | Visibility | 3 |
| smoke/business/console-dashboard.spec.ts | L1 | Organization | 5 |
| smoke/business/create-business.spec.ts | L1 | Organization | 3 |
| smoke/business/member-actions.spec.ts | L1 | RBAC | 1 |
| smoke/business/member-detail.spec.ts | L1 | RBAC | 1 |
| smoke/business/member-management.spec.ts | L1 | RBAC | 4 |
| smoke/business/profile-public.spec.ts | L1 | Organization | 5 |
| smoke/business/role-management.spec.ts | L1 | RBAC | 3 |
| smoke/chat/attachments.spec.ts | L1 | Chat | 1 |
| smoke/chat/chat-mute.spec.ts | L1 | Chat | 1 |
| smoke/chat/chat-requests.spec.ts | L1 | Chat | 1 |
| smoke/chat/conversation-list.spec.ts | L1 | Chat | 4 |
| smoke/chat/delivery-status.spec.ts | L1 | Chat | 1 |
| smoke/chat/entity-sender-badge.spec.ts | L1 | Chat | 2 |
| smoke/chat/group-admin.spec.ts | L1 | Chat | 1 |
| smoke/chat/group-chat.spec.ts | L1 | Chat | 2 |
| smoke/chat/message-edit-delete.spec.ts | L1 | Chat | 2 |
| smoke/chat/presence-indicators.spec.ts | L1 | Chat | 1 |
| smoke/chat/reactions.spec.ts | L1 | Chat | 1 |
| smoke/chat/search-messages.spec.ts | L1 | Chat | 2 |
| smoke/cms/cms-api-keys.spec.ts | L1 | CMS | 2 |
| smoke/cms/cms-content-editing.spec.ts | L1 | CMS | 1 |
| smoke/cms/cms-media-library.spec.ts | L1 | CMS | 2 |
| smoke/cms/cms-page-publish.spec.ts | L1 | CMS | 2 |
| smoke/cms/cms-site-management.spec.ts | L1 | CMS | 2 |
| smoke/explore/filters.spec.ts | L1 | Explore | 2 |
| smoke/explore/search-businesses.spec.ts | L1 | Explore | 5 |
| smoke/explore/search-users.spec.ts | L1 | Explore | 2 |
| smoke/feature-gates/feature-gate-403.spec.ts | L1 | Feature Gates | 3 |
| smoke/forms/field-crud.spec.ts | L1 | Forms | 2 |
| smoke/forms/field-types-all.spec.ts | L1 | Forms | 2 |
| smoke/forms/form-responses.spec.ts | L1 | Forms | 2 |
| smoke/forms/form-submission.spec.ts | L1 | Forms | 2 |
| smoke/forms/template-builder.spec.ts | L1 | Forms | 3 |
| smoke/forms/template-lifecycle.spec.ts | L1 | Forms | 2 |
| smoke/limits/field-length-limits.spec.ts | L1 | Auth, Organization, Limits | 3 |
| smoke/limits/member-quota.spec.ts | L1 | Organization, Limits | 3 |
| smoke/network/connection-list.spec.ts | L1 | Network | 1 |
| smoke/network/disconnect.spec.ts | L1 | Network | 1 |
| smoke/network/following-list.spec.ts | L1 | Network | 1 |
| smoke/network/network-page.spec.ts | L1 | Network | 3 |
| smoke/notifications/notification-center.spec.ts | L1 | Notifications | 2 |
| smoke/notifications/notification-history.spec.ts | L1 | Notifications | 1 |
| smoke/notifications/notification-preferences.spec.ts | L1 | Notifications | 1 |
| smoke/platform/console-dashboard.spec.ts | L1 | Organization | 2 |
| smoke/platform/platform-audit.spec.ts | L1 | Organization | 1 |
| smoke/platform/platform-businesses.spec.ts | L1 | Organization | 2 |
| smoke/platform/platform-cms.spec.ts | L1 | CMS | 4 |
| smoke/platform/platform-forms.spec.ts | L1 | Forms | 2 |
| smoke/platform/platform-management.spec.ts | L1 | RBAC | 3 |
| smoke/platform/platform-transactions.spec.ts | L1 | Transaction | 2 |
| smoke/platform/profile-public.spec.ts | L1 | Organization | 1 |
| smoke/transactions/form-mapping-settings.spec.ts | L1 | Transaction | 2 |
| smoke/transactions/join-request.spec.ts | L1 | Transaction | 2 |
| smoke/transactions/membership-invitation.spec.ts | L1 | Transaction | 2 |
| smoke/transactions/ownership-transfer.spec.ts | L1 | Transaction | 1 |
| smoke/transactions/transaction-deny-cancel.spec.ts | L1 | Transaction | 1 |
| smoke/transactions/transaction-list.spec.ts | L1 | Transaction | 3 |
| smoke/transactions/transaction-pages.spec.ts | L1 | Transaction | 2 |
| smoke/user/home-feed.spec.ts | L1 | Users | 3 |
| smoke/user/other-user-profile.spec.ts | L1 | Users | 2 |
| workflows/audit-trail-verification.spec.ts | L2 | Organization, RBAC | 1 |
| workflows/business-creation-to-first-member.spec.ts | L2 | Auth, Organization, Transaction, RBAC | 1 |
| workflows/business-follow-to-join.spec.ts | L2 | Network, Transaction, Organization | 1 |
| workflows/business-member-rbac-flow.spec.ts | L2 | RBAC, Organization, Auth | 1 |
| workflows/business-network-management.spec.ts | L2 | Network, Organization | 1 |
| workflows/business-status-lifecycle.spec.ts | L2 | Organization, Platform, Auth | 1 |
| workflows/chat-conversation-lifecycle.spec.ts | L2 | Chat, Auth | 1 |
| workflows/chat-request-dm-block-flow.spec.ts | L2 | Chat, Network | 1 |
| workflows/cms-content-lifecycle.spec.ts | L2 | CMS, Platform | 1 |
| workflows/entity-chat-business-context.spec.ts | L2 | Chat, Organization, RBAC | 1 |
| workflows/explore-to-interaction.spec.ts | L2 | Explore, Network, Organization | 1 |
| workflows/form-builder-complete-lifecycle.spec.ts | L2 | Forms, Organization | 1 |
| workflows/form-template-lifecycle.spec.ts | L2 | Forms, Organization | 1 |
| workflows/full-notification-lifecycle.spec.ts | L2 | Notifications | 1 |
| workflows/join-request-with-form.spec.ts | L2 | Transaction, Forms, Organization | 1 |
| workflows/member-discipline-flow.spec.ts | L2 | Organization, RBAC, Auth | 1 |
| workflows/member-invitation-full-cycle.spec.ts | L2 | Transaction, Organization, RBAC | 1 |
| workflows/member-quota-enforcement.spec.ts | L2 | Organization, Transaction, RBAC | 1 |
| workflows/network-follow-connect-flow.spec.ts | L2 | Network, Transaction, Auth | 1 |
| workflows/notification-triggered-actions.spec.ts | L2 | Notifications | 1 |
| workflows/platform-business-management.spec.ts | L2 | Platform, Organization | 1 |
| workflows/registration-email-verification.spec.ts | L2 | Auth | 2 |
| workflows/transaction-form-approval-workflow.spec.ts | L2 | Transaction, Forms, Organization, RBAC | 1 |
| workflows/two-user-chat-realtime.spec.ts | L2 | Chat, Auth | 1 |

## P6 — Real-Time

**11 files, 122 tests**

| File | Layer | Systems | Tests |
|------|-------|---------|-------|
| scenarios/multi-persona-interaction.spec.ts | L3 | Auth, Organization, Network, Chat, Transaction | 21 |
| scenarios/persona-bob-entrepreneur.spec.ts | L3 | Auth, Organization, Forms, RBAC, Transaction | 37 |
| scenarios/persona-carol-admin.spec.ts | L3 | Auth, Platform, Organization, CMS, Forms | 17 |
| scenarios/persona-frank-multi-context.spec.ts | L3 | Auth, Organization, RBAC | 21 |
| scenarios/persona-gary-cms.spec.ts | L3 | Auth, CMS, Platform | 18 |
| smoke/feature-gates/feature-gate-403.spec.ts | L1 | Feature Gates | 3 |
| workflows/cms-content-lifecycle.spec.ts | L2 | CMS, Platform | 1 |
| workflows/form-builder-complete-lifecycle.spec.ts | L2 | Forms, Organization | 1 |
| workflows/form-template-lifecycle.spec.ts | L2 | Forms, Organization | 1 |
| workflows/join-request-with-form.spec.ts | L2 | Transaction, Forms, Organization | 1 |
| workflows/transaction-form-approval-workflow.spec.ts | L2 | Transaction, Forms, Organization, RBAC | 1 |

## P7 — Error Handling

**19 files, 124 tests**

| File | Layer | Systems | Tests |
|------|-------|---------|-------|
| scenarios/multi-persona-interaction.spec.ts | L3 | Auth, Organization, Network, Chat, Transaction | 21 |
| scenarios/persona-alice-newcomer.spec.ts | L3 | Auth, Users, Explore, Network, Transaction, Organization, Chat | 36 |
| scenarios/persona-dave-social.spec.ts | L3 | Auth, Network, Chat, Explore | 20 |
| smoke/auth/email-verification.spec.ts | L1 | Auth | 4 |
| smoke/auth/login.spec.ts | L1 | Auth | 10 |
| smoke/auth/password-change.spec.ts | L1 | Auth | 1 |
| smoke/auth/password-reset.spec.ts | L1 | Auth | 4 |
| smoke/auth/register.spec.ts | L1 | Auth | 7 |
| smoke/business/business-visibility.spec.ts | L1 | Visibility | 3 |
| smoke/business/member-actions.spec.ts | L1 | RBAC | 1 |
| smoke/business/member-detail.spec.ts | L1 | RBAC | 1 |
| smoke/business/profile-public.spec.ts | L1 | Organization | 5 |
| smoke/responsive/chat-mobile.spec.ts | L1 | Chat | 3 |
| smoke/user/profile-edit.spec.ts | L1 | Users | 3 |
| smoke/user/username-change.spec.ts | L1 | Users | 1 |
| workflows/chat-conversation-lifecycle.spec.ts | L2 | Chat, Auth | 1 |
| workflows/chat-request-dm-block-flow.spec.ts | L2 | Chat, Network | 1 |
| workflows/entity-chat-business-context.spec.ts | L2 | Chat, Organization, RBAC | 1 |
| workflows/two-user-chat-realtime.spec.ts | L2 | Chat, Auth | 1 |

## P8 — Responsive

**7 files, 24 tests**

| File | Layer | Systems | Tests |
|------|-------|---------|-------|
| smoke/responsive/auth-mobile.spec.ts | L1 | Auth | 6 |
| smoke/responsive/business-console-mobile.spec.ts | L1 | Organization | 6 |
| smoke/responsive/chat-mobile.spec.ts | L1 | Chat | 3 |
| smoke/responsive/navigation-mobile.spec.ts | L1 | Navigation | 6 |
| workflows/business-network-management.spec.ts | L2 | Network, Organization | 1 |
| workflows/explore-to-interaction.spec.ts | L2 | Explore, Network, Organization | 1 |
| workflows/platform-business-management.spec.ts | L2 | Platform, Organization | 1 |

## P9 — Visual Regression

No test files cover this parameter.

## P10 — Limits & Quotas

**5 files, 46 tests**

| File | Layer | Systems | Tests |
|------|-------|---------|-------|
| scenarios/persona-bob-entrepreneur.spec.ts | L3 | Auth, Organization, Forms, RBAC, Transaction | 37 |
| smoke/limits/field-length-limits.spec.ts | L1 | Auth, Organization, Limits | 3 |
| smoke/limits/member-quota.spec.ts | L1 | Organization, Limits | 3 |
| smoke/limits/rate-limits.spec.ts | L1 | Auth, Limits | 2 |
| workflows/member-quota-enforcement.spec.ts | L2 | Organization, Transaction, RBAC | 1 |

## P11 — Security

**2 files, 30 tests**

| File | Layer | Systems | Tests |
|------|-------|---------|-------|
| scenarios/persona-eve-adversarial.spec.ts | L3 | Auth, Users, Organization, Security | 29 |
| workflows/business-status-lifecycle.spec.ts | L2 | Organization, Platform, Auth | 1 |

## P12 — Accessibility

No test files cover this parameter.

## P13 — Cross-User

**2 files, 30 tests**

| File | Layer | Systems | Tests |
|------|-------|---------|-------|
| scenarios/persona-eve-adversarial.spec.ts | L3 | Auth, Users, Organization, Security | 29 |
| workflows/audit-trail-verification.spec.ts | L2 | Organization, RBAC | 1 |

## P14 — State Persistence

**3 files, 9 tests**

| File | Layer | Systems | Tests |
|------|-------|---------|-------|
| smoke/auth/logout.spec.ts | L1 | Auth | 2 |
| smoke/user/settings.spec.ts | L1 | Users | 6 |
| workflows/feature-gate-degradation.spec.ts | L2 | Feature Gates, Chat | 1 |
