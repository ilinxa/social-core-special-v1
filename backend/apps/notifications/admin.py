"""
Notification Admin
==================
Admin configuration for notification models.
"""

from django.contrib import admin

from apps.notifications.models import NotificationLog, NotificationPreference


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin for NotificationPreference model."""

    list_display = [
        'user',
        'notification_type',
        'email_enabled',
        'push_enabled',
        'sms_enabled',
        'updated_at',
    ]
    list_filter = [
        'notification_type',
        'email_enabled',
        'push_enabled',
        'sms_enabled',
    ]
    search_fields = ['user__email', 'notification_type']
    raw_id_fields = ['user']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (None, {
            'fields': ('user', 'notification_type')
        }),
        ('Channel Preferences', {
            'fields': ('email_enabled', 'push_enabled', 'sms_enabled')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """Admin for NotificationLog model."""

    list_display = [
        'short_id',
        'user',
        'notification_type',
        'channels_display',
        'status',
        'retry_count',
        'created_at',
    ]
    list_filter = [
        'status',
        'notification_type',
        'created_at',
    ]
    search_fields = ['user__email', 'id']
    raw_id_fields = ['user']
    readonly_fields = [
        'id',
        'user',
        'notification_type',
        'channels',
        'context',
        'channel_results',
        'status',
        'retry_count',
        'error_message',
        'created_at',
        'updated_at',
    ]
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('id', 'user', 'notification_type', 'status')
        }),
        ('Channels', {
            'fields': ('channels', 'channel_results')
        }),
        ('Context', {
            'fields': ('context',),
            'classes': ('collapse',)
        }),
        ('Retry Info', {
            'fields': ('retry_count', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def short_id(self, obj):
        """Display shortened UUID."""
        return str(obj.id)[:8]
    short_id.short_description = 'ID'

    def channels_display(self, obj):
        """Display channels as comma-separated list."""
        return ', '.join(obj.channels) if obj.channels else '-'
    channels_display.short_description = 'Channels'

    def has_add_permission(self, request):
        """Disable manual creation of logs."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing of logs."""
        return False
