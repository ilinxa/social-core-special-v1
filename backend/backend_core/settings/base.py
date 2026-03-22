import os
from pathlib import Path

# =============================================================================
# LOAD ENVIRONMENT VARIABLES FROM .env FILE
# =============================================================================
# This MUST be at the top before any os.getenv() calls
# python-dotenv reads .env files and loads them into os.environ
# =============================================================================
from dotenv import load_dotenv

# Path to backend directory: backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR points to backend_core/ for template paths, etc.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env.dev first (for development) - takes priority
dev_dotenv_path = BACKEND_DIR / ".env.dev"
if dev_dotenv_path.exists():
    load_dotenv(dev_dotenv_path, override=False)

# Then load .env (for production or additional vars)
dotenv_path = BACKEND_DIR / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path, override=False)

# Also try to load from project root (django_base_v1/.env)
root_dotenv_path = BACKEND_DIR.parent / ".env"
if root_dotenv_path.exists():
    load_dotenv(root_dotenv_path, override=False)

# ============================================
# SECRET KEY CONFIGURATION
# ============================================
# Dev-safe defaults: These values are intentionally set for local development.
# Production settings (production.py) override all of these via environment variables.
# The insecure prefix below triggers a startup error in production.py if left unchanged.
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-CHANGE-THIS-IN-PRODUCTION-4bil&5)m#3(5ac@a-n@thoa3inoq$&9(+7jp6(7ghfa45y3upf",
)

# SECURITY WARNING: don't run with debug turned on in production!

ALLOWED_HOSTS = []


# ===========================================
# CUSTOM USER MODEL - CRITICAL: Must be set BEFORE any migrations
# ===========================================
AUTH_USER_MODEL = "users.User"

# Application definition

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # Third-party
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "channels",
    # Django Celery Beat for periodic tasks
    "django_celery_beat",
    # ===========================================
    # Local Apps
    # ===========================================
    # Core infrastructure (base models, exceptions, utilities)
    "apps.core",
    # User identity and profiles
    "apps.users",
    # Email infrastructure (templates, sending, tracking)
    "apps.email",
    # Notifications (multi-channel routing, preferences)
    "apps.notifications",
    # Authentication (JWT, OAuth, sessions)
    "apps.auth",
    # Organization (platform, business accounts)
    "apps.organization",
    # RBAC (roles, permissions, memberships)
    "apps.rbac",
    # Transaction system (invitations, requests, approvals)
    "apps.transaction",
    # Form Builder (dynamic forms, responses, indexing)
    "apps.forms",
    # CMS (content management, pages, templates, media)
    "apps.cms",
    # Explore (search and discovery)
    "apps.explore",
    # Network (follows, connections)
    "apps.network",
    # Chat (conversations, messages, real-time)
    "apps.chat",
]

MIDDLEWARE = [
    # === SECURITY & INFRASTRUCTURE ===
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    # === AUTHENTICATION (must be before observability) ===
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # === CMS API Key Authentication (after auth, before observability) ===
    "apps.cms.middleware.CMSApiKeyMiddleware",
    # === OBSERVABILITY (after auth, captures user_id) ===
    "apps.core.observability.logging.middleware.RequestLoggingMiddleware",
    # === LATE PROCESSING ===
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # === CACHE HEADERS (last: sets Cache-Control on API responses) ===
    "apps.core.middleware.CacheControlMiddleware",
]

ROOT_URLCONF = "backend_core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend_core.wsgi.application"
ASGI_APPLICATION = "backend_core.asgi.application"

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Password hashing algorithms (Argon2 preferred, PBKDF2 as fallback for existing hashes)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]


# Internationalization


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

REST_FRAMEWORK = {
    # Renderer classes
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",  # output format will be JSON
        # "rest_framework.renderers.BrowsableAPIRenderer"
    ],
    # Parser classes (JSON only by default — file upload views set their own parsers)
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    # Test client default format (matches parser restriction)
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    # Authentication classes
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.auth.authentication.JWTAuthentication",
    ],
    # Permission classes
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Pagination (custom class from core app)
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    # Versioning (configured for future v2 routes - currently URLs use hardcoded api/v1/ prefix)
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    # Schema generation
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",  # ← Critical
    # Throttling (can be overridden in specific views)
    # Limits request rates (anti-abuse / anti-DDoS)
    #
    # How it works:
    #   - AnonRateThrottle: Uses IP address to identify anonymous users
    #   - UserRateThrottle: Uses user ID for authenticated users
    #   - ScopedRateThrottle: Per-view throttling using 'throttle_scope' attribute
    #
    # Usage in views:
    #   class MyView(APIView):
    #       throttle_scope = 'burst'  # Uses 'burst' rate from THROTTLE_RATES
    #
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",  # Anonymous users (global)
        "user": "1000/hour",  # Authenticated users (global)
        "burst": "60/minute",  # For views with throttle_scope='burst'
        "login": "5/minute",  # For login endpoints
        "password_reset": "3/hour",  # For password reset endpoints
        "verification": "5/minute",  # For email verification code attempts
        "refresh": "30/minute",  # For token refresh endpoint
    },
    # Exception handler
    # Defines how exceptions are converted into HTTP responses (Python => HTTP)
    # Uses custom handler to convert DomainException hierarchy to consistent responses
    "EXCEPTION_HANDLER": "apps.core.exceptions.handler.exception_handler",
}

