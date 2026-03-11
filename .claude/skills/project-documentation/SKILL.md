---
name: project-documentation
description: >
  Create and update project documentation and progress tracking. Use when building a new feature,
  documenting an existing system, logging progress entries, creating implementation docs, writing
  description or plan docs, or when the user mentions documentation, progress tracking, or
  implementation reference. Triggers on: document, progress, describe, plan, implementation doc.
---

# Project Documentation Skill

## Quick Start

- **Progress logs**: `progress/001-100.json` (JSON, append-only, split at 100)
- **Descriptions**: `docs/descriptions/{workspace}/{feature}.md` (pre-build)
- **Plans**: `docs/plans/{workspace}/{feature}.md` (pre-build)
- **Implementation docs**: `docs/implementations/{workspace}/{feature}.md` (post-build)
- **Workspaces**: `backend`, `frontend`, `mobile`
- **Naming**: kebab-case, e.g., `campaign-management.md`

## Documentation Flow

```
Describe → Plan → Review → Implement → Test → Document
                                         ↓
                                   (tests fail?)
                                         ↓
                                   Bug Fix → Test → Document
```

| Phase | Output | Progress Category |
|-------|--------|-------------------|
| 1. Describe | `docs/descriptions/{ws}/{feature}.md` | planning |
| 2. Plan | `docs/plans/{ws}/{feature}.md` | planning |
| 3. Review | Update plan with review notes section | reviewing |
| 4. Implement | Code | developing |
| 5. Test | Tests | testing / bug-fixing |
| 6. Document | `docs/implementations/{ws}/{feature}.md` | documentation |

**When to skip phases:**
- Trivial changes (<50 lines, single file): skip description and plan
- Bug fixes: skip description, plan is optional
- Always log progress regardless

## Progress Tracking

Append a JSON entry to the latest file in `progress/` after each significant iteration.

See @references/progress-schema.md for the full schema and examples.

**Key rules:**
- One entry per significant iteration, NOT per file edit
- `id` is globally sequential across all files, never resets
- Split at 100 entries: `001-100.json`, `101-200.json`, etc.
- Always read the last file first to find the current max ID
- Append-only — never modify past entries
- Include `critical` field only when there's a genuine gotcha or breaking change

## Document Templates

Use the appropriate template from references/:

- @references/description-template.md — pre-build: what the system is
- @references/plan-template.md — pre-build: how to build it
- @references/backend-impl-template.md — post-build: Django implementation reference
- @references/frontend-impl-template.md — post-build: Next.js / React Native reference

**Template rules:**
- Skip sections that don't apply. A 5-section doc is better than 17 empty sections.
- Never leave placeholder text — fill or remove.
- Backend docs emphasize: models, services, selectors, views, audit actions, migrations.
- Frontend docs emphasize: components, hooks, routes, route protection, state management.

## Anti-Patterns

### Progress Tracking
- WRONG: Logging every tiny file edit as a separate entry.
  CORRECT: One entry per significant iteration (feature complete, test pass, architecture decision).

- WRONG: Empty or vague summaries like "worked on stuff".
  CORRECT: Specific: "Implemented BusinessAccountService with 7 methods covering full lifecycle."

- WRONG: Forgetting to read the latest file for the current max ID.
  CORRECT: Always read last entry in latest progress file before adding.

### Documentation
- WRONG: Creating implementation docs for code with failing tests.
  CORRECT: Fix bugs first, verify tests pass, THEN document.

- WRONG: Copying template verbatim with placeholder text.
  CORRECT: Remove sections that don't apply.

- WRONG: Duplicating implementation doc content in app-level INDEX.md.
  CORRECT: App-level docs can be summaries that link to the full implementation doc.

- WRONG: Skipping the description/plan phase for a major feature.
  CORRECT: Always describe and plan first. It saves rework.
