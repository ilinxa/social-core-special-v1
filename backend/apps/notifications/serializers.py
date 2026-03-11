"""
Notification Serializers
========================
Serializers for notification API endpoints.
"""

from rest_framework import serializers

from apps.notifications.models import NotificationLog, NotificationPreference
from apps.notifications.types import get_notification_type, get_configurable_types


class NotificationPreferenceSerializer(serializers.Serializer):
    """Serializer for a single notification preference."""

    notification_type = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)
    user_configurable = serializers.BooleanField(read_only=True)
    email_enabled = serializers.BooleanField()
    push_enabled = serializers.BooleanField()
    sms_enabled = serializers.BooleanField()


class NotificationPreferenceUpdateSerializer(serializers.Serializer):
    """Serializer for updating notification preference."""

    email_enabled = serializers.BooleanField(required=False)
    push_enabled = serializers.BooleanField(required=False)
    sms_enabled = serializers.BooleanField(required=False)

    def validate(self, data):
        """Ensure at least one field is provided."""
        if not any([
            'email_enabled' in data,
            'push_enabled' in data,
            'sms_enabled' in data
        ]):
            raise serializers.ValidationError(
                "At least one channel preference must be provided"
            )
        return data


class AllPreferencesSerializer(serializers.Serializer):
    """Serializer for all user preferences grouped by category."""

    def to_representation(self, preferences_dict):
        """Transform preferences dict to categorized response."""
        # Group by category
        by_category = {}

        for type_name, pref_data in preferences_dict.items():
            category = pref_data.get('category', 'other')
            if category not in by_category:
                by_category[category] = []

            by_category[category].append({
                'notification_type': type_name,
                **pref_data
            })

        return by_category


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for notification log entries."""

    class Meta:
        model = NotificationLog
        fields = [
            'id',
            'notification_type',
            'channels',
            'status',
            'channel_results',
            'created_at',
        ]
        read_only_fields = fields


class NotificationHistorySerializer(serializers.Serializer):
    """Serializer for notification history response."""

    notifications = NotificationLogSerializer(many=True)
    total_count = serializers.IntegerField()


class ConfigurableTypeSerializer(serializers.Serializer):
    """Serializer for listing configurable notification types."""

    name = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    default_channels = serializers.ListField(child=serializers.CharField())

    def to_representation(self, type_config):
        return {
            'name': type_config.name,
            'display_name': type_config.display_name,
            'description': type_config.description,
            'category': type_config.category.value,
            'default_channels': [c.value for c in type_config.default_channels],
        }
