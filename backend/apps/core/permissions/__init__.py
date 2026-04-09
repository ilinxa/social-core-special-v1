"""
Core Permissions
================
Re-exports permission classes.

Usage:
    from apps.core.permissions import IsAuthenticated, IsOwner
"""

from apps.core.permissions.base import (  # Authentication; Staff/Admin; Ownership; Verification; Utility; Feature Gates
    AllowAny,
    DenyAll,
    FeatureRequired,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
    IsOwner,
    IsOwnerOrReadOnly,
    IsOwnerOrStaff,
    IsStaff,
    IsStaffOrReadOnly,
    IsSuperuser,
    IsVerified,
)
from apps.core.permissions.governance import GovernanceTokenRequired

__all__ = [
    # Authentication
    "IsAuthenticated",
    "IsAuthenticatedOrReadOnly",
    # Staff/Admin
    "IsStaff",
    "IsStaffOrReadOnly",
    "IsSuperuser",
    # Ownership
    "IsOwner",
    "IsOwnerOrStaff",
    "IsOwnerOrReadOnly",
    # Verification
    "IsVerified",
    # Utility
    "DenyAll",
    "AllowAny",
    # Feature Gates
    "FeatureRequired",
    # Governance
    "GovernanceTokenRequired",
]
