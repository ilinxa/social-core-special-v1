"""
Email App Configuration
=======================
"""

from django.apps import AppConfig


class EmailConfig(AppConfig):
    """Configuration for the Email app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.email'
    verbose_name = 'Email'
