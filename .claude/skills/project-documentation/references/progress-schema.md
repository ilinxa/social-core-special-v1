# Progress Tracking — JSON Schema

## File Location

`progress/001-100.json`, `progress/101-200.json`, etc.

## Schema

```json
{
  "entries": [
    {
      "id": 1,
      "title": "Short title (max 120 chars)",
      "category": "developing",
      "tags": ["backend", "feature-name"],
      "timestamp": "2026-02-22T14:30:00Z",
      "summary": "What was accomplished, decisions made, blockers (max 500 chars)",
      "critical": "Optional. Gotchas, breaking changes (max 300 chars)",
      "files_changed": ["optional/list/of/files.py"],
      "related_doc": "optional/path/to/doc.md"
    }
  ]
}
```

## Field Reference

| Field | Type | Required | Max Length | Description |
|-------|------|----------|-----------|-------------|
| `id` | integer | Yes | — | Global sequential ID, never resets |
| `title` | string | Yes | 120 | Short descriptive title |
| `category` | enum | Yes | — | See categories below |
| `tags` | string[] | Yes | 1-5 items | App names, feature names, tech |
| `timestamp` | string | Yes | — | ISO 8601 UTC |
| `summary` | string | Yes | 500 | What was accomplished |
| `critical` | string | No | 300 | Gotchas, breaking changes |
| `files_changed` | string[] | No | — | Key files created/modified |
| `related_doc` | string | No | — | Path to related doc |

## Categories

| Category | When to Use |
|----------|-------------|
| `planning` | Designing, describing, or planning a system |
| `developing` | Writing implementation code |
| `testing` | Writing or running tests |
| `error-handling` | Handling unexpected errors during development |
| `bug-fixing` | Fixing bugs found during testing or production |
| `documentation` | Creating or updating docs |
| `deployment` | Deploying, configuring infrastructure |
| `refactoring` | Restructuring existing code without changing behavior |
| `reviewing` | Code review, plan review, design review |

## File Splitting

- `001-100.json` holds entries with id 1-100
- `101-200.json` holds entries with id 101-200
- When the current file has 100 entries, create the next file
- File number = `ceil(id / 100)`, padded to 3 digits
- Each file is self-contained with its own `{"entries": [...]}` wrapper

## Example

```json
{
  "entries": [
    {
      "id": 42,
      "title": "Implement campaign CRUD endpoints",
      "category": "developing",
      "tags": ["backend", "campaigns", "api"],
      "timestamp": "2026-03-15T10:20:00Z",
      "summary": "Built CampaignService with create, update, archive, delete. 4 DRF ViewSets with IsAuthenticated + RBAC policy checks. All writes wrapped in @transaction.atomic.",
      "critical": "Campaign deletion is soft-delete only — sets status to 'deleted', does not remove row.",
      "files_changed": [
        "backend/apps/campaigns/services.py",
        "backend/apps/campaigns/views.py",
        "backend/apps/campaigns/urls.py"
      ],
      "related_doc": "docs/plans/backend/campaigns.md"
    }
  ]
}
```
