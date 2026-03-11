# apps/auth/tests/test_authentication.py
"""
Tests for JWT authentication classes.

Covers:
    - JWTAuthentication: Bearer token extraction, validation, error handling
    - JWTAuthenticationOptional: Same as above but returns None instead of raising
"""

import pytest
from unittest.mock import patch, MagicMock

from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import AuthenticationFailed

from apps.auth.authentication import JWTAuthentication, JWTAuthenticationOptional
from apps.core.exceptions import TokenAlreadyUsed, TokenExpired, TokenInvalid
from apps.users.tests.factories import UserFactory


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def factory():
    """Return a DRF APIRequestFactory instance."""
    return APIRequestFactory()


@pytest.fixture
def jwt_auth():
    """Return a JWTAuthentication instance."""
    return JWTAuthentication()


@pytest.fixture
def jwt_auth_optional():
    """Return a JWTAuthenticationOptional instance."""
    return JWTAuthenticationOptional()


# =============================================================================
# HELPER
# =============================================================================


def _make_request(factory, auth_header=None):
    """
    Create a GET request with the given Authorization header.

    Args:
        factory: APIRequestFactory instance
        auth_header: Value for the Authorization header, or None to omit it
    """
    if auth_header is not None:
        return factory.get('/', HTTP_AUTHORIZATION=auth_header)
    return factory.get('/')


# =============================================================================
# TEST JWT AUTHENTICATION
# =============================================================================


