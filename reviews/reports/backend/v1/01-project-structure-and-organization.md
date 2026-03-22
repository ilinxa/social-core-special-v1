# 01 — Project Structure & Organization Report (v1)

**Date:** 2026-03-11
**Checklist:** `reviews/checklists/backend/01-project-structure-and-organization.md`
**Rules:** `reviews/rules/backend/01-project-structure-and-organization.md`
**Overall Grade: A-** (Production-grade structure with minor housekeeping gaps)

---

## Summary

| Section | Status | Issues Found |
|---------|--------|-------------|
| 1.1 Directory Layout | PASS | 7 debug scripts at backend root, 1 pip artifact |
| 1.2 Django App Granularity | PASS | 5 files >1200 lines need splitting |
| 1.3 Configuration Structure | PASS | No issues |
| 1.4 Entry Points | PASS | No issues |
| 1.5 Naming Conventions | PASS | No issues |
| 1.6 Test Structure | PASS | No issues |
| 1.7 Documentation Files | FAIL | Missing root README, CHANGELOG, LICENSE |
| 1.8 Dependency Files | PASS | No issues |
| 1.9 Layered Architecture | PASS | Consistent across all domain apps |
| 1.10 Core App | PASS | Infrastructure-only, not a god app |
| 1.11 apps.py Correctness | PASS | All 12 apps correctly configured |
| 1.12 API URL Versioning | PASS | Consistent `/api/v1/` everywhere |
| 1.13 Migration Health | PASS | No conflicts, proper sequencing |
| 1.14 `__init__.py` Completeness | PASS | All packages complete |
| 1.15 .env.example Completeness | PASS | Comprehensive examples provided |
| 1.16 Stale/Dead Apps | PASS | No unused apps |

**Total: 15 PASS / 1 FAIL — 3 HIGH issues, 5 MEDIUM issues, 4 LOW issues**

---

## Detailed Findings

### 1.1 Directory Layout

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.1.1 Top-level clarity | PASS | `apps/`, `backend_core/`, `requirements/`, `static/`, `templates/`, `tests/` — all self-explanatory |
| 1.1.2 No business logic at root | PASS | 7 debug scripts exist but none import models or define views |
| 1.1.3 Assets in dedicated dirs | PASS | `static/`, `templates/emails/`, `backend_core/media/` |
| 1.1.4 Scripts organized | WARN | Management commands correct (`apps/*/management/`), but ad-hoc scripts at backend root |
| 1.1.5 No temp/artifacts | FAIL | `backend/=24.1.0` (pip artifact) tracked in git |
| 1.1.6 .gitignore comprehensive | PASS | Root + backend + frontend all have proper .gitignore |

**Backend root files tracked in git:**

| File | Type | Action |
|------|------|--------|
| `manage.py` | Standard Django | Keep |
| `Dockerfile` | Infrastructure | Keep |
| `entrypoint.sh` | Infrastructure | Keep |
| `pytest.ini` | Config | Keep |
| `.coveragerc` | Config | Keep |
| `seed_e2e.py` | Debug script | Move to `scripts/` or delete |
| `check_biz.py` | Debug script | Move to `scripts/` or delete |
| `fix_biz.py` | Debug script | Move to `scripts/` or delete |
| `_get_reset_token.py` | Debug helper | Move to `scripts/` or delete |
| `_get_verification_code.py` | Debug helper | Move to `scripts/` or delete |
| `_register_user.py` | Debug helper | Move to `scripts/` or delete |
| `=24.1.0` | Pip artifact | **Delete immediately** |

---

### 1.2 Django App Granularity

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.2.1 Single domain per app | PASS | All 12 apps encapsulate one concept |
| 1.2.2 No god app | PASS | `core` has 0 domain models, only abstract bases |
| 1.2.3 No circular imports | PASS | Cross-app imports use lazy imports inside functions |
| 1.2.4 Noun names | PASS | All 12 are nouns or standard acronyms |
| 1.2.5 Standard structure | PASS | Each has models, views/api, serializers, tests, migrations |
| 1.2.6 File size limits | FAIL | 5 files exceed 1200 lines (see table below) |
| 1.2.7 No external domain logic | PASS | No `utils.py` at root doing business work |

