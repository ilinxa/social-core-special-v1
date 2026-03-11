# apps/explore/tests/test_views.py
"""
Tests for Explore API views.

These tests mock ExploreSelector methods to avoid PostgreSQL-specific
FTS/Trigram calls, allowing them to run on SQLite in the unit test suite.
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework import status
from rest_framework.response import Response as DRFResponse
from rest_framework.test import APIClient

from apps.core.constants import (
    BusinessStatus,
    VerificationStatus,
)
from apps.explore.models import TagCategory
from apps.explore.tests.factories import SuggestedTagFactory
from apps.organization.tests.factories import (
    BusinessAccountFactory,
    BusinessProfileFactory,
)
from apps.users.tests.factories import UserFactory


EXPLORE_BASE = "/api/v1/explore/"
BUSINESSES_URL = f"{EXPLORE_BASE}businesses/"
USERS_URL = f"{EXPLORE_BASE}users/"
TAGS_URL = f"{EXPLORE_BASE}tags/"
CITIES_URL = f"{EXPLORE_BASE}cities/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory(is_verified=True)


@pytest.fixture
def auth_client(api_client, user):
    """Authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def sample_businesses(db):
    """Create sample businesses for testing."""
    businesses = []
    for i in range(3):
        biz = BusinessAccountFactory(
            status=BusinessStatus.ACTIVE,
            legal_name=f"Test Business {i}",
        )
        BusinessProfileFactory(
            business=biz,
            display_name=f"Test Business {i}",
            is_public=True,
        )
        businesses.append(biz)
    return businesses


@pytest.fixture
def sample_users(db):
    """Create sample users for testing."""
    users = []
    for i in range(3):
        u = UserFactory(is_verified=True)
        u.profile.first_name = f"User{i}"
        u.profile.save()
        users.append(u)
    return users


# =============================================================================
# Combined Endpoint Tests
# =============================================================================


@pytest.mark.django_db
class TestExploreCombinedView:
    """Tests for GET /api/v1/explore/"""

    def test_public_access(self, api_client):
        """Anonymous users can access combined endpoint."""
        with patch(
            "apps.explore.views.ExploreSelector.search_businesses"
        ) as mock_biz:
            mock_biz.return_value = MagicMock(
                __getitem__=lambda s, k: [],
                count=lambda: 0,
            )
            response = api_client.get(EXPLORE_BASE)
        assert response.status_code == status.HTTP_200_OK

    def test_response_structure_anonymous(self, api_client):
        """Anonymous users get businesses but no users."""
        with patch(
            "apps.explore.views.ExploreSelector.search_businesses"
        ) as mock_biz:
            mock_biz.return_value = MagicMock(
                __getitem__=lambda s, k: [],
                count=lambda: 0,
            )
            response = api_client.get(EXPLORE_BASE)

        data = response.data
        assert "businesses" in data
        assert "users" in data
        assert "businesses_count" in data
        assert "users_count" in data
        assert data["users"] == []
        assert data["users_count"] == 0

    def test_response_structure_authenticated(self, auth_client):
        """Authenticated users get both users and businesses."""
        with patch(
            "apps.explore.views.ExploreSelector.search_businesses"
        ) as mock_biz, patch(
            "apps.explore.views.ExploreSelector.search_users"
        ) as mock_users:
            mock_biz.return_value = MagicMock(
                __getitem__=lambda s, k: [],
                count=lambda: 0,
            )
            mock_users.return_value = MagicMock(
                __getitem__=lambda s, k: [],
                count=lambda: 0,
            )
            response = auth_client.get(EXPLORE_BASE)

        data = response.data
        assert "businesses" in data
        assert "users" in data

    def test_passes_query_param(self, api_client):
        """Query param q is passed to search methods."""
        with patch(
            "apps.explore.views.ExploreSelector.search_businesses"
        ) as mock_biz:
            mock_biz.return_value = MagicMock(
                __getitem__=lambda s, k: [],
                count=lambda: 0,
            )
            api_client.get(f"{EXPLORE_BASE}?q=test")
            mock_biz.assert_called_once_with(query="test", include_private=False)


# =============================================================================
# Business Search Tests
# =============================================================================


