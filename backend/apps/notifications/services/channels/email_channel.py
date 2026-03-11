"""
Email Channel
=============
Email notification channel using the Email system.
"""

from typing import Any, Dict

from apps.core.observability import get_logger
from apps.notifications.services.channels.base import BaseChannel
from apps.notifications.types import get_notification_type

logger = get_logger(__name__)


class EmailChannel(BaseChannel):
    """
    Email notification channel.
    Delegates to Email system for actual sending.
    """

    @staticmethod
    def send(
        *,
        user,
        notification_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send notification via email.

        Returns:
            {'status': 'sent', 'email_log_id': '...'}
            or
            {'status': 'failed', 'error': '...'}
            or
            {'status': 'skipped', 'reason': '...'}
        """
        type_config = get_notification_type(notification_type)
        if not type_config or not type_config.email_template:
            return {'status': 'skipped', 'reason': 'No email template'}

        try:
            from apps.email.services import EmailService

            # Add standard context
            full_context = {
                'user_email': user.email,
                **context
            }

            # Try to get user's display name from profile if available
            if hasattr(user, 'profile') and user.profile:
                full_context['user_name'] = user.profile.display_name
            else:
                # Fallback to email username part
                full_context['user_name'] = user.email.split('@')[0]

            # Send via Email system
            email_log = EmailService.send(
                template_name=type_config.email_template,
                to_email=user.email,
                context=full_context
            )

            logger.info(
                "notification.email.sent",
                user_id=str(user.id),
                notification_type=notification_type,
                email_log_id=str(email_log.id),
            )

            return {
                'status': 'sent',
                'email_log_id': str(email_log.id)
            }

        except Exception as e:
            logger.error(
                "notification.email.failed",
                user_id=str(user.id),
                notification_type=notification_type,
                error=str(e),
            )
            return {
                'status': 'failed',
                'error': str(e)
            }

    @staticmethod
    def is_available() -> bool:
        """Email channel is always available."""
        return True
