# apps/rbac/migrations/0003_seed_transaction_permissions.py
"""
Data migration to seed transaction system permissions.
"""

from django.db import migrations

PERMISSIONS = [
    (
        "can_view_transactions",
        "View Transactions",
        "View transactions within the account",
        "transaction",
        ["business", "platform_only"],
    ),
    (
        "can_view_all_transactions",
        "View All Transactions",
        "View transactions across all accounts",
        "transaction",
        ["global_only", "platform_and_global"],
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
        ("rbac", "0002_seed_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_permissions, reverse_permissions),
    ]