# Static files (CSS, JavaScript, Images)

SPECTACULAR_SETTINGS = {
    "TITLE": "Django Backend API",
    "DESCRIPTION": """
## Overview

A production-ready Django REST Framework backend with comprehensive authentication,
notification system, and WebSocket support.

## Authentication

This API uses JWT (JSON Web Token) authentication:

1. **Login** (`POST /api/v1/auth/login/`) to obtain access and refresh tokens
2. Include the access token in requests: `Authorization: Bearer <token>`
3. **Refresh** (`POST /api/v1/auth/refresh/`) when the access token expires

### Token Handling

- **Web clients**: Refresh token is stored in an HttpOnly cookie (automatic)
- **Mobile clients**: Set `X-Client-Type: mobile` header to receive refresh token in response body

### Token Lifetimes

- Access token: 15 minutes
- Refresh token: 7 days (single use, rotates on each refresh)

## Rate Limiting

- Anonymous: 100 requests/hour
- Authenticated: 1000 requests/hour
- Login: 5 attempts/minute
- Password reset: 3 requests/hour
    """,
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Contact information
    "CONTACT": {
        "name": "API Support",
        "email": "support@example.com",
    },
    # License
    "LICENSE": {
        "name": "Proprietary",
    },
    # Security schemes
    "SECURITY": [{"BearerAuth": []}],
    # Component settings
    "COMPONENT_SPLIT_REQUEST": True,
    "COMPONENT_SPLIT_PATCH": True,
    # Schema path prefix for versioned APIs
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
    # Sort operations alphabetically within tags
    "SORT_OPERATIONS": True,
    # Tag ordering
    "TAGS": [
        {"name": "Authentication", "description": "Login, logout, token management"},
        {"name": "Email Verification", "description": "Email verification flows"},
        {"name": "Password Management", "description": "Password reset and change"},
        {"name": "Session Management", "description": "Device session management"},
        {"name": "OAuth", "description": "Social login (Google, Apple)"},
        {"name": "User", "description": "User account management"},
        {"name": "User Profile", "description": "User profile and avatar"},
        {
            "name": "Notifications",
            "description": "Notification preferences and history",
        },
        {"name": "Platform", "description": "Platform account and settings"},
        {"name": "Business", "description": "Business account management"},
        {"name": "Business Admin", "description": "Business admin operations (staff)"},
    ],
    # Swagger UI settings
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": False,
        "filter": True,
        "docExpansion": "none",
        "defaultModelsExpandDepth": 2,
        "syntaxHighlight.theme": "monokai",
    },
    # Preprocessing hooks
    "PREPROCESSING_HOOKS": [
        "drf_spectacular.hooks.preprocess_exclude_path_format",
    ],
    # Postprocessing hooks
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
    ],
}


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Base CORS settings - will be overridden in environment-specific settings
CORS_ALLOWED_ORIGINS = []
CORS_ALLOW_CREDENTIALS = True

# Refresh token cookie SameSite policy.
# "Strict" for same-origin deployments (frontend behind same-domain reverse proxy).
# "None" for cross-origin deployments (frontend and backend on different domains).
# When "None", Secure=True is required (HTTPS only) — handled automatically via DEBUG flag.
REFRESH_TOKEN_COOKIE_SAMESITE = "Strict"
# Additional CORS settings (can be customized)
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-client-type",  # For web vs mobile token handling
    "x-refresh-token",  # For mobile refresh token
]

# ============================================
# CHANNEL LAYERS (WebSocket Configuration)
# ============================================
# Default to in-memory (will be overridden in production/local_docker)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# ============================================
# EMAIL CONFIGURATION
# ============================================
# Default sender email address
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")

# Email backend type: 'ses', 'smtp', or 'console'
EMAIL_BACKEND_TYPE = os.getenv("EMAIL_BACKEND_TYPE", "console")

# AWS SES settings (used when EMAIL_BACKEND_TYPE='ses')
AWS_SES_REGION_NAME = os.getenv("AWS_SES_REGION", "us-east-1")
AWS_SES_CONFIGURATION_SET = os.getenv("AWS_SES_CONFIGURATION_SET", "")

# SMTP settings (used when EMAIL_BACKEND_TYPE='smtp')
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "false").lower() == "true"

# Email log retention (days)
EMAIL_LOG_RETENTION_DAYS = int(os.getenv("EMAIL_LOG_RETENTION_DAYS", "90"))

# ============================================
# CELERY CONFIGURATION
# ============================================
# Broker URL - Redis by default
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Task settings
CELERY_TASK_ALWAYS_EAGER = False  # Set to True for synchronous testing
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes max per task

