# apps/organization/tests/factories.py
"""
Factory-boy factories for Organization app tests.

Usage:
    from apps.organization.tests.factories import BusinessAccountFactory

    # Create a business
    business = BusinessAccountFactory()

    # Create with specific attributes
    business = BusinessAccountFactory(legal_name="Acme Corp", country="US")

    # Build without saving to DB
    business = BusinessAccountFactory.build()
"""

import factory
from factory.django import DjangoModelFactory

from apps.core.constants import (
    BusinessStatus,
    BusinessType,
    CompanySize,
    VerificationStatus,
)
from apps.organization.business.models import (
    BusinessAccount,
    BusinessProfile,
    BusinessSlugHistory,
)
from apps.organization.platform.models import PlatformAccount, PlatformProfile
from apps.users.tests.factories import (  # noqa: F401
    StaffUserFactory,
    SuperuserFactory,
    UserFactory,
)

# =============================================================================
# PLATFORM FACTORIES
# =============================================================================


class PlatformAccountFactory(DjangoModelFactory):
    """
    Factory for PlatformAccount.

    Note: Uses get_or_create to ensure singleton behavior in tests.
    """

    class Meta:
        model = PlatformAccount
        django_get_or_create = ("singleton_key",)  # Ensures singleton in tests

    singleton_key = 1  # DB constraint requires this
    is_configured = True
    max_members = 5  # Matches production default
    open_member_request = False
    settings = factory.LazyFunction(dict)


class PlatformProfileFactory(DjangoModelFactory):
    """Factory for PlatformProfile."""

    class Meta:
        model = PlatformProfile

    platform = factory.SubFactory(PlatformAccountFactory)
    name = "Test Platform"
    tagline = "Your Test Platform"
    description = "A test platform for unit testing."
    primary_color = "#000000"
    secondary_color = "#ffffff"
    contact_email = "platform@example.com"
    contact_phone = "+1234567890"


# =============================================================================
# BUSINESS FACTORIES
# =============================================================================


class BusinessAccountFactory(DjangoModelFactory):
    """Factory for BusinessAccount."""

    class Meta:
        model = BusinessAccount

    legal_name = factory.Sequence(lambda n: f"Test Business {n}")
    slug = factory.LazyAttribute(lambda obj: obj.legal_name.lower().replace(" ", "-"))
    country = "US"
    city = ""
    business_type = BusinessType.LLC
    status = BusinessStatus.ACTIVE
    verification_status = VerificationStatus.UNVERIFIED
    registration_number = factory.Sequence(lambda n: f"REG-{n:06d}")
    tax_id = factory.Sequence(lambda n: f"TAX-{n:06d}")
    is_platform_branch = False
    max_members = 6  # Test convenience (production default is 1)
    open_member_request = False
    legal_address = "123 Test Street, Test City, TC 12345"
    settings = factory.LazyFunction(dict)

    # Audit fields
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class BusinessProfileFactory(DjangoModelFactory):
    """Factory for BusinessProfile."""

    class Meta:
        model = BusinessProfile

    business = factory.SubFactory(BusinessAccountFactory)
    display_name = factory.LazyAttribute(lambda obj: obj.business.legal_name)
    tagline = "Your trusted business partner"
    description = "A test business for unit testing."
    website = "https://example.com"
    contact_email = factory.LazyAttribute(
        lambda obj: f"contact@{obj.business.slug}.example.com"
    )
    contact_phone = "+1234567890"
    industry = "Technology"
    company_size = CompanySize.SIZE_11_50
    founded_year = 2020
    social_links = factory.LazyFunction(
        lambda: {"twitter": "https://twitter.com/example"}
    )
    tags = factory.LazyFunction(list)
    is_public = True


class BusinessSlugHistoryFactory(DjangoModelFactory):
    """Factory for BusinessSlugHistory."""

    class Meta:
        model = BusinessSlugHistory

    business = factory.SubFactory(BusinessAccountFactory)
    old_slug = factory.Sequence(lambda n: f"old-slug-{n}")


# =============================================================================
# COMPOSITE FACTORIES
# =============================================================================


class BusinessAccountWithProfileFactory(BusinessAccountFactory):
    """
    Factory that creates BusinessAccount with its profile.

    Usage:
        business = BusinessAccountWithProfileFactory()
        print(business.profile.display_name)
    """

    profile = factory.RelatedFactory(
        BusinessProfileFactory,
        factory_related_name="business",
    )


class VerifiedBusinessFactory(BusinessAccountFactory):
    """Factory for verified businesses."""

    verification_status = VerificationStatus.VERIFIED
    verified_at = factory.LazyFunction(
        lambda: __import__("django.utils.timezone", fromlist=["now"]).now()
    )


class SuspendedBusinessFactory(BusinessAccountFactory):
    """Factory for suspended businesses."""

    status = BusinessStatus.SUSPENDED
