# apps/explore/tests/test_selectors.py
"""
Tests for ExploreSelector — FTS + Trigram search queries.

These tests require PostgreSQL (FTS, trigram, ArrayField overlap don't work
on SQLite). Marked with requires_postgres and skipped in unit test suite.
"""

import pytest
from django.conf import settings

from apps.core.constants import (
    BusinessStatus,
    BusinessType,
    CompanySize,
    VerificationStatus,
)
from apps.explore.models import TagCategory
from apps.explore.selectors import ExploreSelector
from apps.explore.tests.factories import SuggestedTagFactory
from apps.organization.tests.factories import (
    BusinessAccountFactory,
    BusinessProfileFactory,
)
from apps.users.tests.factories import UserFactory

requires_postgres = pytest.mark.skipif(
    "sqlite" in settings.DATABASES["default"]["ENGINE"],
    reason="Requires PostgreSQL (FTS/Trigram)",
)


# =============================================================================
# Business Search Tests
# =============================================================================


@requires_postgres
@pytest.mark.django_db
class TestSearchBusinesses:
    """Tests for ExploreSelector.search_businesses()."""

    def _create_business(self, **overrides):
        """Helper to create a business with profile."""
        account_kwargs = {}
        profile_kwargs = {"is_public": True}

        for key, val in overrides.items():
            if key in (
                "display_name", "tagline", "description", "industry",
                "company_size", "founded_year", "tags", "website",
                "is_public",
            ):
                profile_kwargs[key] = val
            else:
                account_kwargs[key] = val

        account_kwargs.setdefault("status", BusinessStatus.ACTIVE)
        account = BusinessAccountFactory(**account_kwargs)
        BusinessProfileFactory(business=account, **profile_kwargs)
        return account

    def test_returns_active_public_businesses(self):
        self._create_business(display_name="Active Biz")
        self._create_business(
            display_name="Inactive",
            status=BusinessStatus.SUSPENDED,
        )
        results = ExploreSelector.search_businesses()
        assert results.count() >= 1
        names = [b.profile.display_name for b in results]
        assert "Active Biz" in names
        assert "Inactive" not in names

    def test_excludes_non_public(self):
        self._create_business(display_name="Public Biz")
        self._create_business(display_name="Private Biz", is_public=False)
        results = ExploreSelector.search_businesses()
        names = [b.profile.display_name for b in results]
        assert "Public Biz" in names
        assert "Private Biz" not in names

    def test_fts_search_by_name(self):
        self._create_business(display_name="Quantum Computing Inc")
        self._create_business(display_name="Pizza Palace")
        results = ExploreSelector.search_businesses(query="quantum")
        assert results.count() >= 1
        assert results.first().profile.display_name == "Quantum Computing Inc"

    def test_trigram_typo_tolerance(self):
        self._create_business(display_name="Amazon Web Services")
        results = ExploreSelector.search_businesses(query="amazn")
        assert results.count() >= 1

    def test_filter_by_country(self):
        self._create_business(display_name="US Biz", country="US")
        self._create_business(display_name="UK Biz", country="GB")
        results = ExploreSelector.search_businesses(country=["US"])
        names = [b.profile.display_name for b in results]
        assert "US Biz" in names
        assert "UK Biz" not in names

    def test_filter_by_city(self):
        self._create_business(display_name="NYC Biz", city="New York")
        self._create_business(display_name="LA Biz", city="Los Angeles")
        results = ExploreSelector.search_businesses(city=["New York"])
        names = [b.profile.display_name for b in results]
        assert "NYC Biz" in names
        assert "LA Biz" not in names

    def test_filter_by_industry(self):
        self._create_business(display_name="Tech Co", industry="Technology")
        self._create_business(display_name="Health Co", industry="Healthcare")
        results = ExploreSelector.search_businesses(industry=["Technology"])
        names = [b.profile.display_name for b in results]
        assert "Tech Co" in names
        assert "Health Co" not in names

    def test_filter_by_company_size(self):
        self._create_business(
            display_name="Small",
            company_size=CompanySize.SIZE_2_10,
        )
        self._create_business(
            display_name="Big",
            company_size=CompanySize.SIZE_500_PLUS,
        )
        results = ExploreSelector.search_businesses(
            company_size=[CompanySize.SIZE_2_10]
        )
        names = [b.profile.display_name for b in results]
        assert "Small" in names
        assert "Big" not in names

    def test_filter_by_business_type(self):
        self._create_business(
            display_name="LLC Biz",
            business_type=BusinessType.LLC,
        )
        self._create_business(
            display_name="Corp Biz",
            business_type=BusinessType.CORPORATION,
        )
        results = ExploreSelector.search_businesses(
            business_type=[BusinessType.LLC]
        )
        names = [b.profile.display_name for b in results]
        assert "LLC Biz" in names
        assert "Corp Biz" not in names

    def test_filter_by_verified(self):
        self._create_business(
            display_name="Verified",
            verification_status=VerificationStatus.VERIFIED,
        )
        self._create_business(
            display_name="Unverified",
            verification_status=VerificationStatus.UNVERIFIED,
        )
        results = ExploreSelector.search_businesses(verified=True)
        names = [b.profile.display_name for b in results]
        assert "Verified" in names
        assert "Unverified" not in names

    def test_filter_by_platform_branch(self):
        self._create_business(
            display_name="Branch", is_platform_branch=True
        )
        self._create_business(
            display_name="Regular", is_platform_branch=False
        )
        results = ExploreSelector.search_businesses(is_platform_branch=True)
        names = [b.profile.display_name for b in results]
        assert "Branch" in names
        assert "Regular" not in names

    def test_filter_by_tags(self):
        self._create_business(display_name="Techy", tags=["tech", "saas"])
        self._create_business(display_name="Foody", tags=["food", "organic"])
        results = ExploreSelector.search_businesses(tags=["tech"])
        names = [b.profile.display_name for b in results]
        assert "Techy" in names
        assert "Foody" not in names

    def test_filter_by_founded_year_range(self):
        self._create_business(display_name="Old", founded_year=2000)
        self._create_business(display_name="New", founded_year=2023)
        results = ExploreSelector.search_businesses(
            founded_year_min=2020, founded_year_max=2025
        )
        names = [b.profile.display_name for b in results]
        assert "New" in names
        assert "Old" not in names

    def test_filter_by_has_website(self):
        self._create_business(
            display_name="With Site", website="https://example.com"
        )
        self._create_business(display_name="No Site", website="")
        results = ExploreSelector.search_businesses(has_website=True)
        names = [b.profile.display_name for b in results]
        assert "With Site" in names
        assert "No Site" not in names

    def test_ordering_by_name(self):
        self._create_business(display_name="Zebra Co")
        self._create_business(display_name="Alpha Co")
        results = ExploreSelector.search_businesses(ordering="name")
        names = [b.profile.display_name for b in results]
        assert names.index("Alpha Co") < names.index("Zebra Co")

    def test_ordering_by_newest(self):
        old = self._create_business(display_name="Old Biz")
        new = self._create_business(display_name="New Biz")
        results = ExploreSelector.search_businesses(ordering="newest")
        ids = [b.id for b in results]
        assert ids.index(new.id) < ids.index(old.id)

    def test_combined_filters(self):
        self._create_business(
            display_name="Match",
            country="US",
            industry="Technology",
            tags=["saas"],
        )
        self._create_business(
            display_name="No Match Country",
            country="GB",
            industry="Technology",
            tags=["saas"],
        )
        self._create_business(
            display_name="No Match Industry",
            country="US",
            industry="Healthcare",
            tags=["saas"],
        )
        results = ExploreSelector.search_businesses(
            country=["US"], industry=["Technology"], tags=["saas"]
        )
        names = [b.profile.display_name for b in results]
        assert "Match" in names
        assert "No Match Country" not in names
        assert "No Match Industry" not in names


