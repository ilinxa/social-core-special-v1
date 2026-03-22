# backend/apps/core/types.py
"""
Core Types
==========
Pure data structures used across the platform.

These types are designed to be consumed by multiple systems
without creating circular dependencies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple
from uuid import UUID

from django.utils import timezone

# Import from existing utility - DO NOT duplicate
from apps.core.utils.request import get_client_ip


@dataclass
class ActorContext:
    """
    Captures the complete context of an actor at action time.
    Used by: Transaction system, Form Builder, Audit system

    IMPORTANT: This is a pure data structure. Do NOT add methods that
    import or depend on RBAC models. Use RBACService.build_actor_context()
    to create instances from membership records.

    Attributes:
        user_id: UUID of the acting user (None for anonymous/system)
        account_type: AccountType value ('platform' or 'business')
        account_id: UUID of the account context
        membership_id: UUID of the membership record
        role_id: UUID of the assigned role
        role_name: Human-readable role name
        role_level: Role authority level (0=owner, 10=lowest)
        is_owner: Whether actor is account owner
        permissions_snapshot: List of (code, scope) tuples
        captured_at: When context was captured
        ip_address: Client IP address
        user_agent: Client user agent string
    """

    # NOTE: user_id is UUID because User.id is UUIDField (migrated in 0005/0006)
    user_id: UUID | None
    account_type: str | None  # AccountType value
    account_id: UUID | None
    membership_id: UUID | None
    role_id: UUID | None
    role_name: str | None
    role_level: int | None
    is_owner: bool
    # v2.0: Permissions carry scope as (code, scope) tuples
    # e.g. [("can_view_members", "business"), ("can_remove_member", "global_only")]
    permissions_snapshot: List[Tuple[str, str]] = field(default_factory=list)
    captured_at: datetime = field(default_factory=timezone.now)
    ip_address: str | None = None
    user_agent: str | None = None

    # --- Convenience permission checks (no RBAC imports needed) ---

    def has_permission(self, code: str) -> bool:
        """Check if actor has a permission (any scope)."""
        return any(c == code for c, _ in self.permissions_snapshot)

    def has_permission_with_scope(self, code: str, scope: str) -> bool:
        """Check if actor has a specific permission with a specific scope."""
        return (code, scope) in self.permissions_snapshot

    def has_global_permission(self, code: str) -> bool:
        """Check if actor has a permission with global or platform_and_global scope."""
        return any(
            c == code and s in ("global_only", "platform_and_global")
            for c, s in self.permissions_snapshot
        )

    def permission_codes(self) -> List[str]:
        """Return flat list of permission codes (for backward compatibility)."""
        return list(set(c for c, _ in self.permissions_snapshot))

    # --- Serialization ---

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage/transmission."""
        return {
            "user_id": str(self.user_id) if self.user_id else None,
            "account_type": self.account_type,
            "account_id": str(self.account_id) if self.account_id else None,
            "membership_id": str(self.membership_id) if self.membership_id else None,
            "role_id": str(self.role_id) if self.role_id else None,
            "role_name": self.role_name,
            "role_level": self.role_level,
            "is_owner": self.is_owner,
            # Store as list of [code, scope] pairs
            "permissions_snapshot": [[c, s] for c, s in self.permissions_snapshot],
            "captured_at": self.captured_at.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ActorContext":
        """Reconstruct from dictionary (for reading from storage)."""
        from datetime import datetime as dt

        perms = data.get("permissions_snapshot", [])
        # Handle both old format (flat list) and new format (list of pairs)
        if perms and isinstance(perms[0], str):
            # Legacy: flat list of codes -> treat as business scope
            parsed_perms = [(code, "business") for code in perms]
        else:
            parsed_perms = [(p[0], p[1]) for p in perms]

        return cls(
            user_id=UUID(data["user_id"]) if data.get("user_id") else None,
            account_type=data.get("account_type"),
            account_id=UUID(data["account_id"]) if data.get("account_id") else None,
            membership_id=(
                UUID(data["membership_id"]) if data.get("membership_id") else None
            ),
            role_id=UUID(data["role_id"]) if data.get("role_id") else None,
            role_name=data.get("role_name"),
            role_level=data.get("role_level"),
            is_owner=data.get("is_owner", False),
            permissions_snapshot=parsed_perms,
            captured_at=dt.fromisoformat(data["captured_at"]),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
        )

    @classmethod
    def for_user_context(cls, user, request=None) -> "ActorContext":
        """
        Create ActorContext for user-level actions (no account context).
        Use this for actions that don't require account membership.
        """
        return cls(
            user_id=user.id,
            account_type=None,
            account_id=None,
            membership_id=None,
            role_id=None,
            role_name=None,
            role_level=None,
            is_owner=False,
            permissions_snapshot=[],
            captured_at=timezone.now(),
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get("HTTP_USER_AGENT") if request else None,
        )

    @classmethod
    def for_anonymous(cls, request=None) -> "ActorContext":
        """Create ActorContext for anonymous/unauthenticated actions."""
        return cls(
            user_id=None,
            account_type=None,
            account_id=None,
            membership_id=None,
            role_id=None,
            role_name=None,
            role_level=None,
            is_owner=False,
            permissions_snapshot=[],
            captured_at=timezone.now(),
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get("HTTP_USER_AGENT") if request else None,
        )

    @classmethod
    def for_system(cls) -> "ActorContext":
        """Create ActorContext for system-initiated actions (Celery tasks, etc.)."""
        return cls(
            user_id=None,
            account_type=None,
            account_id=None,
            membership_id=None,
            role_id=None,
            role_name="SYSTEM",
            role_level=None,
            is_owner=False,
            permissions_snapshot=[],
            captured_at=timezone.now(),
            ip_address=None,
            user_agent=None,
        )
