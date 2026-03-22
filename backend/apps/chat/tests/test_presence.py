"""
Presence Manager Tests
======================
Tests for Redis-based online presence tracking.
Mocks Redis — no real Redis needed.
"""

import uuid
from unittest.mock import MagicMock, patch

from apps.chat.presence import PresenceManager


def _setup_mock_redis(mock_from_url, mock_client=None):
    """Helper to set up a mock redis client via from_url."""
    if mock_client is None:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
    mock_from_url.return_value = mock_client
    return mock_client


class TestPresenceSetOnline:
    def setup_method(self):
        PresenceManager.reset()

    @patch("redis.from_url")
    def test_set_online_calls_setex(self, mock_from_url):
        uid = uuid.uuid4()
        mock_redis = _setup_mock_redis(mock_from_url)
        PresenceManager.set_online(uid, ttl=30)
        mock_redis.setex.assert_called_once_with(
            f"chat:presence:{uid}", 30, "1"
        )

    @patch("redis.from_url")
    def test_set_online_default_ttl(self, mock_from_url):
        uid = uuid.uuid4()
        mock_redis = _setup_mock_redis(mock_from_url)
        PresenceManager.set_online(uid)
        # Default TTL is WS_PRESENCE_TTL_SECONDS = 30
        mock_redis.setex.assert_called_once_with(
            f"chat:presence:{uid}", 30, "1"
        )

    @patch("redis.from_url")
    def test_set_online_redis_error_fails_open(self, mock_from_url):
        uid = uuid.uuid4()
        mock_redis = _setup_mock_redis(mock_from_url)
        mock_redis.setex.side_effect = Exception("connection lost")
        # Should not raise
        PresenceManager.set_online(uid)


class TestPresenceSetOffline:
    def setup_method(self):
        PresenceManager.reset()

    @patch("redis.from_url")
    def test_set_offline_calls_delete(self, mock_from_url):
        uid = uuid.uuid4()
        mock_redis = _setup_mock_redis(mock_from_url)
        PresenceManager.set_offline(uid)
        mock_redis.delete.assert_called_once_with(f"chat:presence:{uid}")

    @patch("redis.from_url")
    def test_set_offline_redis_error_fails_open(self, mock_from_url):
        uid = uuid.uuid4()
        mock_redis = _setup_mock_redis(mock_from_url)
        mock_redis.delete.side_effect = Exception("connection lost")
        # Should not raise
        PresenceManager.set_offline(uid)


class TestPresenceIsOnline:
    def setup_method(self):
        PresenceManager.reset()

    @patch("redis.from_url")
    def test_is_online_true(self, mock_from_url):
        uid = uuid.uuid4()
        mock_redis = _setup_mock_redis(mock_from_url)
        mock_redis.exists.return_value = 1
        assert PresenceManager.is_online(uid) is True

    @patch("redis.from_url")
    def test_is_online_false(self, mock_from_url):
        uid = uuid.uuid4()
        mock_redis = _setup_mock_redis(mock_from_url)
        mock_redis.exists.return_value = 0
        assert PresenceManager.is_online(uid) is False

    @patch("redis.from_url")
    def test_is_online_redis_error_returns_false(self, mock_from_url):
        uid = uuid.uuid4()
        mock_redis = _setup_mock_redis(mock_from_url)
        mock_redis.exists.side_effect = Exception("timeout")
        assert PresenceManager.is_online(uid) is False


class TestPresenceGetOnlineUsers:
    def setup_method(self):
        PresenceManager.reset()

    @patch("redis.from_url")
    def test_batch_check(self, mock_from_url):
        uids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        mock_redis = _setup_mock_redis(mock_from_url)
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = [1, 0, 1]
        mock_redis.pipeline.return_value = mock_pipe

        result = PresenceManager.get_online_users(uids)
        assert result[uids[0]] is True
        assert result[uids[1]] is False
        assert result[uids[2]] is True

    def test_empty_list_returns_empty(self):
        PresenceManager._redis = MagicMock()
        result = PresenceManager.get_online_users([])
        assert result == {}

    @patch("redis.from_url")
    def test_batch_redis_error_returns_all_false(self, mock_from_url):
        uids = [uuid.uuid4(), uuid.uuid4()]
        mock_redis = _setup_mock_redis(mock_from_url)
        mock_redis.pipeline.side_effect = Exception("broken")

        result = PresenceManager.get_online_users(uids)
        assert result[uids[0]] is False
        assert result[uids[1]] is False


class TestPresenceRedisInit:
    def setup_method(self):
        PresenceManager.reset()

    def test_reset_clears_connection(self):
        PresenceManager._redis = MagicMock()
        PresenceManager.reset()
        assert PresenceManager._redis is None

    @patch("redis.from_url")
    def test_lazy_init_on_first_call(self, mock_from_url):
        _setup_mock_redis(mock_from_url)
        PresenceManager.is_online(uuid.uuid4())
        mock_from_url.assert_called_once()

    @patch("redis.from_url")
    def test_redis_unavailable_sets_fallback(self, mock_from_url):
        mock_from_url.side_effect = Exception("no redis")
        result = PresenceManager.is_online(uuid.uuid4())
        assert result is False
        assert PresenceManager._redis == "unavailable"
