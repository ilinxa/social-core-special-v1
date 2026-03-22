# 02 — Configuration & Environment Management Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 2.1 Secret Management

| ID | Rule | Verdict |
|----|------|---------|
| 2.1.1 | FAIL if `grep -rn` finds any string matching API key, password, token, or DSN patterns in `.py`, `.yml`, or `.json` files (excluding `.env.example`, tests with dummy values) | PASS/FAIL |
| 2.1.2 | FAIL if any comment contains a real credential, even a "old" or "example" one | PASS/FAIL |
| 2.1.3 | INFO if no secret scanning tool is configured — recommended but not blocking | PASS/INFO |
| 2.1.4 | FAIL if `git log --all -- '*.env' ':!*.env.example' ':!*.env.dev.example'` returns any commits | PASS/FAIL |
| 2.1.5 | WARN if `docker-compose.yml` contains inline credentials instead of `env_file:` or `${VAR}` syntax | PASS/WARN |
| 2.1.6 | FAIL if any migration or fixture file contains database passwords or API keys | PASS/FAIL |
| 2.1.7 | INFO if no CI/CD exists yet — rule applies when CI is added | PASS/INFO |
| 2.1.8 | FAIL if any third-party service key is hardcoded in source (not behind `os.environ` / `os.getenv`) | PASS/FAIL |

## 2.2 `.env` & `.env.example`

| ID | Rule | Verdict |
|----|------|---------|
| 2.2.1 | FAIL if no `.env.example` exists at root or backend level | PASS/FAIL |
| 2.2.2 | FAIL if any `os.environ`/`os.getenv` key in settings is missing from all `.env.example` files | PASS/FAIL |
| 2.2.3 | FAIL if `.env.example` contains a real secret (actual API key, real password, valid token) | PASS/FAIL |
| 2.2.4 | WARN if `.env.example` has no inline comments for non-obvious variables | PASS/WARN |
| 2.2.5 | WARN if `.env.example` has keys not used anywhere in settings (stale entries) | PASS/WARN |
| 2.2.6 | WARN if variables are not grouped by section (e.g. all DB vars together) | PASS/WARN |
| 2.2.7 | INFO if no automated `.env` vs `.env.example` sync check exists — recommended | PASS/INFO |

## 2.3 Settings Architecture

| ID | Rule | Verdict |
|----|------|---------|
| 2.3.1 | FAIL if all settings are in a single `settings.py` with no environment separation | PASS/FAIL |
| 2.3.2 | FAIL if fewer than 3 settings files exist (base + at least dev + prod) | PASS/FAIL |
| 2.3.3 | FAIL if any environment file duplicates more than 20% of `base.py` content | PASS/FAIL |
| 2.3.4 | WARN if `base.py` contains environment-specific values (e.g. `DEBUG = True`) without env override | PASS/WARN |
| 2.3.5 | WARN if `debug_toolbar` or `django_extensions` appear in `base.py` INSTALLED_APPS | PASS/WARN |
| 2.3.6 | FAIL if `production.py` has `DEBUG = True` or relies on env var for DEBUG without a safe default of False | PASS/FAIL |
| 2.3.7 | FAIL if `ALLOWED_HOSTS = ['*']` in production settings | PASS/FAIL |
| 2.3.8 | WARN if dev-only apps are in `base.py` INSTALLED_APPS instead of dev settings only | PASS/WARN |
| 2.3.9 | WARN if `DJANGO_SETTINGS_MODULE` usage is not documented in README or Makefile | PASS/WARN |

## 2.4 Environment Variable Parsing

| ID | Rule | Verdict |
|----|------|---------|
| 2.4.1 | WARN if no dedicated env parsing library is used and all vars use raw `os.environ`/`os.getenv` — acceptable if done consistently with explicit casting | PASS/WARN |
| 2.4.2 | WARN if more than 5 raw `os.environ.get()` calls exist with no type casting | PASS/WARN |
| 2.4.3 | FAIL if any env var is used as a string when it should be int/bool (e.g. `if os.getenv('DEBUG')` truthy check) | PASS/FAIL |
| 2.4.4 | FAIL if boolean env vars are compared as strings incorrectly (e.g. `== 'true'` case-sensitive) | PASS/FAIL |
| 2.4.5 | WARN if list env vars are not split into actual lists (e.g. `ALLOWED_HOSTS` left as comma string) | PASS/WARN |
| 2.4.6 | FAIL if any required env var defaults to `None` and is used without null check, causing runtime crash | PASS/FAIL |
| 2.4.7 | WARN if required production env vars have defaults that mask missing config (e.g. `SECRET_KEY` default) | PASS/WARN |
| 2.4.8 | INFO if DATABASE_URL pattern is not used — individual vars are acceptable if consistent | PASS/INFO |

