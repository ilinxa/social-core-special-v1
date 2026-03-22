# apps/network/tests/test_selectors.py
import uuid

import pytest

from apps.core.exceptions import NotFound
from apps.network.models import ConnectionStatus, FollowStatus
from apps.network.selectors import ConnectionSelector, FollowSelector
from apps.network.tests.factories import (
    AccountConnectionFactory,
    FollowFactory,
    UserConnectionFactory,
)
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestFollowSelector:

    def test_get_by_id(self):
        follow = FollowFactory()
        result = FollowSelector.get_by_id(follow_id=follow.id)
        assert result.id == follow.id

    def test_get_by_id_not_found(self):
        with pytest.raises(NotFound):
            FollowSelector.get_by_id(follow_id=uuid.uuid4())

    def test_is_following_true(self):
        follow = FollowFactory()
        assert (
            FollowSelector.is_following(
                follower_id=follow.follower_id,
                followee_type=follow.followee_type,
                followee_id=follow.followee_id,
            )
            is True
        )

    def test_is_following_false(self):
        assert (
            FollowSelector.is_following(
                follower_id=uuid.uuid4(),
                followee_type="business",
                followee_id=uuid.uuid4(),
            )
            is False
        )

    def test_is_following_removed_is_false(self):
        follow = FollowFactory(status=FollowStatus.REMOVED)
        assert (
            FollowSelector.is_following(
                follower_id=follow.follower_id,
                followee_type=follow.followee_type,
                followee_id=follow.followee_id,
            )
            is False
        )

    def test_get_follow_for_user_active(self):
        follow = FollowFactory()
        result = FollowSelector.get_follow_for_user(
            follower_id=follow.follower_id,
            followee_type=follow.followee_type,
            followee_id=follow.followee_id,
        )
        assert result is not None
        assert result.id == follow.id

    def test_get_follow_for_user_none(self):
        result = FollowSelector.get_follow_for_user(
            follower_id=uuid.uuid4(),
            followee_type="business",
            followee_id=uuid.uuid4(),
        )
        assert result is None

    def test_get_followers(self):
        followee_id = uuid.uuid4()
        f1 = FollowFactory(followee_type="business", followee_id=followee_id)
        f2 = FollowFactory(followee_type="business", followee_id=followee_id)
        FollowFactory(
            followee_type="business",
            followee_id=followee_id,
            status=FollowStatus.REMOVED,
        )

        followers = FollowSelector.get_followers(
            followee_type="business",
            followee_id=followee_id,
        )
        assert followers.count() == 2

    def test_get_following(self):
        user = UserFactory()
        FollowFactory(follower=user, followee_type="business")
        FollowFactory(follower=user, followee_type="platform")

        all_following = FollowSelector.get_following(user_id=user.id)
        assert all_following.count() == 2

        biz_following = FollowSelector.get_following(
            user_id=user.id,
            followee_type="business",
        )
        assert biz_following.count() == 1

    def test_count_followers(self):
        followee_id = uuid.uuid4()
        FollowFactory(followee_type="business", followee_id=followee_id)
        FollowFactory(followee_type="business", followee_id=followee_id)

        count = FollowSelector.count_followers(
            followee_type="business",
            followee_id=followee_id,
        )
        assert count == 2

    def test_count_following(self):
        user = UserFactory()
        FollowFactory(follower=user)
        FollowFactory(follower=user)

        count = FollowSelector.count_following(user_id=user.id)
        assert count == 2