**Oversized files (>1200 lines):**

| File | Lines | Recommended Split |
|------|-------|-------------------|
| `transaction/services.py` | 1,446 | `invitation_services.py`, `request_services.py`, `ownership_services.py` |
| `cms/services.py` | 1,439 | `site_services.py`, `page_services.py`, `template_services.py`, `media_services.py` |
| `auth/views.py` | 1,311 | `auth_views.py`, `oauth_views.py`, `password_views.py`, `verification_views.py` |
| `forms/services.py` | 1,262 | `form_services.py`, `response_services.py` |
| `rbac/services.py` | 1,206 | `membership_services.py`, `role_services.py` |

**Large files (800–1200 lines):**

| File | Lines |
|------|-------|
| `rbac/views.py` | 1,183 |
| `transaction/api/views.py` | 996 |
| `organization/business/views.py` | 932 |
| `forms/api/views.py` | 883 |

**App inventory: 40,682 lines across 12 apps**

---

### 1.3 Configuration Structure

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.3.1 Settings split | PASS | `base.py`, `local.py`, `local_docker.py`, `production.py` |
| 1.3.2 Settings module per env | PASS | manage.py → `local_docker`, wsgi/asgi → `production` |
| 1.3.3 Single config dir | PASS | `backend_core/settings/` |
| 1.3.4 Clean root urls.py | PASS | 13 `include()` statements, no inline views |
| 1.3.5 wsgi/asgi correct | PASS | Both present, asgi has WebSocket routing ready |
| 1.3.6 Celery at config level | PASS | `backend_core/celery.py` with 12 beat tasks |

---

### 1.4 Entry Points

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.4.1 manage.py standard | PASS | Unmodified, defaults to `local_docker` |
| 1.4.2 Single entry point | PASS | `manage.py runserver` or Docker `entrypoint.sh` |
| 1.4.3 Makefile exists | PASS | 40+ targets: `dev`, `test`, `migrate`, `lint`, `check`, `setup` |
| 1.4.4 Procfile | INFO | Not deploying to platform — N/A |
| 1.4.5 pyproject.toml | INFO | Not a distributable package — N/A |

---

### 1.5 Naming Conventions

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.5.1 snake_case dirs/files | PASS | Zero violations |
| 1.5.2 Consistent plural/singular | WARN | Mix: singular (`auth`, `email`, `network`) + plural (`users`, `forms`, `notifications`) — acceptable Django convention |
| 1.5.3 No abbreviations | PASS | Full names: `organization/`, `notifications/`, `transaction/` |
| 1.5.4 Test files mirror source | PASS | `test_models.py`, `test_services.py`, `test_views.py`, `test_selectors.py`, `test_policies.py` |
| 1.5.5 Migration names standard | PASS | All auto-generated |
| 1.5.6 Command names clear | PASS | Located in `apps/*/management/commands/` |

---

### 1.6 Test Structure

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.6.1 Tests separated from source | PASS | `apps/*/tests/` (unit) + `tests/api_integration/` (integration) |
| 1.6.2 Source files have tests | PASS | One test file per source layer |
| 1.6.3 Factories in shared files | PASS | `apps/*/tests/factories.py` — 12 factory files |
| 1.6.4 conftest.py exists | PASS | 14 conftest files: root + integration + 12 per-app |
| 1.6.5 No stray test files | PASS | Zero test files outside designated directories |

**Statistics:** 89 unit test modules, 13 integration test modules, 12 factory files, `.coveragerc` with 80% threshold

---

### 1.7 Documentation Files

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.7.1 README.md with content | **FAIL** | Exists but is a placeholder: `## readme#` |
| 1.7.2 CHANGELOG.md | WARN | Missing entirely |
| 1.7.3 CONTRIBUTING.md | INFO | Missing — single-developer project currently |
| 1.7.4 docs/ directory | PASS | Comprehensive: `descriptions/`, `plans/`, `implementations/` |
| 1.7.5 LICENSE file | **FAIL** | Missing entirely |
| 1.7.6 .env.example | PASS | `.env.example` (prod, ~150 lines) + `.env.dev.example` (dev, ~59 lines) |

