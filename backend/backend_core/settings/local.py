from .base import *


DEBUG=True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Additional directories to search for static files
STATICFILES_DIRS = [
    # BASE_DIR / "static",  # Uncomment if you have a global static directory
]

# ============================================
# MEDIA FILES CONFIGURATION
# ============================================
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "[::1]", "testserver"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ============================================
# CHANNEL LAYERS (WebSocket Configuration)
# ============================================
# In-memory channel layer - simple, no Redis needed
# NOTE: This won't work for multi-process setups
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# ============================================
# CACHE CONFIGURATION
# ============================================
# Dummy cache for local development (no caching)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# ============================================
# SESSION CONFIGURATION
# ============================================
# Use database-backed sessions (default Django behavior)
SESSION_ENGINE = "django.contrib.sessions.backends.db"

CORS_ALLOW_ALL_ORIGINS = True

# Only add if django-debug-toolbar is installed
if "debug_toolbar" in INSTALLED_APPS:
    # Add middleware
    MIDDLEWARE.insert(
        0,  # Add at the beginning
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    )
    
    # Internal IPs that can see debug toolbar
    INTERNAL_IPS = [
        "127.0.0.1",
        "localhost",
    ]


# ============================================
# LOGGING CONFIGURATION
# ============================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
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
        "django.request": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "channels": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# ============================================
# DEVELOPMENT-SPECIFIC SETTINGS
# ============================================
# Show SQL queries in console (useful for debugging)
# LOGGING["loggers"]["django.db.backends"] = {
#     "handlers": ["console"],
#     "level": "DEBUG",
# }

# ============================================
# CELERY CONFIGURATION (LOCAL)
# ============================================
# Run tasks synchronously for easier debugging
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ============================================
# EMAIL CONFIGURATION (LOCAL)
# ============================================
# Use console backend for local development
EMAIL_BACKEND_TYPE = 'console'

# ============================================
# OBSERVABILITY CONFIGURATION (LOCAL)
# ============================================
# Use console format (colored, human-readable) in development
LOGGING_FORMAT = "console"
LOGGING_LEVEL = "DEBUG"

