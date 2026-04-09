"""
Tests for VG (Value Gate) Limits — Phase 5
===========================================
Service-layer enforcement of 16 numeric limits.
Each limit uses feature_config.check_limit() to raise BusinessRuleViolation
when the current count reaches the configured cap (0 = unlimited).
"""

import uuid

import pytest

from apps.core.exceptions import BusinessRuleViolation
from apps.core.feature_config import FeatureConfig, feature_config


def _actor_context_from_membership(membership):
    """Build an ActorContext from a Membership instance (test helper)."""
    from apps.core.types import ActorContext

    return ActorContext(
        user_id=membership.user_id,
        account_type=membership.account_type,
        account_id=membership.account_id,
        membership_id=membership.id,
        role_id=membership.role_id,
        role_name=membership.role.name if membership.role else None,
        role_level=membership.role.level if membership.role else 0,
        is_owner=membership.is_owner,
    )


# =============================================================================
# Foundation — check_limit() helper and BusinessRuleViolation extension
# =============================================================================


class TestCheckLimitHelper:
    """Direct tests for feature_config.check_limit()."""

    def test_raises_when_at_limit(self, feature_config_override):
        feature_config_override({"limits": {"max_users": 5}})

        with pytest.raises(BusinessRuleViolation) as exc:
            feature_config.check_limit(
                "limits.max_users", 5, rule="max_users_exceeded", resource="User"
            )

        assert exc.value.details["rule"] == "max_users_exceeded"
        assert exc.value.details["limit"] == 5
        assert exc.value.details["current"] == 5

    def test_no_raise_when_zero_unlimited(self, feature_config_override):
        feature_config_override({"limits": {"max_users": 0}})

        # Should NOT raise — 0 means unlimited
        feature_config.check_limit(
            "limits.max_users", 9999, rule="max_users_exceeded", resource="User"
        )


class TestBusinessRuleViolationExtended:
    """Test limit and current fields in BusinessRuleViolation details."""

    def test_details_include_limit_and_current(self):
        exc = BusinessRuleViolation(
            message="Test", rule="test_rule", limit=10, current=10
        )

        assert exc.details["rule"] == "test_rule"
        assert exc.details["limit"] == 10
        assert exc.details["current"] == 10


# =============================================================================
# Deployment-Wide Limits
# =============================================================================


@pytest.mark.django_db
class TestMaxUsersLimit:

    def test_enforced_when_at_limit(self, feature_config_override):
        from apps.users.services import UserService
        from apps.users.tests.factories import UserFactory

        feature_config_override({"limits": {"max_users": 1}})
        UserFactory()  # 1 active user — at limit

        with pytest.raises(BusinessRuleViolation) as exc:
            UserService.create_user(email="new@example.com", password="StrongPass1!")

        assert exc.value.details["rule"] == "max_users_exceeded"
        assert exc.value.details["limit"] == 1
        assert exc.value.details["current"] == 1

    def test_unlimited_when_zero(self, feature_config_override):
        from apps.users.services import UserService
        from apps.users.tests.factories import UserFactory

        feature_config_override({"limits": {"max_users": 0}})
        UserFactory()

        user = UserService.create_user(email="new@example.com", password="StrongPass1!")
        assert user is not None


@pytest.mark.django_db
class TestMaxBusinessesLimit:

    def test_enforced_when_at_limit(self, feature_config_override):
        from apps.organization.business.services import BusinessAccountService
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"limits": {"max_businesses": 1}})
        user = UserFactory()
        BusinessAccountFactory(created_by=user)  # 1 active business

        with pytest.raises(BusinessRuleViolation) as exc:
            BusinessAccountService.create_business(
                owner=user, legal_name="New Business", country="US"
            )

        assert exc.value.details["rule"] == "max_businesses_exceeded"
        assert exc.value.details["limit"] == 1

    def test_unlimited_when_zero(self, feature_config_override):
        from apps.organization.business.services import BusinessAccountService
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"limits": {"max_businesses": 0}})
        user = UserFactory()
        BusinessAccountFactory(created_by=user)

        biz = BusinessAccountService.create_business(
            owner=user, legal_name="Another Business", country="US"
        )
        assert biz is not None


