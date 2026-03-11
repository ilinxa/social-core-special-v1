"""
Pagination Classes
==================
Custom pagination classes for consistent API responses.

Configuration:
    Default pagination is set in settings.REST_FRAMEWORK:
        "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
        "PAGE_SIZE": 20,

Usage in Views:
    class ProductListView(APIView):
        pagination_class = LargeResultsPagination  # Override default

        def get(self, request):
            products = Product.objects.all()
            page = self.paginate_queryset(products)
            serializer = ProductSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
"""

from rest_framework.pagination import (
    PageNumberPagination,
    LimitOffsetPagination,
    CursorPagination,
)


# =============================================================================
# PAGE NUMBER PAGINATION (Default)
# =============================================================================

class StandardPagination(PageNumberPagination):
    """
    Standard page-number based pagination.

    Query params:
        page: Page number (1-indexed)
        page_size: Items per page (optional, capped at max)

    Response format:
        {
            "count": 100,
            "next": "http://api.example.com/items/?page=2",
            "previous": null,
            "results": [...]
        }

    Example:
        GET /api/v1/products/?page=2&page_size=10
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    # Custom page query param (default is "page")
    page_query_param = "page"


class SmallResultsPagination(PageNumberPagination):
    """
    Pagination for endpoints with small result sets.

    Use for:
        - Dropdown options
        - Autocomplete suggestions
        - Small lists (notifications, recent items)
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 25


class LargeResultsPagination(PageNumberPagination):
    """
    Pagination for endpoints with large result sets.

    Use for:
        - Data exports
        - Admin listings
        - Bulk operations

    Note:
        Large page sizes can impact performance.
        Consider using CursorPagination for very large datasets.
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


# =============================================================================
# LIMIT OFFSET PAGINATION
# =============================================================================

class LimitOffsetResultsPagination(LimitOffsetPagination):
    """
    Limit/offset based pagination.

    Query params:
        limit: Number of items to return
        offset: Starting position

    Response format:
        {
            "count": 100,
            "next": "http://api.example.com/items/?limit=10&offset=20",
            "previous": "http://api.example.com/items/?limit=10&offset=0",
            "results": [...]
        }

    Example:
        GET /api/v1/products/?limit=10&offset=30

    Use when:
        - Client needs direct offset control
        - Integrating with SQL LIMIT/OFFSET patterns
        - Random access to pages is needed

    Note:
        Offset pagination is inefficient for large offsets.
        Consider CursorPagination for large datasets.
    """

    default_limit = 20
    max_limit = 100


# =============================================================================
# CURSOR PAGINATION
# =============================================================================

class CursorResultsPagination(CursorPagination):
    """
    Cursor-based pagination for large datasets.

    Query params:
        cursor: Opaque cursor string (from previous response)

    Response format:
        {
            "next": "http://api.example.com/items/?cursor=cD0yMDIx...",
            "previous": "http://api.example.com/items/?cursor=cj0xJnA...",
            "results": [...]
        }

    Benefits:
        - Consistent performance regardless of offset
        - No duplicate/missing items when data changes
        - Works well with real-time updates

    Limitations:
        - No random page access
        - No total count
        - Requires ordering by a unique, sequential field

    Use for:
        - Activity feeds
        - Timelines
        - Large datasets (10k+ rows)
    """

    page_size = 20
    ordering = "-created_at"  # Most recent first
    cursor_query_param = "cursor"

    # Allow client to override page size
    page_size_query_param = "page_size"
    max_page_size = 100


class IDCursorPagination(CursorPagination):
    """
    Cursor pagination ordered by ID.

    Use when:
        - Data doesn't have timestamps
        - You want deterministic ordering
        - Results should be ordered by creation (ID approximates this)
    """

    page_size = 20
    ordering = "-id"
    cursor_query_param = "cursor"
    page_size_query_param = "page_size"
    max_page_size = 100


# =============================================================================
# NO PAGINATION
# =============================================================================

class NoPagination:
    """
    Dummy class indicating no pagination.

    Use for endpoints that should return all results:
        class OptionsListView(APIView):
            pagination_class = NoPagination

    Warning:
        Only use for endpoints with guaranteed small result sets
        (e.g., enum options, config values).
    """

    display_page_controls = False

    def paginate_queryset(self, queryset, request, view=None):
        return None

    def get_paginated_response(self, data):
        return data
