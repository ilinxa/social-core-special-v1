# Project Documentation

## Structure

| Folder | Purpose | When Created |
|--------|---------|--------------|
| `setup/` | Environment setup and run modes ([quick ref](setup/setup-and-run-modes.md), [detailed](setup/run-modes-reference.md)) | Project setup |
| `descriptions/` | What a system is, requirements, scope | Before building |
| `plans/` | How to build it, architecture decisions | Before building |
| `implementations/` | Post-build comprehensive reference | After tests pass |

Each doc type folder has workspace subfolders: `backend/`, `frontend/`, `mobile/`.

## Naming Convention

Files use kebab-case: `{feature-name}.md`
Examples: `campaign-management.md`, `organization-v1.md`

## Workflow

1. **Describe** → `descriptions/{workspace}/{feature}.md`
2. **Plan** → `plans/{workspace}/{feature}.md`
3. **Review** → Update plan with review notes
4. **Implement** → Build it
5. **Test** → Verify (if fails → fix → re-test)
6. **Document** → `implementations/{workspace}/{feature}.md`

## Progress Tracking

Iteration logs live in `progress/` (project root, not here).
See `progress/README.md` for the JSON schema.
