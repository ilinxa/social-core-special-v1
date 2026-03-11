"""
Base Channel
============
Abstract base class for notification channels.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseChannel(ABC):
    """
    Abstract base class for notification channels.

    All channels must implement the send method.
    """

    @staticmethod
    @abstractmethod
    def send(
        *,
        user,
        notification_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send notification via this channel.

        Args:
            user: User instance
            notification_type: Notification type name
            context: Template variables

        Returns:
            Dict with at least 'status' key:
            - {'status': 'sent', ...additional info}
            - {'status': 'failed', 'error': '...'}
            - {'status': 'skipped', 'reason': '...'}
        """
        pass

    @staticmethod
    def is_available() -> bool:
        """
        Check if channel is available/configured.
        Override in subclasses to check configuration.
        """
        return True
