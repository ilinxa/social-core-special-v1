# Backend Implementation Document Template

Location: `docs/implementations/backend/{feature-name}.md`

Skip sections that don't apply. Fill or remove — never leave placeholders.

---

```markdown
# {Feature Name} — Implementation Reference

**Version:** v1
**Last Updated:** {YYYY-MM-DD}
**Status:** Implemented | Partial | Deprecated

---

## 1. Architecture Overview

{ASCII diagram showing how this system fits into the broader architecture.
 Show the layer diagram: views → serializers → services → selectors → models.}

## 2. Core Concepts & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| {e.g., "Data model"} | {e.g., "Separate profile table"} | {why} |

## 3. Data Layer

### 3.1 {ModelName}

Location: `apps/{app}/models.py`

| Field | Type | Notes |
|-------|------|-------|
| {field} | {type} | {constraints, defaults, FKs} |

Constraints: {unique together, check constraints, indexes}
Managers: {custom manager methods if any}

{Repeat for each model.}

### Migrations
- `{migration_number}` — {what it does}

## 4. Service Layer

### 4.1 {ServiceName}

Location: `apps/{app}/services.py`

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| {method} | {keyword args} | {return type} | {side effects, transactions} |

### 4.2 Selectors

Location: `apps/{app}/selectors.py`

| Function | Args | Returns | Notes |
|----------|------|---------|-------|
| {function} | {args} | {QuerySet/object} | {filters, ordering} |

## 5. API Layer

### 5.1 Endpoints

| Endpoint | Method | Permission | Description |
|----------|--------|------------|-------------|
| `/api/v1/{path}` | {verb} | {permission class} | {what it does} |

### 5.2 Serializers

Location: `apps/{app}/serializers.py`

| Serializer | Type | Fields | Notes |
|------------|------|--------|-------|
| {name} | Input/Output | {fields} | {validation rules} |

## 6. Types & Constants

{Enums, choices, constants used by this feature.}

## 7. Key Flows

### Flow 1: {Name}
1. {step}
2. {step}
3. {step}

{3-7 flows covering the most important user/system interactions.
 Include error paths where critical.}

## 8. Permissions & Authorization

| Action | RBAC Permission | Audit Action | Notes |
|--------|----------------|--------------|-------|
| {action} | {permission string} | {audit constant} | {who can do this} |

## 9. Configuration & Gotchas

### Settings
| Setting | Location | Default | Notes |
|---------|----------|---------|-------|
| {setting} | {settings file} | {value} | {what it controls} |

### Gotchas
- {gotcha: what goes wrong and how to fix it}

## 10. Local Development

### Setup
{Commands to get this feature running locally.}

### Test Data
{Seed data, test accounts, or fixtures relevant to this feature.}

### Useful URLs
| URL | Purpose |
|-----|---------|
| {url} | {what it shows} |

## 11. Deployment

| Aspect | Local | Production |
|--------|-------|------------|
| {aspect} | {local value} | {prod value} |

### Pre-Deploy Checklist
- [ ] {check 1}
- [ ] {check 2}

## 12. Testing

| Module | Tests | Status |
|--------|-------|--------|
| {module} | {count} | Pass/Fail |
| **Total** | **{total}** | **{status}** |

## 13. File Summary

### New Files
| File | Description |
|------|-------------|
| {path} | {what it does} |

### Modified Files
| File | Change |
|------|--------|
| {path} | {what changed} |

## 14. Known Limitations

1. {limitation}
2. {limitation}

## 15. vNext TODOs

| Item | Context | Priority |
|------|---------|----------|
| {todo} | {why, what already exists to build on} | P0/P1/P2 |

## 16. Changelog

### v1 ({YYYY-MM-DD})
- Initial implementation
```
