"""
Push Channel
============
Push notification channel (Firebase/APNs).

This is a placeholder for future implementation.
Currently returns 'skipped' status.
"""

from typing import Any, Dict

from apps.core.observability import get_logger
from apps.notifications.services.channels.base import BaseChannel

logger = get_logger(__name__)


class PushChannel(BaseChannel):
    """
    Push notification channel via Firebase Cloud Messaging.

    TODO: Implement with Firebase Admin SDK when ready.
    """

    @staticmethod
    def send(
        *,
        user,
        notification_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send notification via push.

        Currently a placeholder that returns 'skipped'.
        """
        # Check if push is configured
        if not PushChannel.is_available():
            return {
                'status': 'skipped',
                'reason': 'Push notifications not configured'
            }

        # TODO: Implement push notification logic
        # 1. Get user's push tokens from device sessions
        # 2. Send via Firebase Admin SDK
        # 3. Handle token refresh/invalidation

        logger.info(
            "notification.push.skipped",
            user_id=str(user.id),
            notification_type=notification_type,
            reason='Not implemented',
        )

        return {
            'status': 'skipped',
            'reason': 'Push channel not implemented yet'
        }

    @staticmethod
    def is_available() -> bool:
        """
        Check if Firebase is configured.
        """
        # TODO: Check for Firebase credentials
        # from django.conf import settings
        # return bool(getattr(settings, 'FIREBASE_CREDENTIALS', None))
        return False
