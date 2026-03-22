# 01 — Project Structure & Organization Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 1.1 Directory Layout

| ID | Rule | Verdict |
|----|------|---------|
| 1.1.1 | FAIL if a new developer cannot understand the purpose of each top-level directory within 10 seconds | PASS/FAIL |
| 1.1.2 | FAIL if any `.py` file at backend root imports models, calls services, or defines views (manage.py and config excluded) | PASS/FAIL |
| 1.1.3 | FAIL if static files, media uploads, or templates are mixed into app directories without a dedicated top-level folder | PASS/FAIL |
| 1.1.4 | WARN if one-off scripts, seed files, or utility scripts are at backend root instead of a `scripts/` directory | PASS/WARN |
| 1.1.5 | FAIL if any file matching `temp_*`, `test[0-9]*.py`, `old_*`, `backup_*`, or build artifacts (e.g. `=24.1.0`) is tracked in git | PASS/FAIL |
| 1.1.6 | FAIL if .gitignore is missing entries for: `__pycache__/`, `*.pyc`, `.env`, `venv/`, `db.sqlite3`, `*.log`, `media/` | PASS/FAIL |

## 1.2 Django App Granularity

| ID | Rule | Verdict |
|----|------|---------|
| 1.2.1 | FAIL if a single app owns more than 3 unrelated domain concepts (e.g. users + billing + notifications) | PASS/FAIL |
| 1.2.2 | FAIL if any app (except core/common) has more than 15 models | PASS/FAIL |
| 1.2.3 | FAIL if two apps import from each other at module level (circular). PASS if lazy imports inside functions | PASS/FAIL |
| 1.2.4 | WARN if app names are verbs or adjectives instead of nouns | PASS/WARN |
| 1.2.5 | FAIL if any app is missing both `models.py` and `apps.py` | PASS/FAIL |
| 1.2.6 | FAIL if any single `.py` file exceeds 1200 lines. WARN if any exceeds 800 lines | PASS/WARN/FAIL |
| 1.2.7 | FAIL if domain logic (model queries, business rules) exists in a file outside any app directory | PASS/FAIL |

## 1.3 Configuration Structure

| ID | Rule | Verdict |
|----|------|---------|
| 1.3.1 | FAIL if all settings are in a single `settings.py` with no environment separation | PASS/FAIL |
| 1.3.2 | FAIL if `DJANGO_SETTINGS_MODULE` is hardcoded in source code without env override capability | PASS/FAIL |
| 1.3.3 | FAIL if settings files are scattered across multiple directories | PASS/FAIL |
| 1.3.4 | FAIL if root `urls.py` contains any view function/class definitions | PASS/FAIL |
| 1.3.5 | FAIL if `wsgi.py` or `asgi.py` is missing or points to wrong settings module | PASS/FAIL |
| 1.3.6 | FAIL if Celery is used but `celery.py` is inside an app instead of at the project config level | PASS/FAIL |

## 1.4 Entry Points

| ID | Rule | Verdict |
|----|------|---------|
| 1.4.1 | FAIL if `manage.py` is not at backend root or has been modified beyond default boilerplate | PASS/FAIL |
| 1.4.2 | FAIL if there are multiple conflicting entry points (e.g. two `manage.py` files) | PASS/FAIL |
| 1.4.3 | WARN if no Makefile, justfile, or equivalent automation exists | PASS/WARN |
| 1.4.4 | INFO if no Procfile — only relevant for platform deployments | PASS/INFO |
| 1.4.5 | INFO if no pyproject.toml — only relevant if project is a distributable package | PASS/INFO |

## 1.5 Naming Conventions

| ID | Rule | Verdict |
|----|------|---------|
| 1.5.1 | FAIL if any directory or Python file uses CamelCase or kebab-case | PASS/FAIL |
| 1.5.2 | WARN if app names mix singular and plural inconsistently without clear rationale | PASS/WARN |
| 1.5.3 | WARN if directory names use abbreviations (e.g. `notifs/` instead of `notifications/`) | PASS/WARN |
| 1.5.4 | WARN if test file names don't mirror source files (e.g. `test_views.py` for `views.py`) | PASS/WARN |
| 1.5.5 | WARN if migration files have been manually renamed from auto-generated names without documented reason | PASS/WARN |
| 1.5.6 | WARN if management command files have generic names (e.g. `run.py` instead of `seed_users.py`) | PASS/WARN |

## 1.6 Test Structure

| ID | Rule | Verdict |
|----|------|---------|
| 1.6.1 | FAIL if test files are mixed with source files in the same directory | PASS/FAIL |
| 1.6.2 | WARN if more than 2 source files lack corresponding test files | PASS/WARN |
| 1.6.3 | WARN if factories are defined inline in test files instead of a shared `factories.py` | PASS/WARN |
| 1.6.4 | FAIL if no `conftest.py` exists at project level or app level | PASS/FAIL |
| 1.6.5 | FAIL if test files exist outside designated test directories | PASS/FAIL |

## 1.7 Documentation Files

