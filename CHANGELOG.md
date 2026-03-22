# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **Organization System** — Business and platform account management with profiles, settings, and slug-based routing
- **RBAC System** — Role-based access control with custom roles, permissions, memberships, and actor contexts
- **Transaction System** — State machine for invitations, requests, approvals, and ownership transfers with form integration
- **Form Builder System** — Dynamic forms with versioned templates, typed fields, response lifecycle, and form-transaction integration
- **CMS System** — Content management with draft/publish workflow, schema validation, rich text sanitization, API key auth, and 23 RBAC permissions
- **Explore System** — Full-text search with trigram fallback, suggested tags, and URL-synced filters for businesses and users
- **Network System** — Follow (User to Business/Platform) and Connection (User to User, Account to Account) with transaction-driven workflows
- **Content Visibility System** — 3-tier field visibility (public, configurable, members-only) with per-field overrides
- **Member Quota System** — Configurable member limits per business/platform with pre-check guards
- **Permission-Aware Responses** — `_permissions` injection on GET detail endpoints for frontend UI gating
- **Relationship Injection** — `_relationship` on GET detail for membership status, active transactions, follow/connection state
- **Cross-Type Conflict Guard** — Prevents duplicate transactions across invitation + request for same user/context
- **Frontend Foundation** — Authentication (Zustand + TanStack Query), route guards, navigation system, 3-tier auth
- **Frontend Feature Systems** — Members, forms, transactions, explore, business/platform profile pages
- **Notification System** — Email notifications with templates, retry logic, and preference management
- **Audit Logging** — Structured audit trail for security-sensitive operations
- **Backend Code Review** — 15-step audit with checklists, rules, and graded reports
- **Frontend Code Review** — 15-step audit with checklists, rules, and graded reports
