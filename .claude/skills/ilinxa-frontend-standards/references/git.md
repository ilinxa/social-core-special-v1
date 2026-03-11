# Git Conventions

## Table of Contents
1. [Branch Naming](#branch-naming)
2. [Commit Messages](#commit-messages)
3. [Branching Strategy](#branching-strategy)
4. [Pull Request Workflow](#pull-request-workflow)
5. [Git Hygiene](#git-hygiene)

---

## Branch Naming

Format: `<type>/<ticket-id>-<short-description>`

| Type | Use |
|------|-----|
| `feat` | New feature |
| `fix` | Bug fix |
| `hotfix` | Urgent prod fix (branch from `main`) |
| `chore` | Tooling, config, deps, refactoring |
| `docs` | Documentation only |
| `test` | Tests only |

Examples: `feat/ILX-1234-user-profile-avatar`, `fix/ILX-5678-login-redirect-loop`

Rules: Always branch from latest `develop` (or `main` for hotfixes). Delete after merge. No personal branches — every branch traces to a ticket.

---

## Commit Messages

Conventional Commits format:
```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

Subject: lowercase after colon, no period, present tense imperative ("add" not "added"), max 72 chars.

| Type | Example |
|------|---------|
| `feat` | `feat(auth): add social login with Google` |
| `fix` | `fix(cart): prevent double-submit on checkout` |
| `refactor` | `refactor(api): extract fetch wrapper to shared util` |
| `chore` | `chore(deps): upgrade react-query to v5` |
| `test` | `test(auth): add integration tests for login flow` |
| `perf` | `perf(images): add lazy loading to product gallery` |
| `ci` | `ci(github): add preview deploy workflow` |

Body: explain **why**. Footer: breaking changes and ticket refs.

```
feat(forms): add dynamic field validation

Server-side validation was causing 300ms+ delays on every keystroke.
Moved validation to client-side with Zod schemas.

Refs: ILX-1234
```

Breaking changes: `refactor(api)!: change response format` + `BREAKING CHANGE:` in footer.

---

## Branching Strategy

Two long-lived branches:
- `main` → production
- `develop` → staging / integration

Flow: feature branch → PR → squash-merge into `develop` → merge `develop` into `main` for release (merge commit, no squash).

Hotfix: branch from `main`, fix, PR to `main`, then merge `main` back into `develop`.

---

## Pull Request Workflow

PR title: same Conventional Commits format (used as squash commit message).

PR template (`.github/pull_request_template.md`):
```markdown
## What
Brief description.

## Why
Context + ticket link.

## How
Technical approach.

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing performed

## Screenshots
Before/after if UI changes.

## Ticket
Closes ILX-XXXX
```

Rules:
- One ticket, one PR
- Aim for <400 lines changed
- Self-review before requesting reviewers
- All CI must pass. At least one approval.
- Resolve all comments before merge.
- Squash-merge into `develop`. Merge commit into `main`.

---

## Git Hygiene

`.gitignore` minimum:
```gitignore
node_modules/
dist/
build/
.next/
out/
.env
.env.local
.env.*.local
.vscode/
!.vscode/settings.json
!.vscode/extensions.json
.idea/
.DS_Store
coverage/
*.log
*.tsbuildinfo
```

- Never commit secrets/API keys. Use `.env` + `.gitignore`.
- If secret committed: rotate immediately, purge with BFG Repo-Cleaner.
- Commit often, each commit leaves codebase in working state.
