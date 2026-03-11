"""
Notifications App
=================
Multi-channel notification routing with user preferences.

This app is the unified communication layer that decides WHAT
and WHEN to communicate to users, then delegates delivery to
appropriate channels (Email, Push, SMS).

Key Components:
    - NotificationService: Main entry point for sending notifications
    - PreferenceService: Manage user channel preferences
    - Channels: Email (uses Email app), Push (future), SMS (future)

Usage:
    from apps.notifications.services import NotificationService

    NotificationService.send(
        user=user,
        notification_type='welcome',
        context={'user_name': 'John'}
    )

Governance:
    - All user-facing messages go through this system
    - No system should call Email directly for user communication
    - Auth triggers notifications, not emails
"""

default_app_config = 'apps.notifications.apps.NotificationsConfig'