@pytest.mark.django_db
class TestMaxBusinessesPerUserLimit:

    def test_enforced_when_at_limit(self, feature_config_override):
        from apps.organization.business.services import BusinessAccountService
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"limits": {"max_businesses_per_user": 1}})
        user = UserFactory()
        BusinessAccountFactory(created_by=user)

        with pytest.raises(BusinessRuleViolation) as exc:
            BusinessAccountService.create_business(
                owner=user, legal_name="Second Business", country="US"
            )

        assert exc.value.details["rule"] == "max_businesses_per_user_exceeded"
        assert exc.value.details["limit"] == 1

    def test_different_user_not_affected(self, feature_config_override):
        from apps.organization.business.services import BusinessAccountService
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"limits": {"max_businesses_per_user": 1}})
        user1 = UserFactory()
        user2 = UserFactory()
        BusinessAccountFactory(created_by=user1)

        # user2 has no businesses — should succeed
        biz = BusinessAccountService.create_business(
            owner=user2, legal_name="User2 Business", country="US"
        )
        assert biz is not None


# =============================================================================
# User Limits
# =============================================================================


@pytest.mark.django_db
class TestMaxMembershipsLimit:

    def test_enforced_when_at_limit(self, feature_config_override):
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.rbac.services import RBACService
        from apps.rbac.tests.factories import MembershipFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"user": {"max_memberships": 1}})
        user = UserFactory()
        biz1 = BusinessAccountFactory()
        RBACService.initialize_business_account(
            business_id=biz1.id, owner=biz1.created_by
        )
        # Create 1 active membership via factory
        MembershipFactory(
            user=user, account_type="business", account_id=biz1.id, status="active"
        )

        biz2 = BusinessAccountFactory()
        RBACService.initialize_business_account(
            business_id=biz2.id, owner=biz2.created_by
        )

        with pytest.raises(BusinessRuleViolation) as exc:
            RBACService.create_membership(
                user=user, account_type="business", account_id=biz2.id
            )

        assert exc.value.details["rule"] == "max_memberships_exceeded"
        assert exc.value.details["limit"] == 1

    def test_unlimited_when_zero(self, feature_config_override):
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.rbac.services import RBACService
        from apps.rbac.tests.factories import MembershipFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"user": {"max_memberships": 0}})
        user = UserFactory()
        biz1 = BusinessAccountFactory()
        RBACService.initialize_business_account(
            business_id=biz1.id, owner=biz1.created_by
        )
        MembershipFactory(
            user=user, account_type="business", account_id=biz1.id, status="active"
        )

        biz2 = BusinessAccountFactory()
        RBACService.initialize_business_account(
            business_id=biz2.id, owner=biz2.created_by
        )

        # Should NOT raise — 0 = unlimited
        membership = RBACService.create_membership(
            user=user, account_type="business", account_id=biz2.id
        )
        assert membership is not None


@pytest.mark.django_db
class TestMaxConnectionsLimit:

    def test_enforced_when_at_limit(self, feature_config_override):
        from apps.network.services import ConnectionService
        from apps.network.tests.factories import UserConnectionFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"user": {"network": {"max_connections": 1}}})
        user_a = UserFactory()
        user_b = UserFactory()
        user_c = UserFactory()
        # Create 1 active connection for user_a
        UserConnectionFactory(user_a=user_a, user_b=user_b)

        with pytest.raises(BusinessRuleViolation) as exc:
            ConnectionService.create_user_connection(
                user_a_id=user_a.id, user_b_id=user_c.id
            )

        assert exc.value.details["rule"] == "max_connections_exceeded"
        assert exc.value.details["limit"] == 1

    def test_unlimited_when_zero(self, feature_config_override):
        from apps.network.services import ConnectionService
        from apps.network.tests.factories import UserConnectionFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"user": {"network": {"max_connections": 0}}})
        user_a = UserFactory()
        user_b = UserFactory()
        user_c = UserFactory()
        UserConnectionFactory(user_a=user_a, user_b=user_b)

        conn = ConnectionService.create_user_connection(
            user_a_id=user_a.id, user_b_id=user_c.id
        )
        assert conn is not None


