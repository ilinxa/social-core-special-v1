# Frontend Implementation Document Template

Location: `docs/implementations/frontend/{feature-name}.md` or `docs/implementations/mobile/{feature-name}.md`

Skip sections that don't apply. Fill or remove — never leave placeholders.

---

```markdown
# {Feature Name} — Implementation Reference

**Version:** v1
**Last Updated:** {YYYY-MM-DD}
**Status:** Implemented | Partial | Deprecated

---

## 1. Architecture Overview

{ASCII diagram showing component tree, data flow, and rendering strategy.
 Show: pages → components → hooks → server actions → API.}

## 2. Core Concepts & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| {e.g., "Rendering"} | {e.g., "ISR with revalidate=60"} | {why} |

## 3. Data Layer

### 3.1 Server DAL

Location: `src/lib/api/{feature}.server.ts`

| Function | Signature | Notes |
|----------|-----------|-------|
| {function} | {args → return} | {auth, caching} |

### 3.2 Client DAL

Location: `src/lib/api/{feature}.ts`

| Function | Notes |
|----------|-------|
| {function} | {when used} |

### 3.3 Query Keys

```typescript
{feature}Keys = {
  all: ["{feature}"],
  list: ["{feature}", "list"],
  detail: ["{feature}", "detail", id],
}
```

## 4. Types & Interfaces

Location: `src/types/{feature}.ts`

```typescript
{key type definitions — database rows, input types, composite types}
```

## 5. Hooks

Location: `src/features/{feature}/hooks/`

| Hook | Type | Query Key | Notes |
|------|------|-----------|-------|
| {hook} | useQuery/mutations | {key} | {invalidation strategy} |

### Invalidation Hierarchy
```
{show which mutations invalidate which queries}
```

## 6. Components

### Admin Components

Location: `src/features/{feature}/components/`

| Component | Purpose |
|-----------|---------|
| {component} | {what it renders and does} |

### Public Components

| Component | Purpose |
|-----------|---------|
| {component} | {what it renders} |

## 7. Pages & Routes

| Route | Type | Data Loading | Component |
|-------|------|-------------|-----------|
| {path} | Server/Client/ISR | {function} | {component} |

## 8. Key Flows

### Flow 1: {Name}
1. {step}
2. {step}

{3-7 flows covering the most important user interactions.}

## 9. Route Protection

| Path | anon | user | admin | Notes |
|------|------|------|-------|-------|
| {path} | {access/redirect} | {access/redirect} | {access} | {notes} |

## 10. Server Actions

Location: `src/features/{feature}/actions/`

| Action | Input | Output | DAL Function |
|--------|-------|--------|-------------|
| {action} | {input type} | {output} | {server function} |

## 11. Configuration & Gotchas

### Environment Variables
| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| {var} | {yes/no} | {value} | {what it does} |

### Gotchas
- {gotcha}

## 12. Local Development

### Setup
```bash
{setup commands}
```

### Test Accounts
| Email | Password | Role |
|-------|----------|------|
| {email} | {pass} | {role} |

### Useful URLs
| URL | Purpose |
|-----|---------|
| {url} | {what it shows} |

## 13. Testing

| Module | Tests | Status |
|--------|-------|--------|
| {module} | {count} | Pass/Fail |

## 14. File Summary

### New Files
| File | Description |
|------|-------------|
| {path} | {what it does} |

### Modified Files
| File | Change |
|------|--------|
| {path} | {what changed} |

## 15. Known Limitations

1. {limitation}

## 16. vNext TODOs

| Item | Context | Priority |
|------|---------|----------|
| {todo} | {what exists to build on} | P0/P1/P2 |

## 17. Changelog

### v1 ({YYYY-MM-DD})
- Initial implementation
```
