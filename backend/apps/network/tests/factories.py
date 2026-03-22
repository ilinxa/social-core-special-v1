# apps/network/tests/factories.py
import factory
from factory.django import DjangoModelFactory

from apps.network.models import (
    Connection,
    ConnectionStatus,
    ConnectionType,
    Follow,
    FolloweeType,
    FollowStatus,
)
from apps.users.tests.factories import UserFactory


class FollowFactory(DjangoModelFactory):
    class Meta:
        model = Follow

    follower = factory.SubFactory(UserFactory)
    followee_type = FolloweeType.BUSINESS
    followee_id = factory.LazyFunction(lambda: factory.Faker._get_faker().uuid4())
    status = FollowStatus.ACTIVE


class UserConnectionFactory(DjangoModelFactory):
    """Factory for user↔user connections."""

    class Meta:
        model = Connection

    connection_type = ConnectionType.USER_USER
    user_a = factory.SubFactory(UserFactory)
    user_b = factory.SubFactory(UserFactory)
    status = ConnectionStatus.ACTIVE
    connected_at = factory.LazyFunction(
        lambda: __import__("django.utils.timezone", fromlist=["now"]).now()
    )


class AccountConnectionFactory(DjangoModelFactory):
    """Factory for account↔account connections."""

    class Meta:
        model = Connection

    connection_type = ConnectionType.ACCOUNT_ACCOUNT
    account_a_type = "business"
    account_a_id = factory.LazyFunction(lambda: factory.Faker._get_faker().uuid4())
    account_b_type = "business"
    account_b_id = factory.LazyFunction(lambda: factory.Faker._get_faker().uuid4())
    status = ConnectionStatus.ACTIVE
    connected_at = factory.LazyFunction(
        lambda: __import__("django.utils.timezone", fromlist=["now"]).now()
    )
