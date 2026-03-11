# apps/organization/migrations/0002_create_platform_singleton.py
"""
Data migration to create the Platform singleton.

The PlatformAccount is a singleton (enforced by unique + check constraints).
This migration creates the initial instance with is_configured=False.
"""

from django.db import migrations


def create_platform_singleton(apps, schema_editor):
    """Create the platform singleton if it doesn't exist."""
    PlatformAccount = apps.get_model("organization", "PlatformAccount")
    PlatformProfile = apps.get_model("organization", "PlatformProfile")

    if not PlatformAccount.objects.exists():
        # singleton_key=1 is enforced by unique + check constraints
        platform = PlatformAccount.objects.create(
            singleton_key=1,
            is_configured=False,
            settings={},
        )
        PlatformProfile.objects.create(
            platform=platform,
            name="Platform",
        )


def reverse_migration(apps, schema_editor):
    """Remove the platform singleton (for reverse migration)."""
    PlatformAccount = apps.get_model("organization", "PlatformAccount")
    PlatformAccount.objects.all().delete()


class Migration(migrations.Migration):
    """Data migration to create the Platform singleton."""

    dependencies = [
        ("organization", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_platform_singleton, reverse_migration),
    ]