class TestJWTAuthentication:
    """Tests for JWTAuthentication class."""

    def test_returns_none_when_no_authorization_header(self, factory, jwt_auth):
        """authenticate() should return None when no Authorization header is present."""
        request = _make_request(factory)
        result = jwt_auth.authenticate(request)
        assert result is None

    def test_returns_none_for_empty_authorization_header(self, factory, jwt_auth):
        """authenticate() should return None when the Authorization header is empty."""
        request = _make_request(factory, auth_header='')
        result = jwt_auth.authenticate(request)
        assert result is None

    def test_returns_none_for_non_bearer_scheme(self, factory, jwt_auth):
        """authenticate() should return None when scheme is not 'Bearer' (e.g., 'Token')."""
        request = _make_request(factory, auth_header='Token abc123')
        result = jwt_auth.authenticate(request)
        assert result is None

    def test_returns_none_for_basic_auth_scheme(self, factory, jwt_auth):
        """authenticate() should return None when scheme is 'Basic'."""
        request = _make_request(factory, auth_header='Basic dXNlcjpwYXNz')
        result = jwt_auth.authenticate(request)
        assert result is None

    def test_raises_when_bearer_with_no_token(self, factory, jwt_auth):
        """authenticate() should raise AuthenticationFailed when 'Bearer' has no token."""
        request = _make_request(factory, auth_header='Bearer')
        with pytest.raises(AuthenticationFailed) as exc_info:
            jwt_auth.authenticate(request)
        assert 'No credentials provided' in str(exc_info.value.detail)

    def test_raises_when_token_contains_spaces(self, factory, jwt_auth):
        """authenticate() should raise AuthenticationFailed when token contains spaces."""
        request = _make_request(factory, auth_header='Bearer abc def')
        with pytest.raises(AuthenticationFailed) as exc_info:
            jwt_auth.authenticate(request)
        assert 'should not contain spaces' in str(exc_info.value.detail)

    @pytest.mark.django_db
    @patch('apps.auth.services.auth_service.AuthService.validate_access_token')
    def test_returns_user_and_payload_for_valid_token(
        self, mock_validate, factory, jwt_auth
    ):
        """authenticate() should return (user, payload) for a valid Bearer token."""
        user = UserFactory()
        payload = {'user_id': user.id, 'token_type': 'access'}
        mock_validate.return_value = (user, payload)

        request = _make_request(factory, auth_header='Bearer valid-token-123')
        result = jwt_auth.authenticate(request)

        assert result is not None
        assert result[0] == user
        assert result[1] == payload
        mock_validate.assert_called_once_with('valid-token-123')

    @patch('apps.auth.services.auth_service.AuthService.validate_access_token')
    def test_raises_token_expired_with_code(self, mock_validate, factory, jwt_auth):
        """authenticate() should raise AuthenticationFailed with code='token_expired' for TokenExpired."""
        mock_validate.side_effect = TokenExpired()

        request = _make_request(factory, auth_header='Bearer expired-token')
        with pytest.raises(AuthenticationFailed) as exc_info:
            jwt_auth.authenticate(request)
        assert 'Token has expired' in str(exc_info.value.detail)
        assert exc_info.value.get_codes() == 'token_expired'

    @patch('apps.auth.services.auth_service.AuthService.validate_access_token')
    def test_raises_token_invalid_with_code(self, mock_validate, factory, jwt_auth):
        """authenticate() should raise AuthenticationFailed with code='token_invalid' for TokenInvalid."""
        mock_validate.side_effect = TokenInvalid(message='Token has been revoked')

        request = _make_request(factory, auth_header='Bearer invalid-token')
        with pytest.raises(AuthenticationFailed) as exc_info:
            jwt_auth.authenticate(request)
        assert 'Token has been revoked' in str(exc_info.value.detail)
        assert exc_info.value.get_codes() == 'token_invalid'

    @patch('apps.auth.services.auth_service.AuthService.validate_access_token')
    def test_raises_token_invalid_default_message(self, mock_validate, factory, jwt_auth):
        """authenticate() should raise AuthenticationFailed('Invalid token') for TokenInvalid with no message."""
        mock_validate.side_effect = TokenInvalid()

        request = _make_request(factory, auth_header='Bearer bad-token')
        with pytest.raises(AuthenticationFailed) as exc_info:
            jwt_auth.authenticate(request)
        detail = str(exc_info.value.detail)
        assert 'Invalid token' in detail or 'token' in detail.lower()
        assert exc_info.value.get_codes() == 'token_invalid'

    @patch('apps.auth.services.auth_service.AuthService.validate_access_token')
    def test_raises_token_already_used_with_code(self, mock_validate, factory, jwt_auth):
        """authenticate() should raise AuthenticationFailed with code='token_already_used' for TokenAlreadyUsed."""
        mock_validate.side_effect = TokenAlreadyUsed()

        request = _make_request(factory, auth_header='Bearer reused-token')
        with pytest.raises(AuthenticationFailed) as exc_info:
            jwt_auth.authenticate(request)
        assert 'already been used' in str(exc_info.value.detail)
        assert exc_info.value.get_codes() == 'token_already_used'

    @patch('apps.auth.services.auth_service.AuthService.validate_access_token')
    def test_raises_authentication_failed_for_unexpected_exception(
        self, mock_validate, factory, jwt_auth
    ):
        """authenticate() should raise AuthenticationFailed('Authentication failed') for unexpected errors."""
        mock_validate.side_effect = RuntimeError('Something went wrong')

        request = _make_request(factory, auth_header='Bearer some-token')
        with pytest.raises(AuthenticationFailed) as exc_info:
            jwt_auth.authenticate(request)
        assert 'Authentication failed' in str(exc_info.value.detail)

    def test_authenticate_header_returns_bearer(self, factory, jwt_auth):
        """authenticate_header() should return 'Bearer'."""
        request = _make_request(factory)
        assert jwt_auth.authenticate_header(request) == 'Bearer'

    def test_keyword_is_bearer(self, jwt_auth):
        """The keyword attribute should be 'Bearer'."""
        assert jwt_auth.keyword == 'Bearer'

    def test_bearer_keyword_is_case_insensitive(self, factory, jwt_auth):
        """authenticate() should accept 'bearer' (lowercase) as a valid scheme."""
        # The code does parts[0].lower() != self.keyword.lower(), so 'bearer' should work.
        # It should proceed to token validation (and fail without a mock), or raise
        # AuthenticationFailed -- but it should NOT return None.
        request = _make_request(factory, auth_header='bearer some-token')
        # Without mocking AuthService, this will raise due to token validation.
        # The key assertion: it does NOT return None (it recognizes the scheme).
        with pytest.raises(Exception):
            jwt_auth.authenticate(request)


