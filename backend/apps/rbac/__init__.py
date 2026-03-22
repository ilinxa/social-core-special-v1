# apps/rbac/__init__.py
"""
RBAC (Role-Based Access Control) App
====================================
Provides permission, role, and membership management for multi-tenant accounts.

Key components:
- Permission: Predefined atomic capabilities (seeded via migration)
- Role: Named bundles of permissions per account
- RolePermission: Assignment of permissions to roles with scope
- Membership: Connection between users and accounts with assigned roles

Usage:
    from apps.rbac.services import RBACService
    from apps.rbac.selectors import MembershipSelector, PermissionSelector
    from apps.rbac.policies import MembershipPolicy
"""

default_app_config = "apps.rbac.apps.RbacConfig"
