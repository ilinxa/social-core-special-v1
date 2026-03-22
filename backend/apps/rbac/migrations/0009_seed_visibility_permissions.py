# apps/rbac/migrations/0009_seed_visibility_permissions.py
"""
Data migration to seed visibility system permissions.
"""

from django.db import migrations

PERMISSIONS = [
    (
        "can_view_legal_info",
        "View Legal Info",
        "View legal information (registration number, tax ID, legal address)",
        "settings",
        ["business", "global_only"],
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
        ("rbac", "0008_seed_network_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_permissions, reverse_permissions),
    ]
