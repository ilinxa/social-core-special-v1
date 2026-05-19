import ast
import inspect
from pathlib import Path

import pytest
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

from apps.auth import throttles as auth_throttles
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

SETTINGS_DIR = Path(__file__).resolve().parents[3] / "backend_core" / "settings"


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


# =============================================================================
# Drift Guard: every declared scope must appear in every settings file
# =============================================================================
#
# A scope referenced by a view but missing from DEFAULT_THROTTLE_RATES raises
# ImproperlyConfigured (HTTP 500) at request time. The default `settings`
# fixture only sees the active test settings (`local`), so a missing scope in
# `local_docker.py` -- which the E2E backend boots with -- slips through
# unit tests. We parse the settings files statically so each file's
# DEFAULT_THROTTLE_RATES is checked independently, without `from .base import *`
# letting one module mutate the dict another module observes.


def _declared_scopes() -> set[str]:
    return {
        cls.scope
        for _, cls in inspect.getmembers(auth_throttles, inspect.isclass)
        if issubclass(cls, SimpleRateThrottle) and getattr(cls, "scope", None)
    }


def _rate_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        # Form A: REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {...}
        if (
            isinstance(target, ast.Subscript)
            and isinstance(target.slice, ast.Constant)
            and target.slice.value == "DEFAULT_THROTTLE_RATES"
            and isinstance(node.value, ast.Dict)
        ):
            for k in node.value.keys:
                if isinstance(k, ast.Constant):
                    keys.add(k.value)
        # Form B: REST_FRAMEWORK = {... "DEFAULT_THROTTLE_RATES": {...} ...}
        if (
            isinstance(target, ast.Name)
            and target.id == "REST_FRAMEWORK"
            and isinstance(node.value, ast.Dict)
        ):
            for k, v in zip(node.value.keys, node.value.values):
                if (
                    isinstance(k, ast.Constant)
                    and k.value == "DEFAULT_THROTTLE_RATES"
                    and isinstance(v, ast.Dict)
                ):
                    for kk in v.keys:
                        if isinstance(kk, ast.Constant):
                            keys.add(kk.value)
    return keys


@pytest.mark.parametrize("settings_file", ["base.py", "local_docker.py"])
class TestEnvironmentThrottleRatesCoverDeclaredScopes:
    def test_all_declared_scopes_have_rates(self, settings_file: str) -> None:
        required = _declared_scopes()
        configured = _rate_keys(SETTINGS_DIR / settings_file)
        missing = required - configured
        assert not missing, (
            f"backend_core/settings/{settings_file} DEFAULT_THROTTLE_RATES is "
            f"missing scopes {sorted(missing)} "
            f"(declared by apps.auth.throttles)."
        )
