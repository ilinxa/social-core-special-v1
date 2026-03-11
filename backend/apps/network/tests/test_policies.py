# apps/network/tests/test_policies.py
import uuid

import pytest
from django.contrib.auth.models import AnonymousUser

from apps.network.policies import NetworkPolicy
from apps.network.tests.factories import FollowFactory, UserConnectionFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestFollowPolicies:

    def test_can_follow_true(self, user):
        result = NetworkPolicy.can_follow(
            user=user, followee_type="business", followee_id=uuid.uuid4(),
        )
        assert result is True

    def test_can_follow_already_following(self, user):
        follow = FollowFactory(follower=user)
        result = NetworkPolicy.can_follow(
            user=user,
            followee_type=follow.followee_type,
            followee_id=follow.followee_id,
        )
        assert result is False

    def test_can_follow_anonymous(self):
        result = NetworkPolicy.can_follow(
            user=AnonymousUser(),
            followee_type="business",
            followee_id=uuid.uuid4(),
        )
        assert result is False

    def test_can_unfollow_owner(self, user):
        follow = FollowFactory(follower=user)
        assert NetworkPolicy.can_unfollow(user=user, follow=follow) is True

    def test_can_unfollow_not_owner(self, user, user_b):
        follow = FollowFactory(follower=user_b)
        assert NetworkPolicy.can_unfollow(user=user, follow=follow) is False


@pytest.mark.django_db
class TestConnectionPolicies:

    def test_can_connect_user(self, user, user_b):
        assert NetworkPolicy.can_connect_user(
            user=user, target_user_id=user_b.id,
        ) is True

    def test_can_connect_self(self, user):
        assert NetworkPolicy.can_connect_user(
            user=user, target_user_id=user.id,
        ) is False

    def test_can_connect_already_connected(self, user, user_b):
        a, b = sorted([user, user_b], key=lambda u: str(u.id))
        UserConnectionFactory(user_a=a, user_b=b)
        assert NetworkPolicy.can_connect_user(
            user=user, target_user_id=user_b.id,
        ) is False

    def test_can_disconnect_party(self, user, user_b):
        a, b = sorted([user, user_b], key=lambda u: str(u.id))
        conn = UserConnectionFactory(user_a=a, user_b=b)
        assert NetworkPolicy.can_disconnect_user(user=user, connection=conn) is True

    def test_can_disconnect_outsider(self, user, user_b, user_c):
        a, b = sorted([user, user_b], key=lambda u: str(u.id))
        conn = UserConnectionFactory(user_a=a, user_b=b)
        assert NetworkPolicy.can_disconnect_user(user=user_c, connection=conn) is False


@pytest.mark.django_db
class TestPermissionHelpers:

    def test_get_follow_permissions_not_following(self, user):
        perms = NetworkPolicy.get_follow_permissions(
            viewer=user, followee_type="business", followee_id=uuid.uuid4(),
        )
        assert perms["can_follow"] is True
        assert perms["can_unfollow"] is False

    def test_get_follow_permissions_following(self, user):
        follow = FollowFactory(follower=user)
        perms = NetworkPolicy.get_follow_permissions(
            viewer=user,
            followee_type=follow.followee_type,
            followee_id=follow.followee_id,
        )
        assert perms["can_follow"] is False
        assert perms["can_unfollow"] is True

    def test_get_connection_permissions_not_connected(self, user, user_b):
        perms = NetworkPolicy.get_connection_permissions_for_user(
            viewer=user, target_user_id=user_b.id,
        )
        assert perms["can_connect"] is True
        assert perms["can_disconnect"] is False

    def test_get_connection_permissions_connected(self, user, user_b):
        a, b = sorted([user, user_b], key=lambda u: str(u.id))
        UserConnectionFactory(user_a=a, user_b=b)
        perms = NetworkPolicy.get_connection_permissions_for_user(
            viewer=user, target_user_id=user_b.id,
        )
        assert perms["can_connect"] is False
        assert perms["can_disconnect"] is True

    def test_get_connection_permissions_self(self, user):
        perms = NetworkPolicy.get_connection_permissions_for_user(
            viewer=user, target_user_id=user.id,
        )
        assert perms["can_connect"] is False
        assert perms["can_disconnect"] is False
