"""
Channel Registry
================
Maps channel names to their implementation classes.
"""

from typing import Type

from apps.notifications.services.channels.base import BaseChannel
from apps.notifications.services.channels.email_channel import EmailChannel
from apps.notifications.services.channels.push_channel import PushChannel
from apps.notifications.services.channels.sms_channel import SMSChannel

# =============================================================================
# CHANNEL REGISTRY
# =============================================================================
# Maps channel names to their implementation classes.
# Add new channels here when implementing push/SMS.

CHANNEL_REGISTRY = {
    "email": EmailChannel,
    "push": PushChannel,
    "sms": SMSChannel,
}


def get_channel(name: str) -> Type[BaseChannel] | None:
    """
    Get channel class by name.

    Args:
        name: Channel name ('email', 'push', 'sms')

    Returns:
        Channel class or None if not found
    """
    return CHANNEL_REGISTRY.get(name)


def get_available_channels() -> list:
    """Return list of implemented channel names."""
    return list(CHANNEL_REGISTRY.keys())


__all__ = [
    "BaseChannel",
    "EmailChannel",
    "PushChannel",
    "SMSChannel",
    "CHANNEL_REGISTRY",
    "get_channel",
    "get_available_channels",
]
