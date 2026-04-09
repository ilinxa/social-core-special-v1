"""
Extend CMS permission scopes to include business.

Business users need to create/edit/delete sites, pages, and API keys
within their own business context. This adds "business" to the
applicable_scopes of CMS structural permissions that were previously
platform_only.
"""

from django.db import migrations

# Permissions that need "business" added to their applicable_scopes
PERMISSIONS_TO_EXTEND = [
    "can_create_cms_site",
    "can_edit_cms_site",
    "can_delete_cms_site",
    "can_create_cms_page",
    "can_edit_cms_page",
    "can_delete_cms_page",
    "can_create_cms_api_key",
    "can_revoke_cms_api_key",
]


def extend_scopes(apps, schema_editor):
    Permission = apps.get_model("rbac", "Permission")
    for code in PERMISSIONS_TO_EXTEND:
        perm = Permission.objects.filter(code=code).first()
        if perm and "business" not in perm.applicable_scopes:
            perm.applicable_scopes = perm.applicable_scopes + ["business"]
            perm.save(update_fields=["applicable_scopes"])


def reverse_scopes(apps, schema_editor):
    Permission = apps.get_model("rbac", "Permission")
    for code in PERMISSIONS_TO_EXTEND:
        perm = Permission.objects.filter(code=code).first()
        if perm and "business" in perm.applicable_scopes:
            perm.applicable_scopes = [
                s for s in perm.applicable_scopes if s != "business"
            ]
            perm.save(update_fields=["applicable_scopes"])


class Migration(migrations.Migration):
    dependencies = [
        ("rbac", "0013_seed_cms_activation_permissions"),
    ]

    operations = [
        migrations.RunPython(extend_scopes, reverse_scopes),
    ]
