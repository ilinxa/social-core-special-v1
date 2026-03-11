"""
User Serializers
================
DRF serializers for User and UserProfile models.

Input Serializers: Validate and deserialize incoming data
Output Serializers: Serialize data for API responses
"""

from typing import Optional

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.serializers import BaseOutputSerializer
from apps.users.models import User, UserProfile


# =============================================================================
# OUTPUT SERIALIZERS (for API responses)
# =============================================================================

class UserProfileOutputSerializer(BaseOutputSerializer):
    """
    Output serializer for UserProfile.

    Used when returning profile data in API responses.
    """
    full_name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    has_avatar = serializers.BooleanField(read_only=True)
    avatar_url = serializers.SerializerMethodField()
    has_cover_image = serializers.BooleanField(read_only=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'first_name',
            'last_name',
            'full_name',
            'display_name',
            'phone',
            'avatar_url',
            'has_avatar',
            'cover_image_url',
            'has_cover_image',
            'timezone',
            'language',
            'bio',
            'country',
            'city',
            'tags',
            'is_public',
        ]

    def _get_image_url(self, image_field) -> Optional[str]:
        """Return absolute URL for an ImageField if it has a value."""
        if image_field:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(image_field.url)
            return image_field.url
        return None

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_avatar_url(self, obj) -> Optional[str]:
        """Return absolute URL for avatar if exists."""
        return self._get_image_url(obj.avatar)

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_cover_image_url(self, obj) -> Optional[str]:
        """Return absolute URL for cover image if exists."""
        return self._get_image_url(obj.cover_image)


class UserOutputSerializer(BaseOutputSerializer):
    """
    Output serializer for User.

    Used when returning user data in API responses.
    Includes nested profile data.
    """
    profile = UserProfileOutputSerializer(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'is_active',
            'is_verified',
            'is_complete',
            'can_create_business',
            'is_staff',
            'is_superuser',
            'date_joined',
            'last_login',
            'profile',
        ]


class UserPublicProfileOutput(BaseOutputSerializer):
    """
    Public profile output — excludes private fields (phone, timezone, language).

    Used for viewing other users' profiles.
    """
    full_name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    has_avatar = serializers.BooleanField(read_only=True)
    avatar_url = serializers.SerializerMethodField()
    has_cover_image = serializers.BooleanField(read_only=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'first_name',
            'last_name',
            'full_name',
            'display_name',
            'avatar_url',
            'has_avatar',
            'cover_image_url',
            'has_cover_image',
            'bio',
            'country',
            'city',
            'tags',
            'is_public',
        ]

    def _get_image_url(self, image_field) -> Optional[str]:
        """Return absolute URL for an ImageField if it has a value."""
        if image_field:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(image_field.url)
            return image_field.url
        return None

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_avatar_url(self, obj) -> Optional[str]:
        """Return absolute URL for avatar if exists."""
        return self._get_image_url(obj.avatar)

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_cover_image_url(self, obj) -> Optional[str]:
        """Return absolute URL for cover image if exists."""
        return self._get_image_url(obj.cover_image)


class UserPublicOutput(BaseOutputSerializer):
    """
    Public user output — excludes email and admin flags.

    Used for the public user detail endpoint (GET /users/{username}/).
    """
    profile = UserPublicProfileOutput(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'is_verified',
            'is_complete',
            'date_joined',
            'profile',
        ]


class UserLimitedOutput(BaseOutputSerializer):
    """
    Limited user output for private profiles (non-connected viewers).

    Shows all T1 profile fields (public identity info) but excludes T3 fields
    (phone, timezone, language). Uses the same public profile serializer as
    UserPublicOutput to avoid duplication.
    """
    profile = UserPublicProfileOutput(read_only=True)
    is_limited = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'is_verified',
            'date_joined',
            'profile',
            'is_limited',
        ]

    def get_is_limited(self, obj) -> bool:
        return True


class UserMinimalOutputSerializer(BaseOutputSerializer):
    """
    Minimal output serializer for User.

    Used for listing users or when only basic info is needed.
    """
    display_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'display_name',
            'avatar_url',
        ]

    @extend_schema_field(serializers.CharField())
    def get_display_name(self, obj) -> str:
        """Get display name from profile."""
        if hasattr(obj, 'profile'):
            return obj.profile.display_name
        return obj.email.split('@')[0]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_avatar_url(self, obj) -> Optional[str]:
        """Get avatar URL from profile."""
        if hasattr(obj, 'profile') and obj.profile.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile.avatar.url)
            return obj.profile.avatar.url
        return None


# =============================================================================
# INPUT SERIALIZERS (for validating incoming data)
# =============================================================================

class UserUpdateInputSerializer(serializers.Serializer):
    """
    Input serializer for updating user basic data.

    Only username can be updated directly on User model.
    """
    username = serializers.CharField(
        min_length=5,
        max_length=30,
        required=False
    )

    def validate_username(self, value):
        """Validate username format."""
        import re
        if not re.match(r'^[a-zA-Z0-9_]{5,30}$', value):
            raise serializers.ValidationError(
                'Username must be 5-30 alphanumeric characters or underscores'
            )
        return value.lower()


class ProfileUpdateInputSerializer(serializers.Serializer):
    """
    Input serializer for updating profile data.
    """
    first_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True
    )
    last_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True
    )
    phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True
    )
    timezone = serializers.CharField(
        max_length=50,
        required=False
    )
    language = serializers.CharField(
        max_length=10,
        required=False
    )
    bio = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True
    )
    country = serializers.CharField(
        max_length=2,
        required=False,
        allow_blank=True
    )
    city = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        max_length=20,
    )
    is_public = serializers.BooleanField(required=False)

    def validate_timezone(self, value):
        """Validate timezone is valid."""
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, KeyError):
            raise serializers.ValidationError(f'Unknown timezone: {value}')
        return value

    def validate_city(self, value):
        """Validate city against predefined city list when country is provided."""
        if not value:
            return value
        country = self.initial_data.get('country', '')
        if country:
            from apps.core.utils.city_data import is_valid_city
            if not is_valid_city(country, value):
                raise serializers.ValidationError(
                    f'"{value}" is not a valid city for country "{country}".'
                )
        return value


class ImageUploadInputSerializer(serializers.Serializer):
    """
    Base input serializer for image uploads (avatar, cover image).
    """
    IMAGE_MAX_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

    def _validate_image(self, value, label="Image"):
        if value.size > self.IMAGE_MAX_SIZE:
            raise serializers.ValidationError(
                f'{label} file too large. Maximum size is 5MB.'
            )
        if value.content_type not in self.ALLOWED_TYPES:
            raise serializers.ValidationError(
                'Invalid image format. Allowed: JPEG, PNG, GIF, WebP.'
            )
        return value


class AvatarUploadInputSerializer(ImageUploadInputSerializer):
    """Input serializer for avatar upload."""
    avatar = serializers.ImageField()

    def validate_avatar(self, value):
        return self._validate_image(value, "Avatar")


class CoverImageUploadInputSerializer(ImageUploadInputSerializer):
    """Input serializer for cover image upload."""
    cover_image = serializers.ImageField()

    def validate_cover_image(self, value):
        return self._validate_image(value, "Cover image")