@pytest.mark.django_db
class TestExploreBusinessSearchView:
    """Tests for GET /api/v1/explore/businesses/"""

    def test_public_access(self, api_client):
        """Business search is public — no auth required."""
        with patch(
            "apps.explore.views.ExploreSelector.search_businesses"
        ) as mock_biz, patch(
            "apps.explore.views.StandardPagination.paginate_queryset",
            return_value=[],
        ), patch(
            "apps.explore.views.StandardPagination.get_paginated_response",
            return_value=DRFResponse({"count": 0, "results": []}),
        ):
            mock_biz.return_value = MagicMock()
            response = api_client.get(BUSINESSES_URL)

        assert response.status_code == status.HTTP_200_OK
        mock_biz.assert_called_once()

    def test_passes_all_filter_params(self, api_client):
        """All 10 filter params are correctly extracted and passed."""
        url = (
            f"{BUSINESSES_URL}"
            "?q=tech"
            "&country=US,GB"
            "&city=New+York"
            "&industry=Technology"
            "&company_size=11-50"
            "&business_type=llc"
            "&verified=true"
            "&is_platform_branch=false"
            "&tags=saas,tech"
            "&founded_year_min=2000"
            "&founded_year_max=2025"
            "&has_website=true"
            "&ordering=name"
        )
        with patch(
            "apps.explore.views.ExploreSelector.search_businesses"
        ) as mock_biz, patch(
            "apps.explore.views.StandardPagination.paginate_queryset",
            return_value=[],
        ), patch(
            "apps.explore.views.StandardPagination.get_paginated_response",
            return_value=DRFResponse({"count": 0, "results": []}),
        ):
            mock_biz.return_value = MagicMock()
            api_client.get(url)

        call_kwargs = mock_biz.call_args[1]
        assert call_kwargs["query"] == "tech"
        assert call_kwargs["country"] == ["US", "GB"]
        assert call_kwargs["city"] == ["New York"]
        assert call_kwargs["industry"] == ["Technology"]
        assert call_kwargs["company_size"] == ["11-50"]
        assert call_kwargs["business_type"] == ["llc"]
        assert call_kwargs["verified"] is True
        assert call_kwargs["is_platform_branch"] is False
        assert call_kwargs["tags"] == ["saas", "tech"]
        assert call_kwargs["founded_year_min"] == 2000
        assert call_kwargs["founded_year_max"] == 2025
        assert call_kwargs["has_website"] is True
        assert call_kwargs["ordering"] == "name"
        assert call_kwargs["include_private"] is False


# =============================================================================
# User Search Tests
# =============================================================================