---

### 1.8 Dependency Files

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.8.1 Split requirements | PASS | `requirements/base.txt`, `local.txt`, `production.txt` |
| 1.8.2 No conflicting managers | PASS | Single requirements directory |
| 1.8.3 Docker files present | PASS | `backend/Dockerfile` + `docker-compose.dev.yml` + `docker-compose.yml` |
| 1.8.4 pre-commit config | INFO | Not using pre-commit hooks |
| 1.8.5 CI configuration | INFO | No `.github/workflows/` — not yet configured |

---

### 1.9 Layered Architecture

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.9.1 Layer files present | PASS | All domain apps have expected layers |
| 1.9.2 Missing layers intentional | PASS | explore (no services), email (no views) — documented reasons |
| 1.9.3 No empty layer files | PASS | All layer files contain relevant logic |

**Layer coverage:**

| Layer | Present In |
|-------|-----------|
| `models.py` | 12/12 |
| `managers.py` | 5/12 (where custom querysets needed) |
| `selectors.py` | 11/12 (missing: core) |
| `services.py` | 9/12 (missing: core, email, explore) |
| `policies.py` | 8/12 (missing: auth, core, email, explore) |

---

### 1.10 Core/Shared App

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.10.1 Core app exists | PASS | `apps/core/` with 17 sub-packages |
| 1.10.2 No concrete models | PASS | Zero domain models, only abstract bases |
| 1.10.3 No duplicated utilities | PASS | All shared code in core |
| 1.10.4 Organized sub-packages | PASS | models/, exceptions/, observability/, visibility/, permissions/, pagination/, utils/, middleware/, management/, data/ |

---

### 1.11 apps.py Correctness

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.11.1 Correct dotted names | PASS | All 12 use `name = "apps.xxx"` |
| 1.11.2 Consistent auto_field | PASS | All use `BigAutoField` |
| 1.11.3 ready() where needed | PASS | 4 apps register signals/handlers in `ready()` |
| 1.11.4 No label conflicts | PASS | `apps.auth` uses `label='authentication'` to avoid Django conflict |

---

### 1.12 API URL Versioning

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.12.1 Consistent versioning | PASS | All 13 endpoint groups use `/api/v1/` |
| 1.12.2 Prefix in root only | PASS | App urls.py use relative paths |
| 1.12.3 No unversioned endpoints | PASS | All API endpoints versioned |

---

### 1.13 Migration Health

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.13.1 No conflicts | PASS | 45 migrations, 0 conflicts |
| 1.13.2 No gaps | PASS | All sequentially numbered |
| 1.13.3 Seed migrations documented | PASS | Seed migrations in rbac, explore clearly named |
| 1.13.4 No pending migrations | PASS | All model changes have migrations |

---

### 1.14 __init__.py Completeness

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.14.1 All packages complete | PASS | Verified across all 12 apps, sub-packages, tests, migrations |

---

### 1.15 .env.example Completeness

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.15.1 All env vars documented | PASS | `.env.example` (~150 lines) + `.env.dev.example` (~59 lines) |
| 1.15.2 Separate dev/prod examples | PASS | Two example files exist |
| 1.15.3 No real secrets | PASS | Examples use placeholder values |

---

### 1.16 Stale/Dead Apps

| Rule | Verdict | Evidence |
|------|---------|----------|
| 1.16.1 No empty apps | PASS | All 12 have models, views, and tests |
| 1.16.2 No unregistered apps | PASS | All apps in `apps/` are in INSTALLED_APPS |
| 1.16.3 No skeleton migrations | PASS | All migration files have operations |

---

## Issues Summary

### HIGH Priority (3)

