# apps/network/tests/test_views.py
"""
Network View Tests
==================
Tests for all network API endpoints.
Uses mock where needed to isolate from transaction system complexity.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status as http_status

from apps.network.models import Connection, ConnectionStatus, Follow, FollowStatus
from apps.network.tests.factories import FollowFactory, UserConnectionFactory
from apps.users.tests.factories import UserFactory

# URL constants
FOLLOW_URL = "/api/v1/network/follow/"
FOLLOWING_URL = "/api/v1/network/following/"
CONNECTIONS_REQUEST_URL = "/api/v1/network/connections/request/"
CONNECTIONS_URL = "/api/v1/network/connections/"
STATS_URL = "/api/v1/network/stats/"


def _biz_followers_url(slug):
    return f"/api/v1/network/business/{slug}/followers/"


def _biz_follower_remove_url(slug, follow_id):
    return f"/api/v1/network/business/{slug}/followers/{follow_id}/"


def _biz_connections_url(slug):
    return f"/api/v1/network/business/{slug}/connections/"


def _biz_connection_request_url(slug):
    return f"/api/v1/network/business/{slug}/connections/request/"


def _biz_stats_url(slug):
    return f"/api/v1/network/business/{slug}/stats/"


# =============================================================================
# FOLLOW TESTS
# =============================================================================


@pytest.mark.django_db
class TestFollowCreate:

    @patch("apps.transaction.services.TransactionService")
    def test_follow_public_business(
        self, mock_txn_service, authenticated_client, business
    ):
        mock_txn = MagicMock()
        mock_txn.id = uuid.uuid4()
        mock_txn.status = "accepted"
        mock_txn_service.create_request.return_value = mock_txn

        response = authenticated_client.post(
            FOLLOW_URL,
            {
                "followee_type": "business",
                "followee_id": str(business.id),
            },
        )
        assert response.status_code == http_status.HTTP_201_CREATED
        assert "transaction_id" in response.data

    @patch("apps.transaction.services.TransactionService")
    def test_follow_private_business(
        self, mock_txn_service, authenticated_client, private_business
    ):
        mock_txn = MagicMock()
        mock_txn.id = uuid.uuid4()
        mock_txn.status = "pending"
        mock_txn_service.create_request.return_value = mock_txn

        response = authenticated_client.post(
            FOLLOW_URL,
            {
                "followee_type": "business",
                "followee_id": str(private_business.id),
            },
        )
        assert response.status_code == http_status.HTTP_201_CREATED

    @patch("apps.transaction.services.TransactionService")
    def test_follow_platform(self, mock_txn_service, authenticated_client, platform):
        mock_txn = MagicMock()
        mock_txn.id = uuid.uuid4()
        mock_txn.status = "accepted"
        mock_txn_service.create_request.return_value = mock_txn

        response = authenticated_client.post(
            FOLLOW_URL,
            {
                "followee_type": "platform",
                "followee_id": str(platform.id),
            },
        )
        assert response.status_code == http_status.HTTP_201_CREATED

    def test_follow_unauthenticated(self, api_client):
        response = api_client.post(
            FOLLOW_URL,
            {
                "followee_type": "business",
                "followee_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_follow_invalid_type(self, authenticated_client):
        response = authenticated_client.post(
            FOLLOW_URL,
            {
                "followee_type": "invalid",
                "followee_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestFollowDelete:

    def test_unfollow(self, authenticated_client, user):
        follow = FollowFactory(follower=user)
        response = authenticated_client.delete(f"{FOLLOW_URL}{follow.id}/")
        assert response.status_code == http_status.HTTP_204_NO_CONTENT

        follow.refresh_from_db()
        assert follow.status == FollowStatus.REMOVED

    def test_unfollow_not_follower(self, authenticated_client, user_b):
        follow = FollowFactory(follower=user_b)
        response = authenticated_client.delete(f"{FOLLOW_URL}{follow.id}/")
        assert response.status_code == http_status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestFollowingList:

    def test_list_following(self, authenticated_client, user):
        FollowFactory(follower=user)
        FollowFactory(follower=user)

        response = authenticated_client.get(FOLLOWING_URL)
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_list_following_filtered(self, authenticated_client, user):
        FollowFactory(follower=user, followee_type="business")
        FollowFactory(follower=user, followee_type="platform")

        response = authenticated_client.get(FOLLOWING_URL + "?type=business")
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["count"] == 1


# =============================================================================
# USER CONNECTION TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserConnectionRequest:

    @patch("apps.transaction.services.TransactionService")
    def test_request_connection(self, mock_txn_service, authenticated_client, user_b):
        mock_txn = MagicMock()
        mock_txn.id = uuid.uuid4()
        mock_txn.status = "pending"
        mock_txn_service.create_request.return_value = mock_txn

        response = authenticated_client.post(
            CONNECTIONS_REQUEST_URL,
            {
                "target_user_id": str(user_b.id),
                "note": "Let's connect!",
            },
        )
        assert response.status_code == http_status.HTTP_201_CREATED
        assert "transaction_id" in response.data

    def test_request_connection_unauthenticated(self, api_client):
        response = api_client.post(
            CONNECTIONS_REQUEST_URL,
            {
                "target_user_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserConnectionDelete:

    def test_disconnect(self, authenticated_client, user, user_b):
        a, b = sorted([user, user_b], key=lambda u: str(u.id))
        conn = UserConnectionFactory(user_a=a, user_b=b)

        response = authenticated_client.delete(f"{CONNECTIONS_URL}{conn.id}/")
        assert response.status_code == http_status.HTTP_204_NO_CONTENT

        conn.refresh_from_db()
        assert conn.status == ConnectionStatus.DISCONNECTED

    def test_disconnect_not_party(self, authenticated_client):
        conn = UserConnectionFactory()
        response = authenticated_client.delete(f"{CONNECTIONS_URL}{conn.id}/")
        assert response.status_code == http_status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestUserConnectionList:

    def test_list_connections(self, authenticated_client, user, user_b, user_c):
        a1, b1 = sorted([user, user_b], key=lambda u: str(u.id))
        a2, b2 = sorted([user, user_c], key=lambda u: str(u.id))
        UserConnectionFactory(user_a=a1, user_b=b1)
        UserConnectionFactory(user_a=a2, user_b=b2)

        response = authenticated_client.get(CONNECTIONS_URL)
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["count"] == 2


# =============================================================================
# BUSINESS FOLLOWER TESTS
# =============================================================================


@pytest.mark.django_db
class TestBusinessFollowers:

    def test_list_followers(self, authenticated_client, business):
        FollowFactory(followee_type="business", followee_id=business.id)
        FollowFactory(followee_type="business", followee_id=business.id)

        response = authenticated_client.get(_biz_followers_url(business.slug))
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["count"] == 2


# =============================================================================
# STATS TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserNetworkStats:

    def test_stats(self, authenticated_client, user, user_b):
        FollowFactory(follower=user)
        a, b = sorted([user, user_b], key=lambda u: str(u.id))
        UserConnectionFactory(user_a=a, user_b=b)

        response = authenticated_client.get(STATS_URL)
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["following_count"] == 1
        assert response.data["connections_count"] == 1


@pytest.mark.django_db
class TestBusinessNetworkStats:

    def test_stats(self, authenticated_client, business):
        FollowFactory(followee_type="business", followee_id=business.id)
        FollowFactory(followee_type="business", followee_id=business.id)

        response = authenticated_client.get(_biz_stats_url(business.slug))
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["followers_count"] == 2