# =============================================================================
# User Search Tests
# =============================================================================


@requires_postgres
@pytest.mark.django_db
class TestSearchUsers:
    """Tests for ExploreSelector.search_users()."""

    def _create_user(self, **profile_kwargs):
        """Helper to create a user with profile data."""
        user = UserFactory(is_verified=True)
        profile = user.profile
        for key, val in profile_kwargs.items():
            setattr(profile, key, val)
        profile.save()
        return user

    def test_returns_active_users(self):
        active = self._create_user(first_name="Active")
        inactive = UserFactory(is_active=False)
        results = ExploreSelector.search_users()
        ids = [u.id for u in results]
        assert active.id in ids
        assert inactive.id not in ids

    def test_fts_search_by_username(self):
        user = UserFactory(username="johndeveloper", is_verified=True)
        results = ExploreSelector.search_users(query="johndeveloper")
        assert results.count() >= 1

    def test_fts_search_by_name(self):
        self._create_user(first_name="Alexander", last_name="Hamilton")
        results = ExploreSelector.search_users(query="alexander hamilton")
        assert results.count() >= 1

    def test_fts_search_by_bio(self):
        self._create_user(bio="Full-stack developer specializing in Python")
        results = ExploreSelector.search_users(query="python developer")
        assert results.count() >= 1

    def test_filter_by_country(self):
        self._create_user(first_name="USUser", country="US")
        self._create_user(first_name="UKUser", country="GB")
        results = ExploreSelector.search_users(country=["US"])
        names = [u.profile.first_name for u in results]
        assert "USUser" in names
        assert "UKUser" not in names

    def test_filter_by_city(self):
        self._create_user(first_name="NYer", city="New York")
        self._create_user(first_name="LAer", city="Los Angeles")
        results = ExploreSelector.search_users(city=["New York"])
        names = [u.profile.first_name for u in results]
        assert "NYer" in names
        assert "LAer" not in names

    def test_filter_by_language(self):
        self._create_user(first_name="English", language="en")
        self._create_user(first_name="French", language="fr")
        results = ExploreSelector.search_users(language="en")
        names = [u.profile.first_name for u in results]
        assert "English" in names
        assert "French" not in names

    def test_filter_by_verified(self):
        verified = UserFactory(is_verified=True)
        unverified = UserFactory(is_verified=False)
        results = ExploreSelector.search_users(verified=True)
        ids = [u.id for u in results]
        assert verified.id in ids
        assert unverified.id not in ids

    def test_filter_by_tags(self):
        self._create_user(first_name="Dev", tags=["developer", "python"])
        self._create_user(first_name="Designer", tags=["designer", "ui"])
        results = ExploreSelector.search_users(tags=["developer"])
        names = [u.profile.first_name for u in results]
        assert "Dev" in names
        assert "Designer" not in names

    def test_fts_search_by_email(self):
        user = UserFactory(email="unique_searchemail@example.com", is_verified=True)
        results = ExploreSelector.search_users(query="unique_searchemail")
        ids = [u.id for u in results]
        assert user.id in ids

    def test_exact_email_match(self):
        user = UserFactory(email="exact_match@example.com", is_verified=True)
        results = ExploreSelector.search_users(query="exact_match@example.com")
        assert results.count() == 1
        assert results.first().id == user.id
        assert results.first().search_rank == 1.0

    def test_ordering_by_name(self):
        UserFactory(username="zebra_user", is_verified=True)
        UserFactory(username="alpha_user", is_verified=True)
        results = ExploreSelector.search_users(ordering="name")
        usernames = [u.username for u in results]
        assert usernames.index("alpha_user") < usernames.index("zebra_user")


