# apps/core/tests/test_visibility_registry.py
"""Tests for field visibility registries — config validation, lookups."""

import pytest

from apps.core.visibility.enums import (
    BusinessVisibility,
    ContentTier,
    PlatformVisibility,
    UserVisibility,
)
from apps.core.visibility.registry import (
    BUSINESS_ACCOUNT_FIELDS,
    BUSINESS_PROFILE_FIELDS,
    PLATFORM_PROFILE_FIELDS,
    USER_PROFILE_FIELDS,
    FieldVisibilityConfig,
    get_account_type_for_registry,
    get_registry,
    get_t2_fields,
    get_visibility_choices,
)

T1 = ContentTier.ALWAYS_PUBLIC
T2 = ContentTier.CONDITIONAL
T3 = ContentTier.ALWAYS_PRIVATE


class TestFieldVisibilityConfig:
    def test_t1_config_no_extras(self):
        config = FieldVisibilityConfig(tier=T1)
        assert config.tier == T1
        assert config.default_level is None
        assert config.required_permission is None

    def test_t2_config_with_default(self):
        config = FieldVisibilityConfig(
            tier=T2, default_level=BusinessVisibility.FOLLOWERS
        )
        assert config.tier == T2
        assert config.default_level == 2

    def test_t3_config_with_permission(self):
        config = FieldVisibilityConfig(
            tier=T3, required_permission="can_view_legal_info"
        )
        assert config.tier == T3
        assert config.required_permission == "can_view_legal_info"

    def test_frozen_dataclass(self):
        config = FieldVisibilityConfig(tier=T1)
        with pytest.raises(AttributeError):
            config.tier = T2


class TestUserProfileRegistry:
    def test_t1_fields_present(self):
        t1_fields = [
            "first_name", "last_name", "full_name", "display_name",
            "avatar_url", "has_avatar", "cover_image_url", "has_cover_image",
            "bio", "country", "city", "tags", "is_public",
        ]
        for field in t1_fields:
            assert field in USER_PROFILE_FIELDS
            assert USER_PROFILE_FIELDS[field].tier == T1

    def test_t3_fields_present(self):
        t3_fields = ["phone", "timezone", "language"]
        for field in t3_fields:
            assert field in USER_PROFILE_FIELDS
            assert USER_PROFILE_FIELDS[field].tier == T3

    def test_no_t2_fields(self):
        t2 = {k: v for k, v in USER_PROFILE_FIELDS.items() if v.tier == T2}
        assert len(t2) == 0


class TestBusinessAccountRegistry:
    def test_t1_fields_include_display_variants(self):
        display_fields = [
            "business_type_display",
            "status_display",
            "verification_status_display",
        ]
        for field in display_fields:
            assert field in BUSINESS_ACCOUNT_FIELDS
            assert BUSINESS_ACCOUNT_FIELDS[field].tier == T1

    def test_t3_legal_fields(self):
        legal_fields = ["registration_number", "tax_id", "legal_address"]
        for field in legal_fields:
            assert field in BUSINESS_ACCOUNT_FIELDS
            assert BUSINESS_ACCOUNT_FIELDS[field].tier == T3
            assert (
                BUSINESS_ACCOUNT_FIELDS[field].required_permission
                == "can_view_legal_info"
            )

    def test_t3_settings_field(self):
        assert BUSINESS_ACCOUNT_FIELDS["settings"].tier == T3
        assert (
            BUSINESS_ACCOUNT_FIELDS["settings"].required_permission
            == "can_edit_business"
        )

    def test_t3_max_members_field(self):
        assert BUSINESS_ACCOUNT_FIELDS["max_members"].tier == T3
        assert (
            BUSINESS_ACCOUNT_FIELDS["max_members"].required_permission
            == "can_view_members"
        )


class TestBusinessProfileRegistry:
    def test_t2_contact_fields(self):
        assert BUSINESS_PROFILE_FIELDS["contact_email"].tier == T2
        assert (
            BUSINESS_PROFILE_FIELDS["contact_email"].default_level
            == BusinessVisibility.FOLLOWERS
        )
        assert BUSINESS_PROFILE_FIELDS["contact_phone"].tier == T2
        assert (
            BUSINESS_PROFILE_FIELDS["contact_phone"].default_level
            == BusinessVisibility.FOLLOWERS
        )

    def test_t1_display_fields(self):
        t1_fields = [
            "display_name", "tagline", "description", "logo",
            "cover_image", "website", "industry", "company_size",
            "founded_year", "social_links", "tags", "is_public",
        ]
        for field in t1_fields:
            assert field in BUSINESS_PROFILE_FIELDS
            assert BUSINESS_PROFILE_FIELDS[field].tier == T1


class TestPlatformProfileRegistry:
    def test_empty_registry(self):
        """Platform is fully public — no fields classified."""
        assert len(PLATFORM_PROFILE_FIELDS) == 0


class TestGetRegistry:
    def test_known_keys(self):
        assert get_registry("user_profile") is USER_PROFILE_FIELDS
        assert get_registry("business_account") is BUSINESS_ACCOUNT_FIELDS
        assert get_registry("business_profile") is BUSINESS_PROFILE_FIELDS
        assert get_registry("platform_profile") is PLATFORM_PROFILE_FIELDS

    def test_unknown_key_returns_empty_dict(self):
        result = get_registry("nonexistent")
        assert result == {}


class TestGetT2Fields:
    def test_business_profile_has_two_t2_fields(self):
        t2 = get_t2_fields("business_profile")
        assert set(t2.keys()) == {"contact_email", "contact_phone"}

    def test_user_profile_has_no_t2_fields(self):
        t2 = get_t2_fields("user_profile")
        assert len(t2) == 0

    def test_business_account_has_no_t2_fields(self):
        t2 = get_t2_fields("business_account")
        assert len(t2) == 0

    def test_unknown_key_returns_empty(self):
        t2 = get_t2_fields("nonexistent")
        assert len(t2) == 0


class TestGetVisibilityChoices:
    def test_business_choices(self):
        choices = get_visibility_choices("business")
        assert len(choices) == 4
        values = [c.value for c in choices]
        assert values == [0, 1, 2, 3]

    def test_user_choices(self):
        choices = get_visibility_choices("user")
        assert len(choices) == 2

    def test_platform_choices(self):
        choices = get_visibility_choices("platform")
        assert len(choices) == 2

    def test_unknown_type_returns_empty(self):
        choices = get_visibility_choices("unknown")
        assert choices == []


class TestGetAccountTypeForRegistry:
    def test_user_profile(self):
        assert get_account_type_for_registry("user_profile") == "user"

    def test_business_keys(self):
        assert get_account_type_for_registry("business_account") == "business"
        assert get_account_type_for_registry("business_profile") == "business"

    def test_platform_profile(self):
        assert get_account_type_for_registry("platform_profile") == "platform"

    def test_unknown_returns_none(self):
        assert get_account_type_for_registry("nonexistent") is None
