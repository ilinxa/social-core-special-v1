"""
Tests for FG Sub-Feature Gates — Phase 4.

Verifies that disabling a sub-feature path via deployment config raises
``FeatureDisabled`` (HTTP 403, code ``feature_disabled``) at the service or
view layer, with the correct feature path in ``details.feature``.

Each test class covers one sub-feature gate. The "enabled" case is not tested
here — existing 4000+ tests cover normal behavior with all features on
(via the session-scoped _enable_all_features fixture).
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from apps.core.exceptions import FeatureDisabled
from apps.users.tests.factories import UserFactory


def _assert_feature_disabled(response, feature_path):
    """Assert response is 403 with feature_disabled code and correct path."""
    assert response.status_code == 403
    assert response.data["error"]["code"] == "feature_disabled"
    assert response.data["error"]["details"]["feature"] == feature_path


# =============================================================================
# Chat — Entity Participation
# =============================================================================


@pytest.mark.django_db
class TestChatEntityGate:
    """business.chat.entity / platform.chat.entity → create_conversation."""

    def test_business_entity_disabled(self, feature_config_override):
        feature_config_override({"business": {"chat": {"entity": False}}})
        from apps.chat.services import ChatService

        user = UserFactory()
        with pytest.raises(FeatureDisabled) as exc:
            ChatService.create_conversation(
                scope_type="global",
                conversation_type="direct",
                participant_ids=[
                    {"participant_type": "business", "participant_id": uuid4()}
                ],
                creator_type="user",
                creator_id=user.id,
                acting_user=user,
            )
        assert exc.value.details["feature"] == "business.chat.entity"

    def test_platform_entity_disabled(self, feature_config_override):
        feature_config_override({"platform": {"chat": {"entity": False}}})
        from apps.chat.services import ChatService

        user = UserFactory()
        with pytest.raises(FeatureDisabled) as exc:
            ChatService.create_conversation(
                scope_type="global",
                conversation_type="direct",
                participant_ids=[
                    {"participant_type": "platform", "participant_id": uuid4()}
                ],
                creator_type="user",
                creator_id=user.id,
                acting_user=user,
            )
        assert exc.value.details["feature"] == "platform.chat.entity"


# =============================================================================
# Chat — Group Conversations
# =============================================================================


@pytest.mark.django_db
class TestChatGroupGate:
    """user.chat.group / business.chat.group → create_conversation GROUP."""

    def test_user_group_disabled(self, feature_config_override):
        feature_config_override({"user": {"chat": {"group": False}}})
        from apps.chat.services import ChatService

        user = UserFactory()
        user2 = UserFactory()
        with pytest.raises(FeatureDisabled) as exc:
            ChatService.create_conversation(
                scope_type="global",
                conversation_type="group",
                participant_ids=[
                    {"participant_type": "user", "participant_id": user2.id}
                ],
                creator_type="user",
                creator_id=user.id,
                acting_user=user,
                name="Test Group",
            )
        assert exc.value.details["feature"] == "user.chat.group"

    def test_business_group_disabled(self, feature_config_override):
        feature_config_override({"business": {"chat": {"group": False}}})
        from apps.chat.services import ChatService

        user = UserFactory()
        user2 = UserFactory()
        # Business scope requires membership — mock the policy check
        with patch("apps.chat.policies.ChatPolicy.validate_scope_eligibility"):
            with pytest.raises(FeatureDisabled) as exc:
                ChatService.create_conversation(
                    scope_type="business",
                    scope_id=uuid4(),
                    conversation_type="group",
                    participant_ids=[
                        {"participant_type": "user", "participant_id": user2.id}
                    ],
                    creator_type="user",
                    creator_id=user.id,
                    acting_user=user,
                    name="Biz Group",
                )
            assert exc.value.details["feature"] == "business.chat.group"


# =============================================================================
# Chat — File Sharing
# =============================================================================


@pytest.mark.django_db
class TestChatFileSharingGate:
    """user.chat.file_sharing / business.chat.file_sharing → upload_attachment."""

    def test_user_file_sharing_disabled(self, feature_config_override):
        feature_config_override({"user": {"chat": {"file_sharing": False}}})
        from apps.chat.services import ChatService

        user = UserFactory()
        with pytest.raises(FeatureDisabled) as exc:
            ChatService.upload_attachment(
                conversation_id=uuid4(),
                user=user,
                file=MagicMock(),
            )
        assert exc.value.details["feature"] == "user.chat.file_sharing"

    def test_business_file_sharing_disabled(self, feature_config_override):
        feature_config_override({"business": {"chat": {"file_sharing": False}}})
        from apps.chat.models import Conversation
        from apps.chat.services import ChatService

        user = UserFactory()
        # Create a conversation in business scope
        conv = Conversation.objects.create(
            scope_type="business",
            scope_id=uuid4(),
            conversation_type="direct",
            created_by_type="user",
            created_by_id=user.id,
        )
        with pytest.raises(FeatureDisabled) as exc:
            ChatService.upload_attachment(
                conversation_id=conv.id,
                user=user,
                file=MagicMock(),
            )
        assert exc.value.details["feature"] == "business.chat.file_sharing"


# =============================================================================
# Chat — Reactions
# =============================================================================


@pytest.mark.django_db
class TestChatReactionsGate:
    """user.chat.reactions → add_reaction."""

    def test_reactions_disabled(self, feature_config_override):
        feature_config_override({"user": {"chat": {"reactions": False}}})
        from apps.chat.services import ChatService

        user = UserFactory()
        with pytest.raises(FeatureDisabled) as exc:
            ChatService.add_reaction(
                message_id=uuid4(),
                user=user,
                reaction="like",
            )
        assert exc.value.details["feature"] == "user.chat.reactions"


# =============================================================================
# Chat — Search
# =============================================================================


@pytest.mark.django_db
class TestChatSearchGate:
    """user.chat.search → ChatSelector.search_messages."""

    def test_search_disabled(self, feature_config_override):
        feature_config_override({"user": {"chat": {"search": False}}})
        from apps.chat.selectors import ChatSelector

        with pytest.raises(FeatureDisabled) as exc:
            ChatSelector.search_messages(
                query="hello",
                participant_type="user",
                participant_id=uuid4(),
                scope_type="global",
            )
        assert exc.value.details["feature"] == "user.chat.search"


# =============================================================================
# Network — Follows
# =============================================================================


@pytest.mark.django_db
class TestNetworkFollowGate:
    """user.network.follows / business.network.followers → create_follow."""

    def test_follows_disabled(self, feature_config_override):
        feature_config_override({"user": {"network": {"follows": False}}})
        from apps.network.services import FollowService

        user = UserFactory()
        with pytest.raises(FeatureDisabled) as exc:
            FollowService.create_follow(
                follower=user,
                followee_type="business",
                followee_id=uuid4(),
            )
        assert exc.value.details["feature"] == "user.network.follows"

    def test_business_followers_disabled(self, feature_config_override):
        feature_config_override({"business": {"network": {"followers": False}}})
        from apps.network.services import FollowService

        user = UserFactory()
        with pytest.raises(FeatureDisabled) as exc:
            FollowService.create_follow(
                follower=user,
                followee_type="business",
                followee_id=uuid4(),
            )
        assert exc.value.details["feature"] == "business.network.followers"


# =============================================================================
# Network — Connections
# =============================================================================


@pytest.mark.django_db
class TestNetworkConnectionGate:
    """user.network.connections / business.network.connections → create_*_connection."""

    def test_user_connections_disabled(self, feature_config_override):
        feature_config_override({"user": {"network": {"connections": False}}})
        from apps.network.services import ConnectionService

        user1 = UserFactory()
        user2 = UserFactory()
        with pytest.raises(FeatureDisabled) as exc:
            ConnectionService.create_user_connection(
                user_a_id=user1.id,
                user_b_id=user2.id,
            )
        assert exc.value.details["feature"] == "user.network.connections"

    def test_business_connections_disabled(self, feature_config_override):
        feature_config_override({"business": {"network": {"connections": False}}})
        from apps.network.services import ConnectionService

        with pytest.raises(FeatureDisabled) as exc:
            ConnectionService.create_account_connection(
                a_type="business",
                a_id=uuid4(),
                b_type="business",
                b_id=uuid4(),
            )
        assert exc.value.details["feature"] == "business.network.connections"


# =============================================================================
# Transaction — Member Invitations
# =============================================================================


@pytest.mark.django_db
class TestMemberInvitationGate:
    """business.members.invitations / platform.members.invitations → create_invitation."""

    def _make_actor_context(self, user_id, account_type="business", account_id=None):
        from apps.core.types import ActorContext

        return ActorContext(
            user_id=user_id,
            account_type=account_type,
            account_id=account_id or uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Owner",
            role_level=0,
            is_owner=True,
            permissions_snapshot=[],
        )

    def test_business_invitations_disabled(self, feature_config_override):
        feature_config_override({"business": {"members": {"invitations": False}}})
        from apps.transaction.services import TransactionService

        user = UserFactory()
        ctx = self._make_actor_context(user.id)
        with pytest.raises(FeatureDisabled) as exc:
            TransactionService.create_invitation(
                transaction_type="business_membership_invitation",
                initiator_context=ctx,
                target_user_id=uuid4(),
            )
        assert exc.value.details["feature"] == "business.members.invitations"

    def test_platform_invitations_disabled(self, feature_config_override):
        feature_config_override({"platform": {"members": {"invitations": False}}})
        from apps.transaction.services import TransactionService

        user = UserFactory()
        ctx = self._make_actor_context(user.id, account_type="platform")
        with pytest.raises(FeatureDisabled) as exc:
            TransactionService.create_invitation(
                transaction_type="platform_membership_invitation",
                initiator_context=ctx,
                target_user_id=uuid4(),
            )
        assert exc.value.details["feature"] == "platform.members.invitations"


# =============================================================================
# Transaction — Member Requests
# =============================================================================


@pytest.mark.django_db
class TestMemberRequestGate:
    """business.members.requests / platform.members.requests → create_request."""

    def test_business_requests_disabled(self, feature_config_override):
        feature_config_override({"business": {"members": {"requests": False}}})
        from apps.transaction.services import TransactionService

        user = UserFactory()
        with pytest.raises(FeatureDisabled) as exc:
            TransactionService.create_request(
                transaction_type="business_membership_request",
                user_id=user.id,
                target_account_type="business",
                target_account_id=uuid4(),
            )
        assert exc.value.details["feature"] == "business.members.requests"

    def test_platform_requests_disabled(self, feature_config_override):
        feature_config_override({"platform": {"members": {"requests": False}}})
        from apps.transaction.services import TransactionService

        user = UserFactory()
        with pytest.raises(FeatureDisabled) as exc:
            TransactionService.create_request(
                transaction_type="platform_membership_request",
                user_id=user.id,
                target_account_type="platform",
                target_account_id=uuid4(),
            )
        assert exc.value.details["feature"] == "platform.members.requests"


# =============================================================================
# Transaction — Sub-Features (verification, ownership transfer)
# =============================================================================


@pytest.mark.django_db
class TestTransactionSubFeatureGate:
    """Verification + ownership transfer sub-feature gates via gate maps."""

    def test_verification_disabled(self, feature_config_override):
        feature_config_override({"business": {"transactions": {"verification": False}}})
        from apps.transaction.services import TransactionService

        user = UserFactory()
        with pytest.raises(FeatureDisabled) as exc:
            TransactionService.create_request(
                transaction_type="business_verification_request",
                user_id=user.id,
                target_account_type="platform",
                target_account_id=uuid4(),
            )
        assert exc.value.details["feature"] == "business.transactions.verification"

    def test_business_ownership_transfer_disabled(self, feature_config_override):
        from apps.core.types import ActorContext

        feature_config_override(
            {"business": {"transactions": {"ownership_transfer": False}}}
        )
        from apps.transaction.services import TransactionService

        user = UserFactory()
        ctx = ActorContext(
            user_id=user.id,
            account_type="business",
            account_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Owner",
            role_level=0,
            is_owner=True,
            permissions_snapshot=[],
        )
        with pytest.raises(FeatureDisabled) as exc:
            TransactionService.create_invitation(
                transaction_type="business_ownership_transfer",
                initiator_context=ctx,
                target_user_id=uuid4(),
            )
        assert (
            exc.value.details["feature"] == "business.transactions.ownership_transfer"
        )

    def test_platform_ownership_transfer_disabled(self, feature_config_override):
        from apps.core.types import ActorContext

        feature_config_override(
            {"platform": {"transactions": {"ownership_transfer": False}}}
        )
        from apps.transaction.services import TransactionService

        user = UserFactory()
        ctx = ActorContext(
            user_id=user.id,
            account_type="platform",
            account_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Owner",
            role_level=0,
            is_owner=True,
            permissions_snapshot=[],
        )
        with pytest.raises(FeatureDisabled) as exc:
            TransactionService.create_invitation(
                transaction_type="platform_ownership_transfer",
                initiator_context=ctx,
                target_user_id=uuid4(),
            )
        assert (
            exc.value.details["feature"] == "platform.transactions.ownership_transfer"
        )


# =============================================================================
# Governance
# =============================================================================


@pytest.mark.django_db
class TestGovernanceGate:
    """platform.governance.business_approval / business_verification."""

    def test_business_approval_disabled(self, feature_config_override):
        feature_config_override(
            {"platform": {"governance": {"business_approval": False}}}
        )
        from apps.transaction.services import TransactionService

        user = UserFactory()
        with pytest.raises(FeatureDisabled) as exc:
            TransactionService.create_request(
                transaction_type="business_creation_permission_request",
                user_id=user.id,
                target_account_type="platform",
                target_account_id=uuid4(),
            )
        assert exc.value.details["feature"] == "platform.governance.business_approval"

    def test_business_verification_disabled(self, feature_config_override):
        feature_config_override(
            {"platform": {"governance": {"business_verification": False}}}
        )
        from apps.transaction.services import TransactionService

        user = UserFactory()
        with pytest.raises(FeatureDisabled) as exc:
            TransactionService.create_request(
                transaction_type="business_verification_request",
                user_id=user.id,
                target_account_type="platform",
                target_account_id=uuid4(),
            )
        # verification has two gates — first disabled wins
        assert exc.value.details["feature"] in (
            "business.transactions.verification",
            "platform.governance.business_verification",
        )


# =============================================================================
# RBAC — Custom Roles
# =============================================================================


@pytest.mark.django_db
class TestCustomRolesGate:
    """business.members.custom_roles / platform.members.custom_roles."""

    def test_business_custom_roles_disabled(self, feature_config_override):
        feature_config_override({"business": {"members": {"custom_roles": False}}})
        from apps.core.types import ActorContext
        from apps.rbac.services import RBACService

        user = UserFactory()
        ctx = ActorContext(
            user_id=user.id,
            account_type="business",
            account_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Owner",
            role_level=0,
            is_owner=True,
            permissions_snapshot=[("can_create_role", "account")],
        )
        with pytest.raises(FeatureDisabled) as exc:
            RBACService.create_custom_role(
                account_type="business",
                account_id=uuid4(),
                name="Test Role",
                level=5,
                actor_context=ctx,
            )
        assert exc.value.details["feature"] == "business.members.custom_roles"

    def test_platform_custom_roles_disabled(self, feature_config_override):
        feature_config_override({"platform": {"members": {"custom_roles": False}}})
        from apps.core.types import ActorContext
        from apps.rbac.services import RBACService

        user = UserFactory()
        ctx = ActorContext(
            user_id=user.id,
            account_type="platform",
            account_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Owner",
            role_level=0,
            is_owner=True,
            permissions_snapshot=[("can_create_role", "account")],
        )
        with pytest.raises(FeatureDisabled) as exc:
            RBACService.create_custom_role(
                account_type="platform",
                account_id=uuid4(),
                name="Test Role",
                level=5,
                actor_context=ctx,
            )
        assert exc.value.details["feature"] == "platform.members.custom_roles"


# =============================================================================
# Forms — Transaction Mapping (early return, not raise)
# =============================================================================


@pytest.mark.django_db
class TestFormTransactionMappingGate:
    """business.forms.transaction_mapping → _validate_form_mapping_requirement."""

    def test_mapping_skipped_when_disabled(self, feature_config_override):
        """When disabled, mapping validation is skipped (no error even without form)."""
        feature_config_override({"business": {"forms": {"transaction_mapping": False}}})
        from apps.transaction.services import TransactionService

        # This should NOT raise — the mapping check is silently skipped
        TransactionService._validate_form_mapping_requirement(
            transaction_type="business_membership_request",
            account_type="business",
            account_id=uuid4(),
            form_response_id=None,
        )
        # If we get here without exception, the gate worked (early return)


# =============================================================================
# Explore — Sub-Feature Gates (view-level)
# =============================================================================


@pytest.mark.django_db
class TestExploreSubFeatureGate:
    """Explore sub-feature gates in views + selector."""

    def test_search_users_disabled_returns_403(self, feature_config_override):
        feature_config_override({"user": {"explore": {"search_users": False}}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        response = client.get("/api/v1/explore/users/")
        _assert_feature_disabled(response, "user.explore.search_users")

    def test_search_businesses_disabled_returns_403_for_auth(
        self, feature_config_override
    ):
        feature_config_override({"user": {"explore": {"search_businesses": False}}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        response = client.get("/api/v1/explore/businesses/")
        _assert_feature_disabled(response, "user.explore.search_businesses")

    def test_search_businesses_still_works_for_anonymous(self, feature_config_override):
        """Anonymous search is not gated by the sub-feature (public endpoint)."""
        feature_config_override({"user": {"explore": {"search_businesses": False}}})
        client = APIClient()
        response = client.get("/api/v1/explore/businesses/")
        assert response.status_code == 200

    def test_combined_view_graceful_skip(self, feature_config_override):
        """When search_users is disabled, combined view returns 0 users (not 403)."""
        feature_config_override({"user": {"explore": {"search_users": False}}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        response = client.get("/api/v1/explore/")
        assert response.status_code == 200
        assert response.data["users_count"] == 0
        assert response.data["users"] == []

    def test_is_discoverable_disabled_returns_empty(self, feature_config_override):
        """When user discoverability is disabled, search returns no users."""
        feature_config_override({"user": {"explore": {"is_discoverable": False}}})
        from apps.explore.selectors import ExploreSelector

        qs = ExploreSelector.search_users(query="test")
        assert qs.count() == 0
