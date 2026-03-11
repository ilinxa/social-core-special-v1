# apps/rbac/migrations/0004_seed_cms_permissions.py
"""
Data migration to seed CMS system permissions.
"""

from django.db import migrations


PERMISSIONS = [
    # CMS - Structural (12 permissions)
    ("can_create_cms_site", "Create CMS Site", "Create new Sites", "cms_structure", ["platform_only"]),
    ("can_edit_cms_site", "Edit CMS Site", "Edit existing Sites", "cms_structure", ["platform_only"]),
    ("can_delete_cms_site", "Delete CMS Site", "Delete Sites", "cms_structure", ["platform_only"]),
    ("can_create_cms_page", "Create CMS Page", "Create new Pages and attach structural placements", "cms_structure", ["platform_only"]),
    ("can_edit_cms_page", "Edit CMS Page", "Edit page metadata and structural placements", "cms_structure", ["platform_only"]),
    ("can_delete_cms_page", "Delete CMS Page", "Delete Pages", "cms_structure", ["platform_only"]),
    ("can_create_cms_template", "Create CMS Template", "Create SectionTemplates and BlockTemplates", "cms_structure", ["platform_only"]),
    ("can_edit_cms_template", "Edit CMS Template", "Edit templates and block schemas", "cms_structure", ["platform_only"]),
    ("can_delete_cms_template", "Delete CMS Template", "Delete templates", "cms_structure", ["platform_only"]),
    ("can_assign_cms_to_business", "Assign CMS to Business", "Assign sites/pages to business accounts", "cms_structure", ["platform_only", "global_only"]),
    ("can_create_cms_api_key", "Create CMS API Key", "Create API keys for public CMS access", "cms_structure", ["platform_only"]),
    ("can_revoke_cms_api_key", "Revoke CMS API Key", "Revoke API keys", "cms_structure", ["platform_only"]),
    # CMS - Content (8 permissions)
    ("can_view_cms_content", "View CMS Content", "View pages, placements, and content", "cms_content", ["platform_only", "business", "global_only"]),
    ("can_edit_cms_content", "Edit CMS Content", "Edit draft_content values", "cms_content", ["platform_only", "business", "global_only"]),
    ("can_publish_cms_content", "Publish CMS Content", "Publish pages", "cms_content", ["platform_only", "business", "global_only"]),
    ("can_toggle_cms_visibility", "Toggle CMS Visibility", "Hide/show non-required placements", "cms_content", ["platform_only", "business"]),
    ("can_view_cms_history", "View CMS History", "View content version history", "cms_content", ["platform_only", "business"]),
    ("can_rollback_cms_content", "Rollback CMS Content", "Rollback draft_content to previous version", "cms_content", ["platform_only", "business"]),
    ("can_export_cms_content", "Export CMS Content", "Export page data as JSON", "cms_content", ["platform_only", "business"]),
    ("can_import_cms_content", "Import CMS Content", "Import page data from JSON", "cms_content", ["platform_only", "business"]),
    # CMS - Media (3 permissions)
    ("can_upload_cms_media", "Upload CMS Media", "Upload media files", "cms_media", ["platform_only", "business", "global_only"]),
    ("can_edit_cms_media", "Edit CMS Media", "Edit media metadata, move, organize", "cms_media", ["platform_only", "business", "global_only"]),
    ("can_delete_cms_media", "Delete CMS Media", "Delete media files", "cms_media", ["platform_only", "business", "global_only"]),
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
        ('rbac', '0003_seed_transaction_permissions'),
    ]

    operations = [
        migrations.RunPython(seed_permissions, reverse_permissions),
    ]
