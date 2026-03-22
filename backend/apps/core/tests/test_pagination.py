# apps/core/tests/test_pagination.py
"""
Tests for core pagination classes.

Covers:
    - StandardPagination: default page_size and max_page_size
    - SmallResultsPagination: smaller page_size and max_page_size
    - LargeResultsPagination: larger page_size and max_page_size
    - NoPagination: paginate_queryset returns None
"""

import pytest

from apps.core.pagination.page import (
    LargeResultsPagination,
    NoPagination,
    SmallResultsPagination,
    StandardPagination,
)

# =============================================================================
# STANDARD PAGINATION TESTS
# =============================================================================


class TestStandardPagination:
    """Tests for StandardPagination class attributes."""

    def test_default_page_size(self):
        """Default page size is 20."""
        assert StandardPagination.page_size == 20

    def test_max_page_size(self):
        """Maximum page size is 100."""
        assert StandardPagination.max_page_size == 100

    def test_page_size_query_param(self):
        """Clients can override page size via 'page_size' query param."""
        assert StandardPagination.page_size_query_param == "page_size"

    def test_page_query_param(self):
        """Page number is specified via 'page' query param."""
        assert StandardPagination.page_query_param == "page"


# =============================================================================
# SMALL RESULTS PAGINATION TESTS
# =============================================================================


class TestSmallResultsPagination:
    """Tests for SmallResultsPagination class attributes."""

    def test_default_page_size(self):
        """Default page size is 10."""
        assert SmallResultsPagination.page_size == 10

    def test_max_page_size(self):
        """Maximum page size is 25."""
        assert SmallResultsPagination.max_page_size == 25

    def test_page_size_query_param(self):
        """Clients can override page size via 'page_size' query param."""
        assert SmallResultsPagination.page_size_query_param == "page_size"


# =============================================================================
# LARGE RESULTS PAGINATION TESTS
# =============================================================================


class TestLargeResultsPagination:
    """Tests for LargeResultsPagination class attributes."""

    def test_default_page_size(self):
        """Default page size is 50."""
        assert LargeResultsPagination.page_size == 50

    def test_max_page_size(self):
        """Maximum page size is 200."""
        assert LargeResultsPagination.max_page_size == 200

    def test_page_size_query_param(self):
        """Clients can override page size via 'page_size' query param."""
        assert LargeResultsPagination.page_size_query_param == "page_size"


# =============================================================================
# NO PAGINATION TESTS
# =============================================================================


class TestNoPagination:
    """Tests for NoPagination class."""

    def test_paginate_queryset_returns_none(self):
        """paginate_queryset() returns None, disabling pagination."""
        paginator = NoPagination()
        result = paginator.paginate_queryset(queryset=[], request=None, view=None)

        assert result is None

    def test_display_page_controls_is_false(self):
        """display_page_controls is False since there is no pagination."""
        assert NoPagination.display_page_controls is False

    def test_get_paginated_response_returns_data_directly(self):
        """get_paginated_response() returns the data as-is without wrapping."""
        paginator = NoPagination()
        data = [{"id": 1}, {"id": 2}]
        result = paginator.get_paginated_response(data)

        assert result == data
