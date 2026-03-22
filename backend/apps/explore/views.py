"""
Explore Views — API endpoints for search and discovery.

Endpoints:
    GET /api/v1/explore/            — Combined search (All tab)
    GET /api/v1/explore/businesses/ — Business search (public)
    GET /api/v1/explore/users/      — User search (authenticated)
    GET /api/v1/explore/tags/       — Tag autocomplete (public)
    GET /api/v1/explore/cities/     — City list by country (public)
"""

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
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

    @extend_schema(
        summary="Combined search across all entities",
        description=(
            "Returns top results from each entity type for the 'All' tab. "
            "Businesses are always included; users are only included for "
            "authenticated requests. Returns up to 6 results per section."
        ),
        tags=["Explore"],
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search query text",
                required=False,
            ),
        ],
        responses={
            200: ExploreCombinedOutput,
        },
    )
    def get(self, request):
        query = request.query_params.get("q", "")
        is_auth = request.user and request.user.is_authenticated

        # Businesses (always visible; authenticated users discover private too)
        biz_qs = ExploreSelector.search_businesses(
            query=query,
            include_private=is_auth,
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

    @extend_schema(
        summary="Search businesses",
        description=(
            "Full-text + trigram search for businesses with 11 filters and pagination. "
            "Public endpoint; authenticated users also see private businesses."
        ),
        tags=["Explore"],
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search query text",
                required=False,
            ),
            OpenApiParameter(
                name="country",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by country codes (comma-separated)",
                required=False,
            ),
            OpenApiParameter(
                name="city",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by cities (comma-separated)",
                required=False,
            ),
            OpenApiParameter(
                name="industry",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by industries (comma-separated)",
                required=False,
            ),
            OpenApiParameter(
                name="company_size",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by company size (comma-separated)",
                required=False,
            ),
            OpenApiParameter(
                name="business_type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by business type (comma-separated)",
                required=False,
            ),
            OpenApiParameter(
                name="verified",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Filter by verification status",
                required=False,
            ),
            OpenApiParameter(
                name="is_platform_branch",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Filter by platform branch status",
                required=False,
            ),
            OpenApiParameter(
                name="tags",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by tags (comma-separated)",
                required=False,
            ),
            OpenApiParameter(
                name="founded_year_min",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Minimum founding year",
                required=False,
            ),
            OpenApiParameter(
                name="founded_year_max",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Maximum founding year",
                required=False,
            ),
            OpenApiParameter(
                name="has_website",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Filter by website presence",
                required=False,
            ),
            OpenApiParameter(
                name="ordering",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Sort order: relevance (default), name, newest",
                required=False,
            ),
        ],
        responses={
            200: ExploreBusinessOutput(many=True),
        },
    )
    def get(self, request):
        params = _extract_business_params(request)
        is_auth = request.user and request.user.is_authenticated
        qs = ExploreSelector.search_businesses(
            **params,
            include_private=is_auth,
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

    @extend_schema(
        summary="Search users",
        description="Full-text + trigram search for users with filters and pagination. Requires authentication.",
        tags=["Explore"],
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search query text",
                required=False,
            ),
            OpenApiParameter(
                name="country",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by country codes (comma-separated)",
                required=False,
            ),
            OpenApiParameter(
                name="city",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by cities (comma-separated)",
                required=False,
            ),
            OpenApiParameter(
                name="language",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by language",
                required=False,
            ),
            OpenApiParameter(
                name="verified",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Filter by verification status",
                required=False,
            ),
            OpenApiParameter(
                name="tags",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by tags (comma-separated)",
                required=False,
            ),
            OpenApiParameter(
                name="ordering",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Sort order: relevance (default), name, newest",
                required=False,
            ),
        ],
        responses={
            200: ExploreUserOutput(many=True),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def get(self, request):
        params = _extract_user_params(request)
        qs = ExploreSelector.search_users(**params)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = ExploreUserOutput(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class ExploreTagSuggestView(APIView):
    """
    GET /api/v1/explore/tags/

    Tag autocomplete suggestions. Public.
    Query params: q (search text), category (user/business).
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get tag suggestions",
        description="Autocomplete tag suggestions filtered by query text and optional category.",
        tags=["Explore"],
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search text for autocomplete",
                required=False,
            ),
            OpenApiParameter(
                name="category",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by tag category (user, business)",
                required=False,
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Max results (default: 20, max: 50)",
                required=False,
            ),
        ],
        responses={
            200: SuggestedTagOutput(many=True),
        },
    )
    def get(self, request):
        query = request.query_params.get("q", "")
        category = request.query_params.get("category")
        limit = _parse_int(request.query_params.get("limit")) or 20
        limit = min(limit, 50)  # Cap at 50

        tags = ExploreSelector.suggest_tags(query=query, category=category, limit=limit)
        serializer = SuggestedTagOutput(tags, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExploreCityListView(APIView):
    """
    GET /api/v1/explore/cities/

    City list for a given country code. Public.
    Query params: country (ISO 3166-1 alpha-2).
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="List cities for a country",
        description="Returns a list of cities for the given ISO 3166-1 alpha-2 country code.",
        tags=["Explore"],
        parameters=[
            OpenApiParameter(
                name="country",
                type=str,
                location=OpenApiParameter.QUERY,
                description="ISO 3166-1 alpha-2 country code (e.g., US, GB)",
                required=False,
            ),
        ],
        responses={
            200: CityListOutput,
        },
    )
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