@pytest.mark.django_db
class TestExploreUserSearchView:
    """Tests for GET /api/v1/explore/users/"""

    def test_requires_authentication(self, api_client):
        """User search requires authentication — 401 for anonymous."""
        response = api_client.get(USERS_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_access(self, auth_client):
        """Authenticated users can access user search."""
        with patch(
            "apps.explore.views.ExploreSelector.search_users"
        ) as mock_users, patch(
            "apps.explore.views.StandardPagination.paginate_queryset",
            return_value=[],
        ), patch(
            "apps.explore.views.StandardPagination.get_paginated_response",
            return_value=DRFResponse({"count": 0, "results": []}),
        ):
            mock_users.return_value = MagicMock()
            response = auth_client.get(USERS_URL)

        assert response.status_code == status.HTTP_200_OK
        mock_users.assert_called_once()

    def test_passes_user_filter_params(self, auth_client):
        """All 5 user filter params are correctly extracted."""
        url = (
            f"{USERS_URL}"
            "?q=john"
            "&country=US"
            "&city=New+York"
            "&language=en"
            "&verified=true"
            "&tags=developer"
            "&ordering=name"
        )
        with patch(
            "apps.explore.views.ExploreSelector.search_users"
        ) as mock_users, patch(
            "apps.explore.views.StandardPagination.paginate_queryset",
            return_value=[],
        ), patch(
            "apps.explore.views.StandardPagination.get_paginated_response",
            return_value=DRFResponse({"count": 0, "results": []}),
        ):
            mock_users.return_value = MagicMock()
            auth_client.get(url)

        call_kwargs = mock_users.call_args[1]
        assert call_kwargs["query"] == "john"
        assert call_kwargs["country"] == ["US"]
        assert call_kwargs["city"] == ["New York"]
        assert call_kwargs["language"] == "en"
        assert call_kwargs["verified"] is True
        assert call_kwargs["tags"] == ["developer"]
        assert call_kwargs["ordering"] == "name"


# =============================================================================
# Tag Suggest Tests
# =============================================================================


@pytest.mark.django_db
class TestExploreTagSuggestView:
    """Tests for GET /api/v1/explore/tags/"""

    def test_public_access(self, api_client):
        """Tag suggestions are public."""
        with patch(
            "apps.explore.views.ExploreSelector.suggest_tags"
        ) as mock_tags:
            mock_tags.return_value = []
            response = api_client.get(TAGS_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_returns_tag_list(self, api_client):
        """Returns serialized tag suggestions."""
        tag = SuggestedTagFactory(name="test-tag-view", usage_count=10)
        with patch(
            "apps.explore.views.ExploreSelector.suggest_tags"
        ) as mock_tags:
            mock_tags.return_value = [tag]
            response = api_client.get(f"{TAGS_URL}?q=test")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "test-tag-view"

    def test_passes_query_and_category(self, api_client):
        """Query and category params are forwarded."""
        with patch(
            "apps.explore.views.ExploreSelector.suggest_tags"
        ) as mock_tags:
            mock_tags.return_value = []
            api_client.get(f"{TAGS_URL}?q=dev&category=user")

        mock_tags.assert_called_once_with(
            query="dev", category="user", limit=20
        )

    def test_limit_param(self, api_client):
        """Custom limit is passed."""
        with patch(
            "apps.explore.views.ExploreSelector.suggest_tags"
        ) as mock_tags:
            mock_tags.return_value = []
            api_client.get(f"{TAGS_URL}?limit=5")

        mock_tags.assert_called_once_with(query="", category=None, limit=5)

    def test_limit_capped_at_50(self, api_client):
        """Limit cannot exceed 50."""
        with patch(
            "apps.explore.views.ExploreSelector.suggest_tags"
        ) as mock_tags:
            mock_tags.return_value = []
            api_client.get(f"{TAGS_URL}?limit=200")

        mock_tags.assert_called_once_with(query="", category=None, limit=50)


# =============================================================================
# City List Tests
# =============================================================================


@pytest.mark.django_db
class TestExploreCityListView:
    """Tests for GET /api/v1/explore/cities/"""

    def test_public_access(self, api_client):
        """City list is public."""
        response = api_client.get(f"{CITIES_URL}?country=US")
        assert response.status_code == status.HTTP_200_OK

    def test_returns_cities_for_country(self, api_client):
        """Returns city list for a valid country."""
        response = api_client.get(f"{CITIES_URL}?country=US")
        data = response.data
        assert data["country"] == "US"
        assert isinstance(data["cities"], list)
        assert len(data["cities"]) > 0
        assert "New York" in data["cities"]

    def test_empty_country(self, api_client):
        """Empty country returns empty list."""
        response = api_client.get(CITIES_URL)
        data = response.data
        assert data["country"] == ""
        assert data["cities"] == []

    def test_unknown_country(self, api_client):
        """Unknown country code returns empty list."""
        response = api_client.get(f"{CITIES_URL}?country=XX")
        data = response.data
        assert data["country"] == "XX"
        assert data["cities"] == []

    def test_case_insensitive(self, api_client):
        """Country code is case-insensitive."""
        response = api_client.get(f"{CITIES_URL}?country=us")
        data = response.data
        assert data["country"] == "US"
        assert len(data["cities"]) > 0


# =============================================================================
# Query Parameter Parsing Tests
# =============================================================================


class TestQueryParamHelpers:
    """Tests for helper functions _parse_csv, _parse_bool, _parse_int."""

    def test_parse_csv_single(self):
        from apps.explore.views import _parse_csv
        assert _parse_csv("US") == ["US"]

    def test_parse_csv_multiple(self):
        from apps.explore.views import _parse_csv
        assert _parse_csv("US,GB,DE") == ["US", "GB", "DE"]

    def test_parse_csv_with_spaces(self):
        from apps.explore.views import _parse_csv
        assert _parse_csv("US, GB, DE") == ["US", "GB", "DE"]

    def test_parse_csv_empty(self):
        from apps.explore.views import _parse_csv
        assert _parse_csv("") is None
        assert _parse_csv(None) is None

    def test_parse_bool_true(self):
        from apps.explore.views import _parse_bool
        assert _parse_bool("true") is True
        assert _parse_bool("1") is True
        assert _parse_bool("yes") is True

    def test_parse_bool_false(self):
        from apps.explore.views import _parse_bool
        assert _parse_bool("false") is False
        assert _parse_bool("0") is False

    def test_parse_bool_none(self):
        from apps.explore.views import _parse_bool
        assert _parse_bool(None) is None

    def test_parse_int_valid(self):
        from apps.explore.views import _parse_int
        assert _parse_int("42") == 42
        assert _parse_int("0") == 0

    def test_parse_int_invalid(self):
        from apps.explore.views import _parse_int
        assert _parse_int("abc") is None
        assert _parse_int(None) is None


# =============================================================================
# Visibility Integration Tests
# =============================================================================


@pytest.mark.django_db
class TestExploreVisibility:
    """Tests for visibility-aware explore behavior."""

    def test_combined_anonymous_passes_include_private_false(self, api_client):
        """Anonymous users get include_private=False for business search."""
        with patch(
            "apps.explore.views.ExploreSelector.search_businesses"
        ) as mock_biz:
            mock_biz.return_value = MagicMock(
                __getitem__=lambda s, k: [],
                count=lambda: 0,
            )
            api_client.get(EXPLORE_BASE)
            mock_biz.assert_called_once_with(query="", include_private=False)

    def test_combined_authenticated_passes_include_private_true(self, auth_client):
        """Authenticated users get include_private=True for business search."""
        with patch(
            "apps.explore.views.ExploreSelector.search_businesses"
        ) as mock_biz, patch(
            "apps.explore.views.ExploreSelector.search_users"
        ) as mock_users:
            mock_biz.return_value = MagicMock(
                __getitem__=lambda s, k: [],
                count=lambda: 0,
            )
            mock_users.return_value = MagicMock(
                __getitem__=lambda s, k: [],
                count=lambda: 0,
            )
            auth_client.get(EXPLORE_BASE)
            mock_biz.assert_called_once_with(query="", include_private=True)

    def test_business_search_authenticated_passes_include_private(self, auth_client):
        """Business search passes include_private=True for authenticated users."""
        with patch(
            "apps.explore.views.ExploreSelector.search_businesses"
        ) as mock_biz, patch(
            "apps.explore.views.StandardPagination.paginate_queryset",
            return_value=[],
        ), patch(
            "apps.explore.views.StandardPagination.get_paginated_response",
            return_value=DRFResponse({"count": 0, "results": []}),
        ):
            mock_biz.return_value = MagicMock()
            auth_client.get(BUSINESSES_URL)

        call_kwargs = mock_biz.call_args[1]
        assert call_kwargs["include_private"] is True

    def test_business_search_anonymous_passes_include_private_false(self, api_client):
        """Business search passes include_private=False for anonymous users."""
        with patch(
            "apps.explore.views.ExploreSelector.search_businesses"
        ) as mock_biz, patch(
            "apps.explore.views.StandardPagination.paginate_queryset",
            return_value=[],
        ), patch(
            "apps.explore.views.StandardPagination.get_paginated_response",
            return_value=DRFResponse({"count": 0, "results": []}),
        ):
            mock_biz.return_value = MagicMock()
            api_client.get(BUSINESSES_URL)

        call_kwargs = mock_biz.call_args[1]
        assert call_kwargs["include_private"] is False

    def test_business_output_includes_is_public(self, api_client, sample_businesses):
        """Business search results include is_public field."""
        biz = sample_businesses[0]
        with patch(
            "apps.explore.views.ExploreSelector.search_businesses"
        ) as mock_biz:
            mock_qs = MagicMock()
            mock_qs.__getitem__ = lambda s, k: [biz]
            mock_qs.count.return_value = 1
            mock_biz.return_value = mock_qs
            response = api_client.get(EXPLORE_BASE)

        data = response.data
        assert len(data["businesses"]) == 1
        assert "is_public" in data["businesses"][0]["profile"]

    def test_user_output_includes_is_public(self, auth_client, sample_users):
        """User search results include is_public field."""
        user_obj = sample_users[0]
        with patch(
            "apps.explore.views.ExploreSelector.search_businesses"
        ) as mock_biz, patch(
            "apps.explore.views.ExploreSelector.search_users"
        ) as mock_users:
            mock_biz.return_value = MagicMock(
                __getitem__=lambda s, k: [],
                count=lambda: 0,
            )
            mock_users_qs = MagicMock()
            mock_users_qs.__getitem__ = lambda s, k: [user_obj]
            mock_users_qs.count.return_value = 1
            mock_users.return_value = mock_users_qs
            response = auth_client.get(EXPLORE_BASE)

        data = response.data
        assert len(data["users"]) == 1
        assert "is_public" in data["users"][0]["profile"]

    def test_user_output_excludes_email(self, auth_client, sample_users):
        """User search results do NOT include email (T3 field)."""
        user_obj = sample_users[0]
        with patch(
            "apps.explore.views.ExploreSelector.search_businesses"
        ) as mock_biz, patch(
            "apps.explore.views.ExploreSelector.search_users"
        ) as mock_users:
            mock_biz.return_value = MagicMock(
                __getitem__=lambda s, k: [],
                count=lambda: 0,
            )
            mock_users_qs = MagicMock()
            mock_users_qs.__getitem__ = lambda s, k: [user_obj]
            mock_users_qs.count.return_value = 1
            mock_users.return_value = mock_users_qs
            response = auth_client.get(EXPLORE_BASE)

        data = response.data
        assert len(data["users"]) == 1
        # email is a T3 field — should NOT be in explore output
        assert "email" not in data["users"][0]
