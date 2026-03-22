"""
Local development with Docker services (PostgreSQL + Redis).
This is the HYBRID approach - run Django locally but use Docker for infrastructure.

Prerequisites:
    docker compose -f docker-compose.dev.yml up -d

Usage:
    python manage.py runserver

Features:
- PostgreSQL database (production-like)
- Redis channel layer (real WebSocket support)
- Redis cache (production-like caching)
- Fast Django iteration (no Docker rebuild)
"""

import os

# Import base settings directly (skip local.py to avoid duplicate prints)
from .base import *  # noqa: F401, F403

# ============================================
# DEBUG MODE
# ============================================
DEBUG = True

# ============================================
# ALLOWED HOSTS
# ============================================
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "[::1]"]

# ============================================
# STATIC FILES
# ============================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ============================================
# MEDIA FILES
# ============================================
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ============================================
# DATABASE CONFIGURATION (PostgreSQL)
# ============================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "backend_core_db"),
        "USER": os.getenv("POSTGRES_USER", "django_user"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres_dev_password"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# ============================================
# REDIS CONFIGURATION
# ============================================
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

# ============================================
# CHANNEL LAYERS (WebSocket - Redis)
# ============================================
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, int(REDIS_PORT))],
            "capacity": 1500,
            "expiry": 10,
        },
    },
}

# ============================================
# CACHE CONFIGURATION (Redis)
# ============================================
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
            },
        },
        "KEY_PREFIX": "dev",
        "TIMEOUT": 300,
    }
}

# ============================================
# SESSION CONFIGURATION (Redis-backed)
# ============================================
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ============================================
# CELERY CONFIGURATION (LOCAL DOCKER)
# ============================================
# Run tasks synchronously — no Celery worker needed in dev
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ============================================
# CORS (Allow all in development)
# ============================================
CORS_ALLOW_ALL_ORIGINS = True

# ============================================
# LOGGING
# ============================================
# ============================================
# THROTTLE RATES (relaxed for integration testing)
# ============================================
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "anon": "10000/hour",
    "user": "100000/hour",
    "burst": "6000/minute",
    "login": "1000/minute",
    "password_reset": "1000/hour",
    "verification": "1000/minute",
    "refresh": "1000/minute",
}

# ============================================
# DJANGO-SILK PROFILING (opt-in via ENABLE_SILK=1)
# ============================================
if os.getenv("ENABLE_SILK", "") == "1":
    INSTALLED_APPS += ["silk"]  # noqa: F405
    MIDDLEWARE.insert(0, "silk.middleware.SilkyMiddleware")  # noqa: F405
    SILKY_PYTHON_PROFILER = True
    SILKY_PYTHON_PROFILER_BINARY = True
    SILKY_MAX_RECORDED_REQUESTS = 1000
    SILKY_META = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
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
    },
}
