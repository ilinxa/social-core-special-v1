# apps/rbac/migrations/0006_seed_platform_base_member_role.py
"""
Data migration to add Base Member role (level 10) to existing platform accounts.

Platform initialization previously created only 3 roles (Owner, Admin, Moderator).
This adds the Base Member role as a safe fallback for membership creation,
matching the pattern used by business accounts.
"""

from django.db import migrations


def add_platform_base_member_role(apps, schema_editor):
    """Add Base Member role to all existing platform accounts that don't have one."""
    Role = apps.get_model("rbac", "Role")

    # Find all platform accounts that have roles (i.e., were initialized)
    platform_account_ids = (
        Role.objects.filter(account_type="platform")
        .values_list("account_id", flat=True)
        .distinct()
    )

    for platform_id in platform_account_ids:
        # Only add if Base Member doesn't already exist
        if not Role.objects.filter(
            account_type="platform",
            account_id=platform_id,
            name="Base Member",
        ).exists():
            Role.objects.create(
                account_type="platform",
                account_id=platform_id,
                name="Base Member",
                level=10,
                is_system_role=True,
                description="Basic member with no special permissions",
            )


def remove_platform_base_member_role(apps, schema_editor):
    """Remove Base Member role from platform accounts (reverse migration)."""
    Role = apps.get_model("rbac", "Role")
    Role.objects.filter(
        account_type="platform",
        name="Base Member",
        level=10,
        is_system_role=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rbac", "0005_update_settings_permission_scopes"),
    ]

    operations = [
        migrations.RunPython(
            add_platform_base_member_role,
            remove_platform_base_member_role,
        ),
    ]
