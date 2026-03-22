# Code Review System

Reusable framework for auditing the codebase. Each review step has three artifacts:

```
reviews/
├── checklists/
│   ├── backend/             # WHAT to check (enumerated items, checkboxes)
│   └── frontend/            # WHAT to check (enumerated items, checkboxes)
├── rules/
│   ├── backend/             # HOW to judge (pass/fail criteria per item)
│   └── frontend/            # HOW to judge (pass/fail criteria per item)
└── reports/
    ├── backend/v1/          # RESULTS (findings, evidence, remediation)
    └── frontend/v1/         # RESULTS (findings, evidence, remediation)
```

## How It Works

1. **Checklist** defines the items to verify — organized by section (1.1, 1.2, ...).
2. **Rules** define pass/fail thresholds — one rule per checklist item, written as actionable criteria.
3. **Report** records actual findings — references checklist items, applies rules, grades PASS/FAIL/WARN.

## Running a Review

1. Open the checklist for the step you're auditing.
2. For each item, apply the corresponding rule from the rules file.
3. Record findings in a new report under `reports/{workspace}/vN/` (increment version for re-audits).

## Versioning

Reports are versioned: `v1/`, `v2/`, etc. Re-audit the same checklist after fixing issues to track improvement.

---

## Backend Steps (Django 5.1 REST API)

| # | Topic | Grade | Status |
|---|-------|-------|--------|
| 01 | Project Structure & Organization | A- | Audited (v1) |
| 02 | Configuration & Environment | B+ | Audited (v1) |
| 03 | Database & Models | A | Audited (v1) |
| 04 | API Design (DRF) | A- | Audited (v1) |
| 05 | Authentication & Authorization | B+ | Audited (v1) |
| 06 | Validation & Business Logic | B+ | Audited (v1) |
| 07 | Testing | A- | Audited (v1) |
| 08 | Performance | B | Audited (v1) |
| 09 | Security | A- | Audited (v1) |
| 10 | Code Quality & Style | A- | Audited (v1) |
| 11 | Dependency Management | B+ | Audited (v1) |
| 12 | DevOps & Infrastructure | B+ | Audited (v1) |
| 13 | CI/CD Pipeline | C- | Audited (v1) |
| 14 | Documentation | B- | Audited (v1) |
| 15 | Observability & Monitoring | C+ | Audited (v1) |

**Overall Backend Grade: B+** (5 A-tier, 6 B-tier, 2 C-tier)

---

## Frontend Steps (Next.js 16 + React 19 + TypeScript)

| # | Topic | Sections | Status |
|---|-------|----------|--------|
| 01 | Project Structure & Organization | 10 | Checklist ready |
| 02 | Configuration & Environment | 10 | Checklist ready |
| 03 | Routing & Navigation | 10 | Checklist ready |
| 04 | Component Architecture | 11 | Checklist ready |
| 05 | State Management | 10 | Checklist ready |
| 06 | Data Fetching & API Integration | 11 | Checklist ready |
| 07 | Authentication & Authorization | 11 | Checklist ready |
| 08 | Forms & Validation | 10 | Checklist ready |
| 09 | Styling & Theming | 9 | Checklist ready |
| 10 | TypeScript & Type Safety | 10 | Checklist ready |
| 11 | Testing | 12 | Checklist ready |
| 12 | Performance & Optimization | 11 | Checklist ready |
| 13 | Security | 10 | Checklist ready |
| 14 | Accessibility & UX | 10 | Checklist ready |
| 15 | Error Handling & Observability | 10 | Checklist ready |

**Total: 155 subsections across 15 steps** — See [frontend index](checklists/frontend/00-index.md) for details.
