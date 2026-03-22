# 01 — Project Structure & Organization Checklist

## 1.1 Directory Layout

- [ ] Top-level directories are immediately understandable (apps/, config/, tests/, docs/, scripts/)
- [ ] No business logic files at root level
- [ ] Static assets, media, and templates are in dedicated directories
- [ ] Scripts (management commands, seed data) have their own folder
- [ ] No temporary or experimental files committed (temp_, test2.py, old_views.py)
- [ ] .gitignore is comprehensive and matches the stack (Python, Django, env files, IDE files)

## 1.2 Django App Granularity

- [ ] Each app encapsulates one domain concept (e.g. users, billing, notifications)
- [ ] No "god app" that owns half the system (e.g. core/ with 20+ models)
- [ ] Apps are independently importable — no circular dependencies between apps
- [ ] App names are nouns, not verbs or adjectives
- [ ] Each app has the standard Django structure (models.py, views.py, serializers.py, urls.py, admin.py, apps.py)
- [ ] Large apps are split into sub-modules (e.g. models/ directory with __init__.py) rather than one 800+ line file
- [ ] No domain logic living outside of an app (e.g. no utils.py at root doing business work)

## 1.3 Configuration Structure

- [ ] Settings are split by environment: base.py, development.py, staging.py, production.py
- [ ] DJANGO_SETTINGS_MODULE is set per environment, not hardcoded
- [ ] A single config/ or settings/ directory holds all configuration
- [ ] urls.py root file only routes to app-level urls.py files — no inline view definitions
- [ ] wsgi.py and asgi.py are present, clean, and correctly point to settings
- [ ] celery.py (if used) is at the project config level, not inside an app

## 1.4 Entry Points

- [ ] manage.py is at the root, unmodified from Django's default
- [ ] One clear application entry point — no ambiguity about how to start the server
- [ ] Makefile or justfile present with standard commands (make run, make test, make migrate)
- [ ] Procfile or equivalent is present if deploying to a platform
- [ ] pyproject.toml or setup.cfg defines project metadata if it's a package

## 1.5 Naming Conventions

- [ ] All directory and file names use snake_case
- [ ] App directory names are singular or plural consistently (pick one, stick to it)
- [ ] No abbreviations in directory/file names
- [ ] Test files mirror the source structure (test_views.py maps to views.py)
- [ ] Migration files are unmodified from auto-generated names
- [ ] Management command files are named clearly after what they do

## 1.6 Test Structure

- [ ] Tests live in a dedicated top-level tests/ directory or inside each app — not mixed
- [ ] Test directory mirrors the app structure (one test file per source file)
- [ ] Fixtures and factories are in a dedicated fixtures/ or factories/ directory
- [ ] conftest.py is present at the appropriate level with shared fixtures
- [ ] No test files outside the designated test directories

## 1.7 Documentation Files

- [ ] README.md exists at root level with real content (not a placeholder)
- [ ] CHANGELOG.md is present and maintained
- [ ] CONTRIBUTING.md exists if the project has multiple contributors
- [ ] docs/ directory exists for anything beyond the README
- [ ] LICENSE file is present
- [ ] .env.example is at root level and complete

## 1.8 Dependency Files

- [ ] requirements/ directory with split files (base.txt, dev.txt, prod.txt) or pyproject.toml with groups
- [ ] No duplicate or conflicting requirement files at root level
- [ ] Dockerfile and docker-compose.yml are at root level
- [ ] .pre-commit-config.yaml is present if pre-commit hooks are used
- [ ] CI configuration (.github/workflows/, .gitlab-ci.yml) is in its designated directory

## 1.9 Layered Architecture Files

- [ ] Each domain app has the expected layer files (models, selectors, services, policies, serializers, views)
- [ ] Missing layers are intentional (e.g. explore has no services because it's read-only)
- [ ] Layer files that exist are non-empty and contain relevant logic

## 1.10 Core/Shared App

- [ ] A core or common app exists for shared base classes, mixins, exceptions, utilities
- [ ] Core app has zero domain models (only abstract base models)
- [ ] Shared utilities are in core, not scattered across random apps
- [ ] Core sub-packages are well-organized (not a flat dump of files)

## 1.11 apps.py Correctness

- [ ] Each app's AppConfig has the correct dotted `name` path (e.g. `apps.users`)
- [ ] `default_auto_field` is set consistently across all apps
- [ ] `ready()` method is used where needed (signals, handlers registration)
- [ ] No conflicting app labels

## 1.12 API URL Versioning

- [ ] All endpoints follow a consistent versioning scheme (e.g. /api/v1/)
- [ ] Version prefix is applied in root urls.py, not repeated in app urls.py
- [ ] No unversioned endpoints exposed

## 1.13 Migration Health

- [ ] No conflicting migrations (two migrations with the same number in one app)
- [ ] No gaps in migration numbering
- [ ] Seed/data migrations are clearly named and documented
- [ ] No stale or orphaned migrations

## 1.14 __init__.py Completeness

- [ ] Every Python package directory has a proper __init__.py
- [ ] No missing __init__.py causing silent import failures

## 1.15 .env.example Completeness

- [ ] All environment variables used in settings are documented in .env.example
- [ ] Separate examples exist for dev and production if configurations differ significantly
- [ ] No real secrets in example files

## 1.16 Stale/Dead Apps

- [ ] No registered apps that are empty or unused
- [ ] All apps in INSTALLED_APPS have models, views, or provide functionality
- [ ] No skeleton apps left from abandoned features
