"""
Core Permissions
================
Re-exports permission classes.

Usage:
    from apps.core.permissions import IsAuthenticated, IsOwner
"""

from apps.core.permissions.base import (  # Authentication; Staff/Admin; Ownership; Verification; Utility
    AllowAny,
    DenyAll,
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
]