@pytest.mark.django_db
class TestMaxFollowsLimit:

    def test_enforced_when_at_limit(self, feature_config_override):
        from apps.network.services import FollowService
        from apps.network.tests.factories import FollowFactory
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"user": {"network": {"max_follows": 1}}})
        user = UserFactory()
        biz1 = BusinessAccountFactory()
        FollowFactory(follower=user, followee_type="business", followee_id=biz1.id)

        biz2 = BusinessAccountFactory()

        with pytest.raises(BusinessRuleViolation) as exc:
            FollowService.create_follow(
                follower=user, followee_type="business", followee_id=biz2.id
            )

        assert exc.value.details["rule"] == "max_follows_exceeded"
        assert exc.value.details["limit"] == 1

    def test_unlimited_when_zero(self, feature_config_override):
        from apps.network.services import FollowService
        from apps.network.tests.factories import FollowFactory
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"user": {"network": {"max_follows": 0}}})
        user = UserFactory()
        biz1 = BusinessAccountFactory()
        FollowFactory(follower=user, followee_type="business", followee_id=biz1.id)

        biz2 = BusinessAccountFactory()

        follow = FollowService.create_follow(
            follower=user, followee_type="business", followee_id=biz2.id
        )
        assert follow is not None


@pytest.mark.django_db
class TestMaxGroupsLimit:

    def test_user_global_group_limit(self, feature_config_override):
        from apps.chat.services import ChatService
        from apps.chat.tests.factories import ConversationFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"user": {"chat": {"max_groups": 1}}})
        user = UserFactory()
        ConversationFactory(
            scope_type="global",
            scope_id=None,
            conversation_type="group",
            created_by_type="user",
            created_by_id=user.id,
        )

        with pytest.raises(BusinessRuleViolation) as exc:
            ChatService.create_conversation(
                scope_type="global",
                scope_id=None,
                conversation_type="group",
                participant_ids=[],
                name="New Group",
                creator_type="user",
                creator_id=user.id,
                acting_user=user,
            )

        assert exc.value.details["rule"] == "max_groups_exceeded"
        assert exc.value.details["limit"] == 1

    def test_business_scope_group_limit(self, feature_config_override):
        from apps.chat.services import ChatService
        from apps.chat.tests.factories import ConversationFactory
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.rbac.services import RBACService
        from apps.users.tests.factories import UserFactory

        feature_config_override({"business": {"chat": {"max_groups": 1}}})
        user = UserFactory()
        biz = BusinessAccountFactory(created_by=user)
        RBACService.initialize_business_account(business_id=biz.id, owner=user)
        ConversationFactory(
            scope_type="business",
            scope_id=biz.id,
            conversation_type="group",
            created_by_type="user",
            created_by_id=user.id,
        )

        with pytest.raises(BusinessRuleViolation) as exc:
            ChatService.create_conversation(
                scope_type="business",
                scope_id=biz.id,
                conversation_type="group",
                participant_ids=[],
                name="Biz Group",
                creator_type="user",
                creator_id=user.id,
                acting_user=user,
            )

        assert exc.value.details["rule"] == "max_groups_exceeded"
        assert exc.value.details["limit"] == 1


@pytest.mark.django_db
class TestMaxPendingLimit:

    def test_invitation_limit(self, feature_config_override):
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.rbac.models import Membership
        from apps.rbac.services import RBACService
        from apps.transaction.services import TransactionService
        from apps.transaction.tests.factories import TransactionFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"user": {"transactions": {"max_pending": 1}}})
        user = UserFactory()
        biz = BusinessAccountFactory(created_by=user)
        RBACService.initialize_business_account(business_id=biz.id, owner=user)
        membership = Membership.objects.get(user=user, account_id=biz.id)

        # 1 pending transaction for this membership
        TransactionFactory(
            initiator_id=membership.id,
            status="pending",
        )

        actor_context = _actor_context_from_membership(membership)
        target = UserFactory()

        with pytest.raises(BusinessRuleViolation) as exc:
            TransactionService.create_invitation(
                transaction_type="business_membership_invitation",
                initiator_context=actor_context,
                target_user_id=target.id,
            )

        assert exc.value.details["rule"] == "max_pending_exceeded"
        assert exc.value.details["limit"] == 1

    def test_request_limit(self, feature_config_override):
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.rbac.services import RBACService
        from apps.transaction.services import TransactionService
        from apps.transaction.tests.factories import TransactionFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"user": {"transactions": {"max_pending": 1}}})
        user = UserFactory()
        biz = BusinessAccountFactory(open_member_request=True)
        RBACService.initialize_business_account(
            business_id=biz.id, owner=biz.created_by
        )

        # 1 pending transaction for this user
        TransactionFactory(
            initiator_id=user.id,
            status="pending",
        )

        with pytest.raises(BusinessRuleViolation) as exc:
            TransactionService.create_request(
                transaction_type="business_membership_request",
                user_id=user.id,
                target_account_type="business",
                target_account_id=biz.id,
            )

        assert exc.value.details["rule"] == "max_pending_exceeded"
        assert exc.value.details["limit"] == 1


