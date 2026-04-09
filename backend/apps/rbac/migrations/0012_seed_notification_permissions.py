# apps/rbac/migrations/0012_seed_notification_permissions.py
"""
Data migration to seed Notification system permissions.
"""

from django.db import migrations

PERMISSIONS = [
    (
        "can_manage_notifications",
        "Manage Notifications",
        "Manage organization notification settings and send announcements",
        "settings",
        ["business", "platform_only"],
    ),
]


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model("rbac", "Permission")
    for code, name, description, category, applicable_scopes in PERMISSIONS:
        Permission.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "description": description,
                "category": category,
                "applicable_scopes": applicable_scopes,
            },
        )


def reverse_permissions(apps, schema_editor):
    Permission = apps.get_model("rbac", "Permission")
    codes = [p[0] for p in PERMISSIONS]
    Permission.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("rbac", "0011_remove_role_unique_role_name_per_account_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_permissions, reverse_permissions),
    ]
