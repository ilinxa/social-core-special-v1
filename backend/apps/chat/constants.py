"""
Chat Constants
==============
All enums and constants for the chat system.
"""

from django.db import models


class ScopeType(models.TextChoices):
    GLOBAL = "global", "Global"
    BUSINESS = "business", "Business"
    PLATFORM = "platform", "Platform"
    # TEAM = "team", "Team"  # Future


class ConversationType(models.TextChoices):
    DIRECT = "direct", "Direct Message"
    GROUP = "group", "Group Chat"


class ParticipantType(models.TextChoices):
    USER = "user", "User"
    BUSINESS = "business", "Business"
    PLATFORM = "platform", "Platform"
    # TEAM = "team", "Team"  # Future


class ParticipantRole(models.TextChoices):
    MEMBER = "member", "Member"
    ADMIN = "admin", "Admin"


class RequestStatus(models.TextChoices):
    NONE = "none", "None"
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    IGNORED = "ignored", "Ignored"
    BLOCKED = "blocked", "Blocked"


class MessageContentType(models.TextChoices):
    TEXT = "text", "Text"
    SYSTEM = "system", "System"
    IMAGE = "image", "Image"
    # FILE = "file", "File"          # Future
    # LINK = "link", "Link"          # Future


class MessageStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    EDITED = "edited", "Edited"
    DELETED = "deleted", "Deleted"


class ReactionType(models.TextChoices):
    LIKE = "like", "👍"
    HEART = "heart", "❤️"
    LAUGH = "laugh", "😂"
    WOW = "wow", "😮"
    SAD = "sad", "😢"
    ANGRY = "angry", "😡"


class AttachmentType(models.TextChoices):
    IMAGE = "image", "Image"


# Chat settings
CHAT_MESSAGE_MAX_LENGTH = 5000
CHAT_MESSAGE_EDIT_WINDOW_MINUTES = 15
CHAT_MESSAGE_PREVIEW_LENGTH = 200
CHAT_REQUEST_MAX_MESSAGES = 3
CHAT_REQUEST_EXPIRY_DAYS = 30
CHAT_GROUP_MAX_PARTICIPANTS = 100

# Rate limit settings
CHAT_RATE_LIMIT_MESSAGES_PER_MINUTE = 30
CHAT_RATE_LIMIT_CONVERSATIONS_PER_HOUR = 5
CHAT_RATE_LIMIT_REQUESTS_PER_HOUR = 10

# Image attachment settings
CHAT_ALLOWED_IMAGE_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
})
CHAT_ALLOWED_IMAGE_EXTENSIONS = frozenset({
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
})
CHAT_MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
CHAT_MAX_ATTACHMENTS_PER_MESSAGE = 10
CHAT_ATTACHMENT_ORPHAN_TTL_HOURS = 24

# WebSocket settings
WS_PRESENCE_TTL_SECONDS = 30
WS_HEARTBEAT_INTERVAL_SECONDS = 20
WS_MAX_PRESENCE_SUBSCRIPTIONS = 50
