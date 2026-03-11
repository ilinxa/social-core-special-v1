"""
Core App Configuration
======================
Django app configuration for the core infrastructure app.

This app provides:
    - Base models for inheritance
    - Shared exceptions and handlers
    - Utility functions (JWT, password, datetime)
    - Base serializers and pagination
    - Common permissions

Note:
    This app should have NO business logic.
    It's purely shared infrastructure.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """
    Configuration for the core app.

    Attributes:
        name: Python path to the app
        verbose_name: Human-readable name for admin
        default_auto_field: Primary key type for models
    """

    name = "apps.core"
    verbose_name = "Core Infrastructure"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """
        Called when Django starts.

        Use for:
            - Configuring structured logging
            - Registering signals (when needed)
            - One-time initialization
        """
        # Configure structured logging on startup
        from apps.core.observability.logging.config import configure_logging
        configure_logging()

        # Import signals here when they're added
        # from apps.core import signals  # noqa
