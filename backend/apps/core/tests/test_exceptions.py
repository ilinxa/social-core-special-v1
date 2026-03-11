"""
Tests for domain exceptions.

Covers all exception classes in apps.core.exceptions.domain:
DomainException, NotFound, PermissionDenied, ValidationError, ConflictError,
AuthenticationError (and subclasses), BusinessRuleViolation, SessionLimitExceeded,
RateLimitExceeded, ServiceUnavailable, OAuthError.
"""

import pytest

from apps.core.exceptions.domain import (
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


# =============================================================================
# DomainException (base)
# =============================================================================


class TestDomainException:
    """Tests for the base DomainException class."""

    def test_default_message(self):
        """Use default message when none provided."""
        exc = DomainException()

        assert exc.message == "A domain error occurred"

    def test_default_code(self):
        """Use default code when none provided."""
        exc = DomainException()

        assert exc.code == "domain_error"

    def test_default_details_empty(self):
        """Default details is an empty dict."""
        exc = DomainException()

        assert exc.details == {}

    def test_custom_message(self):
        """Accept custom message."""
        exc = DomainException(message="Something broke")

        assert exc.message == "Something broke"

    def test_custom_code(self):
        """Accept custom code."""
        exc = DomainException(code="custom_code")

        assert exc.code == "custom_code"

    def test_custom_details(self):
        """Accept custom details dict."""
        details = {"key": "value", "count": 42}
        exc = DomainException(details=details)

        assert exc.details == {"key": "value", "count": 42}

    def test_all_custom_params(self):
        """Accept all custom params simultaneously."""
        exc = DomainException(
            message="Custom msg",
            code="custom_code",
            details={"foo": "bar"},
        )

        assert exc.message == "Custom msg"
        assert exc.code == "custom_code"
        assert exc.details == {"foo": "bar"}

    def test_to_dict_defaults(self):
        """Return correct dict with default values."""
        exc = DomainException()

        result = exc.to_dict()

        assert result == {
            "message": "A domain error occurred",
            "code": "domain_error",
            "details": {},
        }

    def test_to_dict_with_details(self):
        """Return correct dict including details."""
        exc = DomainException(
            message="Err",
            code="err_code",
            details={"resource": "User"},
        )

        result = exc.to_dict()

        assert result == {
            "message": "Err",
            "code": "err_code",
            "details": {"resource": "User"},
        }

    def test_str_without_details(self):
        """Format as '[code] message' when no details."""
        exc = DomainException(message="Some error", code="some_code")

        assert str(exc) == "[some_code] Some error"

    def test_str_with_details(self):
        """Format as '[code] message - details' when details present."""
        exc = DomainException(
            message="Some error",
            code="some_code",
            details={"key": "val"},
        )

        assert str(exc) == "[some_code] Some error - {'key': 'val'}"

    def test_inherits_from_exception(self):
        """Inherit from built-in Exception."""
        exc = DomainException()

        assert isinstance(exc, Exception)

    def test_is_catchable_as_exception(self):
        """Be catchable with except Exception."""
        with pytest.raises(Exception):
            raise DomainException()

    def test_exception_args_contains_message(self):
        """Pass message to Exception.__init__ as args."""
        exc = DomainException(message="test msg")

        assert exc.args == ("test msg",)

    def test_details_not_shared_between_instances(self):
        """Each instance gets its own details dict."""
        exc1 = DomainException()
        exc2 = DomainException()

        exc1.details["added"] = True

        assert "added" not in exc2.details


# =============================================================================
# NotFound
# =============================================================================


class TestNotFound:
    """Tests for NotFound exception."""

    def test_default_message(self):
        """Use 'Resource not found' as default message."""
        exc = NotFound()

        assert exc.message == "Resource not found"

    def test_default_code(self):
        """Use 'not_found' as default code."""
        exc = NotFound()

        assert exc.code == "not_found"

    def test_default_details_empty(self):
        """Default details is empty when no resource provided."""
        exc = NotFound()

        assert exc.details == {}

    def test_custom_message(self):
        """Accept custom message."""
        exc = NotFound(message="Product not found")

        assert exc.message == "Product not found"

    def test_resource_generates_message(self):
        """Generate message from resource name when no message given."""
        exc = NotFound(resource="User")

        assert exc.message == "User not found"

    def test_resource_in_details(self):
        """Put resource in details dict."""
        exc = NotFound(resource="Product")

        assert exc.details["resource"] == "Product"

    def test_resource_id_in_details(self):
        """Put resource_id as string in details dict."""
        exc = NotFound(resource="Order", resource_id=123)

        assert exc.details["resource_id"] == "123"

    def test_resource_id_string_conversion(self):
        """Convert resource_id to string."""
        exc = NotFound(resource="Item", resource_id=456)

        assert isinstance(exc.details["resource_id"], str)

    def test_resource_id_without_resource(self):
        """Include resource_id even without resource name."""
        exc = NotFound(resource_id=99)

        assert exc.details == {"resource_id": "99"}

    def test_custom_message_overrides_resource_message(self):
        """Explicit message takes priority over resource-based message."""
        exc = NotFound(message="Custom not found", resource="User")

        assert exc.message == "Custom not found"

    def test_to_dict_with_resource_and_id(self):
        """Return full dict with resource details."""
        exc = NotFound(resource="User", resource_id=42)

        result = exc.to_dict()

        assert result == {
            "message": "User not found",
            "code": "not_found",
            "details": {"resource": "User", "resource_id": "42"},
        }

    def test_str_with_resource(self):
        """Format string with details."""
        exc = NotFound(resource="User", resource_id=1)

        result = str(exc)

        assert "[not_found]" in result
        assert "User not found" in result

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException."""
        exc = NotFound()

        assert isinstance(exc, DomainException)

    def test_resource_id_zero_included(self):
        """Include resource_id when it is 0 (falsy but not None)."""
        exc = NotFound(resource="Item", resource_id=0)

        assert "resource_id" in exc.details
        assert exc.details["resource_id"] == "0"

    def test_resource_id_none_excluded(self):
        """Exclude resource_id when it is None."""
        exc = NotFound(resource="Item", resource_id=None)

        assert "resource_id" not in exc.details


# =============================================================================
# PermissionDenied
# =============================================================================


class TestPermissionDenied:
    """Tests for PermissionDenied exception."""

    def test_default_message(self):
        """Use 'Permission denied' as default message."""
        exc = PermissionDenied()

        assert exc.message == "Permission denied"

    def test_default_code(self):
        """Use 'permission_denied' as default code."""
        exc = PermissionDenied()

        assert exc.code == "permission_denied"

    def test_default_details_empty(self):
        """Default details is empty when no action/resource provided."""
        exc = PermissionDenied()

        assert exc.details == {}

    def test_custom_message(self):
        """Accept custom message."""
        exc = PermissionDenied(message="Cannot delete this")

        assert exc.message == "Cannot delete this"

    def test_action_in_details(self):
        """Put action in details dict."""
        exc = PermissionDenied(action="delete")

        assert exc.details["action"] == "delete"

    def test_resource_in_details(self):
        """Put resource in details dict."""
        exc = PermissionDenied(resource="Organization")

        assert exc.details["resource"] == "Organization"

    def test_action_and_resource_in_details(self):
        """Put both action and resource in details dict."""
        exc = PermissionDenied(action="update", resource="Campaign")

        assert exc.details == {"action": "update", "resource": "Campaign"}

    def test_to_dict_with_action_and_resource(self):
        """Return full dict with action and resource."""
        exc = PermissionDenied(
            message="Forbidden",
            action="delete",
            resource="User",
        )

        result = exc.to_dict()

        assert result == {
            "message": "Forbidden",
            "code": "permission_denied",
            "details": {"action": "delete", "resource": "User"},
        }

    def test_str_without_details(self):
        """Format string without details."""
        exc = PermissionDenied()

        assert str(exc) == "[permission_denied] Permission denied"

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException."""
        exc = PermissionDenied()

        assert isinstance(exc, DomainException)

    def test_none_action_excluded(self):
        """Exclude action from details when None."""
        exc = PermissionDenied(action=None, resource="Post")

        assert "action" not in exc.details
        assert exc.details["resource"] == "Post"

    def test_none_resource_excluded(self):
        """Exclude resource from details when None."""
        exc = PermissionDenied(action="edit", resource=None)

        assert "resource" not in exc.details
        assert exc.details["action"] == "edit"


# =============================================================================
# ValidationError
# =============================================================================


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_default_message(self):
        """Use 'Validation failed' as default message."""
        exc = ValidationError()

        assert exc.message == "Validation failed"

    def test_default_code(self):
        """Use 'validation_error' as default code."""
        exc = ValidationError()

        assert exc.code == "validation_error"

    def test_default_details_empty(self):
        """Default details is empty when no field/value provided."""
        exc = ValidationError()

        assert exc.details == {}

    def test_custom_message(self):
        """Accept custom message."""
        exc = ValidationError(message="Email not allowed")

        assert exc.message == "Email not allowed"

    def test_field_in_details(self):
        """Put field in details dict."""
        exc = ValidationError(field="email")

        assert exc.details["field"] == "email"

    def test_value_in_details(self):
        """Put value as string in details dict."""
        exc = ValidationError(field="age", value=15)

        assert exc.details["value"] == "15"

    def test_value_string_conversion(self):
        """Convert value to string."""
        exc = ValidationError(field="count", value=100)

        assert isinstance(exc.details["value"], str)

    def test_value_without_field(self):
        """Include value even without field."""
        exc = ValidationError(value="bad_data")

        assert exc.details == {"value": "bad_data"}

    def test_value_zero_included(self):
        """Include value when it is 0 (falsy but not None)."""
        exc = ValidationError(field="quantity", value=0)

        assert "value" in exc.details
        assert exc.details["value"] == "0"

    def test_value_none_excluded(self):
        """Exclude value when it is None."""
        exc = ValidationError(field="name", value=None)

        assert "value" not in exc.details

    def test_to_dict_with_field_and_value(self):
        """Return full dict with field and value."""
        exc = ValidationError(
            message="Invalid email",
            field="email",
            value="notanemail",
        )

        result = exc.to_dict()

        assert result == {
            "message": "Invalid email",
            "code": "validation_error",
            "details": {"field": "email", "value": "notanemail"},
        }

    def test_str_with_details(self):
        """Format string with details."""
        exc = ValidationError(field="email", value="bad")

        result = str(exc)

        assert "[validation_error]" in result
        assert "Validation failed" in result

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException."""
        exc = ValidationError()

        assert isinstance(exc, DomainException)


# =============================================================================
# ConflictError
# =============================================================================


class TestConflictError:
    """Tests for ConflictError exception."""

    def test_default_message(self):
        """Use 'Resource conflict' as default message."""
        exc = ConflictError()

        assert exc.message == "Resource conflict"

    def test_default_code(self):
        """Use 'conflict' as default code."""
        exc = ConflictError()

        assert exc.code == "conflict"

    def test_default_details_empty(self):
        """Default details is empty when no resource/conflict_type provided."""
        exc = ConflictError()

        assert exc.details == {}

    def test_custom_message(self):
        """Accept custom message."""
        exc = ConflictError(message="Duplicate entry")

        assert exc.message == "Duplicate entry"

    def test_resource_in_details(self):
        """Put resource in details dict."""
        exc = ConflictError(resource="User")

        assert exc.details["resource"] == "User"

    def test_conflict_type_in_details(self):
        """Put conflict_type in details dict."""
        exc = ConflictError(conflict_type="duplicate")

        assert exc.details["conflict_type"] == "duplicate"

    def test_resource_and_conflict_type_in_details(self):
        """Put both resource and conflict_type in details dict."""
        exc = ConflictError(resource="Email", conflict_type="duplicate")

        assert exc.details == {"resource": "Email", "conflict_type": "duplicate"}

    def test_to_dict_with_resource_and_conflict_type(self):
        """Return full dict with resource and conflict_type."""
        exc = ConflictError(
            message="Email already registered",
            resource="User",
            conflict_type="duplicate",
        )

        result = exc.to_dict()

        assert result == {
            "message": "Email already registered",
            "code": "conflict",
            "details": {"resource": "User", "conflict_type": "duplicate"},
        }

    def test_str_without_details(self):
        """Format string without details."""
        exc = ConflictError()

        assert str(exc) == "[conflict] Resource conflict"

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException."""
        exc = ConflictError()

        assert isinstance(exc, DomainException)


# =============================================================================
# AuthenticationError
# =============================================================================


class TestAuthenticationError:
    """Tests for AuthenticationError exception."""

    def test_default_message(self):
        """Use 'Authentication required' as default message."""
        exc = AuthenticationError()

        assert exc.message == "Authentication required"

    def test_default_code(self):
        """Use 'authentication_error' as default code."""
        exc = AuthenticationError()

        assert exc.code == "authentication_error"

    def test_custom_message(self):
        """Accept custom message."""
        exc = AuthenticationError(message="Please log in")

        assert exc.message == "Please log in"

    def test_custom_code(self):
        """Accept custom code."""
        exc = AuthenticationError(code="auth_custom")

        assert exc.code == "auth_custom"

    def test_to_dict_defaults(self):
        """Return correct dict with default values."""
        exc = AuthenticationError()

        result = exc.to_dict()

        assert result == {
            "message": "Authentication required",
            "code": "authentication_error",
            "details": {},
        }

    def test_str_without_details(self):
        """Format string without details."""
        exc = AuthenticationError()

        assert str(exc) == "[authentication_error] Authentication required"

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException."""
        exc = AuthenticationError()

        assert isinstance(exc, DomainException)


# =============================================================================
# InvalidCredentials
# =============================================================================


class TestInvalidCredentials:
    """Tests for InvalidCredentials exception."""

    def test_default_message(self):
        """Use 'Invalid email or password' as default message."""
        exc = InvalidCredentials()

        assert exc.message == "Invalid email or password"

    def test_default_code(self):
        """Use 'invalid_credentials' as default code."""
        exc = InvalidCredentials()

        assert exc.code == "invalid_credentials"

    def test_custom_message(self):
        """Accept custom message."""
        exc = InvalidCredentials(message="Wrong password")

        assert exc.message == "Wrong password"

    def test_to_dict_defaults(self):
        """Return correct dict with default values."""
        exc = InvalidCredentials()

        result = exc.to_dict()

        assert result == {
            "message": "Invalid email or password",
            "code": "invalid_credentials",
            "details": {},
        }

    def test_str_without_details(self):
        """Format string without details."""
        exc = InvalidCredentials()

        assert str(exc) == "[invalid_credentials] Invalid email or password"

    def test_inherits_from_authentication_error(self):
        """Inherit from AuthenticationError."""
        exc = InvalidCredentials()

        assert isinstance(exc, AuthenticationError)

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException (transitive)."""
        exc = InvalidCredentials()

        assert isinstance(exc, DomainException)

    def test_catchable_as_authentication_error(self):
        """Be catchable with except AuthenticationError."""
        with pytest.raises(AuthenticationError):
            raise InvalidCredentials()


# =============================================================================
# TokenExpired
# =============================================================================


class TestTokenExpired:
    """Tests for TokenExpired exception."""

    def test_default_message(self):
        """Use 'Token has expired' as default message."""
        exc = TokenExpired()

        assert exc.message == "Token has expired"

    def test_default_code(self):
        """Use 'token_expired' as default code."""
        exc = TokenExpired()

        assert exc.code == "token_expired"

    def test_custom_message(self):
        """Accept custom message."""
        exc = TokenExpired(message="Access token expired")

        assert exc.message == "Access token expired"

    def test_to_dict_defaults(self):
        """Return correct dict with default values."""
        exc = TokenExpired()

        result = exc.to_dict()

        assert result == {
            "message": "Token has expired",
            "code": "token_expired",
            "details": {},
        }

    def test_str_without_details(self):
        """Format string without details."""
        exc = TokenExpired()

        assert str(exc) == "[token_expired] Token has expired"

    def test_inherits_from_authentication_error(self):
        """Inherit from AuthenticationError."""
        exc = TokenExpired()

        assert isinstance(exc, AuthenticationError)

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException (transitive)."""
        exc = TokenExpired()

        assert isinstance(exc, DomainException)

    def test_catchable_as_authentication_error(self):
        """Be catchable with except AuthenticationError."""
        with pytest.raises(AuthenticationError):
            raise TokenExpired()


# =============================================================================
# TokenInvalid
# =============================================================================


class TestTokenInvalid:
    """Tests for TokenInvalid exception."""

    def test_default_message(self):
        """Use 'Invalid token' as default message."""
        exc = TokenInvalid()

        assert exc.message == "Invalid token"

    def test_default_code(self):
        """Use 'token_invalid' as default code."""
        exc = TokenInvalid()

        assert exc.code == "token_invalid"

    def test_custom_message(self):
        """Accept custom message."""
        exc = TokenInvalid(message="Malformed JWT")

        assert exc.message == "Malformed JWT"

    def test_to_dict_defaults(self):
        """Return correct dict with default values."""
        exc = TokenInvalid()

        result = exc.to_dict()

        assert result == {
            "message": "Invalid token",
            "code": "token_invalid",
            "details": {},
        }

    def test_str_without_details(self):
        """Format string without details."""
        exc = TokenInvalid()

        assert str(exc) == "[token_invalid] Invalid token"

    def test_inherits_from_authentication_error(self):
        """Inherit from AuthenticationError."""
        exc = TokenInvalid()

        assert isinstance(exc, AuthenticationError)

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException (transitive)."""
        exc = TokenInvalid()

        assert isinstance(exc, DomainException)

    def test_catchable_as_authentication_error(self):
        """Be catchable with except AuthenticationError."""
        with pytest.raises(AuthenticationError):
            raise TokenInvalid()


# =============================================================================
# AccountNotVerified
# =============================================================================


class TestAccountNotVerified:
    """Tests for AccountNotVerified exception."""

    def test_default_message(self):
        """Use 'Email verification required' as default message."""
        exc = AccountNotVerified()

        assert exc.message == "Email verification required"

    def test_default_code(self):
        """Use 'account_not_verified' as default code."""
        exc = AccountNotVerified()

        assert exc.code == "account_not_verified"

    def test_custom_message(self):
        """Accept custom message."""
        exc = AccountNotVerified(message="Please verify your email first")

        assert exc.message == "Please verify your email first"

    def test_to_dict_defaults(self):
        """Return correct dict with default values."""
        exc = AccountNotVerified()

        result = exc.to_dict()

        assert result == {
            "message": "Email verification required",
            "code": "account_not_verified",
            "details": {},
        }

    def test_str_without_details(self):
        """Format string without details."""
        exc = AccountNotVerified()

        assert str(exc) == "[account_not_verified] Email verification required"

    def test_inherits_from_authentication_error(self):
        """Inherit from AuthenticationError."""
        exc = AccountNotVerified()

        assert isinstance(exc, AuthenticationError)

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException (transitive)."""
        exc = AccountNotVerified()

        assert isinstance(exc, DomainException)

    def test_catchable_as_authentication_error(self):
        """Be catchable with except AuthenticationError."""
        with pytest.raises(AuthenticationError):
            raise AccountNotVerified()


# =============================================================================
# AccountInactive
# =============================================================================


class TestAccountInactive:
    """Tests for AccountInactive exception."""

    def test_default_message(self):
        """Use 'Account is inactive' as default message."""
        exc = AccountInactive()

        assert exc.message == "Account is inactive"

    def test_default_code(self):
        """Use 'account_inactive' as default code."""
        exc = AccountInactive()

        assert exc.code == "account_inactive"

    def test_custom_message(self):
        """Accept custom message."""
        exc = AccountInactive(message="Your account was deactivated")

        assert exc.message == "Your account was deactivated"

    def test_to_dict_defaults(self):
        """Return correct dict with default values."""
        exc = AccountInactive()

        result = exc.to_dict()

        assert result == {
            "message": "Account is inactive",
            "code": "account_inactive",
            "details": {},
        }

    def test_str_without_details(self):
        """Format string without details."""
        exc = AccountInactive()

        assert str(exc) == "[account_inactive] Account is inactive"

    def test_inherits_from_authentication_error(self):
        """Inherit from AuthenticationError."""
        exc = AccountInactive()

        assert isinstance(exc, AuthenticationError)

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException (transitive)."""
        exc = AccountInactive()

        assert isinstance(exc, DomainException)

    def test_catchable_as_authentication_error(self):
        """Be catchable with except AuthenticationError."""
        with pytest.raises(AuthenticationError):
            raise AccountInactive()


# =============================================================================
# TokenAlreadyUsed
# =============================================================================


class TestTokenAlreadyUsed:
    """Tests for TokenAlreadyUsed exception."""

    def test_default_message(self):
        """Use 'Token has already been used' as default message."""
        exc = TokenAlreadyUsed()

        assert exc.message == "Token has already been used"

    def test_default_code(self):
        """Use 'token_already_used' as default code."""
        exc = TokenAlreadyUsed()

        assert exc.code == "token_already_used"

    def test_custom_message(self):
        """Accept custom message."""
        exc = TokenAlreadyUsed(message="Refresh token was already consumed")

        assert exc.message == "Refresh token was already consumed"

    def test_to_dict_defaults(self):
        """Return correct dict with default values."""
        exc = TokenAlreadyUsed()

        result = exc.to_dict()

        assert result == {
            "message": "Token has already been used",
            "code": "token_already_used",
            "details": {},
        }

    def test_str_without_details(self):
        """Format string without details."""
        exc = TokenAlreadyUsed()

        assert str(exc) == "[token_already_used] Token has already been used"

    def test_inherits_from_token_invalid(self):
        """Inherit from TokenInvalid."""
        exc = TokenAlreadyUsed()

        assert isinstance(exc, TokenInvalid)

    def test_inherits_from_authentication_error(self):
        """Inherit from AuthenticationError (transitive via TokenInvalid)."""
        exc = TokenAlreadyUsed()

        assert isinstance(exc, AuthenticationError)

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException (transitive)."""
        exc = TokenAlreadyUsed()

        assert isinstance(exc, DomainException)

    def test_catchable_as_token_invalid(self):
        """Be catchable with except TokenInvalid."""
        with pytest.raises(TokenInvalid):
            raise TokenAlreadyUsed()

    def test_catchable_as_authentication_error(self):
        """Be catchable with except AuthenticationError."""
        with pytest.raises(AuthenticationError):
            raise TokenAlreadyUsed()


# =============================================================================
# BusinessRuleViolation
# =============================================================================


class TestBusinessRuleViolation:
    """Tests for BusinessRuleViolation exception."""

    def test_default_message(self):
        """Use 'Business rule violation' as default message."""
        exc = BusinessRuleViolation()

        assert exc.message == "Business rule violation"

    def test_default_code(self):
        """Use 'business_rule_violation' as default code."""
        exc = BusinessRuleViolation()

        assert exc.code == "business_rule_violation"

    def test_default_details_empty(self):
        """Default details is empty when no rule provided."""
        exc = BusinessRuleViolation()

        assert exc.details == {}

    def test_custom_message(self):
        """Accept custom message."""
        exc = BusinessRuleViolation(message="Cannot cancel shipped order")

        assert exc.message == "Cannot cancel shipped order"

    def test_rule_in_details(self):
        """Put rule in details dict."""
        exc = BusinessRuleViolation(rule="order_cancellation_policy")

        assert exc.details["rule"] == "order_cancellation_policy"

    def test_to_dict_with_rule(self):
        """Return full dict with rule."""
        exc = BusinessRuleViolation(
            message="Max 5 active campaigns",
            rule="campaign_limit",
        )

        result = exc.to_dict()

        assert result == {
            "message": "Max 5 active campaigns",
            "code": "business_rule_violation",
            "details": {"rule": "campaign_limit"},
        }

    def test_str_with_rule(self):
        """Format string with rule details."""
        exc = BusinessRuleViolation(rule="some_rule")

        result = str(exc)

        assert "[business_rule_violation]" in result
        assert "Business rule violation" in result

    def test_str_without_rule(self):
        """Format string without details."""
        exc = BusinessRuleViolation()

        assert str(exc) == "[business_rule_violation] Business rule violation"

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException."""
        exc = BusinessRuleViolation()

        assert isinstance(exc, DomainException)

    def test_none_rule_excluded(self):
        """Exclude rule from details when None."""
        exc = BusinessRuleViolation(rule=None)

        assert "rule" not in exc.details


# =============================================================================
# SessionLimitExceeded
# =============================================================================


class TestSessionLimitExceeded:
    """Tests for SessionLimitExceeded exception."""

    def test_default_message(self):
        """Use 'Maximum session limit exceeded' as default message."""
        exc = SessionLimitExceeded()

        assert exc.message == "Maximum session limit exceeded"

    def test_default_code(self):
        """Use 'session_limit_exceeded' as default code."""
        exc = SessionLimitExceeded()

        assert exc.code == "session_limit_exceeded"

    def test_custom_message(self):
        """Accept custom message."""
        exc = SessionLimitExceeded(message="Too many active sessions")

        assert exc.message == "Too many active sessions"

    def test_rule_in_details(self):
        """Put rule in details dict (inherited from BusinessRuleViolation)."""
        exc = SessionLimitExceeded(rule="max_sessions_per_user")

        assert exc.details["rule"] == "max_sessions_per_user"

    def test_to_dict_defaults(self):
        """Return correct dict with default values."""
        exc = SessionLimitExceeded()

        result = exc.to_dict()

        assert result == {
            "message": "Maximum session limit exceeded",
            "code": "session_limit_exceeded",
            "details": {},
        }

    def test_to_dict_with_rule(self):
        """Return dict including rule from parent constructor."""
        exc = SessionLimitExceeded(rule="max_5_sessions")

        result = exc.to_dict()

        assert result["details"] == {"rule": "max_5_sessions"}

    def test_str_without_details(self):
        """Format string without details."""
        exc = SessionLimitExceeded()

        assert str(exc) == "[session_limit_exceeded] Maximum session limit exceeded"

    def test_inherits_from_business_rule_violation(self):
        """Inherit from BusinessRuleViolation."""
        exc = SessionLimitExceeded()

        assert isinstance(exc, BusinessRuleViolation)

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException (transitive)."""
        exc = SessionLimitExceeded()

        assert isinstance(exc, DomainException)

    def test_catchable_as_business_rule_violation(self):
        """Be catchable with except BusinessRuleViolation."""
        with pytest.raises(BusinessRuleViolation):
            raise SessionLimitExceeded()


# =============================================================================
# RateLimitExceeded
# =============================================================================


class TestRateLimitExceeded:
    """Tests for RateLimitExceeded exception."""

    def test_default_message(self):
        """Use 'Rate limit exceeded' as default message."""
        exc = RateLimitExceeded()

        assert exc.message == "Rate limit exceeded"

    def test_default_code(self):
        """Use 'rate_limit_exceeded' as default code."""
        exc = RateLimitExceeded()

        assert exc.code == "rate_limit_exceeded"

    def test_default_details_empty(self):
        """Default details is empty when no retry_after provided."""
        exc = RateLimitExceeded()

        assert exc.details == {}

    def test_custom_message(self):
        """Accept custom message."""
        exc = RateLimitExceeded(message="Too many password reset attempts")

        assert exc.message == "Too many password reset attempts"

    def test_retry_after_in_details(self):
        """Put retry_after in details dict."""
        exc = RateLimitExceeded(retry_after=60)

        assert exc.details["retry_after"] == 60

    def test_retry_after_as_integer(self):
        """Keep retry_after as integer (not string-converted)."""
        exc = RateLimitExceeded(retry_after=120)

        assert isinstance(exc.details["retry_after"], int)

    def test_to_dict_with_retry_after(self):
        """Return full dict with retry_after."""
        exc = RateLimitExceeded(
            message="Slow down",
            retry_after=30,
        )

        result = exc.to_dict()

        assert result == {
            "message": "Slow down",
            "code": "rate_limit_exceeded",
            "details": {"retry_after": 30},
        }

    def test_str_with_retry_after(self):
        """Format string with retry_after details."""
        exc = RateLimitExceeded(retry_after=60)

        result = str(exc)

        assert "[rate_limit_exceeded]" in result
        assert "Rate limit exceeded" in result

    def test_str_without_details(self):
        """Format string without details."""
        exc = RateLimitExceeded()

        assert str(exc) == "[rate_limit_exceeded] Rate limit exceeded"

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException."""
        exc = RateLimitExceeded()

        assert isinstance(exc, DomainException)

    def test_none_retry_after_excluded(self):
        """Exclude retry_after from details when None."""
        exc = RateLimitExceeded(retry_after=None)

        assert "retry_after" not in exc.details


# =============================================================================
# ServiceUnavailable
# =============================================================================


class TestServiceUnavailable:
    """Tests for ServiceUnavailable exception."""

    def test_default_message(self):
        """Use 'Service temporarily unavailable' as default message."""
        exc = ServiceUnavailable()

        assert exc.message == "Service temporarily unavailable"

    def test_default_code(self):
        """Use 'service_unavailable' as default code."""
        exc = ServiceUnavailable()

        assert exc.code == "service_unavailable"

    def test_default_details_empty(self):
        """Default details is empty when no service/retry_after provided."""
        exc = ServiceUnavailable()

        assert exc.details == {}

    def test_custom_message(self):
        """Accept custom message."""
        exc = ServiceUnavailable(message="Email service is down")

        assert exc.message == "Email service is down"

    def test_service_in_details(self):
        """Put service name in details dict."""
        exc = ServiceUnavailable(service="email")

        assert exc.details["service"] == "email"

    def test_retry_after_in_details(self):
        """Put retry_after in details dict."""
        exc = ServiceUnavailable(retry_after=300)

        assert exc.details["retry_after"] == 300

    def test_service_and_retry_after_in_details(self):
        """Put both service and retry_after in details dict."""
        exc = ServiceUnavailable(service="payment", retry_after=60)

        assert exc.details == {"service": "payment", "retry_after": 60}

    def test_to_dict_with_service_and_retry_after(self):
        """Return full dict with service and retry_after."""
        exc = ServiceUnavailable(
            message="Payment gateway down",
            service="stripe",
            retry_after=120,
        )

        result = exc.to_dict()

        assert result == {
            "message": "Payment gateway down",
            "code": "service_unavailable",
            "details": {"service": "stripe", "retry_after": 120},
        }

    def test_str_with_details(self):
        """Format string with details."""
        exc = ServiceUnavailable(service="redis")

        result = str(exc)

        assert "[service_unavailable]" in result
        assert "Service temporarily unavailable" in result

    def test_str_without_details(self):
        """Format string without details."""
        exc = ServiceUnavailable()

        assert str(exc) == "[service_unavailable] Service temporarily unavailable"

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException."""
        exc = ServiceUnavailable()

        assert isinstance(exc, DomainException)

    def test_none_service_excluded(self):
        """Exclude service from details when None."""
        exc = ServiceUnavailable(service=None, retry_after=10)

        assert "service" not in exc.details
        assert exc.details["retry_after"] == 10

    def test_none_retry_after_excluded(self):
        """Exclude retry_after from details when None."""
        exc = ServiceUnavailable(service="cache", retry_after=None)

        assert "retry_after" not in exc.details
        assert exc.details["service"] == "cache"


# =============================================================================
# OAuthError
# =============================================================================


class TestOAuthError:
    """Tests for OAuthError exception."""

    def test_default_message(self):
        """Use 'OAuth authentication failed' as default message."""
        exc = OAuthError()

        assert exc.message == "OAuth authentication failed"

    def test_default_code(self):
        """Use 'oauth_error' as default code."""
        exc = OAuthError()

        assert exc.code == "oauth_error"

    def test_default_details_empty(self):
        """Default details is empty when no provider/oauth_error provided."""
        exc = OAuthError()

        assert exc.details == {}

    def test_custom_message(self):
        """Accept custom message."""
        exc = OAuthError(message="Google login failed")

        assert exc.message == "Google login failed"

    def test_provider_in_details(self):
        """Put provider in details dict."""
        exc = OAuthError(provider="google")

        assert exc.details["provider"] == "google"

    def test_oauth_error_in_details(self):
        """Put oauth_error in details dict."""
        exc = OAuthError(oauth_error="access_denied")

        assert exc.details["oauth_error"] == "access_denied"

    def test_provider_and_oauth_error_in_details(self):
        """Put both provider and oauth_error in details dict."""
        exc = OAuthError(provider="apple", oauth_error="invalid_grant")

        assert exc.details == {"provider": "apple", "oauth_error": "invalid_grant"}

    def test_to_dict_with_provider_and_error(self):
        """Return full dict with provider and oauth_error."""
        exc = OAuthError(
            message="Google token invalid",
            provider="google",
            oauth_error="invalid_token",
        )

        result = exc.to_dict()

        assert result == {
            "message": "Google token invalid",
            "code": "oauth_error",
            "details": {"provider": "google", "oauth_error": "invalid_token"},
        }

    def test_str_with_details(self):
        """Format string with details."""
        exc = OAuthError(provider="google")

        result = str(exc)

        assert "[oauth_error]" in result
        assert "OAuth authentication failed" in result

    def test_str_without_details(self):
        """Format string without details."""
        exc = OAuthError()

        assert str(exc) == "[oauth_error] OAuth authentication failed"

    def test_inherits_from_domain_exception(self):
        """Inherit from DomainException."""
        exc = OAuthError()

        assert isinstance(exc, DomainException)

    def test_none_provider_excluded(self):
        """Exclude provider from details when None."""
        exc = OAuthError(provider=None, oauth_error="timeout")

        assert "provider" not in exc.details
        assert exc.details["oauth_error"] == "timeout"

    def test_none_oauth_error_excluded(self):
        """Exclude oauth_error from details when None."""
        exc = OAuthError(provider="google", oauth_error=None)

        assert "oauth_error" not in exc.details
        assert exc.details["provider"] == "google"


# =============================================================================
# Inheritance chain integration tests
# =============================================================================


class TestInheritanceChains:
    """Verify full inheritance hierarchy across all exception classes."""

    def test_not_found_mro(self):
        """NotFound inherits DomainException -> Exception."""
        assert issubclass(NotFound, DomainException)
        assert issubclass(NotFound, Exception)

    def test_permission_denied_mro(self):
        """PermissionDenied inherits DomainException -> Exception."""
        assert issubclass(PermissionDenied, DomainException)
        assert issubclass(PermissionDenied, Exception)

    def test_validation_error_mro(self):
        """ValidationError inherits DomainException -> Exception."""
        assert issubclass(ValidationError, DomainException)
        assert issubclass(ValidationError, Exception)

    def test_conflict_error_mro(self):
        """ConflictError inherits DomainException -> Exception."""
        assert issubclass(ConflictError, DomainException)
        assert issubclass(ConflictError, Exception)

    def test_authentication_error_mro(self):
        """AuthenticationError inherits DomainException -> Exception."""
        assert issubclass(AuthenticationError, DomainException)
        assert issubclass(AuthenticationError, Exception)

    def test_invalid_credentials_mro(self):
        """InvalidCredentials inherits AuthenticationError -> DomainException."""
        assert issubclass(InvalidCredentials, AuthenticationError)
        assert issubclass(InvalidCredentials, DomainException)

    def test_token_expired_mro(self):
        """TokenExpired inherits AuthenticationError -> DomainException."""
        assert issubclass(TokenExpired, AuthenticationError)
        assert issubclass(TokenExpired, DomainException)

    def test_token_invalid_mro(self):
        """TokenInvalid inherits AuthenticationError -> DomainException."""
        assert issubclass(TokenInvalid, AuthenticationError)
        assert issubclass(TokenInvalid, DomainException)

    def test_token_already_used_mro(self):
        """TokenAlreadyUsed inherits TokenInvalid -> AuthenticationError -> DomainException."""
        assert issubclass(TokenAlreadyUsed, TokenInvalid)
        assert issubclass(TokenAlreadyUsed, AuthenticationError)
        assert issubclass(TokenAlreadyUsed, DomainException)

    def test_account_not_verified_mro(self):
        """AccountNotVerified inherits AuthenticationError -> DomainException."""
        assert issubclass(AccountNotVerified, AuthenticationError)
        assert issubclass(AccountNotVerified, DomainException)

    def test_account_inactive_mro(self):
        """AccountInactive inherits AuthenticationError -> DomainException."""
        assert issubclass(AccountInactive, AuthenticationError)
        assert issubclass(AccountInactive, DomainException)

    def test_business_rule_violation_mro(self):
        """BusinessRuleViolation inherits DomainException -> Exception."""
        assert issubclass(BusinessRuleViolation, DomainException)
        assert issubclass(BusinessRuleViolation, Exception)

    def test_session_limit_exceeded_mro(self):
        """SessionLimitExceeded inherits BusinessRuleViolation -> DomainException."""
        assert issubclass(SessionLimitExceeded, BusinessRuleViolation)
        assert issubclass(SessionLimitExceeded, DomainException)

    def test_rate_limit_exceeded_mro(self):
        """RateLimitExceeded inherits DomainException -> Exception."""
        assert issubclass(RateLimitExceeded, DomainException)
        assert issubclass(RateLimitExceeded, Exception)

    def test_service_unavailable_mro(self):
        """ServiceUnavailable inherits DomainException -> Exception."""
        assert issubclass(ServiceUnavailable, DomainException)
        assert issubclass(ServiceUnavailable, Exception)

    def test_oauth_error_mro(self):
        """OAuthError inherits DomainException -> Exception."""
        assert issubclass(OAuthError, DomainException)
        assert issubclass(OAuthError, Exception)

    def test_all_domain_exceptions_share_base(self):
        """All exception classes inherit from DomainException."""
        all_exceptions = [
            NotFound,
            PermissionDenied,
            ValidationError,
            ConflictError,
            AuthenticationError,
            InvalidCredentials,
            TokenExpired,
            TokenInvalid,
            TokenAlreadyUsed,
            AccountNotVerified,
            AccountInactive,
            BusinessRuleViolation,
            SessionLimitExceeded,
            RateLimitExceeded,
            ServiceUnavailable,
            OAuthError,
        ]

        for exc_class in all_exceptions:
            assert issubclass(exc_class, DomainException), (
                f"{exc_class.__name__} does not inherit from DomainException"
            )

    def test_catch_all_auth_errors_with_authentication_error(self):
        """Catch all auth subclasses with a single except AuthenticationError."""
        auth_subclasses = [
            InvalidCredentials,
            TokenExpired,
            TokenInvalid,
            TokenAlreadyUsed,
            AccountNotVerified,
            AccountInactive,
        ]

        for exc_class in auth_subclasses:
            with pytest.raises(AuthenticationError):
                raise exc_class()

    def test_not_found_is_not_authentication_error(self):
        """NotFound is not an AuthenticationError."""
        assert not issubclass(NotFound, AuthenticationError)

    def test_oauth_error_is_not_authentication_error(self):
        """OAuthError is not an AuthenticationError."""
        assert not issubclass(OAuthError, AuthenticationError)

    def test_session_limit_is_not_authentication_error(self):
        """SessionLimitExceeded is not an AuthenticationError."""
        assert not issubclass(SessionLimitExceeded, AuthenticationError)
