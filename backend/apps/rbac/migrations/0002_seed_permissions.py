# apps/rbac/migrations/0002_seed_permissions.py
"""
Data migration to seed predefined permissions.

Permissions are immutable after creation - they define the atomic
capabilities available in the system.
"""

from django.db import migrations


PERMISSIONS = [
    # (code, name, description, category, applicable_scopes)
    # Membership
    ("can_invite_member", "Invite Member", "Invite new members to the account", "membership", ["business", "platform_only", "global_only"]),
    ("can_remove_member", "Remove Member", "Remove members from the account", "membership", ["business", "global_only"]),
    ("can_change_member_role", "Change Member Role", "Change the role assigned to a member", "membership", ["business", "global_only"]),
    ("can_suspend_member", "Suspend Member", "Temporarily suspend a member's access", "membership", ["business", "global_only"]),
    ("can_ban_member", "Ban Member", "Permanently ban a member from the account", "membership", ["business", "global_only"]),
    ("can_approve_membership_request", "Approve Membership Request", "Approve pending membership requests", "membership", ["business", "platform_only"]),
    ("can_view_members", "View Members", "View the list of account members", "membership", ["business", "platform_only", "global_only"]),

    # Roles
    ("can_create_role", "Create Role", "Create new custom roles for the account", "roles", ["business", "platform_only"]),
    ("can_edit_role", "Edit Role", "Modify existing custom roles", "roles", ["business", "platform_only"]),
    ("can_delete_role", "Delete Role", "Delete custom roles from the account", "roles", ["business", "platform_only"]),

    # Settings
    ("can_edit_business", "Edit Business", "Edit business account settings and information", "settings", ["business", "global_only"]),
    ("can_edit_profile", "Edit Profile", "Edit the public profile of the account", "settings", ["business", "global_only"]),
    ("can_view_settings", "View Settings", "View account settings", "settings", ["business", "platform_only"]),

    # Platform
    ("can_suspend_business", "Suspend Business", "Suspend a business account", "platform", ["global_only"]),
    ("can_remove_business_owner", "Remove Business Owner", "Remove the owner of a business account", "platform", ["global_only"]),
    ("can_transfer_business_ownership", "Transfer Business Ownership", "Force transfer ownership of a business", "platform", ["global_only"]),
    ("can_view_businesses", "View Businesses", "View all business accounts on the platform", "platform", ["global_only", "platform_only"]),
    ("can_approve_verification_request", "Approve Verification", "Approve business verification requests", "platform", ["platform_only", "global_only"]),
    ("can_approve_business_creation", "Approve Business Creation", "Approve new business account creation requests", "platform", ["platform_only"]),

    # Audit
    ("can_view_audit_logs", "View Audit Logs", "View audit logs for the account", "audit", ["business", "platform_only", "global_only", "platform_and_global"]),

    # Forms
    ("can_create_form", "Create Form", "Create new forms", "forms", ["business", "platform_only"]),
    ("can_edit_form", "Edit Form", "Edit existing forms", "forms", ["business", "platform_only", "global_only"]),
    ("can_delete_form", "Delete Form", "Delete forms", "forms", ["business", "platform_only", "global_only"]),
    ("can_view_responses", "View Responses", "View form responses", "forms", ["business", "platform_only", "global_only"]),
    ("can_export_responses", "Export Responses", "Export form responses to external formats", "forms", ["business", "platform_only", "global_only"]),
    ("can_process_response", "Process Response", "Process/handle form responses", "forms", ["business", "platform_only", "global_only"]),
]


def seed_permissions(apps, schema_editor):
    """Seed all predefined permissions."""
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
    """Remove seeded permissions."""
    Permission = apps.get_model('rbac', 'Permission')
    codes = [p[0] for p in PERMISSIONS]
    Permission.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('rbac', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_permissions, reverse_permissions),
    ]
