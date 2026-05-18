from rest_framework.throttling import AnonRateThrottle

from apps.auth.throttles import (
    LoginRateThrottle,
    OAuthRateThrottle,
    PasswordResetRateThrottle,
    RegisterRateThrottle,
    VerificationRateThrottle,
)
from apps.auth.views import (
    AppleOAuthCallbackView,
    AppleOAuthView,
    GoogleOAuthCallbackView,
    GoogleOAuthView,
    PasswordResetConfirmView,
    RegisterView,
    VerifyEmailLinkView,
)


class TestLoginRateThrottle:
    def test_inherits_from_anon_rate_throttle(self):
        assert issubclass(LoginRateThrottle, AnonRateThrottle)

    def test_scope_is_login(self):
        assert LoginRateThrottle.scope == "login"


class TestRegisterRateThrottle:
    def test_inherits_from_anon_rate_throttle(self):
        assert issubclass(RegisterRateThrottle, AnonRateThrottle)

    def test_scope_is_register(self):
        assert RegisterRateThrottle.scope == "register"


class TestPasswordResetRateThrottle:
    def test_inherits_from_anon_rate_throttle(self):
        assert issubclass(PasswordResetRateThrottle, AnonRateThrottle)

    def test_scope_is_password_reset(self):
        assert PasswordResetRateThrottle.scope == "password_reset"


class TestVerificationRateThrottle:
    def test_inherits_from_anon_rate_throttle(self):
        assert issubclass(VerificationRateThrottle, AnonRateThrottle)

    def test_scope_is_verification(self):
        assert VerificationRateThrottle.scope == "verification"


class TestOAuthRateThrottle:
    def test_inherits_from_anon_rate_throttle(self):
        assert issubclass(OAuthRateThrottle, AnonRateThrottle)

    def test_scope_is_oauth(self):
        assert OAuthRateThrottle.scope == "oauth"


# =============================================================================
# View-Level Wire-up Tests
# =============================================================================
#
# Unit tests run under `backend_core.settings.local` which uses DummyCache —
# DRF throttle counters can't persist, so end-to-end 429 verification has to
# live in the integration suite (`make test-api`, runs against Redis).
#
# At unit-test level we verify the *wiring*: each view declares the correct
# throttle_classes value. This is the contract; the throttle itself is
# DRF-provided behavior that is well-tested upstream.


class TestViewThrottleWireUp:
    def test_register_view_uses_register_throttle(self):
        assert RegisterView.throttle_classes == [RegisterRateThrottle]

    def test_verify_email_link_view_uses_verification_throttle(self):
        assert VerifyEmailLinkView.throttle_classes == [VerificationRateThrottle]

    def test_password_reset_confirm_view_uses_password_reset_throttle(self):
        assert PasswordResetConfirmView.throttle_classes == [PasswordResetRateThrottle]

    def test_google_oauth_view_uses_oauth_throttle(self):
        assert GoogleOAuthView.throttle_classes == [OAuthRateThrottle]

    def test_google_oauth_callback_view_uses_oauth_throttle(self):
        assert GoogleOAuthCallbackView.throttle_classes == [OAuthRateThrottle]

    def test_apple_oauth_view_uses_oauth_throttle(self):
        assert AppleOAuthView.throttle_classes == [OAuthRateThrottle]

    def test_apple_oauth_callback_view_uses_oauth_throttle(self):
        assert AppleOAuthCallbackView.throttle_classes == [OAuthRateThrottle]


class TestThrottleRatesConfigured:
    """Confirm DEFAULT_THROTTLE_RATES has rates for every scope we declare."""

    def test_register_scope_has_rate(self, settings):
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        assert "register" in rates
        assert rates["register"] == "5/hour"

    def test_oauth_scope_has_rate(self, settings):
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        assert "oauth" in rates
        assert rates["oauth"] == "10/minute"
