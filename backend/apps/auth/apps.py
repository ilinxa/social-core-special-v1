"""
Auth App Configuration
"""

from django.apps import AppConfig


class AuthConfig(AppConfig):
    """Configuration for the auth app."""

    name = "apps.auth"
    label = "authentication"  # Avoid conflict with Django's built-in 'auth' app
    verbose_name = "Authentication"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """Called when Django starts."""
        # Import signals if any
        pass