# =============================================================================
# TEST JWT AUTHENTICATION OPTIONAL
# =============================================================================


class TestJWTAuthenticationOptional:
    """Tests for JWTAuthenticationOptional class."""

    def test_returns_none_when_no_authorization_header(self, factory, jwt_auth_optional):
        """authenticate() should return None when no Authorization header is present."""
        request = _make_request(factory)
        result = jwt_auth_optional.authenticate(request)
        assert result is None

    def test_returns_none_for_non_bearer_scheme(self, factory, jwt_auth_optional):
        """authenticate() should return None for non-Bearer auth schemes."""
        request = _make_request(factory, auth_header='Token abc123')
        result = jwt_auth_optional.authenticate(request)
        assert result is None

    @patch('apps.auth.services.auth_service.AuthService.validate_access_token')
    def test_returns_none_for_expired_token(self, mock_validate, factory, jwt_auth_optional):
        """authenticate() should return None (not raise) for expired tokens."""
        mock_validate.side_effect = TokenExpired()

        request = _make_request(factory, auth_header='Bearer expired-token')
        result = jwt_auth_optional.authenticate(request)
        assert result is None

    @patch('apps.auth.services.auth_service.AuthService.validate_access_token')
    def test_returns_none_for_invalid_token(self, mock_validate, factory, jwt_auth_optional):
        """authenticate() should return None (not raise) for invalid tokens."""
        mock_validate.side_effect = TokenInvalid()

        request = _make_request(factory, auth_header='Bearer invalid-token')
        result = jwt_auth_optional.authenticate(request)
        assert result is None

    @patch('apps.auth.services.auth_service.AuthService.validate_access_token')
    def test_returns_none_for_bearer_with_no_token(self, mock_validate, factory, jwt_auth_optional):
        """authenticate() should return None (not raise) for 'Bearer' with no token."""
        request = _make_request(factory, auth_header='Bearer')
        result = jwt_auth_optional.authenticate(request)
        assert result is None

    @patch('apps.auth.services.auth_service.AuthService.validate_access_token')
    def test_returns_none_for_token_with_spaces(self, mock_validate, factory, jwt_auth_optional):
        """authenticate() should return None (not raise) for token with spaces."""
        request = _make_request(factory, auth_header='Bearer abc def')
        result = jwt_auth_optional.authenticate(request)
        assert result is None

    @patch('apps.auth.services.auth_service.AuthService.validate_access_token')
    def test_returns_none_for_unexpected_exception(self, mock_validate, factory, jwt_auth_optional):
        """authenticate() should return None (not raise) for unexpected errors."""
        mock_validate.side_effect = RuntimeError('Something went wrong')

        request = _make_request(factory, auth_header='Bearer some-token')
        result = jwt_auth_optional.authenticate(request)
        assert result is None

    @pytest.mark.django_db
    @patch('apps.auth.services.auth_service.AuthService.validate_access_token')
    def test_returns_user_and_payload_for_valid_token(
        self, mock_validate, factory, jwt_auth_optional
    ):
        """authenticate() should return (user, payload) for a valid token."""
        user = UserFactory()
        payload = {'user_id': user.id, 'token_type': 'access'}
        mock_validate.return_value = (user, payload)

        request = _make_request(factory, auth_header='Bearer valid-token-123')
        result = jwt_auth_optional.authenticate(request)

        assert result is not None
        assert result[0] == user
        assert result[1] == payload
        mock_validate.assert_called_once_with('valid-token-123')
