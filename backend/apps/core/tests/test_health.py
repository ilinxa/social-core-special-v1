"""
Tests for health and readiness probes.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from backend_core.health import health_check, readiness_check

pytestmark = pytest.mark.django_db


class TestHealthCheck:
    """Tests for the liveness probe (/health/)."""

    def test_returns_200(self):
        request = RequestFactory().get("/health/")
        response = health_check(request)
        assert response.status_code == 200

    def test_returns_ok_status(self):
        request = RequestFactory().get("/health/")
        response = health_check(request)
        assert json.loads(response.content) == {"status": "ok"}

    @patch("backend_core.health.connection")
    def test_returns_200_even_if_db_is_down(self, mock_conn):
        """Liveness probe should NOT check dependencies."""
        mock_conn.ensure_connection.side_effect = Exception("DB down")
        request = RequestFactory().get("/health/")
        response = health_check(request)
        assert response.status_code == 200


class TestReadinessCheck:
    """Tests for the readiness probe (/ready/)."""

    def test_returns_200_when_all_healthy(self):
        request = RequestFactory().get("/ready/")
        with (
            patch("backend_core.health.connection") as mock_conn,
            patch("backend_core.health.cache") as mock_cache,
            patch("backend_core.health.celery_app", create=True) as mock_celery,
        ):
            mock_conn.ensure_connection.return_value = None
            mock_cache.set.return_value = True
            mock_cache.get.return_value = "1"

            # Mock the celery import inside the function
            mock_app = MagicMock()
            mock_app.control.inspect.return_value.ping.return_value = {
                "worker1": {"ok": "pong"}
            }

            with patch.dict(
                "sys.modules", {"backend_core.celery": MagicMock(app=mock_app)}
            ):
                response = readiness_check(request)

            assert response.status_code == 200
            data = json.loads(response.content)
            assert data["status"] == "ok"
            assert data["database"] == "ok"
            assert data["cache"] == "ok"

    @patch("backend_core.health.connection")
    def test_returns_503_when_db_is_down(self, mock_conn):
        mock_conn.ensure_connection.side_effect = Exception("DB down")
        request = RequestFactory().get("/ready/")
        response = readiness_check(request)
        assert response.status_code == 503
        data = json.loads(response.content)
        assert data["database"] == "error"
        assert data["status"] == "error"

    @patch("backend_core.health.cache")
    def test_returns_503_when_cache_is_down(self, mock_cache):
        mock_cache.set.side_effect = Exception("Redis down")
        request = RequestFactory().get("/ready/")
        response = readiness_check(request)
        assert response.status_code == 503
        data = json.loads(response.content)
        assert data["cache"] == "error"
        assert data["status"] == "error"

    @patch("backend_core.health.cache")
    def test_cache_get_returns_wrong_value(self, mock_cache):
        mock_cache.set.return_value = True
        mock_cache.get.return_value = None  # Wrong value
        request = RequestFactory().get("/ready/")
        response = readiness_check(request)
        data = json.loads(response.content)
        assert data["cache"] == "error"

    def test_celery_broker_error_returns_503(self):
        request = RequestFactory().get("/ready/")
        with (
            patch("backend_core.health.connection"),
            patch("backend_core.health.cache") as mock_cache,
        ):
            mock_cache.get.return_value = "1"

            # Make the celery import raise
            import sys

            original = sys.modules.get("backend_core.celery")
            try:
                # Force import to fail inside the function
                mock_module = MagicMock()
                mock_module.app.control.inspect.return_value.ping.side_effect = (
                    Exception("Broker down")
                )
                sys.modules["backend_core.celery"] = mock_module

                response = readiness_check(request)
                data = json.loads(response.content)
                assert data["celery_broker"] == "error"
                assert data["status"] == "error"
            finally:
                if original is not None:
                    sys.modules["backend_core.celery"] = original

    def test_celery_no_workers_still_ok(self):
        """If broker is reachable but no workers respond, mark workers as 'none' but broker as 'ok'."""
        request = RequestFactory().get("/ready/")
        with (
            patch("backend_core.health.connection"),
            patch("backend_core.health.cache") as mock_cache,
        ):
            mock_cache.get.return_value = "1"

            import sys

            original = sys.modules.get("backend_core.celery")
            try:
                mock_module = MagicMock()
                mock_module.app.control.inspect.return_value.ping.return_value = None
                sys.modules["backend_core.celery"] = mock_module

                response = readiness_check(request)
                data = json.loads(response.content)
                assert data["celery_broker"] == "ok"
                assert data["celery_workers"] == "none"
            finally:
                if original is not None:
                    sys.modules["backend_core.celery"] = original