# Serialization
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Timezone
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True

# Beat scheduler (using django-celery-beat)
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Queue routing — workers must listen to all queues:
#   celery worker -Q critical,default,bulk
CELERY_TASK_ROUTES = {
    # Critical delivery — low latency, email/notification/security
    "apps.email.tasks.send_email_task": {"queue": "critical"},
    "apps.notifications.tasks.dispatch_notification_task": {"queue": "critical"},
    "auth.revoke_user_tokens": {"queue": "critical"},
    # Retry — default queue
    "apps.transaction.tasks.retry_outcome_execution_task": {"queue": "default"},
    "apps.notifications.tasks.retry_partial_notification_task": {"queue": "default"},
    "apps.email.tasks.retry_failed_emails_task": {"queue": "default"},
    # Bulk — cleanup and batch operations
    "apps.transaction.tasks.expire_transactions_task": {"queue": "bulk"},
    "apps.transaction.tasks.cleanup_old_transaction_logs_task": {"queue": "bulk"},
    "apps.transaction.tasks.send_expiration_reminder_task": {"queue": "bulk"},
    "apps.notifications.tasks.cleanup_old_notification_logs": {"queue": "bulk"},
    "apps.email.tasks.cleanup_old_email_logs": {"queue": "bulk"},
    "apps.chat.tasks.expire_stale_chat_requests": {"queue": "bulk"},
    "apps.chat.tasks.cleanup_orphan_attachments": {"queue": "bulk"},
    "auth.cleanup_expired_tokens": {"queue": "bulk"},
    "auth.cleanup_inactive_sessions": {"queue": "bulk"},
    "cms.cleanup_tombstoned_media": {"queue": "bulk"},
    "cms.prune_content_versions": {"queue": "bulk"},
}

# ============================================
# NOTIFICATION CONFIGURATION
# ============================================
# Log retention (days)
NOTIFICATION_LOG_RETENTION_DAYS = int(
    os.getenv("NOTIFICATION_LOG_RETENTION_DAYS", "90")
)

# ============================================
# JWT AUTHENTICATION CONFIGURATION
# ============================================
JWT_AUTH = {
    "ACCESS_TOKEN_LIFETIME": int(
        os.getenv("JWT_ACCESS_TOKEN_LIFETIME", "900")
    ),  # 15 minutes
    "REFRESH_TOKEN_LIFETIME": int(
        os.getenv("JWT_REFRESH_TOKEN_LIFETIME", "604800")
    ),  # 7 days
    "ALGORITHM": "HS256",
}

# Dedicated JWT signing key (falls back to SECRET_KEY if not set)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)

# JWT issuer and audience claims (prevents token substitution across services)
JWT_ISSUER = os.getenv("JWT_ISSUER", "socialmedia-adv-api")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "socialmedia-adv-client")

# Maximum active sessions per user
AUTH_MAX_SESSIONS_PER_USER = int(os.getenv("AUTH_MAX_SESSIONS_PER_USER", "5"))

# Account lockout after failed login attempts
AUTH_MAX_FAILED_ATTEMPTS = int(os.getenv("AUTH_MAX_FAILED_ATTEMPTS", "10"))
AUTH_LOCKOUT_DURATION = int(os.getenv("AUTH_LOCKOUT_DURATION", "900"))  # 15 minutes

# ============================================
# OAUTH CONFIGURATION
# ============================================
# Google OAuth
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")

# Apple OAuth
APPLE_OAUTH_CLIENT_ID = os.getenv("APPLE_OAUTH_CLIENT_ID", "")  # Services ID
APPLE_OAUTH_TEAM_ID = os.getenv("APPLE_OAUTH_TEAM_ID", "")
APPLE_OAUTH_KEY_ID = os.getenv("APPLE_OAUTH_KEY_ID", "")
APPLE_OAUTH_PRIVATE_KEY = os.getenv("APPLE_OAUTH_PRIVATE_KEY", "")

# Frontend URL (for OAuth redirects and email links)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Allowed origins for OAuth redirect_to validation
ALLOWED_REDIRECT_ORIGINS = [FRONTEND_URL]

# Backend URL (for OAuth callbacks)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ============================================
# REDIS CONFIGURATION
# ============================================
# Used for JTI blacklist and caching
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ============================================
# OBSERVABILITY CONFIGURATION
# ============================================
# Audit log settings
AUDIT_LOG_ENABLED = True
AUDIT_LOG_RETENTION_DAYS = 365 * 2  # 2 years

# Logging settings
# Format: "json" for production, "console" for development
LOGGING_FORMAT = "json"
LOGGING_LEVEL = "INFO"
LOGGING_REQUEST_ID_HEADER = "X-Request-ID"
LOGGING_SERVICE_NAME = "django-api"

# Metrics settings (future)
METRICS_ENABLED = False
METRICS_BACKEND = "noop"  # "noop", "prometheus"

# ============================================
# FILE UPLOAD LIMITS
# ============================================
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
