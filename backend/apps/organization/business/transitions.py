# apps/organization/business/transitions.py
"""
Business Status State Machine
==============================
Defines valid status transitions and provides validation.

Transition Rules:
    PENDING   → [ACTIVE, ARCHIVED]
    ACTIVE    → [SUSPENDED, ARCHIVED, DELETED]
    SUSPENDED → [ACTIVE, ARCHIVED]
    ARCHIVED  → [] (terminal)
    DELETED   → [] (terminal)

Notes:
    - PENDING only reached when platform.governance.business_approval gate is ON
    - ACTIVE → DELETED: owner-only (soft delete)
    - ACTIVE/SUSPENDED → ARCHIVED: owner or governance
    - ACTIVE → SUSPENDED: governance only, mandatory reason
    - Force-delete: superuser-only via /admin diagnostics
"""

from apps.core.constants import BusinessStatus

VALID_TRANSITIONS = {
    BusinessStatus.PENDING: [BusinessStatus.ACTIVE, BusinessStatus.ARCHIVED],
    BusinessStatus.ACTIVE: [
        BusinessStatus.SUSPENDED,
        BusinessStatus.ARCHIVED,
        BusinessStatus.DELETED,
    ],
    BusinessStatus.SUSPENDED: [BusinessStatus.ACTIVE, BusinessStatus.ARCHIVED],
    BusinessStatus.ARCHIVED: [],  # terminal
    BusinessStatus.DELETED: [],  # terminal
}


def validate_transition(current_status: str, new_status: str) -> None:
    """
    Validate that a business status transition is allowed.

    Args:
        current_status: Current business status.
        new_status: Target business status.

    Raises:
        ValidationError: If the transition is not allowed.
    """
    from apps.core.exceptions import ValidationError

    allowed = VALID_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise ValidationError(
            message=f"Cannot transition from '{current_status}' to '{new_status}'",
            field="status",
        )