| ID | Rule | Verdict |
|----|------|---------|
| 1.7.1 | FAIL if root README.md is missing or contains only a placeholder | PASS/FAIL |
| 1.7.2 | WARN if no CHANGELOG.md exists | PASS/WARN |
| 1.7.3 | INFO if no CONTRIBUTING.md — only relevant for multi-contributor projects | PASS/INFO |
| 1.7.4 | WARN if no `docs/` directory exists for documentation beyond the README | PASS/WARN |
| 1.7.5 | FAIL if no LICENSE file is present in a public or shared repository | PASS/FAIL |
| 1.7.6 | FAIL if no `.env.example` exists or if it's missing variables used in settings | PASS/FAIL |

## 1.8 Dependency Files

| ID | Rule | Verdict |
|----|------|---------|
| 1.8.1 | FAIL if all dependencies are in a single requirements.txt with no environment separation | PASS/FAIL |
| 1.8.2 | FAIL if conflicting dependency managers exist (e.g. both requirements.txt and Pipfile defining overlapping deps) | PASS/FAIL |
| 1.8.3 | WARN if using Docker but Dockerfile or docker-compose files are missing | PASS/WARN |
| 1.8.4 | INFO if no .pre-commit-config.yaml — recommended but not required | PASS/INFO |
| 1.8.5 | INFO if no CI configuration — recommended for any shared project | PASS/INFO |

## 1.9 Layered Architecture

| ID | Rule | Verdict |
|----|------|---------|
| 1.9.1 | FAIL if a domain app is missing more than 2 expected layer files without documented reason | PASS/FAIL |
| 1.9.2 | PASS if missing layers are intentional (e.g. no services in a read-only search app) | PASS |
| 1.9.3 | FAIL if layer files exist but are empty (0 functions/classes) | PASS/FAIL |

## 1.10 Core/Shared App

| ID | Rule | Verdict |
|----|------|---------|
| 1.10.1 | FAIL if no core/common app exists and shared utilities are scattered across 3+ apps | PASS/FAIL |
| 1.10.2 | FAIL if core app defines more than 5 concrete (non-abstract) database models | PASS/FAIL |
| 1.10.3 | WARN if shared utilities (base models, exceptions, mixins) are duplicated across apps | PASS/WARN |
| 1.10.4 | WARN if core app is a flat directory with 10+ files instead of organized sub-packages | PASS/WARN |

## 1.11 apps.py Correctness

| ID | Rule | Verdict |
|----|------|---------|
| 1.11.1 | FAIL if any app's `AppConfig.name` doesn't match its import path (e.g. `name = "users"` when path is `apps.users`) | PASS/FAIL |
| 1.11.2 | WARN if `default_auto_field` is inconsistent across apps | PASS/WARN |
| 1.11.3 | WARN if `ready()` is missing in apps that register signals or handlers | PASS/WARN |
| 1.11.4 | FAIL if two apps have the same `label` causing Django startup errors | PASS/FAIL |

## 1.12 API URL Versioning

| ID | Rule | Verdict |
|----|------|---------|
| 1.12.1 | FAIL if endpoints mix versioned and unversioned paths (e.g. `/api/v1/users/` alongside `/api/users/`) | PASS/FAIL |
| 1.12.2 | WARN if version prefix is hardcoded in app-level urls.py instead of applied once in root urls.py | PASS/WARN |
| 1.12.3 | WARN if any API endpoint is exposed without a version prefix | PASS/WARN |

## 1.13 Migration Health

| ID | Rule | Verdict |
|----|------|---------|
| 1.13.1 | FAIL if any app has two migration files with the same number (conflict) | PASS/FAIL |
| 1.13.2 | WARN if there are gaps in migration numbering sequence | PASS/WARN |
| 1.13.3 | WARN if data/seed migrations lack a docstring or comment explaining their purpose | PASS/WARN |
| 1.13.4 | WARN if `makemigrations` generates new migrations (indicates unapplied model changes) | PASS/WARN |

## 1.14 __init__.py Completeness

| ID | Rule | Verdict |
|----|------|---------|
| 1.14.1 | FAIL if any Python package directory (containing .py files and imported elsewhere) is missing `__init__.py` | PASS/FAIL |

## 1.15 .env.example Completeness

| ID | Rule | Verdict |
|----|------|---------|
| 1.15.1 | FAIL if settings reference an env var via `os.environ` or `os.getenv` that isn't in any `.env.example` | PASS/FAIL |
| 1.15.2 | WARN if dev and production use different env vars but only one `.env.example` exists | PASS/WARN |
| 1.15.3 | FAIL if `.env.example` contains real secrets or credentials | PASS/FAIL |

## 1.16 Stale/Dead Apps

| ID | Rule | Verdict |
|----|------|---------|
| 1.16.1 | FAIL if any app in INSTALLED_APPS has no models, no views, and no management commands | PASS/FAIL |
| 1.16.2 | WARN if an app exists in the `apps/` directory but is not in INSTALLED_APPS | PASS/WARN |
| 1.16.3 | WARN if an app's migrations directory exists but contains only `__init__.py` and `0001_initial.py` with empty operations | PASS/WARN |
