"""
Seed CMS activation and template management permissions.

New permissions for CMS business access:
- can_approve_cms_activation: Platform approves CMS activation requests
- can_manage_business_cms: Platform directly enables/disables business CMS
- can_activate_cms_template: Org activates templates from catalog
- can_deactivate_cms_template: Org removes templates from library
"""

from django.db import migrations

PERMISSIONS = [
    (
        "can_approve_cms_activation",
        "Approve CMS Activation",
        "Approve or deny business CMS activation requests",
        "cms_management",
        ["platform_only"],
    ),
    (
        "can_manage_business_cms",
        "Manage Business CMS",
        "Directly enable or disable CMS for businesses",
        "cms_management",
        ["platform_only"],
    ),
    (
        "can_activate_cms_template",
        "Activate CMS Template",
        "Activate templates from the catalog into the organization library",
        "cms_structure",
        ["business", "platform_only"],
    ),
    (
        "can_deactivate_cms_template",
        "Deactivate CMS Template",
        "Remove templates from the organization library",
        "cms_structure",
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
        ("rbac", "0012_seed_notification_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_permissions, reverse_permissions),
    ]
