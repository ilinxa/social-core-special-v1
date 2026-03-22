# apps/rbac/migrations/0005_update_settings_permission_scopes.py
"""
Data migration to add 'platform_only' to applicable_scopes for
can_edit_profile and can_edit_business permissions.

Without this, Platform Admin role cannot receive these permissions
(Platform Admin only gets 'platform_only' scoped permissions).
"""

from django.db import migrations

UPDATES = [
    # (code, new_applicable_scopes)
    ("can_edit_profile", ["business", "global_only", "platform_only"]),
    ("can_edit_business", ["business", "global_only", "platform_only"]),
]


def update_scopes(apps, schema_editor):
    Permission = apps.get_model("rbac", "Permission")
    for code, new_scopes in UPDATES:
        Permission.objects.filter(code=code).update(applicable_scopes=new_scopes)


def reverse_scopes(apps, schema_editor):
    Permission = apps.get_model("rbac", "Permission")
    for code, _ in UPDATES:
        Permission.objects.filter(code=code).update(
            applicable_scopes=["business", "global_only"],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("rbac", "0004_seed_cms_permissions"),
    ]

    operations = [
        migrations.RunPython(update_scopes, reverse_scopes),
    ]
