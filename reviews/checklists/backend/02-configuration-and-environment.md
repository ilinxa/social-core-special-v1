# 02 — Configuration & Environment Management Checklist

## 2.1 Secret Management

- [ ] Zero hardcoded secrets in any file — no API keys, passwords, tokens, DSNs in source code
- [ ] Zero hardcoded secrets in comments — no "old password was X" style comments
- [ ] Secret scanning tool configured (`detect-secrets`, `gitleaks`, or `trufflehog`) in pre-commit or CI
- [ ] `.env` file is in `.gitignore` and has never been committed (verify via `git log -- .env`)
- [ ] No secrets embedded in `docker-compose.yml` directly — uses `env_file` or external secret store
- [ ] Database credentials are not in any migration file or fixture
- [ ] No secrets in CI/CD pipeline YAML files — uses encrypted secret variables
- [ ] Third-party service keys (Stripe, AWS, SendGrid, etc.) are all env-driven

## 2.2 `.env` & `.env.example`

- [ ] `.env.example` exists at root level and is always committed
- [ ] `.env.example` contains every variable the app needs — nothing missing
- [ ] `.env.example` uses placeholder values, not real values (`SECRET_KEY=your-secret-key-here`)
- [ ] `.env.example` has inline comments explaining non-obvious variables
- [ ] `.env.example` is kept in sync with the actual `.env` — no stale or missing keys
- [ ] Variables in `.env.example` are grouped logically (Django, Database, Redis, Email, etc.)
- [ ] A validation step or script exists to compare `.env` against `.env.example` on startup or in CI

## 2.3 Settings Architecture

- [ ] Settings are never a single flat `settings.py` for a production-grade project
- [ ] Settings are split into: `base.py` → `development.py` → `staging.py` → `production.py`
- [ ] Each environment file only overrides what differs — no full copy-paste between files
- [ ] `base.py` contains only settings that are truly shared across all environments
- [ ] `development.py` enables debug tools (`django-debug-toolbar`, verbose logging) absent in `production.py`
- [ ] `production.py` has `DEBUG = False` hardcoded — never relies on env var for this
- [ ] `ALLOWED_HOSTS` is explicitly set per environment — no `['*']` in staging or production
- [ ] `INSTALLED_APPS` dev-only apps (`debug_toolbar`, `django_extensions`) are only in `development.py`
- [ ] `DJANGO_SETTINGS_MODULE` is set correctly per environment — documented in README

## 2.4 Environment Variable Parsing

- [ ] A dedicated library handles env var parsing — `django-environ`, `python-decouple`, or `pydantic-settings`
- [ ] No raw `os.environ.get()` calls scattered across settings files — all go through the parsing library
- [ ] All env vars have explicit types defined (`int`, `bool`, `list`) — no implicit string casting
- [ ] Boolean env vars are parsed correctly (`True`/`False` strings → Python bools)
- [ ] List env vars (e.g. `ALLOWED_HOSTS`, `CORS_ORIGINS`) are parsed as actual lists
- [ ] All env vars have safe defaults for local development — no `None` defaults that silently break
- [ ] Required env vars (no default) raise a clear error on startup if missing — fail fast
- [ ] URL-type vars (database, Redis, broker) are parsed via URL scheme (`DATABASE_URL`, `REDIS_URL`)

## 2.5 Database Configuration

- [ ] `DATABASE_URL` or equivalent is the single source of database configuration
- [ ] No database credentials split across multiple separate env vars when a URL string is cleaner
- [ ] Connection pooling is configured (`CONN_MAX_AGE` set, or pgBouncer in use)
- [ ] `CONN_MAX_AGE` is not set to `0` in production (defeats connection reuse)
- [ ] Test database is separate and auto-created — not the same as development DB
- [ ] `ATOMIC_REQUESTS = True` is considered and deliberately set or unset with documented reason
- [ ] Read replicas (if any) are configured as a secondary database, not mixed into the default

## 2.6 Cache Configuration

- [ ] Cache backend is explicitly configured — no reliance on Django's default in-memory cache in production
- [ ] `REDIS_URL` or `CACHE_URL` drives cache config — not hardcoded host/port
- [ ] Cache key prefix is set per environment to prevent dev/staging/prod key collisions
- [ ] Cache timeout defaults are explicitly set — no invisible `None` (infinite) timeouts
- [ ] Session backend (if Redis-based) is configured separately from the default cache
- [ ] Cache version or namespace strategy exists for safe cache invalidation on deploy

## 2.7 Email Configuration

