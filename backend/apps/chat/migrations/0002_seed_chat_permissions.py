"""
Data migration to seed chat permissions into the RBAC Permission table.
"""

from django.db import migrations

PERMISSIONS = [
    # (code, name, description, category, applicable_scopes)
    (
        "can_manage_chat",
        "Manage Chat",
        "Send and receive messages as the entity account, access entity inbox",
        "chat",
        ["business", "platform_only"],
    ),
]


def seed_permissions(apps, schema_editor):
    """Seed chat permissions."""
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
    """Remove seeded chat permissions."""
    Permission = apps.get_model("rbac", "Permission")
    codes = [p[0] for p in PERMISSIONS]
    Permission.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0001_initial"),
        ("rbac", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_permissions, reverse_permissions),
    ]
