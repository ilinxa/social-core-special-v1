from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID
from apps.core.constants import ContextType
from apps.transaction.constants import TransactionMode, PartyType, ApproverPolicy


@dataclass
class TransactionTypeConfig:
    id: str
    name: str
    mode: TransactionMode
    initiator_types: List[PartyType]
    target_types: List[PartyType]
    context_type: ContextType
    approver_policy: ApproverPolicy
    required_permissions: List[str] = field(default_factory=list)
    approval_permission: Optional[str] = None
    owner_only: bool = False
    required_form_template_id: Optional[UUID] = None
    optional_form_template_id: Optional[UUID] = None
    required_form_template_slug: Optional[str] = None
    optional_form_template_slug: Optional[str] = None
    payload_schema: dict = field(default_factory=dict)
    expiration_days: int = 7
    resubmission_cooldown_days: int = 0
    category: str = ""
    conflict_group: str = ""
    outcome_handler: str = ""
    on_create_handler: str = ""
    on_close_handler: str = ""
    user_configurable: bool = True
    enabled: bool = True

    @property
    def requires_form(self) -> bool:
        return self.required_form_template_slug is not None or self.required_form_template_id is not None

    @property
    def has_optional_form(self) -> bool:
        return self.optional_form_template_slug is not None or self.optional_form_template_id is not None


