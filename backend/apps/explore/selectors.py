"""
Explore Selectors — Read-only queries for search and discovery.

Provides FTS (Full-Text Search) + Trigram similarity search for
businesses and users, with entity-specific filters.

PostgreSQL-specific: Uses SearchVector, SearchQuery, SearchRank,
TrigramSimilarity. These will NOT work on SQLite.
"""

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramSimilarity,
)
import operator
from functools import reduce

from django.db.models import FloatField, Q, QuerySet, Value
from django.db.models.functions import Coalesce, Greatest

from apps.core.constants import BusinessStatus, VerificationStatus
from apps.explore.models import SuggestedTag
from apps.organization.business.models import BusinessAccount
from apps.users.models import User


class ExploreSelector:
    """Search and discovery queries for the explore system."""

    # -------------------------------------------------------------------------
    # Business Search
    # -------------------------------------------------------------------------

    @staticmethod
    def search_businesses(
        *,
        query: str = "",
        country: list[str] | None = None,
        city: list[str] | None = None,
        industry: list[str] | None = None,
        company_size: list[str] | None = None,
        business_type: list[str] | None = None,
        verified: bool | None = None,
        is_platform_branch: bool | None = None,
        tags: list[str] | None = None,
        founded_year_min: int | None = None,
        founded_year_max: int | None = None,
        has_website: bool | None = None,
        ordering: str = "relevance",
        include_private: bool = False,
    ) -> QuerySet[BusinessAccount]:
        """
        Search businesses with FTS + trigram and entity-specific filters.

        Only returns active, non-deleted businesses. By default only public
        profiles are returned; set include_private=True for authenticated
        users to discover private businesses too.
        """
        qs = (
            BusinessAccount.objects
            .filter(
                status=BusinessStatus.ACTIVE,
                is_deleted=False,
            )
            .select_related("profile")
        )
        if not include_private:
            qs = qs.filter(profile__is_public=True)

        # --- Text search ---
        if query and query.strip():
            q = query.strip()

            # FTS: weighted search vector
            search_vector = (
                SearchVector("profile__display_name", weight="A")
                + SearchVector("legal_name", weight="A")
                + SearchVector("profile__tagline", weight="B")
                + SearchVector("profile__industry", weight="B")
                + SearchVector("profile__description", weight="C")
            )
            search_query = SearchQuery(q, search_type="websearch")
            fts_rank = SearchRank(search_vector, search_query)

            # Trigram: similarity on name fields
            trigram_rank = Greatest(
                TrigramSimilarity("profile__display_name", q),
                TrigramSimilarity("legal_name", q),
                output_field=FloatField(),
            )

            # Combined score: FTS primary, trigram as fallback (scaled)
            search_rank = Greatest(
                Coalesce(fts_rank, Value(0.0, output_field=FloatField())),
                Coalesce(trigram_rank * 0.5, Value(0.0, output_field=FloatField())),
                output_field=FloatField(),
            )

            qs = qs.annotate(
                search_rank=search_rank,
            ).filter(
                Q(search_rank__gt=0.01)  # Any non-trivial match
            )
        else:
            qs = qs.annotate(
                search_rank=Value(0.0, output_field=FloatField()),
            )

        # --- Filters ---
        if country:
            qs = qs.filter(country__in=country)
        if city:
            qs = qs.filter(city__in=city)
        if industry:
            qs = qs.filter(profile__industry__in=industry)
        if company_size:
            qs = qs.filter(profile__company_size__in=company_size)
        if business_type:
            qs = qs.filter(business_type__in=business_type)
        if verified is True:
            qs = qs.filter(verification_status=VerificationStatus.VERIFIED)
        if is_platform_branch is not None:
            qs = qs.filter(is_platform_branch=is_platform_branch)
        if tags:
            tag_q = reduce(operator.or_, [Q(profile__tags__contains=tag) for tag in tags])
            qs = qs.filter(tag_q)
        if founded_year_min is not None:
            qs = qs.filter(profile__founded_year__gte=founded_year_min)
        if founded_year_max is not None:
            qs = qs.filter(profile__founded_year__lte=founded_year_max)
        if has_website is True:
            qs = qs.exclude(profile__website="")

        # --- Ordering ---
        if ordering == "name":
            qs = qs.order_by("profile__display_name")
        elif ordering == "newest":
            qs = qs.order_by("-created_at")
        else:
            # Default: relevance (search_rank desc, then newest)
            qs = qs.order_by("-search_rank", "-created_at")

        return qs

    # -------------------------------------------------------------------------
    # User Search
    # -------------------------------------------------------------------------

    @staticmethod
    def search_users(
        *,
        query: str = "",
        country: list[str] | None = None,
        city: list[str] | None = None,
        language: str | None = None,
        verified: bool | None = None,
        tags: list[str] | None = None,
        ordering: str = "relevance",
    ) -> QuerySet[User]:
        """
        Search users with FTS + trigram and entity-specific filters.

        Returns active users with profiles. Both public and private users
        are included; the view layer applies visibility filtering.
        """
        qs = (
            User.objects
            .filter(is_active=True)
            .select_related("profile")
        )

        # --- Text search ---
        if query and query.strip():
            q = query.strip()

            # Exact email match — if the query looks like an email, try exact match first
            if "@" in q:
                exact_match = qs.filter(email__iexact=q)
                if exact_match.exists():
                    return exact_match.annotate(
                        search_rank=Value(1.0, output_field=FloatField()),
                    )

            search_vector = (
                SearchVector("username", weight="A")
                + SearchVector("email", weight="A")
                + SearchVector("profile__first_name", weight="A")
                + SearchVector("profile__last_name", weight="A")
                + SearchVector("profile__bio", weight="B")
            )
            search_query = SearchQuery(q, search_type="websearch")
            fts_rank = SearchRank(search_vector, search_query)

            trigram_rank = Greatest(
                TrigramSimilarity("username", q),
                TrigramSimilarity("email", q),
                TrigramSimilarity("profile__first_name", q),
                TrigramSimilarity("profile__last_name", q),
                output_field=FloatField(),
            )

            search_rank = Greatest(
                Coalesce(fts_rank, Value(0.0, output_field=FloatField())),
                Coalesce(trigram_rank * 0.5, Value(0.0, output_field=FloatField())),
                output_field=FloatField(),
            )

            qs = qs.annotate(
                search_rank=search_rank,
            ).filter(
                Q(search_rank__gt=0.01)
            )
        else:
            qs = qs.annotate(
                search_rank=Value(0.0, output_field=FloatField()),
            )

        # --- Filters ---
        if country:
            qs = qs.filter(profile__country__in=country)
        if city:
            qs = qs.filter(profile__city__in=city)
        if language:
            qs = qs.filter(profile__language=language)
        if verified is True:
            qs = qs.filter(is_verified=True)
        if tags:
            tag_q = reduce(operator.or_, [Q(profile__tags__contains=tag) for tag in tags])
            qs = qs.filter(tag_q)

        # --- Ordering ---
        if ordering == "name":
            qs = qs.order_by("username")
        elif ordering == "newest":
            qs = qs.order_by("-date_joined")
        else:
            qs = qs.order_by("-search_rank", "-date_joined")

        return qs

    # -------------------------------------------------------------------------
    # Tag Suggestions
    # -------------------------------------------------------------------------

    @staticmethod
    def suggest_tags(
        *,
        query: str = "",
        category: str | None = None,
        limit: int = 20,
    ) -> QuerySet[SuggestedTag]:
        """
        Suggest tags for autocomplete.

        When a query is provided, uses trigram similarity for fuzzy matching.
        When no query, returns popular tags sorted by usage_count.
        """
        qs = SuggestedTag.objects.filter(is_active=True)

        # Filter by category (user/business also includes "both")
        if category in ("user", "business"):
            qs = qs.filter(Q(category=category) | Q(category="both"))

        if query and query.strip():
            q = query.strip()
            qs = qs.annotate(
                similarity=TrigramSimilarity("name", q),
            ).filter(
                similarity__gt=0.1,
            ).order_by("-similarity", "-usage_count")
        else:
            qs = qs.order_by("-usage_count", "name")

        return qs[:limit]
