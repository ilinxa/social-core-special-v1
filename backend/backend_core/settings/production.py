"""
Production settings.
Includes security hardening, PostgreSQL, Redis, and optional S3/Cloudflare R2 storage.

Environment Variables Required:
    - DJANGO_SECRET_KEY (CRITICAL - must be strong and unique)
    - ALLOWED_HOSTS (comma-separated, e.g., "example.com,www.example.com")
    - POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST
    - REDIS_URL (e.g., "redis://redis:6379")
    
Optional (for S3/Cloudflare R2):
    - USE_S3=true
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_STORAGE_BUCKET_NAME
    - AWS_S3_ENDPOINT_URL (for Cloudflare R2)
    - AWS_S3_CUSTOM_DOMAIN (for CDN)

Usage:
    # Set in docker-compose.yml or environment
    DJANGO_SETTINGS_MODULE=backend_core.settings.production
"""

import logging as _logging

from .base import *

_prod_logger = _logging.getLogger(__name__)

# ============================================
# SECURITY - DEBUG MODE
# ============================================
DEBUG = False

# Validate that DEBUG is actually False
assert DEBUG == False, "DEBUG must be False in production!"

# Validate that SECRET_KEY is not the dev default
if SECRET_KEY.startswith("django-insecure"):
    raise ValueError(
        "SECRET_KEY starts with 'django-insecure' — set a strong key in production!\n"
        'Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"'
    )

# ============================================
# ALLOWED HOSTS
# ============================================
# CRITICAL: Set this from environment variable
ALLOWED_HOSTS_STR = os.getenv("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STR.split(",") if host.strip()]

# Validate that ALLOWED_HOSTS is set
if not ALLOWED_HOSTS or ALLOWED_HOSTS == [""]:
    raise ValueError(
        "ALLOWED_HOSTS environment variable must be set in production!\n"
        "Example: ALLOWED_HOSTS=example.com,www.example.com"
    )

# Ensure wildcard is not used
if "*" in ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS cannot contain '*' in production!")

# ============================================
# SECURITY SETTINGS
# ============================================
# Force HTTPS redirect (disable only if using external SSL termination like AWS ALB)
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True") == "True"

# Secure cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Referrer policy (defense-in-depth — nginx also sets this header)
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Secure proxy SSL header (if using nginx/load balancer)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ============================================
# DATABASE CONFIGURATION
# ============================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST", "db"),  # Docker service name
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        # Connection pooling for production
        "CONN_MAX_AGE": 600,  # 10 minutes
        # Additional options
        "OPTIONS": {
            "connect_timeout": 10,
            "sslmode": os.getenv("POSTGRES_SSLMODE", "require"),
            "options": "-c statement_timeout=30000",
        },
    }
}

# Validate database credentials are set
if not all(
    [
        os.getenv("POSTGRES_DB"),
        os.getenv("POSTGRES_USER"),
        os.getenv("POSTGRES_PASSWORD"),
    ]
):
    raise ValueError(
        "Database credentials (POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD) must be set!"
    )

# ============================================
# REDIS CONFIGURATION
# ============================================
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

if not REDIS_URL:
    raise ValueError("REDIS_URL environment variable must be set in production!")

# ============================================
# CHANNEL LAYERS (WebSocket Configuration)
# ============================================
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
            "capacity": 1500,
            "expiry": 10,
        },
    },
}

# ============================================
# CACHE CONFIGURATION
# ============================================
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_URL}/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
            },
            # Optional: Enable compression
            # "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
        },
        "KEY_PREFIX": "prod",
        "TIMEOUT": 300,  # 5 minutes default
    }
}

# ============================================
# SESSION CONFIGURATION
# ============================================
# Use Redis-backed cache for sessions
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 86400  # 1 day in seconds
SESSION_SAVE_EVERY_REQUEST = False

# ============================================
# CORS CONFIGURATION
# ============================================
# Get allowed origins from environment
CORS_ALLOWED_ORIGINS_STR = os.getenv("CORS_ALLOWED_ORIGINS", "")
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in CORS_ALLOWED_ORIGINS_STR.split(",") if origin.strip()
]

# Ensure credentials support
CORS_ALLOW_CREDENTIALS = True

# CSRF trusted origins (defaults to CORS origins)
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", CORS_ALLOWED_ORIGINS_STR).split(",")
    if origin.strip()
]

