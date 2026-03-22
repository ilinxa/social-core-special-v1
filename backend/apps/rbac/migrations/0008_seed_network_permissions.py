# apps/rbac/migrations/0008_seed_network_permissions.py
"""
Data migration to seed Network system permissions.
"""

from django.db import migrations

PERMISSIONS = [
    (
        "can_manage_followers",
        "Manage Followers",
        "Remove followers from the account",
        "network",
        ["business", "platform_only"],
    ),
    (
        "can_manage_connections",
        "Manage Connections",
        "Accept, reject, and manage account connections",
        "network",
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
        ("rbac", "0007_seed_configure_transactions_permission"),
    ]

    operations = [
        migrations.RunPython(seed_permissions, reverse_permissions),
    ]
