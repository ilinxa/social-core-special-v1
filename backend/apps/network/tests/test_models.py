# apps/network/tests/test_models.py
import uuid

import pytest
from django.db import IntegrityError

from apps.network.models import (
    Connection,
    ConnectionStatus,
    ConnectionType,
    Follow,
    FolloweeType,
    FollowStatus,
)
from apps.network.tests.factories import (
    AccountConnectionFactory,
    FollowFactory,
    UserConnectionFactory,
)
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestFollowModel:

    def test_create_follow(self):
        follow = FollowFactory()
        assert follow.id is not None
        assert follow.status == FollowStatus.ACTIVE
        assert follow.followee_type == FolloweeType.BUSINESS
        assert follow.removed_at is None

    def test_follow_str(self):
        follow = FollowFactory()
        expected = f"{follow.follower_id} → {follow.followee_type}:{follow.followee_id} (active)"
        assert str(follow) == expected

    def test_follow_defaults(self):
        follow = FollowFactory()
        assert follow.status == FollowStatus.ACTIVE
        assert follow.removed_at is None
        assert follow.removed_by is None

    def test_unique_active_follow_constraint(self):
        user = UserFactory()
        followee_id = uuid.uuid4()
        FollowFactory(follower=user, followee_type="business", followee_id=followee_id)
        with pytest.raises(IntegrityError):
            FollowFactory(
                follower=user, followee_type="business", followee_id=followee_id
            )

    def test_unique_active_follow_allows_removed(self):
        user = UserFactory()
        followee_id = uuid.uuid4()
        FollowFactory(
            follower=user,
            followee_type="business",
            followee_id=followee_id,
            status=FollowStatus.REMOVED,
        )
        # Should not raise — unique constraint only applies to active
        follow2 = FollowFactory(
            follower=user,
            followee_type="business",
            followee_id=followee_id,
        )
        assert follow2.status == FollowStatus.ACTIVE

    def test_follow_ordering(self):
        f1 = FollowFactory()
        f2 = FollowFactory()
        follows = list(Follow.objects.all())
        assert follows[0].id == f2.id  # newest first


@pytest.mark.django_db
class TestConnectionModel:

    def test_create_user_connection(self):
        conn = UserConnectionFactory()
        assert conn.id is not None
        assert conn.connection_type == ConnectionType.USER_USER
        assert conn.status == ConnectionStatus.ACTIVE
        assert conn.user_a is not None
        assert conn.user_b is not None

    def test_create_account_connection(self):
        conn = AccountConnectionFactory()
        assert conn.connection_type == ConnectionType.ACCOUNT_ACCOUNT
        assert conn.account_a_id is not None
        assert conn.account_b_id is not None

    def test_connection_str_user(self):
        conn = UserConnectionFactory()
        assert "↔" in str(conn)
        assert "(active)" in str(conn)

    def test_connection_str_account(self):
        conn = AccountConnectionFactory()
        assert "↔" in str(conn)
        assert "(active)" in str(conn)

    def test_connection_defaults(self):
        conn = UserConnectionFactory()
        assert conn.note == ""
        assert conn.disconnected_at is None
        assert conn.disconnected_by is None

    def test_unique_active_user_connection(self):
        user_a = UserFactory()
        user_b = UserFactory()
        UserConnectionFactory(user_a=user_a, user_b=user_b)
        with pytest.raises(IntegrityError):
            UserConnectionFactory(user_a=user_a, user_b=user_b)

    def test_unique_active_allows_disconnected(self):
        user_a = UserFactory()
        user_b = UserFactory()
        UserConnectionFactory(
            user_a=user_a,
            user_b=user_b,
            status=ConnectionStatus.DISCONNECTED,
        )
        conn2 = UserConnectionFactory(user_a=user_a, user_b=user_b)
        assert conn2.status == ConnectionStatus.ACTIVE

    def test_connection_ordering(self):
        c1 = UserConnectionFactory()
        c2 = UserConnectionFactory()
        conns = list(Connection.objects.all())
        assert conns[0].id == c2.id  # newest first
