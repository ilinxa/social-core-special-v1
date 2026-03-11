# Progress Tracking

## Schema

Each JSON file contains an `entries` array. Each entry:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | Yes | Global sequential ID, never resets |
| `title` | string (120 chars) | Yes | What was done |
| `category` | enum | Yes | See categories below |
| `tags` | string[] (1-5) | Yes | App names, feature names, tech labels |
| `timestamp` | ISO 8601 | Yes | UTC timestamp |
| `summary` | string (500 chars) | Yes | What was accomplished |
| `critical` | string (300 chars) | No | Gotchas, breaking changes, must-remember |
| `files_changed` | string[] | No | Key files created/modified |
| `related_doc` | string | No | Path to related doc |

## Categories

`planning`, `developing`, `testing`, `error-handling`, `bug-fixing`, `documentation`, `deployment`, `refactoring`, `reviewing`

## File Splitting

- `001-100.json` = entries 1-100
- `101-200.json` = entries 101-200
- Split at 100 entries. New file for the next entry.
- ID never resets. File number = ceil(id / 100).

## Rules

- One entry per significant iteration (not per file edit)
- Always read the last file to find the current max ID before adding
- Never modify past entries (append-only log)