@pytest.mark.django_db
class TestConnectionSelector:

    def test_get_by_id(self):
        conn = UserConnectionFactory()
        result = ConnectionSelector.get_by_id(connection_id=conn.id)
        assert result.id == conn.id

    def test_get_by_id_not_found(self):
        with pytest.raises(NotFound):
            ConnectionSelector.get_by_id(connection_id=uuid.uuid4())

    def test_is_connected_true(self):
        user_a = UserFactory()
        user_b = UserFactory()
        a, b = sorted([user_a, user_b], key=lambda u: str(u.id))
        UserConnectionFactory(user_a=a, user_b=b)
        assert (
            ConnectionSelector.is_connected(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
            )
            is True
        )

    def test_is_connected_false(self):
        assert (
            ConnectionSelector.is_connected(
                user_a_id=uuid.uuid4(),
                user_b_id=uuid.uuid4(),
            )
            is False
        )

    def test_is_connected_canonical_order(self):
        """is_connected works regardless of argument order."""
        user_a = UserFactory()
        user_b = UserFactory()
        # Ensure canonical ordering
        a, b = sorted([user_a, user_b], key=lambda u: str(u.id))
        UserConnectionFactory(user_a=a, user_b=b)

        # Test both orderings
        assert (
            ConnectionSelector.is_connected(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
            )
            is True
        )
        assert (
            ConnectionSelector.is_connected(
                user_a_id=user_b.id,
                user_b_id=user_a.id,
            )
            is True
        )

    def test_is_connected_disconnected_is_false(self):
        conn = UserConnectionFactory(status=ConnectionStatus.DISCONNECTED)
        assert (
            ConnectionSelector.is_connected(
                user_a_id=conn.user_a_id,
                user_b_id=conn.user_b_id,
            )
            is False
        )

    def test_is_connected_account(self):
        a_id = uuid.uuid4()
        b_id = uuid.uuid4()
        # Ensure canonical order in factory data
        ca_id, cb_id = (a_id, b_id) if str(a_id) <= str(b_id) else (b_id, a_id)
        AccountConnectionFactory(
            account_a_type="business",
            account_a_id=ca_id,
            account_b_type="business",
            account_b_id=cb_id,
        )
        assert (
            ConnectionSelector.is_connected_account(
                a_type="business",
                a_id=a_id,
                b_type="business",
                b_id=b_id,
            )
            is True
        )

    def test_get_user_connections(self):
        user = UserFactory()
        UserConnectionFactory(user_a=user)
        UserConnectionFactory(user_b=user)
        UserConnectionFactory(user_a=user, status=ConnectionStatus.DISCONNECTED)

        active = ConnectionSelector.get_user_connections(user_id=user.id)
        assert active.count() == 2

    def test_get_account_connections(self):
        acct_id = uuid.uuid4()
        AccountConnectionFactory(account_a_type="business", account_a_id=acct_id)
        AccountConnectionFactory(account_b_type="business", account_b_id=acct_id)

        conns = ConnectionSelector.get_account_connections(
            account_type="business",
            account_id=acct_id,
        )
        assert conns.count() == 2

    def test_count_user_connections(self):
        user = UserFactory()
        UserConnectionFactory(user_a=user)
        UserConnectionFactory(user_b=user)

        assert ConnectionSelector.count_user_connections(user_id=user.id) == 2

    def test_count_account_connections(self):
        acct_id = uuid.uuid4()
        AccountConnectionFactory(account_a_type="business", account_a_id=acct_id)
        assert (
            ConnectionSelector.count_account_connections(
                account_type="business",
                account_id=acct_id,
            )
            == 1
        )

    def test_get_mutual_connections(self):
        user_a = UserFactory()
        user_b = UserFactory()
        mutual = UserFactory()

        # Both connected to mutual
        a_ids = sorted([str(user_a.id), str(mutual.id)])
        b_ids = sorted([str(user_b.id), str(mutual.id)])

        ua, um1 = (
            (user_a, mutual) if str(user_a.id) < str(mutual.id) else (mutual, user_a)
        )
        ub, um2 = (
            (user_b, mutual) if str(user_b.id) < str(mutual.id) else (mutual, user_b)
        )

        UserConnectionFactory(user_a=ua, user_b=um1)
        UserConnectionFactory(user_a=ub, user_b=um2)

        mutuals = ConnectionSelector.get_mutual_connections(
            user_a_id=user_a.id,
            user_b_id=user_b.id,
        )
        assert list(mutuals.values_list("id", flat=True)) == [mutual.id]

    def test_get_connection_between_users(self):
        user_a = UserFactory()
        user_b = UserFactory()
        a, b = sorted([user_a, user_b], key=lambda u: str(u.id))
        conn = UserConnectionFactory(user_a=a, user_b=b)

        result = ConnectionSelector.get_connection_between_users(
            user_a_id=user_a.id,
            user_b_id=user_b.id,
        )
        assert result is not None
        assert result.id == conn.id

    def test_get_connection_between_users_none(self):
        result = ConnectionSelector.get_connection_between_users(
            user_a_id=uuid.uuid4(),
            user_b_id=uuid.uuid4(),
        )
        assert result is None
