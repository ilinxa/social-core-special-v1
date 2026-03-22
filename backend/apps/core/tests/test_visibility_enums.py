# apps/core/tests/test_visibility_enums.py
"""Tests for visibility enums — ordering, hierarchy, labels."""

import pytest

from apps.core.visibility.enums import (
    VISIBILITY_ENUMS,
    BusinessVisibility,
    ContentTier,
    PlatformVisibility,
    UserVisibility,
)


class TestContentTier:
    def test_has_three_tiers(self):
        assert len(ContentTier.choices) == 3

    def test_tier_values(self):
        assert ContentTier.ALWAYS_PUBLIC == "T1"
        assert ContentTier.CONDITIONAL == "T2"
        assert ContentTier.ALWAYS_PRIVATE == "T3"

    def test_tier_labels(self):
        assert ContentTier.ALWAYS_PUBLIC.label == "Always Public"
        assert ContentTier.CONDITIONAL.label == "Conditional"
        assert ContentTier.ALWAYS_PRIVATE.label == "Always Private"


class TestUserVisibility:
    def test_has_two_levels(self):
        assert len(UserVisibility.choices) == 2

    def test_hierarchy_order(self):
        """CONNECTIONS (0) < WORLD (1) — lower = more restrictive."""
        assert UserVisibility.CONNECTIONS < UserVisibility.WORLD

    def test_values(self):
        assert UserVisibility.CONNECTIONS == 0
        assert UserVisibility.WORLD == 1


class TestBusinessVisibility:
    def test_has_four_levels(self):
        assert len(BusinessVisibility.choices) == 4

    def test_hierarchy_order(self):
        """MEMBERS < CONNECTIONS < FOLLOWERS < WORLD."""
        assert BusinessVisibility.MEMBERS < BusinessVisibility.CONNECTIONS
        assert BusinessVisibility.CONNECTIONS < BusinessVisibility.FOLLOWERS
        assert BusinessVisibility.FOLLOWERS < BusinessVisibility.WORLD

    def test_values(self):
        assert BusinessVisibility.MEMBERS == 0
        assert BusinessVisibility.CONNECTIONS == 1
        assert BusinessVisibility.FOLLOWERS == 2
        assert BusinessVisibility.WORLD == 3

    def test_labels(self):
        assert BusinessVisibility.MEMBERS.label == "Members"
        assert BusinessVisibility.WORLD.label == "World (everyone)"


class TestPlatformVisibility:
    def test_has_two_levels(self):
        assert len(PlatformVisibility.choices) == 2

    def test_hierarchy_order(self):
        assert PlatformVisibility.MEMBERS < PlatformVisibility.WORLD

    def test_values(self):
        assert PlatformVisibility.MEMBERS == 0
        assert PlatformVisibility.WORLD == 1


class TestVisibilityEnumsMapping:
    def test_all_account_types_mapped(self):
        assert "user" in VISIBILITY_ENUMS
        assert "business" in VISIBILITY_ENUMS
        assert "platform" in VISIBILITY_ENUMS

    def test_correct_enum_classes(self):
        assert VISIBILITY_ENUMS["user"] is UserVisibility
        assert VISIBILITY_ENUMS["business"] is BusinessVisibility
        assert VISIBILITY_ENUMS["platform"] is PlatformVisibility

    def test_unknown_type_not_in_map(self):
        assert "unknown" not in VISIBILITY_ENUMS
