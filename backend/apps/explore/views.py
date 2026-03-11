"""
Explore Views — API endpoints for search and discovery.

Endpoints:
    GET /api/v1/explore/            — Combined search (All tab)
    GET /api/v1/explore/businesses/ — Business search (public)
    GET /api/v1/explore/users/      — User search (authenticated)
    GET /api/v1/explore/tags/       — Tag autocomplete (public)
    GET /api/v1/explore/cities/     — City list by country (public)
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination
from apps.core.permissions import AllowAny, IsAuthenticated
from apps.core.utils.city_data import get_cities_for_country
from apps.explore.selectors import ExploreSelector
from apps.explore.serializers import (
    CityListOutput,
    ExploreBusinessOutput,
    ExploreCombinedOutput,
    ExploreUserOutput,
    SuggestedTagOutput,
)


# =============================================================================
# Query parameter helpers
# =============================================================================


def _parse_csv(value: str | None) -> list[str] | None:
    """Parse comma-separated query param into a list, or None."""
    if not value:
        return None
    parts = [v.strip() for v in value.split(",") if v.strip()]
    return parts or None


def _parse_bool(value: str | None) -> bool | None:
    """Parse boolean query param (true/1 → True, false/0 → False, else None)."""
    if value is None:
        return None
    return value.lower() in ("true", "1", "yes")


def _parse_int(value: str | None) -> int | None:
    """Parse integer query param, or None."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _extract_business_params(request) -> dict:
    """Extract business search params from request query params."""
    params = request.query_params
    return {
        "query": params.get("q", ""),
        "country": _parse_csv(params.get("country")),
        "city": _parse_csv(params.get("city")),
        "industry": _parse_csv(params.get("industry")),
        "company_size": _parse_csv(params.get("company_size")),
        "business_type": _parse_csv(params.get("business_type")),
        "verified": _parse_bool(params.get("verified")),
        "is_platform_branch": _parse_bool(params.get("is_platform_branch")),
        "tags": _parse_csv(params.get("tags")),
        "founded_year_min": _parse_int(params.get("founded_year_min")),
        "founded_year_max": _parse_int(params.get("founded_year_max")),
        "has_website": _parse_bool(params.get("has_website")),
        "ordering": params.get("ordering", "relevance"),
    }


def _extract_user_params(request) -> dict:
    """Extract user search params from request query params."""
    params = request.query_params
    return {
        "query": params.get("q", ""),
        "country": _parse_csv(params.get("country")),
        "city": _parse_csv(params.get("city")),
        "language": params.get("language"),
        "verified": _parse_bool(params.get("verified")),
        "tags": _parse_csv(params.get("tags")),
        "ordering": params.get("ordering", "relevance"),
    }


# =============================================================================
# Views
# =============================================================================


class ExploreCombinedView(APIView):
    """
    GET /api/v1/explore/

    Combined search for the "All" tab. Returns top 6 businesses (always)
    and top 6 users (only if authenticated).
    """

    permission_classes = [AllowAny]

    SECTION_LIMIT = 6

    def get(self, request):
        query = request.query_params.get("q", "")
        is_auth = request.user and request.user.is_authenticated

        # Businesses (always visible; authenticated users discover private too)
        biz_qs = ExploreSelector.search_businesses(
            query=query, include_private=is_auth,
        )
        biz_results = biz_qs[: self.SECTION_LIMIT]
        biz_count = biz_qs.count()

        # Users (only for authenticated users)
        if request.user and request.user.is_authenticated:
            user_qs = ExploreSelector.search_users(query=query)
            user_results = user_qs[: self.SECTION_LIMIT]
            user_count = user_qs.count()
        else:
            user_results = []
            user_count = 0

        data = {
            "users": ExploreUserOutput(
                user_results, many=True, context={"request": request}
            ).data,
            "businesses": ExploreBusinessOutput(
                biz_results, many=True, context={"request": request}
            ).data,
            "users_count": user_count,
            "businesses_count": biz_count,
        }

        return Response(data, status=status.HTTP_200_OK)


class ExploreBusinessSearchView(APIView):
    """
    GET /api/v1/explore/businesses/

    Business search with 10 filters + pagination. Public.
    """

    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get(self, request):
        params = _extract_business_params(request)
        is_auth = request.user and request.user.is_authenticated
        qs = ExploreSelector.search_businesses(
            **params, include_private=is_auth,
        )

        # Paginate
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = ExploreBusinessOutput(
            page, many=True, context={"request": request}
        )
        return paginator.get_paginated_response(serializer.data)


class ExploreUserSearchView(APIView):
    """
    GET /api/v1/explore/users/

    User search with 5 filters + pagination. Requires authentication.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get(self, request):
        params = _extract_user_params(request)
        qs = ExploreSelector.search_users(**params)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = ExploreUserOutput(
            page, many=True, context={"request": request}
        )
        return paginator.get_paginated_response(serializer.data)


class ExploreTagSuggestView(APIView):
    """
    GET /api/v1/explore/tags/

    Tag autocomplete suggestions. Public.
    Query params: q (search text), category (user/business).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "")
        category = request.query_params.get("category")
        limit = _parse_int(request.query_params.get("limit")) or 20
        limit = min(limit, 50)  # Cap at 50

        tags = ExploreSelector.suggest_tags(
            query=query, category=category, limit=limit
        )
        serializer = SuggestedTagOutput(tags, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExploreCityListView(APIView):
    """
    GET /api/v1/explore/cities/

    City list for a given country code. Public.
    Query params: country (ISO 3166-1 alpha-2).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        country = request.query_params.get("country", "")
        if not country:
            return Response(
                {"country": "", "cities": []},
                status=status.HTTP_200_OK,
            )

        cities = get_cities_for_country(country)
        serializer = CityListOutput({"country": country.upper(), "cities": cities})
        return Response(serializer.data, status=status.HTTP_200_OK)