# Cross-origin cookie policy:
# "None" when frontend and backend are on different domains (requires HTTPS)
# "Strict" when both are behind the same reverse proxy / domain
REFRESH_TOKEN_COOKIE_SAMESITE = os.getenv("REFRESH_TOKEN_COOKIE_SAMESITE", "Strict")

# ============================================
# STATIC & MEDIA FILES - CONDITIONAL S3/R2
# ============================================
USE_S3 = os.getenv("USE_S3", "False").lower() == "true"

if USE_S3:
    # ========================================
    # AWS S3 / CLOUDFLARE R2 CONFIGURATION
    # ========================================

    # Validate required S3 credentials
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")

    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME]):
        raise ValueError(
            "When USE_S3=true, you must set: "
            "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME"
        )

    # Endpoint URL (required for Cloudflare R2)
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL", None)

    # Region
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "auto")

    # Custom domain (CDN)
    AWS_S3_CUSTOM_DOMAIN = os.getenv("AWS_S3_CUSTOM_DOMAIN", None)

    # S3 settings
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None  # Use bucket's default ACL
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "max-age=86400",  # 1 day
    }

    # Storage backends
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "location": "media",
                "file_overwrite": False,
            },
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3boto3.S3StaticStorage",
            "OPTIONS": {
                "location": "static",
            },
        },
    }

    # URLs
    if AWS_S3_CUSTOM_DOMAIN:
        STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
    elif AWS_S3_ENDPOINT_URL:
        STATIC_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/static/"
        MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/media/"
    else:
        STATIC_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/static/"
        MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/media/"

    _prod_logger.info("Using S3/Cloudflare R2 for static and media files")

else:
    # ========================================
    # LOCAL/NGINX FILE SERVING
    # ========================================

    STATIC_URL = "/static/"
    STATIC_ROOT = "/app/staticfiles"

    MEDIA_URL = "/media/"
    MEDIA_ROOT = "/app/media"

    # WhiteNoise for serving static files (if nginx is not serving them)
    # Add WhiteNoise middleware
    if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:
        MIDDLEWARE.insert(
            MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
            "whitenoise.middleware.WhiteNoiseMiddleware",
        )

    # Configure storages
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

    # WhiteNoise settings
    WHITENOISE_MAX_AGE = 31536000  # 1 year
    WHITENOISE_COMPRESS_OFFLINE = True

    _prod_logger.info("Using local filesystem for static and media files")

# ============================================
# EMAIL CONFIGURATION
# ============================================
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)

# SMTP Settings
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)

# ============================================
# LOGGING CONFIGURATION
# ============================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "filters": ["require_debug_false"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "channels": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# ============================================
# ADMINS
# ============================================
# Admins receive error emails (format: DJANGO_ADMINS=Name:email@example.com,Name2:email2@example.com)
_admins_str = os.getenv("DJANGO_ADMINS", "")
ADMINS = [
    tuple(entry.strip().split(":")) for entry in _admins_str.split(",") if ":" in entry
]

MANAGERS = ADMINS

# ============================================
# SENTRY ERROR TRACKING (env-var gated)
# ============================================
# Only activates when SENTRY_DSN environment variable is set.
# No impact when absent — sentry-sdk does nothing without init().
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    # PII scrubbing — strip sensitive fields from event data before sending.
    # Duplicates SENSITIVE_KEYS from processors.py inline because apps.core
    # is not importable at settings-load time.
    _SENTRY_SENSITIVE_KEYS = frozenset(
        {
            "password",
            "token",
            "secret",
            "api_key",
            "apikey",
            "authorization",
            "credit_card",
            "creditcard",
            "ssn",
            "access_token",
            "refresh_token",
            "cookie",
            "session_id",
            "private_key",
            "privatekey",
            "otp",
            "verification_code",
            "csrf",
        }
    )

    def _sentry_before_send(event, hint):
        """Strip sensitive fields from Sentry events."""
        if "request" in event and "data" in event["request"]:
            data = event["request"]["data"]
            if isinstance(data, dict):
                for key in list(data.keys()):
                    if key.lower() in _SENTRY_SENSITIVE_KEYS:
                        data[key] = "[REDACTED]"
        return event

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        release=os.getenv("GIT_SHA", "unknown"),
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        send_default_pii=False,
        before_send=_sentry_before_send,
    )

    _prod_logger.info(
        "Sentry initialized (environment=%s)",
        os.getenv("SENTRY_ENVIRONMENT", "production"),
    )
