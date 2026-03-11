# apps/explore/tests/test_models.py
"""Tests for Explore models (SuggestedTag)."""

import pytest

from apps.explore.models import SuggestedTag, TagCategory
from apps.explore.tests.factories import SuggestedTagFactory


@pytest.mark.django_db
class TestSuggestedTag:
    """Tests for SuggestedTag model."""

    def test_create_tag(self):
        tag = SuggestedTagFactory(name="test-create-tag", slug="test-create-tag")
        assert tag.name == "test-create-tag"
        assert tag.slug == "test-create-tag"
        assert tag.category == TagCategory.BOTH
        assert tag.usage_count == 0
        assert tag.is_active is True

    def test_auto_slug_on_save(self):
        tag = SuggestedTag(name="Test Auto Slug", category=TagCategory.BOTH)
        tag.save()
        assert tag.slug == "test-auto-slug"

    def test_str_representation(self):
        tag = SuggestedTagFactory(name="test-str-repr")
        assert str(tag) == "test-str-repr"

    def test_unique_name(self):
        SuggestedTagFactory(name="unique-tag")
        with pytest.raises(Exception):
            SuggestedTagFactory(name="unique-tag")

    def test_ordering(self):
        """Tags ordered by -usage_count, then name."""
        tag_a = SuggestedTagFactory(name="alpha", usage_count=5)
        tag_b = SuggestedTagFactory(name="beta", usage_count=10)
        tag_c = SuggestedTagFactory(name="gamma", usage_count=5)

        tags = list(SuggestedTag.objects.all())
        assert tags[0] == tag_b  # highest usage
        assert tags[1] == tag_a  # same usage, alpha first
        assert tags[2] == tag_c

    def test_category_choices(self):
        for category in [TagCategory.USER, TagCategory.BUSINESS, TagCategory.BOTH]:
            tag = SuggestedTagFactory(category=category)
            assert tag.category == category
