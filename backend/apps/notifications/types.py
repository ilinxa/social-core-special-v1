"""
Notification Type Definitions
=============================
Code-defined notification types for type safety and version control.

All notification types MUST be defined here. Types are not stored in the
database to ensure changes are version-controlled and deployed atomically.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


class Channel(str, Enum):
    """Available notification channels."""

    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


class Category(str, Enum):
    """Notification categories for grouping."""

    AUTH = "auth"
    SECURITY = "security"
    TRANSACTIONAL = "transactional"
    MARKETING = "marketing"
    SYSTEM = "system"
    SOCIAL = "social"


@dataclass
class NotificationTypeConfig:
    """
    Configuration for a notification type.
    Defined in code for type safety and version control.
    """

    name: str
    display_name: str
    description: str
    category: Category
    default_channels: List[Channel]
    required_context: List[str]  # Required context keys for validation
    email_template: str | None = None  # EmailTemplate.name
    push_template: str | None = None  # Push notification template
    sms_template: str | None = None  # SMS template
    user_configurable: bool = True  # Can user change preferences?
    enabled: bool = True
    default_recipient_permissions: List[str] | None = None
    # None = direct-target only (send() with user=). send_to_org() is rejected.
    # ["perm_a", "perm_b"] = org-broadcastable. send_to_org() resolves members
    #   with ANY of these permissions + owner. Caller can override at call time.


# =============================================================================
# NOTIFICATION TYPE REGISTRY
# =============================================================================

NOTIFICATION_TYPES = {
    # -------------------------------------------------------------------------
    # AUTH NOTIFICATIONS
    # -------------------------------------------------------------------------
    "verify_email": NotificationTypeConfig(
        name="verify_email",
        display_name="Email Verification",
        description="Verification email sent after registration",
        category=Category.AUTH,
        default_channels=[Channel.EMAIL],
        required_context=["verification_link", "code"],
        email_template="verify_email",
        user_configurable=False,  # Cannot disable
    ),
    "welcome": NotificationTypeConfig(
        name="welcome",
        display_name="Welcome Email",
        description="Welcome email after verification",
        category=Category.AUTH,
        default_channels=[Channel.EMAIL],
        required_context=[],  # user_name added automatically
        email_template="welcome",
        user_configurable=False,
    ),
    "password_reset": NotificationTypeConfig(
        name="password_reset",
        display_name="Password Reset",
        description="Password reset link",
        category=Category.AUTH,
        default_channels=[Channel.EMAIL],
        required_context=["reset_link"],
        email_template="password_reset",
        user_configurable=False,
    ),
    # -------------------------------------------------------------------------
    # SECURITY NOTIFICATIONS
    # -------------------------------------------------------------------------
    "password_changed": NotificationTypeConfig(
        name="password_changed",
        display_name="Password Changed",
        description="Confirmation when password is changed",
        category=Category.SECURITY,
        default_channels=[Channel.EMAIL],
        required_context=[],
        email_template="password_changed",
        user_configurable=False,
    ),
    "new_login": NotificationTypeConfig(
        name="new_login",
        display_name="New Login Alert",
        description="Alert when logging in from new device",
        category=Category.SECURITY,
        default_channels=[Channel.EMAIL],
        required_context=["device", "location", "time"],
        email_template="login_alert",
        user_configurable=True,
    ),
    "suspicious_activity": NotificationTypeConfig(
        name="suspicious_activity",
        display_name="Suspicious Activity",
        description="Alert for suspicious account activity",
        category=Category.SECURITY,
        default_channels=[Channel.EMAIL, Channel.PUSH],
        required_context=["activity_type", "details"],
        email_template="suspicious_activity",
        user_configurable=False,
    ),
    # -------------------------------------------------------------------------
    # MARKETING NOTIFICATIONS
    # -------------------------------------------------------------------------
    "newsletter": NotificationTypeConfig(
        name="newsletter",
        display_name="Newsletter",
        description="Periodic newsletter and updates",
        category=Category.MARKETING,
        default_channels=[Channel.EMAIL],
        required_context=["content"],
        email_template="newsletter",
        user_configurable=True,
    ),
    "promotions": NotificationTypeConfig(
        name="promotions",
        display_name="Promotions",
        description="Special offers and promotions",
        category=Category.MARKETING,
        default_channels=[Channel.EMAIL],
        required_context=["offer_title", "offer_details"],
        email_template="promotion",
        user_configurable=True,
    ),
    # -------------------------------------------------------------------------
    # TRANSACTIONAL NOTIFICATIONS (Transaction System)
    # -------------------------------------------------------------------------
    "transaction_invitation_received": NotificationTypeConfig(
        name="transaction_invitation_received",
        display_name="Invitation Received",
        description="Notification when you receive an invitation",
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL, Channel.PUSH],
        required_context=["transaction_id", "transaction_type"],
        email_template="transaction_invitation",
        user_configurable=True,
    ),
    "transaction_accepted": NotificationTypeConfig(
        name="transaction_accepted",
        display_name="Transaction Accepted",
        description="Notification when your transaction is accepted",
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL, Channel.PUSH],
        required_context=["transaction_id", "transaction_type"],
        email_template="transaction_accepted",
        user_configurable=True,
    ),
    "transaction_denied": NotificationTypeConfig(
        name="transaction_denied",
        display_name="Transaction Denied",
        description="Notification when your transaction is denied",
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL],
        required_context=["transaction_id", "reason"],
        email_template="transaction_denied",
        user_configurable=True,
    ),
    "transaction_cancelled": NotificationTypeConfig(
        name="transaction_cancelled",
        display_name="Transaction Cancelled",
        description="Notification when a transaction you are part of is cancelled",
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL],
        required_context=["transaction_id", "transaction_type"],
        email_template="transaction_cancelled",
        user_configurable=True,
    ),
    "transaction_expired": NotificationTypeConfig(
        name="transaction_expired",
        display_name="Transaction Expired",
        description="Notification when your transaction expires",
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL],
        required_context=["transaction_id", "transaction_type"],
        email_template="transaction_expired",
        user_configurable=True,
    ),
    "transaction_expiring_soon": NotificationTypeConfig(
        name="transaction_expiring_soon",
        display_name="Transaction Expiring Soon",
        description="Reminder that a pending transaction is about to expire",
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL, Channel.PUSH],
        required_context=["transaction_id", "expires_at"],
        email_template="transaction_expiring",
        user_configurable=True,
    ),
    "transaction_info_requested": NotificationTypeConfig(
        name="transaction_info_requested",
        display_name="More Information Requested",
        description="Notification when additional information is requested for your submission",
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL, Channel.PUSH],
        required_context=["transaction_id", "message"],
        email_template="transaction_info_requested",
        user_configurable=True,
    ),
    "transaction_resubmitted": NotificationTypeConfig(
        name="transaction_resubmitted",
        display_name="Request Updated",
        description="Notification when a request has been updated after info was requested",
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL],
        required_context=["transaction_id"],
        email_template="transaction_resubmitted",
        user_configurable=True,
    ),
    "transaction_pending_approval": NotificationTypeConfig(
        name="transaction_pending_approval",
        display_name="Transaction Pending Approval",
        description="A new transaction request needs your review",
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL, Channel.PUSH],
        required_context=["transaction_id", "transaction_type"],
        email_template="transaction_pending_approval",
        user_configurable=True,
        default_recipient_permissions=["can_approve_membership_request"],
    ),
    # -------------------------------------------------------------------------
    # SOCIAL NOTIFICATIONS (Network System)
    # -------------------------------------------------------------------------
    "new_follower": NotificationTypeConfig(
        name="new_follower",
        display_name="New Follower",
        description="Notification when someone follows your account",
        category=Category.SOCIAL,
        default_channels=[Channel.PUSH],
        required_context=["follower_id", "followee_type", "followee_id"],
        user_configurable=True,
    ),
    "follow_request_received": NotificationTypeConfig(
        name="follow_request_received",
        display_name="Follow Request Received",
        description="Notification when someone requests to follow your private account",
        category=Category.SOCIAL,
        default_channels=[Channel.PUSH, Channel.EMAIL],
        required_context=[
            "transaction_id",
            "follower_id",
            "followee_type",
            "followee_id",
        ],
        user_configurable=True,
    ),
    "follow_request_accepted": NotificationTypeConfig(
        name="follow_request_accepted",
        display_name="Follow Request Accepted",
        description="Notification when your follow request is accepted",
        category=Category.SOCIAL,
        default_channels=[Channel.PUSH],
        required_context=["followee_type", "followee_id"],
        user_configurable=True,
    ),
    "connection_request_received": NotificationTypeConfig(
        name="connection_request_received",
        display_name="Connection Request Received",
        description="Notification when someone sends you a connection request",
        category=Category.SOCIAL,
        default_channels=[Channel.PUSH, Channel.EMAIL],
        required_context=["transaction_id", "requester_id"],
        user_configurable=True,
    ),
    "connection_accepted": NotificationTypeConfig(
        name="connection_accepted",
        display_name="Connection Accepted",
        description="Notification when your connection request is accepted",
        category=Category.SOCIAL,
        default_channels=[Channel.PUSH],
        required_context=["connection_id", "other_user_id"],
        user_configurable=True,
    ),
    # -------------------------------------------------------------------------
    # SOCIAL NOTIFICATIONS (Chat System)
    # -------------------------------------------------------------------------
    "chat_message_received": NotificationTypeConfig(
        name="chat_message_received",
        display_name="New Chat Message",
        description="Notification when you receive a new chat message while offline",
        category=Category.SOCIAL,
        default_channels=[Channel.PUSH],
        required_context=["conversation_id", "sender_name", "preview"],
        user_configurable=True,
    ),
    "chat_request_received": NotificationTypeConfig(
        name="chat_request_received",
        display_name="Chat Request Received",
        description="Notification when someone sends you a chat request",
        category=Category.SOCIAL,
        default_channels=[Channel.PUSH, Channel.EMAIL],
        required_context=["conversation_id", "requester_name", "preview"],
        user_configurable=True,
    ),
    "chat_request_accepted": NotificationTypeConfig(
        name="chat_request_accepted",
        display_name="Chat Request Accepted",
        description="Notification when your chat request is accepted",
        category=Category.SOCIAL,
        default_channels=[Channel.PUSH],
        required_context=["conversation_id", "accepter_name"],
        user_configurable=True,
    ),
    "chat_group_added": NotificationTypeConfig(
        name="chat_group_added",
        display_name="Added to Group Chat",
        description="Notification when you are added to a group conversation",
        category=Category.SOCIAL,
        default_channels=[Channel.PUSH],
        required_context=["conversation_id", "group_name", "added_by_name"],
        user_configurable=True,
    ),
    # Chat — Phase 4 (Reactions)
    "chat_reaction_received": NotificationTypeConfig(
        name="chat_reaction_received",
        display_name="Reaction on Your Message",
        description="Notification when someone reacts to your message",
        category=Category.SOCIAL,
        default_channels=[Channel.PUSH],
        required_context=["conversation_id", "reactor_name", "message_preview"],
        user_configurable=True,
    ),
}


# =============================================================================
# MANDATORY TYPES (Cannot be disabled by users)
# =============================================================================
MANDATORY_NOTIFICATION_TYPES = frozenset(
    t.name for t in NOTIFICATION_TYPES.values() if not t.user_configurable
)


def get_notification_type(name: str) -> NotificationTypeConfig | None:
    """Get notification type config by name."""
    return NOTIFICATION_TYPES.get(name)


def get_types_by_category(category: Category) -> List[NotificationTypeConfig]:
    """Get all notification types in a category."""
    return [t for t in NOTIFICATION_TYPES.values() if t.category == category]


def get_configurable_types() -> List[NotificationTypeConfig]:
    """Get all user-configurable notification types."""
    return [t for t in NOTIFICATION_TYPES.values() if t.user_configurable]


def get_all_types() -> List[NotificationTypeConfig]:
    """Get all notification types."""
    return list(NOTIFICATION_TYPES.values())


def is_org_broadcastable(name: str) -> bool:
    """Check if a notification type supports send_to_org()."""
    config = get_notification_type(name)
    return config is not None and config.default_recipient_permissions is not None