- [ ] Email backend differs per environment: `console` or `filebased` in dev, real SMTP/SES in prod
- [ ] `DEFAULT_FROM_EMAIL` and `SERVER_EMAIL` are set explicitly — not left as Django defaults
- [ ] Email credentials (`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`) come from env vars
- [ ] A staging environment uses a safe email backend to prevent accidental real sends
- [ ] `ADMINS` and `MANAGERS` are set in production for Django error emails (if used)

## 2.8 Static & Media Files Configuration

- [ ] `STATIC_ROOT` and `MEDIA_ROOT` are configured and point to correct directories
- [ ] `STATICFILES_DIRS` is only for source static files — not confused with `STATIC_ROOT`
- [ ] In production, static files are served via CDN/S3/WhiteNoise — not Django's dev server
- [ ] `DEFAULT_FILE_STORAGE` and `STATICFILES_STORAGE` backends are explicitly set for production
- [ ] Media file upload path uses a callable or structured pattern — not flat root uploads
- [ ] File size limits are configured for uploads — no unbounded file acceptance

## 2.9 Security Settings

- [ ] `SECRET_KEY` is long (50+ chars), random, and unique per environment
- [ ] `SECRET_KEY` is never the Django default or a placeholder in any non-local environment
- [ ] `DEBUG = False` is enforced in staging and production — CI verifies this
- [ ] `SECURE_SSL_REDIRECT = True` in production
- [ ] `SESSION_COOKIE_SECURE = True` in production
- [ ] `CSRF_COOKIE_SECURE = True` in production
- [ ] `SECURE_HSTS_SECONDS` is set to a reasonable value (e.g. `31536000`) in production
- [ ] `SECURE_HSTS_INCLUDE_SUBDOMAINS = True` in production
- [ ] `X_FRAME_OPTIONS = 'DENY'` is set
- [ ] `SECURE_CONTENT_TYPE_NOSNIFF = True` is set

## 2.10 Celery & Background Task Configuration

- [ ] `CELERY_BROKER_URL` comes from env var — not hardcoded
- [ ] `CELERY_RESULT_BACKEND` is explicitly configured — not left as default
- [ ] Celery task serializer is set to `'json'` — not `'pickle'` (security risk)
- [ ] `CELERY_TASK_ALWAYS_EAGER = True` is only in test settings — never in production
- [ ] Celery timezone matches Django's `TIME_ZONE` setting
- [ ] Beat schedule (if used) is defined in settings or a dedicated file
- [ ] Task soft and hard time limits are configured globally with per-task overrides where needed

## 2.11 Logging Configuration

- [ ] Logging is configured in settings via `LOGGING` dict — not via `basicConfig()` calls in code
- [ ] Log level differs per environment: `DEBUG` locally, `INFO` or `WARNING` in production
- [ ] Production logging outputs structured JSON — not plain text
- [ ] A `request_id` or `correlation_id` is injected into every log record
- [ ] Sensitive data (passwords, tokens, PII) is explicitly filtered from log output
- [ ] Django's default `django.security` and `django.request` loggers are configured
- [ ] Log output goes to `stdout`/`stderr` in containerized environments — not to files

## 2.12 Third-Party Service Configuration

- [ ] All third-party SDK configurations (Sentry, AWS, Stripe, etc.) are driven by env vars
- [ ] Sentry DSN is set only in staging and production — not in local dev
- [ ] Sentry environment tag (`SENTRY_ENVIRONMENT`) is set correctly per environment
- [ ] AWS region, bucket names, and credentials all come from env vars
- [ ] No SDK is initialized with hardcoded credentials anywhere in the codebase

## 2.13 Startup Validation

- [ ] App performs a startup check that all required env vars are present and valid
- [ ] Django system checks (`python manage.py check --deploy`) pass cleanly in CI
- [ ] A `ReadinessCheck` or health endpoint verifies DB, cache, and broker connectivity on startup
- [ ] Missing or malformed critical config causes an immediate loud failure — not silent degraded state
- [ ] Env var validation errors produce human-readable messages identifying exactly which variable is wrong

## 2.14 CORS Configuration

- [ ] `CORS_ALLOW_ALL_ORIGINS` is not `True` in production — only specific origins allowed
- [ ] CORS allowed origins are driven by env vars, not hardcoded domain lists
- [ ] `CORS_ALLOW_CREDENTIALS = True` is not combined with `CORS_ALLOW_ALL_ORIGINS = True`

## 2.15 Time Zone & Internationalization

- [ ] `TIME_ZONE` is set deliberately — not left as Django's default `'America/Chicago'`
- [ ] `USE_TZ = True` in all environments — timezone-naive datetimes cause production bugs
- [ ] `LANGUAGE_CODE` and `USE_I18N` are set appropriately if internationalization is planned
