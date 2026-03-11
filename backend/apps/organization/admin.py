# apps/organization/admin.py
"""
Organization Admin Configuration.

This file imports admin configurations from sub-apps so Django can discover them.
Django only auto-loads admin.py from apps in INSTALLED_APPS, not sub-packages.
"""

# Import business admin to register its models
from apps.organization.business import admin as business_admin  # noqa: F401

# Import platform admin to register its models
from apps.organization.platform import admin as platform_admin  # noqa: F401
