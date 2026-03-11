"""
SMS Channel
===========
SMS notification channel (Twilio).

This is a placeholder for future implementation.
Currently returns 'skipped' status.
"""

from typing import Any, Dict

from apps.core.observability import get_logger
from apps.notifications.services.channels.base import BaseChannel

logger = get_logger(__name__)


class SMSChannel(BaseChannel):
    """
    SMS notification channel via Twilio.

    TODO: Implement with Twilio SDK when ready.
    """

    @staticmethod
    def send(
        *,
        user,
        notification_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send notification via SMS.

        Currently a placeholder that returns 'skipped'.
        """
        # Check if SMS is configured
        if not SMSChannel.is_available():
            return {
                'status': 'skipped',
                'reason': 'SMS notifications not configured'
            }

        # TODO: Implement SMS notification logic
        # 1. Get user's phone from profile
        # 2. Validate phone number format
        # 3. Send via Twilio
        # 4. Track delivery status

        logger.info(
            "notification.sms.skipped",
            user_id=str(user.id),
            notification_type=notification_type,
            reason='Not implemented',
        )

        return {
            'status': 'skipped',
            'reason': 'SMS channel not implemented yet'
        }

    @staticmethod
    def is_available() -> bool:
        """
        Check if Twilio is configured.
        """
        # TODO: Check for Twilio credentials
        # from django.conf import settings
        # return bool(getattr(settings, 'TWILIO_AUTH_TOKEN', None))
        return False
