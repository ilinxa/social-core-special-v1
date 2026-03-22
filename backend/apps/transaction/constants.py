from django.db import models


class TransactionMode(models.TextChoices):
    INVITATION = "invitation", "Invitation"
    REQUEST = "request", "Request"


class TransactionStatus(models.TextChoices):
    CREATED = "created", "Created"
    PENDING = "pending", "Pending"
    PENDING_REVIEW = "pending_review", "Pending Review"
    ACCEPTED = "accepted", "Accepted"
    DENIED = "denied", "Denied"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"
    DISMISSED = "dismissed", "Dismissed"
    INVALIDATED = "invalidated", "Invalidated"
    INFO_REQUESTED = "info_requested", "Info Requested"


class PartyType(models.TextChoices):
    USER = "user", "User"
    ACCOUNT = "account", "Account"
    MEMBERSHIP_ACTOR = "membership_actor", "Membership Actor"
    SYSTEM = "system", "System"


class ApproverPolicy(models.TextChoices):
    TARGET_ACCEPTANCE = "target_acceptance", "Target Acceptance"
    ACCOUNT_AUTHORITY = "account_authority", "Account Authority"
    PLATFORM_AUTHORITY = "platform_authority", "Platform Authority"
    AUTO_APPROVAL = "auto_approval", "Auto Approval"


TERMINAL_STATES = frozenset(
    [
        TransactionStatus.ACCEPTED,
        TransactionStatus.DENIED,
        TransactionStatus.CANCELLED,
        TransactionStatus.EXPIRED,
        TransactionStatus.DISMISSED,
        TransactionStatus.INVALIDATED,
    ]
)

VALID_TRANSITIONS = {
    TransactionStatus.CREATED: [
        TransactionStatus.PENDING,
        TransactionStatus.EXPIRED,
        TransactionStatus.INVALIDATED,
    ],
    TransactionStatus.PENDING: [
        TransactionStatus.ACCEPTED,
        TransactionStatus.DENIED,
        TransactionStatus.CANCELLED,
        TransactionStatus.DISMISSED,
        TransactionStatus.EXPIRED,
        TransactionStatus.INVALIDATED,
        TransactionStatus.INFO_REQUESTED,
        TransactionStatus.PENDING_REVIEW,
    ],
    TransactionStatus.PENDING_REVIEW: [
        TransactionStatus.ACCEPTED,
        TransactionStatus.DENIED,
        TransactionStatus.CANCELLED,
        TransactionStatus.EXPIRED,
        TransactionStatus.INVALIDATED,
        TransactionStatus.INFO_REQUESTED,
    ],
    TransactionStatus.INFO_REQUESTED: [
        TransactionStatus.PENDING,
        TransactionStatus.PENDING_REVIEW,
        TransactionStatus.CANCELLED,
        TransactionStatus.EXPIRED,
        TransactionStatus.INVALIDATED,
    ],
    # Terminal states that allow dismiss (cleanup action)
    TransactionStatus.ACCEPTED: [
        TransactionStatus.DISMISSED,
    ],
    TransactionStatus.DENIED: [
        TransactionStatus.DISMISSED,
    ],
}
