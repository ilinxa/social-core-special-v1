# Plan Document Template

Location: `docs/plans/{workspace}/{feature-name}.md`

---

```markdown
# {Feature Name} — Implementation Plan

**Status:** Draft | Reviewed | Approved | Superseded
**Date:** {YYYY-MM-DD}
**Description Doc:** {link to description doc}

---

## 1. Architecture Overview

{ASCII diagram or high-level description of how this fits into the system.}

## 2. Core Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| {e.g., "Data model"} | {e.g., "Separate profile table"} | {why} |

## 3. Data Model

{Tables, fields, relationships, constraints.
 For Django: model classes and key fields.
 For frontend: API response shapes or DB schema.}

## 4. API Design

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| {path} | {verb} | {permission} | {what it does} |

## 5. Implementation Steps

### Phase 1: {name}
1. {step}
2. {step}

### Phase 2: {name}
1. {step}

## 6. Testing Strategy

- Unit tests: {what gets tested}
- Integration tests: {what gets tested}
- Edge cases: {key edge cases}

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| {risk} | {high/medium/low} | {plan} |

## 8. Review Notes

{Updated after review — decisions made, changes from original plan.}
```
