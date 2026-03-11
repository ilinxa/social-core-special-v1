"""
Tests for Exception Handler
============================
Comprehensive tests for the custom DRF exception handler that converts
domain exceptions and DRF exceptions to consistent HTTP responses.

Tests cover:
    - get_status_code() mapping for all codes in STATUS_CODE_MAP
    - exception_handler() with DRF built-in exceptions
    - exception_handler() with all DomainException subclasses
    - exception_handler() with unhandled Python exceptions
    - Helper functions (_extract_message, _extract_details, _status_to_code, _get_view_name)
"""

import pytest
from unittest.mock import MagicMock

from rest_framework.exceptions import (
    AuthenticationFailed as DRFAuthenticationFailed,
    NotAuthenticated as DRFNotAuthenticated,
    NotFound as DRFNotFound,
    PermissionDenied as DRFPermissionDenied,
    Throttled as DRFThrottled,
    ValidationError as DRFValidationError,
    MethodNotAllowed as DRFMethodNotAllowed,
)
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.core.exceptions import (
    AccountInactive,
    AccountNotVerified,
    AuthenticationError,
    BusinessRuleViolation,
    ConflictError,
    DomainException,
    InvalidCredentials,
    NotFound,
    OAuthError,
    PermissionDenied,
    RateLimitExceeded,
    ServiceUnavailable,
    SessionLimitExceeded,
    TokenAlreadyUsed,
    TokenExpired,
    TokenInvalid,
    ValidationError,
)
from apps.core.exceptions.handler import (
    STATUS_CODE_MAP,
    _extract_details,
    _extract_message,
    _get_view_name,
    _status_to_code,
    exception_handler,
    get_status_code,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def handler_context():
    """
    Create a minimal DRF exception handler context.

    The context dict requires a 'view' key (and optionally 'request')
    for the handler to work correctly.
    """
    factory = APIRequestFactory()
    request = factory.get("/test/")
    return {"view": APIView(), "request": request}


# =============================================================================
# get_status_code TESTS
# =============================================================================

class TestGetStatusCode:
    """Tests for the get_status_code() function."""

    @pytest.mark.parametrize(
        "code,expected_status",
        [
            ("domain_error", 400),
            ("validation_error", 400),
            ("business_rule_violation", 400),
            ("authentication_error", 401),
            ("invalid_credentials", 401),
            ("token_expired", 401),
            ("token_invalid", 401),
            ("permission_denied", 403),
            ("not_found", 404),
            ("conflict", 409),
            ("rate_limit_exceeded", 429),
            ("service_unavailable", 503),
        ],
    )
    def test_known_codes_return_correct_status(self, code, expected_status):
        """Every code in STATUS_CODE_MAP should return the expected HTTP status."""
        assert get_status_code(code) == expected_status

    def test_all_status_code_map_entries_are_covered(self):
        """Verify every key in STATUS_CODE_MAP returns the mapped value."""
        for code, expected_status in STATUS_CODE_MAP.items():
            assert get_status_code(code) == expected_status

    def test_unknown_code_defaults_to_400(self):
        """Unknown exception codes should default to HTTP 400."""
        assert get_status_code("totally_unknown_code") == 400

    def test_empty_string_defaults_to_400(self):
        """An empty string code should default to HTTP 400."""
        assert get_status_code("") == 400

    def test_none_like_string_defaults_to_400(self):
        """A string that is not in the map should default to 400."""
        assert get_status_code("something_random") == 400


# =============================================================================
# exception_handler TESTS — DRF EXCEPTIONS
# =============================================================================

class TestExceptionHandlerDRFExceptions:
    """Tests for DRF built-in exceptions handled by the custom exception_handler."""

    def test_drf_validation_error_single_field(self, handler_context):
        """DRF ValidationError for a single field returns 400 with wrapped error format."""
        exc = DRFValidationError({"email": ["Enter a valid email address."]})

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 400
        assert "error" in response.data
        assert "message" in response.data["error"]
        assert "code" in response.data["error"]
        assert response.data["error"]["code"] == "bad_request"

    def test_drf_validation_error_multiple_fields(self, handler_context):
        """DRF ValidationError with multiple fields returns 400 with wrapped error format."""
        exc = DRFValidationError({
            "email": ["Enter a valid email address."],
            "username": ["This field is required."],
        })

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 400
        assert "error" in response.data
        assert response.data["error"]["code"] == "bad_request"
        # Details should contain the field errors
        assert "details" in response.data["error"]

    def test_drf_validation_error_non_field_errors(self, handler_context):
        """DRF ValidationError with non_field_errors returns message from first error."""
        exc = DRFValidationError({
            "non_field_errors": ["The two passwords did not match."]
        })

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 400
        assert "error" in response.data
        assert response.data["error"]["message"] == "The two passwords did not match."

    def test_drf_validation_error_string_detail(self, handler_context):
        """DRF ValidationError with a plain string detail returns it as message."""
        exc = DRFValidationError("Something went wrong.")

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 400
        assert "error" in response.data

    def test_drf_validation_error_list_detail(self, handler_context):
        """DRF ValidationError with a list returns 400 with wrapped error format."""
        exc = DRFValidationError(["Error one.", "Error two."])

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 400
        assert "error" in response.data

    def test_drf_authentication_failed(self, handler_context):
        """DRF AuthenticationFailed returns 401 with its default code preserved."""
        exc = DRFAuthenticationFailed("Invalid token header.")

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 401
        assert "error" in response.data
        assert response.data["error"]["code"] == "authentication_failed"
        assert response.data["error"]["message"] == "Invalid token header."

    def test_drf_authentication_failed_preserves_custom_code(self, handler_context):
        """DRF AuthenticationFailed with custom code='token_expired' preserves it."""
        exc = DRFAuthenticationFailed(detail="Token has expired", code="token_expired")

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 401
        assert response.data["error"]["code"] == "token_expired"
        assert response.data["error"]["message"] == "Token has expired"

    def test_drf_authentication_failed_preserves_token_already_used(self, handler_context):
        """DRF AuthenticationFailed with code='token_already_used' preserves it."""
        exc = DRFAuthenticationFailed(
            detail="Token has already been used", code="token_already_used"
        )

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 401
        assert response.data["error"]["code"] == "token_already_used"

    def test_drf_authentication_failed_preserves_token_invalid(self, handler_context):
        """DRF AuthenticationFailed with code='token_invalid' preserves it."""
        exc = DRFAuthenticationFailed(detail="Token has been revoked", code="token_invalid")

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 401
        assert response.data["error"]["code"] == "token_invalid"

    def test_drf_not_authenticated(self, handler_context):
        """DRF NotAuthenticated returns 401 with its default code preserved."""
        exc = DRFNotAuthenticated()

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 401
        assert "error" in response.data
        assert response.data["error"]["code"] == "not_authenticated"

    def test_drf_permission_denied(self, handler_context):
        """DRF PermissionDenied returns 403 with wrapped error format."""
        exc = DRFPermissionDenied("You do not have permission.")

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 403
        assert "error" in response.data
        assert response.data["error"]["code"] == "permission_denied"
        assert response.data["error"]["message"] == "You do not have permission."

    def test_drf_not_found(self, handler_context):
        """DRF NotFound returns 404 with wrapped error format."""
        exc = DRFNotFound("Not found.")

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 404
        assert "error" in response.data
        assert response.data["error"]["code"] == "not_found"

    def test_drf_throttled(self, handler_context):
        """DRF Throttled returns 429 with its default code preserved."""
        exc = DRFThrottled(wait=60)

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 429
        assert "error" in response.data
        assert response.data["error"]["code"] == "throttled"

    def test_drf_method_not_allowed(self, handler_context):
        """DRF MethodNotAllowed returns 405 with wrapped error format."""
        exc = DRFMethodNotAllowed("DELETE")

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 405
        assert "error" in response.data
        assert response.data["error"]["code"] == "method_not_allowed"

    def test_drf_exception_response_structure(self, handler_context):
        """All DRF exceptions should return consistent {error: {message, code, details}} format."""
        exc = DRFAuthenticationFailed("Token expired")

        response = exception_handler(exc, handler_context)

        assert response is not None
        error = response.data["error"]
        assert "message" in error
        assert "code" in error
        assert "details" in error
        assert isinstance(error["message"], str)
        assert isinstance(error["code"], str)
        assert isinstance(error["details"], dict)


# =============================================================================
# exception_handler TESTS — DOMAIN EXCEPTIONS
# =============================================================================

class TestExceptionHandlerDomainExceptions:
    """Tests for DomainException subclasses handled by the custom exception_handler."""

    def test_base_domain_exception(self, handler_context):
        """Base DomainException returns 400 with to_dict() format."""
        exc = DomainException(message="Something failed", details={"key": "value"})

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 400
        assert response.data == {
            "error": {
                "message": "Something failed",
                "code": "domain_error",
                "details": {"key": "value"},
            }
        }

    def test_base_domain_exception_defaults(self, handler_context):
        """Base DomainException with no arguments uses default message and code."""
        exc = DomainException()

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 400
        assert response.data["error"]["message"] == "A domain error occurred"
        assert response.data["error"]["code"] == "domain_error"
        assert response.data["error"]["details"] == {}

    def test_not_found_exception(self, handler_context):
        """NotFound returns 404 with resource details."""
        exc = NotFound(resource="User", resource_id="123")

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 404
        assert response.data == {
            "error": {
                "message": "User not found",
                "code": "not_found",
                "details": {"resource": "User", "resource_id": "123"},
            }
        }

    def test_not_found_exception_default_message(self, handler_context):
        """NotFound without resource uses default message."""
        exc = NotFound()

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 404
        assert response.data["error"]["message"] == "Resource not found"
        assert response.data["error"]["code"] == "not_found"

    def test_not_found_custom_message(self, handler_context):
        """NotFound with custom message uses that message."""
        exc = NotFound(message="Organization not found", resource="Organization", resource_id="abc")

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 404
        assert response.data["error"]["message"] == "Organization not found"
        assert response.data["error"]["details"]["resource"] == "Organization"
        assert response.data["error"]["details"]["resource_id"] == "abc"

    def test_permission_denied_exception(self, handler_context):
        """PermissionDenied returns 403 with action and resource details."""
        exc = PermissionDenied(
            message="You cannot delete this organization",
            action="delete",
            resource="Organization",
        )

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 403
        assert response.data == {
            "error": {
                "message": "You cannot delete this organization",
                "code": "permission_denied",
                "details": {"action": "delete", "resource": "Organization"},
            }
        }

    def test_permission_denied_default(self, handler_context):
        """PermissionDenied with no args uses defaults."""
        exc = PermissionDenied()

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 403
        assert response.data["error"]["message"] == "Permission denied"
        assert response.data["error"]["code"] == "permission_denied"

    def test_validation_error(self, handler_context):
        """Domain ValidationError returns 400 with field details."""
        exc = ValidationError(
            message="Email domain not allowed",
            field="email",
            value="user@blocked.com",
        )

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert response.data["error"]["message"] == "Email domain not allowed"
        assert response.data["error"]["details"]["field"] == "email"
        assert response.data["error"]["details"]["value"] == "user@blocked.com"

    def test_conflict_error(self, handler_context):
        """ConflictError returns 409 with resource and conflict_type details."""
        exc = ConflictError(
            message="User with this email already exists",
            resource="User",
            conflict_type="duplicate",
        )

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 409
        assert response.data == {
            "error": {
                "message": "User with this email already exists",
                "code": "conflict",
                "details": {"resource": "User", "conflict_type": "duplicate"},
            }
        }

    def test_conflict_error_default(self, handler_context):
        """ConflictError with no args uses defaults."""
        exc = ConflictError()

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 409
        assert response.data["error"]["message"] == "Resource conflict"
        assert response.data["error"]["code"] == "conflict"

    def test_authentication_error(self, handler_context):
        """AuthenticationError returns 401."""
        exc = AuthenticationError(message="Invalid or expired token")

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 401
        assert response.data["error"]["code"] == "authentication_error"
        assert response.data["error"]["message"] == "Invalid or expired token"

    def test_invalid_credentials(self, handler_context):
        """InvalidCredentials returns 401."""
        exc = InvalidCredentials()

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 401
        assert response.data["error"]["code"] == "invalid_credentials"
        assert response.data["error"]["message"] == "Invalid email or password"

    def test_token_expired(self, handler_context):
        """TokenExpired returns 401."""
        exc = TokenExpired()

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 401
        assert response.data["error"]["code"] == "token_expired"
        assert response.data["error"]["message"] == "Token has expired"

    def test_token_invalid(self, handler_context):
        """TokenInvalid returns 401."""
        exc = TokenInvalid()

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 401
        assert response.data["error"]["code"] == "token_invalid"
        assert response.data["error"]["message"] == "Invalid token"

    def test_token_already_used(self, handler_context):
        """TokenAlreadyUsed returns 401."""
        exc = TokenAlreadyUsed()

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 401
        assert response.data["error"]["code"] == "token_already_used"
        assert response.data["error"]["message"] == "Token has already been used"

    def test_account_not_verified(self, handler_context):
        """AccountNotVerified returns 401."""
        exc = AccountNotVerified()

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 401
        assert response.data["error"]["code"] == "account_not_verified"
        assert response.data["error"]["message"] == "Email verification required"

    def test_account_inactive(self, handler_context):
        """AccountInactive returns 401."""
        exc = AccountInactive()

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 401
        assert response.data["error"]["code"] == "account_inactive"
        assert response.data["error"]["message"] == "Account is inactive"

    def test_business_rule_violation(self, handler_context):
        """BusinessRuleViolation returns 400 with rule details."""
        exc = BusinessRuleViolation(
            message="Cannot cancel order after shipping",
            rule="order_cancellation_policy",
        )

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 400
        assert response.data["error"]["code"] == "business_rule_violation"
        assert response.data["error"]["message"] == "Cannot cancel order after shipping"
        assert response.data["error"]["details"]["rule"] == "order_cancellation_policy"

    def test_session_limit_exceeded(self, handler_context):
        """SessionLimitExceeded returns 400."""
        exc = SessionLimitExceeded()

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 400
        assert response.data["error"]["code"] == "session_limit_exceeded"
        assert response.data["error"]["message"] == "Maximum session limit exceeded"

    def test_rate_limit_exceeded(self, handler_context):
        """RateLimitExceeded returns 429 with retry_after details."""
        exc = RateLimitExceeded(
            message="Too many password reset attempts",
            retry_after=300,
        )

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 429
        assert response.data["error"]["code"] == "rate_limit_exceeded"
        assert response.data["error"]["message"] == "Too many password reset attempts"
        assert response.data["error"]["details"]["retry_after"] == 300

    def test_rate_limit_exceeded_default(self, handler_context):
        """RateLimitExceeded with no args uses defaults."""
        exc = RateLimitExceeded()

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 429
        assert response.data["error"]["message"] == "Rate limit exceeded"

    def test_service_unavailable(self, handler_context):
        """ServiceUnavailable returns 503 with service and retry_after details."""
        exc = ServiceUnavailable(
            message="Email service is down",
            service="email",
            retry_after=60,
        )

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 503
        assert response.data["error"]["code"] == "service_unavailable"
        assert response.data["error"]["message"] == "Email service is down"
        assert response.data["error"]["details"]["service"] == "email"
        assert response.data["error"]["details"]["retry_after"] == 60

    def test_service_unavailable_default(self, handler_context):
        """ServiceUnavailable with no args uses defaults."""
        exc = ServiceUnavailable()

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 503
        assert response.data["error"]["message"] == "Service temporarily unavailable"

    def test_oauth_error(self, handler_context):
        """OAuthError returns 400 with provider and oauth_error details."""
        exc = OAuthError(
            message="Google token invalid",
            provider="google",
            oauth_error="invalid_grant",
        )

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 400
        assert response.data["error"]["code"] == "oauth_error"
        assert response.data["error"]["message"] == "Google token invalid"
        assert response.data["error"]["details"]["provider"] == "google"
        assert response.data["error"]["details"]["oauth_error"] == "invalid_grant"

    def test_oauth_error_default(self, handler_context):
        """OAuthError with no args uses defaults."""
        exc = OAuthError()

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 400
        assert response.data["error"]["message"] == "OAuth authentication failed"
        assert response.data["error"]["code"] == "oauth_error"

    def test_domain_exception_with_custom_code(self, handler_context):
        """DomainException with a custom code not in STATUS_CODE_MAP defaults to 400."""
        exc = DomainException(
            message="Custom error",
            code="some_custom_code",
            details={"info": "test"},
        )

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.status_code == 400
        assert response.data["error"]["code"] == "some_custom_code"

    def test_domain_exception_response_uses_to_dict(self, handler_context):
        """Domain exception response payload matches exc.to_dict()."""
        exc = NotFound(resource="Campaign", resource_id="42")

        response = exception_handler(exc, handler_context)

        assert response is not None
        assert response.data["error"] == exc.to_dict()


# =============================================================================
# exception_handler TESTS — UNHANDLED EXCEPTIONS
# =============================================================================

class TestExceptionHandlerUnhandledExceptions:
    """Tests for unhandled (non-DRF, non-domain) exceptions."""

    def test_regular_python_exception_returns_none(self, handler_context):
        """A plain Python exception should return None (unhandled)."""
        exc = ValueError("Something went wrong")

        response = exception_handler(exc, handler_context)

        assert response is None

    def test_runtime_error_returns_none(self, handler_context):
        """RuntimeError should return None (unhandled)."""
        exc = RuntimeError("Unexpected runtime error")

        response = exception_handler(exc, handler_context)

        assert response is None

    def test_type_error_returns_none(self, handler_context):
        """TypeError should return None (unhandled)."""
        exc = TypeError("Wrong type")

        response = exception_handler(exc, handler_context)

        assert response is None

    def test_key_error_returns_none(self, handler_context):
        """KeyError should return None (unhandled)."""
        exc = KeyError("missing_key")

        response = exception_handler(exc, handler_context)

        assert response is None

    def test_generic_exception_returns_none(self, handler_context):
        """Generic Exception should return None (unhandled)."""
        exc = Exception("Generic failure")

        response = exception_handler(exc, handler_context)

        assert response is None


# =============================================================================
# HELPER FUNCTION TESTS — _extract_message
# =============================================================================

class TestExtractMessage:
    """Tests for the _extract_message() helper function."""

    def test_string_input(self):
        """A plain string is returned as-is."""
        assert _extract_message("Something went wrong") == "Something went wrong"

    def test_empty_string_input(self):
        """An empty string is returned as-is."""
        assert _extract_message("") == ""

    def test_dict_with_detail_string(self):
        """Dict with a 'detail' string returns the detail."""
        data = {"detail": "Not found."}
        assert _extract_message(data) == "Not found."

    def test_dict_with_detail_list(self):
        """Dict with a 'detail' list returns string representation."""
        data = {"detail": ["Error one", "Error two"]}
        result = _extract_message(data)
        assert isinstance(result, str)
        # The handler converts via str(), so it contains the list contents
        assert "Error one" in result

    def test_dict_with_non_field_errors(self):
        """Dict with 'non_field_errors' returns first error."""
        data = {"non_field_errors": ["Passwords do not match.", "Another error."]}
        assert _extract_message(data) == "Passwords do not match."

    def test_dict_with_non_field_errors_empty_list(self):
        """Dict with empty 'non_field_errors' list returns string representation."""
        data = {"non_field_errors": []}
        result = _extract_message(data)
        assert isinstance(result, str)

    def test_dict_with_non_field_errors_string(self):
        """Dict with 'non_field_errors' as a string returns the string."""
        data = {"non_field_errors": "Single error"}
        assert _extract_message(data) == "Single error"

    def test_dict_with_field_errors_list(self):
        """Dict with field-level errors returns 'field: first_error'."""
        data = {"email": ["Enter a valid email address."]}
        assert _extract_message(data) == "email: Enter a valid email address."

    def test_dict_with_field_errors_string(self):
        """Dict with field-level error as string returns 'field: error'."""
        data = {"username": "This field is required."}
        assert _extract_message(data) == "username: This field is required."

    def test_list_input(self):
        """A list returns the first element."""
        assert _extract_message(["First error", "Second error"]) == "First error"

    def test_empty_list_input(self):
        """An empty list returns the fallback message."""
        assert _extract_message([]) == "An error occurred"

    def test_other_type_input(self):
        """Non-string, non-dict, non-list input returns the fallback message."""
        assert _extract_message(12345) == "An error occurred"
        assert _extract_message(None) == "An error occurred"
        assert _extract_message(True) == "An error occurred"

    def test_empty_dict(self):
        """An empty dict returns the fallback from the loop (no iterations)."""
        # An empty dict has no keys, so it falls through to the final return
        assert _extract_message({}) == "An error occurred"


# =============================================================================
# HELPER FUNCTION TESTS — _extract_details
# =============================================================================

class TestExtractDetails:
    """Tests for the _extract_details() helper function."""

    def test_dict_with_detail_key_removed(self):
        """'detail' key should be excluded from the returned details."""
        data = {"detail": "Not found", "extra_info": "some value"}
        result = _extract_details(data)
        assert "detail" not in result
        assert result == {"extra_info": "some value"}

    def test_dict_with_only_detail_key(self):
        """Dict containing only 'detail' returns empty dict."""
        data = {"detail": "Not found"}
        assert _extract_details(data) == {}

    def test_dict_with_field_errors(self):
        """Dict with field errors returns those fields."""
        data = {"email": ["Invalid email"], "username": ["Too short"]}
        result = _extract_details(data)
        assert result == {"email": ["Invalid email"], "username": ["Too short"]}

    def test_dict_with_mixed_keys(self):
        """Dict with 'detail' and other keys returns only the non-detail keys."""
        data = {"detail": "Error message", "field1": "value1", "field2": "value2"}
        result = _extract_details(data)
        assert result == {"field1": "value1", "field2": "value2"}

    def test_empty_dict(self):
        """Empty dict returns empty dict."""
        assert _extract_details({}) == {}

    def test_non_dict_string(self):
        """Non-dict input (string) returns empty dict."""
        assert _extract_details("some string") == {}

    def test_non_dict_list(self):
        """Non-dict input (list) returns empty dict."""
        assert _extract_details(["error1", "error2"]) == {}

    def test_non_dict_none(self):
        """None input returns empty dict."""
        assert _extract_details(None) == {}

    def test_non_dict_int(self):
        """Integer input returns empty dict."""
        assert _extract_details(42) == {}


# =============================================================================
# HELPER FUNCTION TESTS — _status_to_code
# =============================================================================

class TestStatusToCode:
    """Tests for the _status_to_code() helper function."""

    @pytest.mark.parametrize(
        "status_code,expected_code",
        [
            (400, "bad_request"),
            (401, "authentication_error"),
            (403, "permission_denied"),
            (404, "not_found"),
            (405, "method_not_allowed"),
            (429, "rate_limit_exceeded"),
            (500, "internal_error"),
        ],
    )
    def test_known_status_codes(self, status_code, expected_code):
        """Known HTTP status codes should return the correct machine-readable code."""
        assert _status_to_code(status_code) == expected_code

    def test_unknown_status_code_defaults_to_error(self):
        """Unknown HTTP status codes should default to 'error'."""
        assert _status_to_code(418) == "error"
        assert _status_to_code(502) == "error"
        assert _status_to_code(503) == "error"
        assert _status_to_code(422) == "error"

    def test_status_code_200_defaults_to_error(self):
        """Success status codes (not in the map) should also default to 'error'."""
        assert _status_to_code(200) == "error"
        assert _status_to_code(201) == "error"


# =============================================================================
# HELPER FUNCTION TESTS — _get_view_name
# =============================================================================

class TestGetViewName:
    """Tests for the _get_view_name() helper function."""

    def test_with_api_view(self):
        """Context with an APIView should return its full module.class path."""
        context = {"view": APIView()}
        result = _get_view_name(context)
        assert result == "rest_framework.views.APIView"

    def test_with_no_view(self):
        """Context without a 'view' key should return 'unknown'."""
        context = {}
        result = _get_view_name(context)
        assert result == "unknown"

    def test_with_none_view(self):
        """Context with view=None should return 'unknown'."""
        context = {"view": None}
        result = _get_view_name(context)
        assert result == "unknown"

    def test_with_custom_view_class(self):
        """Context with a custom view class should return its full path."""

        class MyCustomView(APIView):
            pass

        context = {"view": MyCustomView()}
        result = _get_view_name(context)
        # The module will be the test module itself
        assert "MyCustomView" in result

    def test_with_mock_view(self):
        """Context with a mock object as view should return mock module and class."""
        mock_view = MagicMock()
        mock_view.__class__.__module__ = "apps.myapp.views"
        mock_view.__class__.__name__ = "SomeView"

        context = {"view": mock_view}
        result = _get_view_name(context)
        assert result == "apps.myapp.views.SomeView"


# =============================================================================
# INTEGRATION TESTS — RESPONSE FORMAT CONSISTENCY
# =============================================================================

class TestResponseFormatConsistency:
    """Tests that all handled exceptions produce consistent response format."""

    def _assert_error_format(self, response):
        """Assert the response follows the standard error format."""
        assert response is not None
        assert "error" in response.data
        error = response.data["error"]
        assert "message" in error
        assert "code" in error
        assert isinstance(error["message"], str)
        assert isinstance(error["code"], str)
        assert len(error["message"]) > 0
        assert len(error["code"]) > 0

    def test_all_drf_exceptions_have_consistent_format(self, handler_context):
        """Every DRF exception should produce the standard {error: {...}} format."""
        drf_exceptions = [
            DRFValidationError({"field": ["Error"]}),
            DRFAuthenticationFailed("Bad token"),
            DRFNotAuthenticated(),
            DRFPermissionDenied("Forbidden"),
            DRFNotFound("Not found"),
            DRFThrottled(wait=30),
            DRFMethodNotAllowed("POST"),
        ]

        for exc in drf_exceptions:
            response = exception_handler(exc, handler_context)
            self._assert_error_format(response)

    def test_all_domain_exceptions_have_consistent_format(self, handler_context):
        """Every domain exception should produce the standard {error: {...}} format."""
        domain_exceptions = [
            DomainException(),
            NotFound(resource="Item", resource_id="1"),
            PermissionDenied(action="view", resource="Secret"),
            ValidationError(field="age", value="-1"),
            ConflictError(resource="Email"),
            AuthenticationError(),
            InvalidCredentials(),
            TokenExpired(),
            TokenInvalid(),
            TokenAlreadyUsed(),
            AccountNotVerified(),
            AccountInactive(),
            BusinessRuleViolation(rule="max_items"),
            SessionLimitExceeded(),
            RateLimitExceeded(retry_after=120),
            ServiceUnavailable(service="payments"),
            OAuthError(provider="apple"),
        ]

        for exc in domain_exceptions:
            response = exception_handler(exc, handler_context)
            self._assert_error_format(response)
            # Domain exceptions always include details key
            assert "details" in response.data["error"]
            assert isinstance(response.data["error"]["details"], dict)

    def test_domain_exception_response_matches_to_dict(self, handler_context):
        """For every domain exception, response.data['error'] should equal exc.to_dict()."""
        exceptions_to_test = [
            DomainException(message="Test", details={"a": 1}),
            NotFound(resource="User", resource_id="99"),
            ConflictError(message="Duplicate", resource="Order", conflict_type="duplicate"),
            TokenExpired(),
            RateLimitExceeded(retry_after=60),
            ServiceUnavailable(service="email", retry_after=30),
            OAuthError(provider="google", oauth_error="invalid_token"),
        ]

        for exc in exceptions_to_test:
            response = exception_handler(exc, handler_context)
            assert response.data["error"] == exc.to_dict(), (
                f"Mismatch for {exc.__class__.__name__}: "
                f"response={response.data['error']}, to_dict={exc.to_dict()}"
            )


# =============================================================================
# LOGGING TESTS
# =============================================================================

class TestExceptionHandlerLogging:
    """Tests that the handler logs domain and unhandled exceptions correctly."""

    def test_domain_exception_logs_warning_for_4xx(self, handler_context, caplog):
        """Domain exceptions with 4xx status should log at WARNING level."""
        import logging

        with caplog.at_level(logging.WARNING, logger="apps.core.exceptions.handler"):
            exc = NotFound(resource="User", resource_id="123")
            exception_handler(exc, handler_context)

        assert any("Domain exception" in record.message for record in caplog.records)

    def test_domain_exception_logs_error_for_5xx(self, handler_context, caplog):
        """Domain exceptions with 5xx status should log at ERROR level."""
        import logging

        with caplog.at_level(logging.ERROR, logger="apps.core.exceptions.handler"):
            exc = ServiceUnavailable(service="email")
            exception_handler(exc, handler_context)

        assert any("Domain exception" in record.message for record in caplog.records)

    def test_unhandled_exception_logs_exception(self, handler_context, caplog):
        """Unhandled exceptions should log at ERROR level with full traceback."""
        import logging

        with caplog.at_level(logging.ERROR, logger="apps.core.exceptions.handler"):
            exc = ValueError("Unexpected error")
            exception_handler(exc, handler_context)

        assert any("Unhandled exception" in record.message for record in caplog.records)
