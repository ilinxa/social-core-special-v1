# apps/network/tests/test_services.py
import uuid

import pytest
from django.utils import timezone

from apps.core.exceptions import ConflictError, PermissionDenied, BusinessRuleViolation
from apps.network.models import Follow, FollowStatus, Connection, ConnectionStatus
from apps.network.services import FollowService, ConnectionService
from apps.network.tests.factories import FollowFactory, UserConnectionFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestFollowServiceCreate:

    def test_create_follow(self, user):
        followee_id = uuid.uuid4()
        follow = FollowService.create_follow(
            follower=user,
            followee_type="business",
            followee_id=followee_id,
        )
        assert follow.follower == user
        assert follow.followee_type == "business"
        assert follow.followee_id == followee_id
        assert follow.status == FollowStatus.ACTIVE

    def test_create_follow_duplicate_raises(self, user):
        followee_id = uuid.uuid4()
        FollowService.create_follow(
            follower=user, followee_type="business", followee_id=followee_id,
        )
        with pytest.raises(ConflictError):
            FollowService.create_follow(
                follower=user, followee_type="business", followee_id=followee_id,
            )

    def test_create_follow_reactivates_removed(self, user):
        followee_id = uuid.uuid4()
        follow = FollowFactory(
            follower=user, followee_type="business", followee_id=followee_id,
            status=FollowStatus.REMOVED, removed_at=timezone.now(),
        )
        reactivated = FollowService.create_follow(
            follower=user, followee_type="business", followee_id=followee_id,
        )
        assert reactivated.id == follow.id
        assert reactivated.status == FollowStatus.ACTIVE
        assert reactivated.removed_at is None


@pytest.mark.django_db
class TestFollowServiceUnfollow:

    def test_unfollow(self, user):
        follow = FollowFactory(follower=user)
        result = FollowService.unfollow(follow_id=follow.id, user=user)
        assert result.status == FollowStatus.REMOVED
        assert result.removed_at is not None
        assert result.removed_by == user

    def test_unfollow_not_follower_raises(self, user, user_b):
        follow = FollowFactory(follower=user_b)
        with pytest.raises(PermissionDenied):
            FollowService.unfollow(follow_id=follow.id, user=user)

    def test_unfollow_already_removed_raises(self, user):
        follow = FollowFactory(follower=user, status=FollowStatus.REMOVED)
        with pytest.raises(BusinessRuleViolation):
            FollowService.unfollow(follow_id=follow.id, user=user)


@pytest.mark.django_db
class TestFollowServiceRemoveFollower:

    def test_remove_follower_permission_denied(self, user):
        follow = FollowFactory()
        from apps.core.types import ActorContext
        actor_context = ActorContext.for_user_context(user)
        with pytest.raises(PermissionDenied):
            FollowService.remove_follower(
                follow_id=follow.id, actor=user, actor_context=actor_context,
            )


@pytest.mark.django_db
class TestConnectionServiceCreateUser:

    def test_create_user_connection(self):
        user_a = UserFactory()
        user_b = UserFactory()
        conn = ConnectionService.create_user_connection(
            user_a_id=user_a.id,
            user_b_id=user_b.id,
            note="Hello!",
            initiated_by_id=user_a.id,
        )
        assert conn.status == ConnectionStatus.ACTIVE
        assert conn.note == "Hello!"
        assert conn.connected_at is not None

    def test_create_user_connection_canonical_order(self):
        """user_a.id should be < user_b.id after canonical ordering."""
        user_a = UserFactory()
        user_b = UserFactory()
        conn = ConnectionService.create_user_connection(
            user_a_id=user_a.id,
            user_b_id=user_b.id,
        )
        assert str(conn.user_a_id) <= str(conn.user_b_id)

    def test_create_user_connection_duplicate_raises(self):
        user_a = UserFactory()
        user_b = UserFactory()
        ConnectionService.create_user_connection(
            user_a_id=user_a.id, user_b_id=user_b.id,
        )
        with pytest.raises(ConflictError):
            ConnectionService.create_user_connection(
                user_a_id=user_a.id, user_b_id=user_b.id,
            )

    def test_create_user_connection_reactivates_disconnected(self):
        user_a = UserFactory()
        user_b = UserFactory()
        a_id, b_id = ConnectionService._canonical_user_pair(user_a.id, user_b.id)
        old_conn = UserConnectionFactory(
            user_a_id=a_id, user_b_id=b_id,
            status=ConnectionStatus.DISCONNECTED,
        )
        reactivated = ConnectionService.create_user_connection(
            user_a_id=user_a.id, user_b_id=user_b.id, note="Back!",
        )
        assert reactivated.id == old_conn.id
        assert reactivated.status == ConnectionStatus.ACTIVE
        assert reactivated.note == "Back!"


@pytest.mark.django_db
class TestConnectionServiceCreateAccount:

    def test_create_account_connection(self):
        a_id = uuid.uuid4()
        b_id = uuid.uuid4()
        initiator = UserFactory()
        conn = ConnectionService.create_account_connection(
            a_type="business", a_id=a_id,
            b_type="business", b_id=b_id,
            initiated_by_id=initiator.id,
            note="Partnership",
        )
        assert conn.status == ConnectionStatus.ACTIVE
        assert conn.note == "Partnership"

    def test_create_account_connection_canonical_order(self):
        a_id = uuid.uuid4()
        b_id = uuid.uuid4()
        conn = ConnectionService.create_account_connection(
            a_type="business", a_id=a_id,
            b_type="business", b_id=b_id,
        )
        assert (conn.account_a_type, str(conn.account_a_id)) <= (
            conn.account_b_type, str(conn.account_b_id),
        )


@pytest.mark.django_db
class TestConnectionServiceDisconnectUser:

    def test_disconnect_user_connection(self):
        user_a = UserFactory()
        user_b = UserFactory()
        a, b = sorted([user_a, user_b], key=lambda u: str(u.id))
        conn = UserConnectionFactory(user_a=a, user_b=b)

        result = ConnectionService.disconnect_user_connection(
            connection_id=conn.id, user=user_a,
        )
        assert result.status == ConnectionStatus.DISCONNECTED
        assert result.disconnected_at is not None
        assert result.disconnected_by == user_a

    def test_disconnect_not_party_raises(self):
        conn = UserConnectionFactory()
        outsider = UserFactory()
        with pytest.raises(PermissionDenied):
            ConnectionService.disconnect_user_connection(
                connection_id=conn.id, user=outsider,
            )

    def test_disconnect_already_disconnected_raises(self):
        user_a = UserFactory()
        user_b = UserFactory()
        a, b = sorted([user_a, user_b], key=lambda u: str(u.id))
        conn = UserConnectionFactory(
            user_a=a, user_b=b, status=ConnectionStatus.DISCONNECTED,
        )
        with pytest.raises(BusinessRuleViolation):
            ConnectionService.disconnect_user_connection(
                connection_id=conn.id, user=user_a,
            )

    def test_disconnect_wrong_type_raises(self):
        from apps.network.tests.factories import AccountConnectionFactory
        conn = AccountConnectionFactory()
        outsider = UserFactory()
        with pytest.raises(BusinessRuleViolation):
            ConnectionService.disconnect_user_connection(
                connection_id=conn.id, user=outsider,
            )
