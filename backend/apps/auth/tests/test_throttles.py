from rest_framework.throttling import AnonRateThrottle
from apps.auth.throttles import (
    LoginRateThrottle,
    PasswordResetRateThrottle,
    VerificationRateThrottle,
    OAuthRateThrottle,
)


class TestLoginRateThrottle:
    def test_inherits_from_anon_rate_throttle(self):
        assert issubclass(LoginRateThrottle, AnonRateThrottle)

    def test_scope_is_login(self):
        assert LoginRateThrottle.scope == 'login'


class TestPasswordResetRateThrottle:
    def test_inherits_from_anon_rate_throttle(self):
        assert issubclass(PasswordResetRateThrottle, AnonRateThrottle)

    def test_scope_is_password_reset(self):
        assert PasswordResetRateThrottle.scope == 'password_reset'


class TestVerificationRateThrottle:
    def test_inherits_from_anon_rate_throttle(self):
        assert issubclass(VerificationRateThrottle, AnonRateThrottle)

    def test_scope_is_verification(self):
        assert VerificationRateThrottle.scope == 'verification'


class TestOAuthRateThrottle:
    def test_inherits_from_anon_rate_throttle(self):
        assert issubclass(OAuthRateThrottle, AnonRateThrottle)

    def test_scope_is_oauth(self):
        assert OAuthRateThrottle.scope == 'oauth'
