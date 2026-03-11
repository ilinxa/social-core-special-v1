# apps/explore/tests/factories.py
"""
Factory-boy factories for Explore app tests.
"""

import factory
from factory.django import DjangoModelFactory

from apps.explore.models import SuggestedTag, TagCategory


class SuggestedTagFactory(DjangoModelFactory):
    """Factory for SuggestedTag."""

    class Meta:
        model = SuggestedTag

    name = factory.Sequence(lambda n: f"tag-{n}")
    slug = factory.LazyAttribute(lambda obj: obj.name)
    category = TagCategory.BOTH
    usage_count = 0
    is_active = True