# =============================================================================
# Business Limits
# =============================================================================


@pytest.mark.django_db
class TestMaxRolesLimit:

    def test_business_role_limit(self, feature_config_override):
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.rbac.models import Membership
        from apps.rbac.services import RBACService
        from apps.rbac.tests.factories import RoleFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"business": {"members": {"max_roles": 1}}})
        user = UserFactory()
        biz = BusinessAccountFactory(created_by=user)
        RBACService.initialize_business_account(business_id=biz.id, owner=user)
        # 1 custom (non-system) role
        RoleFactory(account_type="business", account_id=biz.id, is_system_role=False)

        membership = Membership.objects.get(user=user, account_id=biz.id)
        actor_context = _actor_context_from_membership(membership)

        with pytest.raises(BusinessRuleViolation) as exc:
            RBACService.create_custom_role(
                account_type="business",
                account_id=biz.id,
                name="Extra Role",
                level=5,
                actor_context=actor_context,
            )

        assert exc.value.details["rule"] == "max_roles_exceeded"
        assert exc.value.details["limit"] == 1

    def test_platform_role_limit(self, feature_config_override):
        from apps.organization.platform.services import PlatformAccountService
        from apps.organization.tests.factories import PlatformAccountFactory
        from apps.rbac.models import Membership
        from apps.rbac.services import RBACService
        from apps.rbac.tests.factories import RoleFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"platform": {"members": {"max_roles": 1}}})
        user = UserFactory(is_staff=True)
        platform = PlatformAccountFactory()
        if not platform.is_configured:
            PlatformAccountService.configure(name="Test Platform", actor=user)
        # Ensure owner membership
        membership = Membership.objects.filter(
            user=user, account_type="platform", account_id=platform.id
        ).first()
        if not membership:
            membership = RBACService.create_membership(
                user=user, account_type="platform", account_id=platform.id
            )

        # 1 custom (non-system) role
        RoleFactory(
            account_type="platform", account_id=platform.id, is_system_role=False
        )

        actor_context = _actor_context_from_membership(membership)

        with pytest.raises(BusinessRuleViolation) as exc:
            RBACService.create_custom_role(
                account_type="platform",
                account_id=platform.id,
                name="Extra Platform Role",
                level=5,
                actor_context=actor_context,
            )

        assert exc.value.details["rule"] == "max_roles_exceeded"
        assert exc.value.details["limit"] == 1


@pytest.mark.django_db
class TestMaxFollowersLimit:

    def test_enforced_when_at_limit(self, feature_config_override):
        from apps.network.services import FollowService
        from apps.network.tests.factories import FollowFactory
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.users.tests.factories import UserFactory

        feature_config_override({"business": {"network": {"max_followers": 1}}})
        biz = BusinessAccountFactory()
        user1 = UserFactory()
        user2 = UserFactory()
        FollowFactory(follower=user1, followee_type="business", followee_id=biz.id)

        with pytest.raises(BusinessRuleViolation) as exc:
            FollowService.create_follow(
                follower=user2, followee_type="business", followee_id=biz.id
            )

        assert exc.value.details["rule"] == "max_followers_exceeded"
        assert exc.value.details["limit"] == 1


@pytest.mark.django_db
class TestMaxAccountConnectionsLimit:

    def test_enforced_when_at_limit(self, feature_config_override):
        from apps.network.services import ConnectionService
        from apps.network.tests.factories import AccountConnectionFactory
        from apps.organization.tests.factories import BusinessAccountFactory

        feature_config_override({"business": {"network": {"max_connections": 1}}})
        biz1 = BusinessAccountFactory()
        biz2 = BusinessAccountFactory()
        biz3 = BusinessAccountFactory()
        AccountConnectionFactory(
            account_a_type="business",
            account_a_id=biz1.id,
            account_b_type="business",
            account_b_id=biz2.id,
        )

        with pytest.raises(BusinessRuleViolation) as exc:
            ConnectionService.create_account_connection(
                a_type="business",
                a_id=biz1.id,
                b_type="business",
                b_id=biz3.id,
            )

        assert exc.value.details["rule"] == "max_connections_exceeded"
        assert exc.value.details["limit"] == 1


