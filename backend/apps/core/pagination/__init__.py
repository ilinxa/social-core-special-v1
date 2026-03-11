"""
Core Pagination
===============
Re-exports pagination classes.

Usage:
    from apps.core.pagination import StandardPagination, CursorResultsPagination
"""

from apps.core.pagination.page import (
    # Page number pagination
    StandardPagination,
    SmallResultsPagination,
    LargeResultsPagination,
    # Limit offset pagination
    LimitOffsetResultsPagination,
    # Cursor pagination
    CursorResultsPagination,
    IDCursorPagination,
    # No pagination
    NoPagination,
)

__all__ = [
    # Page number pagination
    "StandardPagination",
    "SmallResultsPagination",
    "LargeResultsPagination",
    # Limit offset pagination
    "LimitOffsetResultsPagination",
    # Cursor pagination
    "CursorResultsPagination",
    "IDCursorPagination",
    # No pagination
    "NoPagination",
]