TRANSACTION_TYPES = {
    # --- PLATFORM ---
    "platform_membership_invitation": TransactionTypeConfig(
        id="platform_membership_invitation",
        name="Platform Membership Invitation",
        category="membership",
        conflict_group="platform_membership",
        mode=TransactionMode.INVITATION,
        initiator_types=[PartyType.MEMBERSHIP_ACTOR],
        target_types=[PartyType.USER],
        context_type=ContextType.PLATFORM,
        approver_policy=ApproverPolicy.TARGET_ACCEPTANCE,
        required_permissions=["can_invite_member"],
        payload_schema={
            "role_id": {"type": "string", "format": "uuid", "required": True},
            "message": {"type": "string", "max_length": 500, "required": False},
        },
        expiration_days=14,
        outcome_handler="apps.transaction.outcome_handlers.MembershipOutcomeHandler.handle_invitation_accepted",
    ),
    "platform_membership_request": TransactionTypeConfig(
        id="platform_membership_request",
        name="Platform Membership Request",
        category="membership",
        conflict_group="platform_membership",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.USER],
        target_types=[PartyType.ACCOUNT],
        context_type=ContextType.PLATFORM,
        approver_policy=ApproverPolicy.PLATFORM_AUTHORITY,
        approval_permission="can_approve_membership_request",
        expiration_days=30,
        resubmission_cooldown_days=7,
        outcome_handler="apps.transaction.outcome_handlers.MembershipOutcomeHandler.handle_request_approved",
    ),
    "platform_ownership_transfer": TransactionTypeConfig(
        id="platform_ownership_transfer",
        name="Platform Ownership Transfer",
        category="ownership",
        conflict_group="platform_ownership",
        mode=TransactionMode.INVITATION,
        initiator_types=[PartyType.MEMBERSHIP_ACTOR],
        target_types=[PartyType.USER],
        context_type=ContextType.PLATFORM,
        approver_policy=ApproverPolicy.TARGET_ACCEPTANCE,
        owner_only=True,
        expiration_days=7,
        outcome_handler="apps.transaction.outcome_handlers.OwnershipOutcomeHandler.handle_accepted",
    ),

    # --- BUSINESS ---
    "business_membership_invitation": TransactionTypeConfig(
        id="business_membership_invitation",
        name="Business Membership Invitation",
        category="membership",
        conflict_group="business_membership",
        mode=TransactionMode.INVITATION,
        initiator_types=[PartyType.MEMBERSHIP_ACTOR],
        target_types=[PartyType.USER],
        context_type=ContextType.BUSINESS,
        approver_policy=ApproverPolicy.TARGET_ACCEPTANCE,
        required_permissions=["can_invite_member"],
        payload_schema={
            "role_id": {"type": "string", "format": "uuid", "required": True},
            "message": {"type": "string", "max_length": 500, "required": False},
        },
        expiration_days=7,
        outcome_handler="apps.transaction.outcome_handlers.MembershipOutcomeHandler.handle_invitation_accepted",
    ),
    "business_membership_request": TransactionTypeConfig(
        id="business_membership_request",
        name="Business Membership Request",
        category="membership",
        conflict_group="business_membership",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.USER],
        target_types=[PartyType.ACCOUNT],
        context_type=ContextType.BUSINESS,
        approver_policy=ApproverPolicy.ACCOUNT_AUTHORITY,
        approval_permission="can_approve_membership_request",
        payload_schema={
            "message": {"type": "string", "max_length": 1000, "required": False},
            "referral_code": {"type": "string", "required": False},
        },
        expiration_days=30,
        resubmission_cooldown_days=7,
        outcome_handler="apps.transaction.outcome_handlers.MembershipOutcomeHandler.handle_request_approved",
    ),
    "business_verification_request": TransactionTypeConfig(
        id="business_verification_request",
        name="Business Verification Request",
        category="verification",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.MEMBERSHIP_ACTOR],
        target_types=[PartyType.ACCOUNT],
        context_type=ContextType.PLATFORM,
        approver_policy=ApproverPolicy.PLATFORM_AUTHORITY,
        approval_permission="can_approve_verification_request",
        required_form_template_slug="system-business-verification",
        payload_schema={
            "documents": {"type": "array", "required": False},
        },
        expiration_days=90,
        resubmission_cooldown_days=30,
        outcome_handler="apps.transaction.outcome_handlers.VerificationOutcomeHandler.handle_accepted",
        on_create_handler="apps.transaction.outcome_handlers.VerificationOutcomeHandler.handle_created",
        on_close_handler="apps.transaction.outcome_handlers.VerificationOutcomeHandler.handle_closed",
    ),
    "business_follow_request": TransactionTypeConfig(
        id="business_follow_request",
        name="Business Follow Request",
        category="social",
        conflict_group="business_follow",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.USER],
        target_types=[PartyType.ACCOUNT],
        context_type=ContextType.BUSINESS,
        approver_policy=ApproverPolicy.AUTO_APPROVAL,
        expiration_days=30,
        outcome_handler="apps.network.outcome_handlers.FollowOutcomeHandler.handle_accepted",
    ),
    "business_follow_approval_request": TransactionTypeConfig(
        id="business_follow_approval_request",
        name="Business Follow Approval Request",
        category="social",
        conflict_group="business_follow",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.USER],
        target_types=[PartyType.ACCOUNT],
        context_type=ContextType.BUSINESS,
        approver_policy=ApproverPolicy.ACCOUNT_AUTHORITY,
        approval_permission="can_manage_followers",
        expiration_days=30,
        outcome_handler="apps.network.outcome_handlers.FollowOutcomeHandler.handle_accepted",
    ),
    "platform_follow_request": TransactionTypeConfig(
        id="platform_follow_request",
        name="Platform Follow Request",
        category="social",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.USER],
        target_types=[PartyType.ACCOUNT],
        context_type=ContextType.PLATFORM,
        approver_policy=ApproverPolicy.AUTO_APPROVAL,
        expiration_days=30,
        outcome_handler="apps.network.outcome_handlers.FollowOutcomeHandler.handle_accepted",
    ),
    "business_ownership_transfer": TransactionTypeConfig(
        id="business_ownership_transfer",
        name="Business Ownership Transfer",
        category="ownership",
        conflict_group="business_ownership",
        mode=TransactionMode.INVITATION,
        initiator_types=[PartyType.MEMBERSHIP_ACTOR],
        target_types=[PartyType.USER],
        context_type=ContextType.BUSINESS,
        approver_policy=ApproverPolicy.TARGET_ACCEPTANCE,
        owner_only=True,
        payload_schema={
            "message": {"type": "string", "required": False},
        },
        expiration_days=7,
        outcome_handler="apps.transaction.outcome_handlers.OwnershipOutcomeHandler.handle_accepted",
    ),
    "business_creation_permission_request": TransactionTypeConfig(
        id="business_creation_permission_request",
        name="Business Creation Permission Request",
        category="permission",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.USER],
        target_types=[PartyType.ACCOUNT],
        context_type=ContextType.PLATFORM,
        approver_policy=ApproverPolicy.PLATFORM_AUTHORITY,
        approval_permission="can_approve_business_creation",
        required_form_template_slug="system-business-creation",
        expiration_days=30,
        resubmission_cooldown_days=30,
        outcome_handler="apps.transaction.outcome_handlers.PermissionOutcomeHandler.handle_business_creation_approved",
    ),

    # --- BUSINESS CONNECTIONS ---
    "business_connection_request": TransactionTypeConfig(
        id="business_connection_request",
        name="Business Connection Request",
        category="social",
        conflict_group="business_connection",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.USER],
        target_types=[PartyType.ACCOUNT],
        context_type=ContextType.BUSINESS,
        approver_policy=ApproverPolicy.ACCOUNT_AUTHORITY,
        approval_permission="can_manage_connections",
        payload_schema={
            "initiator_account_type": {"type": "string", "required": True},
            "initiator_account_id": {"type": "string", "format": "uuid", "required": True},
            "note": {"type": "string", "max_length": 500, "required": False},
        },
        expiration_days=30,
        resubmission_cooldown_days=7,
        outcome_handler="apps.network.outcome_handlers.ConnectionOutcomeHandler.handle_account_accepted",
    ),
    "business_platform_connection_request": TransactionTypeConfig(
        id="business_platform_connection_request",
        name="Business-Platform Connection Request",
        category="social",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.USER],
        target_types=[PartyType.ACCOUNT],
        context_type=ContextType.PLATFORM,
        approver_policy=ApproverPolicy.PLATFORM_AUTHORITY,
        approval_permission="can_manage_connections",
        payload_schema={
            "initiator_account_type": {"type": "string", "required": True},
            "initiator_account_id": {"type": "string", "format": "uuid", "required": True},
            "note": {"type": "string", "max_length": 500, "required": False},
        },
        expiration_days=30,
        resubmission_cooldown_days=7,
        outcome_handler="apps.network.outcome_handlers.ConnectionOutcomeHandler.handle_account_accepted",
    ),

    # --- USER-TO-USER ---
    "user_connection_request": TransactionTypeConfig(
        id="user_connection_request",
        name="User Connection Request",
        category="social",
        conflict_group="user_connection",
        mode=TransactionMode.REQUEST,
        initiator_types=[PartyType.USER],
        target_types=[PartyType.USER],
        context_type=ContextType.USER,
        approver_policy=ApproverPolicy.TARGET_ACCEPTANCE,
        payload_schema={
            "note": {"type": "string", "max_length": 500, "required": False},
        },
        expiration_days=30,
        resubmission_cooldown_days=7,
        outcome_handler="apps.network.outcome_handlers.ConnectionOutcomeHandler.handle_user_accepted",
    ),
}


def get_conflict_group_types(conflict_group: str) -> list[str]:
    """Return all transaction type IDs in the same conflict group."""
    if not conflict_group:
        return []
    return [
        cfg.id for cfg in TRANSACTION_TYPES.values()
        if cfg.conflict_group == conflict_group
    ]


def get_transaction_type(type_id: str) -> TransactionTypeConfig:
    from apps.core.exceptions import NotFound
    config = TRANSACTION_TYPES.get(type_id)
    if not config:
        raise NotFound(
            message=f"Unknown transaction type: {type_id}",
            resource="TransactionType",
            resource_id=type_id,
        )
    return config
