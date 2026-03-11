# apps/rbac/permissions/registry.py
"""
Permission Registry
===================
Defines all system permissions and their applicable scopes.

These permissions are seeded via data migration and are immutable.
Businesses cannot create new permissions - they can only bundle
existing permissions into custom roles.

Scope meanings:
- business: Only within the business where the role is assigned
- platform_only: Only within the platform account
- global_only: Cross-account (e.g., platform staff acting on businesses)
- platform_and_global: Both platform-internal and cross-account
"""

from typing import List, Optional

# Permission definition format:
# (code, name, description, category, applicable_scopes)

PERMISSIONS: List[tuple] = [
    # =========================================================================
    # MEMBERSHIP PERMISSIONS
    # =========================================================================
    (
        "can_invite_member",
        "Invite Member",
        "Invite new members to the account",
        "membership",
        ["business", "platform_only", "global_only"],
    ),
    (
        "can_remove_member",
        "Remove Member",
        "Remove members from the account",
        "membership",
        ["business", "global_only"],
    ),
    (
        "can_change_member_role",
        "Change Member Role",
        "Change the role assigned to a member",
        "membership",
        ["business", "global_only"],
    ),
    (
        "can_suspend_member",
        "Suspend Member",
        "Temporarily suspend a member's access",
        "membership",
        ["business", "global_only"],
    ),
    (
        "can_ban_member",
        "Ban Member",
        "Permanently ban a member from the account",
        "membership",
        ["business", "global_only"],
    ),
    (
        "can_approve_membership_request",
        "Approve Membership Request",
        "Approve pending membership requests",
        "membership",
        ["business", "platform_only"],
    ),
    (
        "can_view_members",
        "View Members",
        "View the list of account members",
        "membership",
        ["business", "platform_only", "global_only"],
    ),

    # =========================================================================
    # ROLE PERMISSIONS
    # =========================================================================
    (
        "can_create_role",
        "Create Role",
        "Create new custom roles for the account",
        "roles",
        ["business", "platform_only"],
    ),
    (
        "can_edit_role",
        "Edit Role",
        "Modify existing custom roles",
        "roles",
        ["business", "platform_only"],
    ),
    (
        "can_delete_role",
        "Delete Role",
        "Delete custom roles from the account",
        "roles",
        ["business", "platform_only"],
    ),

    # =========================================================================
    # SETTINGS PERMISSIONS
    # =========================================================================
    (
        "can_edit_business",
        "Edit Business",
        "Edit business account settings and information",
        "settings",
        ["business", "global_only"],
    ),
    (
        "can_edit_profile",
        "Edit Profile",
        "Edit the public profile of the account",
        "settings",
        ["business", "global_only"],
    ),
    (
        "can_view_settings",
        "View Settings",
        "View account settings",
        "settings",
        ["business", "platform_only"],
    ),

    # =========================================================================
    # PLATFORM PERMISSIONS (primarily global scope)
    # =========================================================================
    (
        "can_suspend_business",
        "Suspend Business",
        "Suspend a business account",
        "platform",
        ["global_only"],
    ),
    (
        "can_remove_business_owner",
        "Remove Business Owner",
        "Remove the owner of a business account",
        "platform",
        ["global_only"],
    ),
    (
        "can_transfer_business_ownership",
        "Transfer Business Ownership",
        "Force transfer ownership of a business",
        "platform",
        ["global_only"],
    ),
    (
        "can_view_businesses",
        "View Businesses",
        "View all business accounts on the platform",
        "platform",
        ["global_only", "platform_only"],
    ),
    (
        "can_approve_verification_request",
        "Approve Verification",
        "Approve business verification requests",
        "platform",
        ["platform_only", "global_only"],
    ),
    (
        "can_approve_business_creation",
        "Approve Business Creation",
        "Approve new business account creation requests",
        "platform",
        ["platform_only"],
    ),

    # =========================================================================
    # VISIBILITY PERMISSIONS
    # =========================================================================
    (
        "can_view_legal_info",
        "View Legal Info",
        "View legal information (registration number, tax ID, legal address)",
        "settings",
        ["business", "global_only"],
    ),

    # =========================================================================
    # TRANSACTION PERMISSIONS
    # =========================================================================
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

    # =========================================================================
    # AUDIT PERMISSIONS
    # =========================================================================
    (
        "can_view_audit_logs",
        "View Audit Logs",
        "View audit logs for the account",
        "audit",
        ["business", "platform_only", "global_only", "platform_and_global"],
    ),

    # =========================================================================
    # FORMS PERMISSIONS (for Form Builder system)
    # =========================================================================
    (
        "can_create_form",
        "Create Form",
        "Create new forms",
        "forms",
        ["business", "platform_only"],
    ),
    (
        "can_edit_form",
        "Edit Form",
        "Edit existing forms",
        "forms",
        ["business", "platform_only", "global_only"],
    ),
    (
        "can_delete_form",
        "Delete Form",
        "Delete forms",
        "forms",
        ["business", "platform_only", "global_only"],
    ),
    (
        "can_view_responses",
        "View Responses",
        "View form responses",
        "forms",
        ["business", "platform_only", "global_only"],
    ),
    (
        "can_export_responses",
        "Export Responses",
        "Export form responses to external formats",
        "forms",
        ["business", "platform_only", "global_only"],
    ),
    (
        "can_process_response",
        "Process Response",
        "Process/handle form responses",
        "forms",
        ["business", "platform_only", "global_only"],
    ),

    # =========================================================================
    # CMS PERMISSIONS (for Content Management System)
    # =========================================================================

    # CMS - Structural (12 permissions, platform_only scope)
    (
        "can_create_cms_site",
        "Create CMS Site",
        "Create new Sites",
        "cms_structure",
        ["platform_only"],
    ),
    (
        "can_edit_cms_site",
        "Edit CMS Site",
        "Edit existing Sites",
        "cms_structure",
        ["platform_only"],
    ),
    (
        "can_delete_cms_site",
        "Delete CMS Site",
        "Delete Sites",
        "cms_structure",
        ["platform_only"],
    ),
    (
        "can_create_cms_page",
        "Create CMS Page",
        "Create new Pages and attach structural placements",
        "cms_structure",
        ["platform_only"],
    ),
    (
        "can_edit_cms_page",
        "Edit CMS Page",
        "Edit page metadata and structural placements",
        "cms_structure",
        ["platform_only"],
    ),
    (
        "can_delete_cms_page",
        "Delete CMS Page",
        "Delete Pages",
        "cms_structure",
        ["platform_only"],
    ),
    (
        "can_create_cms_template",
        "Create CMS Template",
        "Create SectionTemplates and BlockTemplates",
        "cms_structure",
        ["platform_only"],
    ),
    (
        "can_edit_cms_template",
        "Edit CMS Template",
        "Edit templates and block schemas",
        "cms_structure",
        ["platform_only"],
    ),
    (
        "can_delete_cms_template",
        "Delete CMS Template",
        "Delete templates",
        "cms_structure",
        ["platform_only"],
    ),
    (
        "can_assign_cms_to_business",
        "Assign CMS to Business",
        "Assign sites/pages to business accounts",
        "cms_structure",
        ["platform_only", "global_only"],
    ),
    (
        "can_create_cms_api_key",
        "Create CMS API Key",
        "Create API keys for public CMS access",
        "cms_structure",
        ["platform_only"],
    ),
    (
        "can_revoke_cms_api_key",
        "Revoke CMS API Key",
        "Revoke API keys",
        "cms_structure",
        ["platform_only"],
    ),

    # CMS - Content (8 permissions)
    (
        "can_view_cms_content",
        "View CMS Content",
        "View pages, placements, and content",
        "cms_content",
        ["platform_only", "business", "global_only"],
    ),
    (
        "can_edit_cms_content",
        "Edit CMS Content",
        "Edit draft_content values",
        "cms_content",
        ["platform_only", "business", "global_only"],
    ),
    (
        "can_publish_cms_content",
        "Publish CMS Content",
        "Publish pages",
        "cms_content",
        ["platform_only", "business", "global_only"],
    ),
    (
        "can_toggle_cms_visibility",
        "Toggle CMS Visibility",
        "Hide/show non-required placements",
        "cms_content",
        ["platform_only", "business"],
    ),
    (
        "can_view_cms_history",
        "View CMS History",
        "View content version history",
        "cms_content",
        ["platform_only", "business"],
    ),
    (
        "can_rollback_cms_content",
        "Rollback CMS Content",
        "Rollback draft_content to previous version",
        "cms_content",
        ["platform_only", "business"],
    ),
    (
        "can_export_cms_content",
        "Export CMS Content",
        "Export page data as JSON",
        "cms_content",
        ["platform_only", "business"],
    ),
    (
        "can_import_cms_content",
        "Import CMS Content",
        "Import page data from JSON",
        "cms_content",
        ["platform_only", "business"],
    ),

    # CMS - Media (3 permissions)
    (
        "can_upload_cms_media",
        "Upload CMS Media",
        "Upload media files",
        "cms_media",
        ["platform_only", "business", "global_only"],
    ),
    (
        "can_edit_cms_media",
        "Edit CMS Media",
        "Edit media metadata, move, organize",
        "cms_media",
        ["platform_only", "business", "global_only"],
    ),
    (
        "can_delete_cms_media",
        "Delete CMS Media",
        "Delete media files",
        "cms_media",
        ["platform_only", "business", "global_only"],
    ),

    # =========================================================================
    # NETWORK PERMISSIONS (follow / connection management)
    # =========================================================================
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


def get_permission_by_code(code: str) -> Optional[tuple]:
    """
    Get a permission definition by its code.

    Args:
        code: The permission code to look up

    Returns:
        Tuple of (code, name, description, category, applicable_scopes) or None
    """
    for perm in PERMISSIONS:
        if perm[0] == code:
            return perm
    return None


def get_permissions_by_category(category: str) -> List[tuple]:
    """
    Get all permissions in a specific category.

    Args:
        category: The category to filter by

    Returns:
        List of permission tuples in the category
    """
    return [p for p in PERMISSIONS if p[3] == category]


def get_business_permissions() -> List[tuple]:
    """
    Get all permissions that can be assigned with 'business' scope.

    Returns:
        List of permission tuples applicable to business accounts
    """
    return [p for p in PERMISSIONS if "business" in p[4]]


def get_platform_permissions() -> List[tuple]:
    """
    Get all permissions that can be assigned with platform scopes.

    Returns:
        List of permission tuples applicable to platform account
    """
    return [
        p for p in PERMISSIONS
        if any(s in p[4] for s in ["platform_only", "global_only", "platform_and_global"])
    ]


def get_global_permissions() -> List[tuple]:
    """
    Get all permissions that can be assigned with global scope.

    Returns:
        List of permission tuples with global reach
    """
    return [
        p for p in PERMISSIONS
        if any(s in p[4] for s in ["global_only", "platform_and_global"])
    ]