@pytest.mark.django_db
class TestMaxFormsLimit:

    def test_enforced_when_at_limit(self, feature_config_override):
        from apps.forms.services import FormBuilderService
        from apps.forms.tests.factories import FormTemplateFactory
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.rbac.models import Membership
        from apps.rbac.services import RBACService
        from apps.users.tests.factories import UserFactory

        feature_config_override({"business": {"forms": {"max_forms": 1}}})
        user = UserFactory()
        biz = BusinessAccountFactory(created_by=user)
        RBACService.initialize_business_account(business_id=biz.id, owner=user)
        FormTemplateFactory(owner_type="business", owner_id=biz.id, is_current=True)

        membership = Membership.objects.get(user=user, account_id=biz.id)
        actor_context = _actor_context_from_membership(membership)

        with pytest.raises(BusinessRuleViolation) as exc:
            FormBuilderService.create_form_template(
                actor_context=actor_context,
                actor=user,
                name="New Form",
                owner_type="business",
                owner_id=biz.id,
                scope="business",
            )

        assert exc.value.details["rule"] == "max_forms_exceeded"
        assert exc.value.details["limit"] == 1


# =============================================================================
# Effective Limit — max_members wiring (config vs model)
# =============================================================================


@pytest.mark.django_db
class TestMemberQuotaEffectiveLimit:
    """Test effective_limit() wiring where both config and model define max_members."""

    def test_config_tighter_than_model(self, feature_config_override):
        """Config=2, Model=10 → effective=2."""
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.rbac.services import RBACService
        from apps.users.tests.factories import UserFactory

        feature_config_override({"business": {"members": {"max_members": 2}}})
        user = UserFactory()
        biz = BusinessAccountFactory(max_members=10, created_by=user)
        RBACService.initialize_business_account(business_id=biz.id, owner=user)
        # Owner = 1 member. Add 1 more to reach config limit of 2.
        user2 = UserFactory()
        RBACService.create_membership(
            user=user2, account_type="business", account_id=biz.id
        )

        user3 = UserFactory()
        with pytest.raises(BusinessRuleViolation) as exc:
            RBACService.create_membership(
                user=user3, account_type="business", account_id=biz.id
            )

        assert exc.value.details["rule"] == "member_quota_exceeded"
        assert exc.value.details["limit"] == 2

    def test_model_tighter_than_config(self, feature_config_override):
        """Config=10, Model=2 → effective=2."""
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.rbac.services import RBACService
        from apps.users.tests.factories import UserFactory

        feature_config_override({"business": {"members": {"max_members": 10}}})
        user = UserFactory()
        biz = BusinessAccountFactory(max_members=2, created_by=user)
        RBACService.initialize_business_account(business_id=biz.id, owner=user)
        # Owner = 1 member. Add 1 more to reach model limit of 2.
        user2 = UserFactory()
        RBACService.create_membership(
            user=user2, account_type="business", account_id=biz.id
        )

        user3 = UserFactory()
        with pytest.raises(BusinessRuleViolation) as exc:
            RBACService.create_membership(
                user=user3, account_type="business", account_id=biz.id
            )

        assert exc.value.details["rule"] == "member_quota_exceeded"
        assert exc.value.details["limit"] == 2

    def test_config_unlimited_model_limited(self, feature_config_override):
        """Config=0 (unlimited), Model=2 → effective=2 (model sets ceiling)."""
        from apps.organization.tests.factories import BusinessAccountFactory
        from apps.rbac.services import RBACService
        from apps.users.tests.factories import UserFactory

        feature_config_override({"business": {"members": {"max_members": 0}}})
        user = UserFactory()
        biz = BusinessAccountFactory(max_members=2, created_by=user)
        RBACService.initialize_business_account(business_id=biz.id, owner=user)
        # Owner = 1 member. Add 1 more to reach model limit of 2.
        user2 = UserFactory()
        RBACService.create_membership(
            user=user2, account_type="business", account_id=biz.id
        )

        user3 = UserFactory()
        with pytest.raises(BusinessRuleViolation) as exc:
            RBACService.create_membership(
                user=user3, account_type="business", account_id=biz.id
            )

        assert exc.value.details["rule"] == "member_quota_exceeded"
        assert exc.value.details["limit"] == 2
