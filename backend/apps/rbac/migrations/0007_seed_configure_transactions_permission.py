# apps/rbac/migrations/0007_seed_configure_transactions_permission.py
"""
Data migration to seed can_configure_transactions permission.
"""

from django.db import migrations


PERMISSIONS = [
    (
        "can_configure_transactions",
        "Configure Transactions",
        "Configure transaction form mappings and settings",
        "transaction",
        ["business", "platform_only"],
    ),
]


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model('rbac', 'Permission')
    for code, name, description, category, applicable_scopes in PERMISSIONS:
        Permission.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'description': description,
                'category': category,
                'applicable_scopes': applicable_scopes,
            }
        )


def reverse_permissions(apps, schema_editor):
    Permission = apps.get_model('rbac', 'Permission')
    codes = [p[0] for p in PERMISSIONS]
    Permission.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('rbac', '0006_seed_platform_base_member_role'),
    ]

    operations = [
        migrations.RunPython(seed_permissions, reverse_permissions),
    ]