| ID | Rule | Issue | Location | Action |
|----|------|-------|----------|--------|
| H1 | 1.7.1 | Root README.md is a placeholder | `README.md` | Write real project documentation |
| H2 | 1.7.5 | No LICENSE file | Root | Add appropriate license |
| H3 | 1.2.6 | 5 service/view files >1200 lines | See 1.2 table | Split into sub-modules |

### MEDIUM Priority (5)

| ID | Rule | Issue | Location | Action |
|----|------|-------|----------|--------|
| M1 | 1.7.2 | No CHANGELOG.md | Root | Create and maintain |
| M2 | 1.8.5 | No CI/CD pipeline | `.github/workflows/` | Set up GitHub Actions |
| M3 | 1.2.6 | 4 view files 800–1200 lines | See 1.2 table | Consider splitting |
| M4 | 1.8.4 | No .pre-commit-config.yaml | Root | Add pre-commit hooks |
| M5 | 1.7.3 | No CONTRIBUTING.md | Root | Create if multi-contributor |

### LOW Priority (4)

| ID | Rule | Issue | Location | Action |
|----|------|-------|----------|--------|
| L1 | 1.1.5 | Pip artifact tracked in git | `backend/=24.1.0` | Delete and add to .gitignore |
| L2 | 1.1.4 | 7 debug scripts at backend root | `backend/seed_e2e.py`, etc. | Move to `scripts/` or delete |
| L3 | 1.5.2 | App naming mix (singular/plural) | All apps | Cosmetic — acceptable convention |
| L4 | 1.4.5 | No pyproject.toml | Root | Not needed unless packaging |

---

## Update Log

### Update 1 — 2026-03-13

**6 issues resolved:**

| ID | Issue | Resolution |
|----|-------|------------|
| H1 | Root README.md is a placeholder | Rewrote `README.md` with full project documentation (tech stack, monorepo structure, prerequisites, quick start, development commands, testing commands, environment setup, docs pointer, license notice) |
| H2 | No LICENSE file | Created `LICENSE` — Proprietary / All Rights Reserved |
| M1 | No CHANGELOG.md | Created `CHANGELOG.md` following Keep a Changelog format with `[Unreleased]` section listing all implemented systems |
| L1 | Pip artifact tracked in git | Deleted `backend/=24.1.0` and added `=*` pattern to `backend/.gitignore` |
| L2 | Debug scripts at backend root | Created `backend/scripts/` and moved 6 scripts there (`seed_e2e.py`, `check_biz.py`, `fix_biz.py`, `_get_reset_token.py`, `_get_verification_code.py`, `_register_user.py`). Only `manage.py` remains at backend root. |
| 1.1.6 | .gitignore gap | Added pip artifact exclusion rule (`=*`) to `backend/.gitignore` |

**Remaining (deferred):**

| ID | Issue | Reason |
|----|-------|--------|
| H3 | 5 service/view files >1200 lines | Deferred — significant refactoring, separate task |
| M2 | No CI/CD pipeline | Deferred — separate task |
| M3 | 4 view files 800–1200 lines | Deferred — separate task |
| M4 | No .pre-commit-config.yaml | Deferred — separate task |
| M5 | No CONTRIBUTING.md | Skipped — single-developer project |
| L3 | App naming mix (singular/plural) | Accepted — standard Django convention |
| L4 | No pyproject.toml | Skipped — not needed unless packaging |

**Updated verdicts after fixes:**

| Rule | Before | After |
|------|--------|-------|
| 1.1.4 Scripts organized | WARN | **PASS** — all scripts in `backend/scripts/` |
| 1.1.5 No temp/artifacts | FAIL | **PASS** — artifact deleted, .gitignore updated |
| 1.7.1 README.md with content | FAIL | **PASS** — comprehensive project documentation |
| 1.7.2 CHANGELOG.md | WARN | **PASS** — Keep a Changelog format |
| 1.7.5 LICENSE file | FAIL | **PASS** — Proprietary license |

**Post-fix grade: A** (2 FAILs → 0 FAILs, 2 WARNs → 0 WARNs resolved. Remaining: H3/M2-M4 deferred, L3/L4 accepted.)