## 2.5 Database Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 2.5.1 | PASS if database config is driven by env vars (either URL or individual vars) | PASS/FAIL |
| 2.5.2 | INFO — individual DB vars vs URL is a style choice, not a defect | PASS/INFO |
| 2.5.3 | WARN if `CONN_MAX_AGE` is not set in production settings | PASS/WARN |
| 2.5.4 | WARN if `CONN_MAX_AGE = 0` in production (no connection reuse) | PASS/WARN |
| 2.5.5 | PASS if test database uses SQLite or auto-created test DB — not the dev database | PASS/FAIL |
| 2.5.6 | INFO if `ATOMIC_REQUESTS` is not set — document the choice | PASS/INFO |
| 2.5.7 | INFO — read replicas only relevant if the project uses them | PASS/INFO |

## 2.6 Cache Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 2.6.1 | FAIL if production uses `DummyCache` or `LocMemCache` backend | PASS/FAIL |
| 2.6.2 | WARN if Redis cache host/port is hardcoded instead of using `REDIS_URL` env var | PASS/WARN |
| 2.6.3 | WARN if no cache key prefix is set (risk of cross-environment collisions) | PASS/WARN |
| 2.6.4 | WARN if no explicit `TIMEOUT` is set on the default cache (Django defaults to 300s) | PASS/WARN |
| 2.6.5 | WARN if sessions use cache backend but share the same Redis DB as general cache | PASS/WARN |
| 2.6.6 | INFO if no cache version/namespace strategy exists — recommended for zero-downtime deploys | PASS/INFO |

## 2.7 Email Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 2.7.1 | FAIL if production uses `console` or `filebased` email backend | PASS/FAIL |
| 2.7.2 | WARN if `DEFAULT_FROM_EMAIL` is left as Django's default `webmaster@localhost` in any env file | PASS/WARN |
| 2.7.3 | FAIL if email credentials are hardcoded in settings (not env vars) | PASS/FAIL |
| 2.7.4 | WARN if staging has no safe email backend configured (risk of real sends) | PASS/WARN |
| 2.7.5 | INFO if `ADMINS`/`MANAGERS` is not set — only needed if using Django's admin email feature | PASS/INFO |

## 2.8 Static & Media Files

| ID | Rule | Verdict |
|----|------|---------|
| 2.8.1 | FAIL if `STATIC_ROOT` or `MEDIA_ROOT` is not set in production | PASS/FAIL |
| 2.8.2 | FAIL if `STATICFILES_DIRS` contains the same path as `STATIC_ROOT` | PASS/FAIL |
| 2.8.3 | FAIL if production serves static files via Django's dev server (`django.views.static.serve`) | PASS/FAIL |
| 2.8.4 | WARN if no explicit storage backend is set for production (no WhiteNoise, S3, or CDN) | PASS/WARN |
| 2.8.5 | WARN if media uploads go to a flat directory (e.g. `uploads/`) without structured subdirectories | PASS/WARN |
| 2.8.6 | WARN if no `FILE_UPLOAD_MAX_MEMORY_SIZE` or `DATA_UPLOAD_MAX_MEMORY_SIZE` is configured | PASS/WARN |

## 2.9 Security Settings

| ID | Rule | Verdict |
|----|------|---------|
| 2.9.1 | FAIL if `SECRET_KEY` is shorter than 50 characters or is the Django default | PASS/FAIL |
| 2.9.2 | FAIL if the same `SECRET_KEY` value appears in multiple environment configs | PASS/FAIL |
| 2.9.3 | FAIL if `DEBUG = True` in production.py (even conditionally via env var without False default) | PASS/FAIL |
| 2.9.4 | FAIL if `SECURE_SSL_REDIRECT` is not True in production | PASS/FAIL |
| 2.9.5 | FAIL if `SESSION_COOKIE_SECURE` is not True in production | PASS/FAIL |
| 2.9.6 | FAIL if `CSRF_COOKIE_SECURE` is not True in production | PASS/FAIL |
| 2.9.7 | WARN if `SECURE_HSTS_SECONDS` is not set or < 3600 in production | PASS/WARN |
| 2.9.8 | WARN if `SECURE_HSTS_INCLUDE_SUBDOMAINS` is not True in production | PASS/WARN |
| 2.9.9 | WARN if `X_FRAME_OPTIONS` is not set to `'DENY'` or `'SAMEORIGIN'` | PASS/WARN |
| 2.9.10 | WARN if `SECURE_CONTENT_TYPE_NOSNIFF` is not True | PASS/WARN |