# =============================================================================
# Tag Suggestion Tests
# =============================================================================


@requires_postgres
@pytest.mark.django_db
class TestSuggestTags:
    """Tests for ExploreSelector.suggest_tags()."""

    def test_returns_active_tags(self):
        SuggestedTagFactory(name="active-tag", is_active=True)
        SuggestedTagFactory(name="inactive-tag", is_active=False)
        results = ExploreSelector.suggest_tags()
        names = [t.name for t in results]
        assert "active-tag" in names
        assert "inactive-tag" not in names

    def test_filter_by_category_user(self):
        SuggestedTagFactory(name="user-tag", category=TagCategory.USER, usage_count=9999)
        SuggestedTagFactory(name="biz-tag", category=TagCategory.BUSINESS, usage_count=9999)
        SuggestedTagFactory(name="both-tag", category=TagCategory.BOTH, usage_count=9999)
        results = ExploreSelector.suggest_tags(category="user")
        names = [t.name for t in results]
        assert "user-tag" in names
        assert "both-tag" in names  # "both" includes "user"
        assert "biz-tag" not in names

    def test_filter_by_category_business(self):
        SuggestedTagFactory(name="user-tag2", category=TagCategory.USER, usage_count=9999)
        SuggestedTagFactory(name="biz-tag2", category=TagCategory.BUSINESS, usage_count=9999)
        SuggestedTagFactory(name="both-tag2", category=TagCategory.BOTH, usage_count=9999)
        results = ExploreSelector.suggest_tags(category="business")
        names = [t.name for t in results]
        assert "biz-tag2" in names
        assert "both-tag2" in names
        assert "user-tag2" not in names

    def test_trigram_search(self):
        SuggestedTagFactory(name="xylotechnology", usage_count=10)
        SuggestedTagFactory(name="xylopizza", usage_count=5)
        results = ExploreSelector.suggest_tags(query="xylotechno")
        names = [t.name for t in results]
        assert "xylotechnology" in names

    def test_limit(self):
        for i in range(10):
            SuggestedTagFactory(name=f"xylo-limited-tag-{i}")
        results = ExploreSelector.suggest_tags(limit=5)
        assert len(results) <= 5

    def test_ordered_by_usage_count(self):
        SuggestedTagFactory(name="xylo-popular", usage_count=99999)
        SuggestedTagFactory(name="xylo-niche", usage_count=1)
        results = ExploreSelector.suggest_tags()
        names = [t.name for t in results]
        assert names.index("xylo-popular") < names.index("xylo-niche")
