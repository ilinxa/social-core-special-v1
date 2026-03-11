"""
Core Permissions
================
Re-exports permission classes.

Usage:
    from apps.core.permissions import IsAuthenticated, IsOwner
"""

from apps.core.permissions.base import (
    # Authentication
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
    # Staff/Admin
    IsStaff,
    IsStaffOrReadOnly,
    IsSuperuser,
    # Ownership
    IsOwner,
    IsOwnerOrStaff,
    IsOwnerOrReadOnly,
    # Verification
    IsVerified,
    # Utility
    DenyAll,
    AllowAny,
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