## 2.10 Celery & Background Tasks

| ID | Rule | Verdict |
|----|------|---------|
| 2.10.1 | FAIL if `CELERY_BROKER_URL` is hardcoded in settings (not from env var) | PASS/FAIL |
| 2.10.2 | WARN if `CELERY_RESULT_BACKEND` is not explicitly configured | PASS/WARN |
| 2.10.3 | FAIL if `CELERY_TASK_SERIALIZER` is set to `'pickle'` in any environment | PASS/FAIL |
| 2.10.4 | FAIL if `CELERY_TASK_ALWAYS_EAGER = True` in production settings | PASS/FAIL |
| 2.10.5 | WARN if Celery timezone doesn't match `TIME_ZONE` setting | PASS/WARN |
| 2.10.6 | PASS if beat schedule is defined in settings or celery.py | PASS/FAIL |
| 2.10.7 | WARN if no global task time limits (`CELERY_TASK_SOFT_TIME_LIMIT`, `CELERY_TASK_TIME_LIMIT`) are set | PASS/WARN |

## 2.11 Logging Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 2.11.1 | FAIL if logging is configured via `logging.basicConfig()` in production code instead of Django `LOGGING` dict | PASS/FAIL |
| 2.11.2 | WARN if log level is the same across all environments (no DEBUG→INFO/WARNING progression) | PASS/WARN |
| 2.11.3 | WARN if production logs are plain text instead of structured JSON | PASS/WARN |
| 2.11.4 | WARN if no request_id/correlation_id is present in log records | PASS/WARN |
| 2.11.5 | FAIL if passwords, tokens, or PII appear in log output (check log formatters for sensitive field filtering) | PASS/FAIL |
| 2.11.6 | WARN if `django.security` or `django.request` loggers are not configured | PASS/WARN |
| 2.11.7 | WARN if production logs to files instead of stdout/stderr (incompatible with container orchestration) | PASS/WARN |

## 2.12 Third-Party Services

| ID | Rule | Verdict |
|----|------|---------|
| 2.12.1 | FAIL if any third-party SDK is initialized with hardcoded credentials in source code | PASS/FAIL |
| 2.12.2 | WARN if Sentry DSN is configured in local dev settings | PASS/WARN |
| 2.12.3 | WARN if Sentry environment tag is not set or is hardcoded | PASS/WARN |
| 2.12.4 | FAIL if AWS credentials are hardcoded instead of using env vars or IAM roles | PASS/FAIL |
| 2.12.5 | FAIL if any SDK `init()` call contains a literal API key string | PASS/FAIL |

## 2.13 Startup Validation

| ID | Rule | Verdict |
|----|------|---------|
| 2.13.1 | WARN if no startup validation exists for required env vars | PASS/WARN |
| 2.13.2 | INFO if `manage.py check --deploy` is not run in CI — recommended | PASS/INFO |
| 2.13.3 | WARN if no health/readiness endpoint exists for container orchestration | PASS/WARN |
| 2.13.4 | FAIL if missing critical config (DB, SECRET_KEY) causes a silent failure instead of immediate crash | PASS/FAIL |
| 2.13.5 | WARN if startup error messages don't identify which specific env var is missing | PASS/WARN |

## 2.14 CORS Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 2.14.1 | FAIL if `CORS_ALLOW_ALL_ORIGINS = True` in production settings | PASS/FAIL |
| 2.14.2 | WARN if CORS allowed origins are hardcoded instead of env-driven | PASS/WARN |
| 2.14.3 | WARN if `CORS_ALLOW_CREDENTIALS = True` with `CORS_ALLOW_ALL_ORIGINS = True` (security risk) | PASS/WARN |

## 2.15 Time Zone & Internationalization

| ID | Rule | Verdict |
|----|------|---------|
| 2.15.1 | WARN if `TIME_ZONE` is left as default `'America/Chicago'` without deliberate choice | PASS/WARN |
| 2.15.2 | FAIL if `USE_TZ = False` in any environment (timezone-naive datetimes cause bugs) | PASS/FAIL |
| 2.15.3 | INFO if `LANGUAGE_CODE` and `USE_I18N` are default — only relevant if i18n is planned | PASS/INFO |
