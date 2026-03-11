# apps/organization/apps.py
"""Organization app configuration."""

from django.apps import AppConfig


class OrganizationConfig(AppConfig):
    """Configuration for the Organization app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.organization"
    verbose_name = "Organization"

    def ready(self):
        """Import signal handlers when app is ready."""
        pass  # Signal handlers will be added if needed
