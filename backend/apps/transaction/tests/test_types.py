"""
Tests for TransactionTypeConfig, TRANSACTION_TYPES registry, and get_transaction_type.

Covers:
- All 10 transaction types are registered
- get_transaction_type returns correct config / raises NotFound
- Mode validation (INVITATION vs REQUEST)
- Approver policies
- owner_only flags
- Target types
- Expiration, cooldown, and permission fields
"""

import pytest

from apps.core.constants import ContextType
from apps.core.exceptions import NotFound
from apps.transaction.constants import ApproverPolicy, PartyType, TransactionMode
from apps.transaction.types import (
    TRANSACTION_TYPES,
    TransactionTypeConfig,
    get_transaction_type,
)

ALL_TYPE_IDS = [
    "platform_membership_invitation",
    "platform_membership_request",
    "platform_ownership_transfer",
    "business_membership_invitation",
    "business_membership_request",
    "business_verification_request",
    "business_follow_request",
    "business_follow_approval_request",
    "platform_follow_request",
    "business_ownership_transfer",
    "business_creation_permission_request",
    "business_connection_request",
    "business_platform_connection_request",
    "cms_activation_request",
    "user_connection_request",
    "business_suspension_appeal",
    "membership_enforcement_appeal",
]

INVITATION_TYPES = [
    "platform_membership_invitation",
    "platform_ownership_transfer",
    "business_membership_invitation",
    "business_ownership_transfer",
]

REQUEST_TYPES = [
    "platform_membership_request",
    "business_membership_request",
    "business_verification_request",
    "business_follow_request",
    "business_follow_approval_request",
    "platform_follow_request",
    "business_creation_permission_request",
    "business_connection_request",
    "business_platform_connection_request",
    "user_connection_request",
    "cms_activation_request",
    "business_suspension_appeal",
    "membership_enforcement_appeal",
]


class TestTransactionTypesRegistry:

    def test_all_types_registered(self):
        assert len(TRANSACTION_TYPES) == 17

    @pytest.mark.parametrize("type_id", ALL_TYPE_IDS)
    def test_type_is_registered(self, type_id):
        assert type_id in TRANSACTION_TYPES


class TestGetTransactionType:

    @pytest.mark.parametrize("type_id", ALL_TYPE_IDS)
    def test_returns_correct_config_for_valid_type(self, type_id):
        config = get_transaction_type(type_id)
        assert isinstance(config, TransactionTypeConfig)
        assert config.id == type_id

    def test_raises_not_found_for_unknown_type(self):
        with pytest.raises(NotFound):
            get_transaction_type("nonexistent_type")


class TestTransactionTypeConfigFields:

    @pytest.mark.parametrize("type_id", ALL_TYPE_IDS)
    def test_all_types_have_required_fields(self, type_id):
        config = get_transaction_type(type_id)
        assert config.id, "id must not be empty"
        assert config.name, "name must not be empty"
        assert config.mode, "mode must not be empty"
        assert config.context_type, "context_type must not be empty"

    @pytest.mark.parametrize("type_id", ALL_TYPE_IDS)
    def test_all_types_have_expiration_days_gt_zero(self, type_id):
        config = get_transaction_type(type_id)
        assert config.expiration_days > 0


class TestTransactionModes:

    @pytest.mark.parametrize("type_id", INVITATION_TYPES)
    def test_invitation_types_have_invitation_mode(self, type_id):
        config = get_transaction_type(type_id)
        assert config.mode == TransactionMode.INVITATION

    @pytest.mark.parametrize("type_id", REQUEST_TYPES)
    def test_request_types_have_request_mode(self, type_id):
        config = get_transaction_type(type_id)
        assert config.mode == TransactionMode.REQUEST


class TestApproverPolicies:

    def test_business_follow_request_has_auto_approval(self):
        config = get_transaction_type("business_follow_request")
        assert config.approver_policy == ApproverPolicy.AUTO_APPROVAL

    def test_platform_membership_request_has_platform_authority(self):
        config = get_transaction_type("platform_membership_request")
        assert config.approver_policy == ApproverPolicy.PLATFORM_AUTHORITY

    def test_business_membership_request_has_account_authority(self):
        config = get_transaction_type("business_membership_request")
        assert config.approver_policy == ApproverPolicy.ACCOUNT_AUTHORITY


class TestTargetTypes:

    def test_user_connection_request_targets_user(self):
        config = get_transaction_type("user_connection_request")
        assert config.target_types == [PartyType.USER]


class TestOwnerOnlyTypes:

    @pytest.mark.parametrize(
        "type_id",
        [
            "platform_ownership_transfer",
            "business_ownership_transfer",
        ],
    )
    def test_ownership_transfer_types_are_owner_only(self, type_id):
        config = get_transaction_type(type_id)
        assert config.owner_only is True

    @pytest.mark.parametrize(
        "type_id",
        [
            t
            for t in ALL_TYPE_IDS
            if t
            not in (
                "platform_ownership_transfer",
                "business_ownership_transfer",
                "cms_activation_request",
            )
        ],
    )
    def test_non_ownership_transfer_types_are_not_owner_only(self, type_id):
        config = get_transaction_type(type_id)
        assert config.owner_only is False


class TestPermissions:

    @pytest.mark.parametrize("type_id", ALL_TYPE_IDS)
    def test_types_with_required_permissions_are_not_empty_strings(self, type_id):
        config = get_transaction_type(type_id)
        for perm in config.required_permissions:
            assert perm, "Required permission must not be an empty string"
