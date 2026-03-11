# apps/core/tests/test_utils.py
"""
Tests for core utility modules: JWT, password, and datetime utilities.

Covers:
    - JWT encoding, decoding, and token inspection
    - Password hashing, verification, and strength validation
    - Temporary password generation
    - Timezone-aware datetime helpers and formatting
"""

import string
import time
from datetime import datetime, date, timedelta, timezone
from unittest.mock import patch

import jwt as pyjwt
import pytest
from django.conf import settings

from apps.core.exceptions import TokenExpired, TokenInvalid
from apps.core.utils.jwt import (
    ALLOWED_ALGORITHMS,
    decode_token,
    decode_token_unverified,
    encode_token,
    get_token_expiry,
    is_token_expired,
)
from apps.core.utils.password import (
    generate_temporary_password,
    hash_password,
    is_password_valid,
    validate_password_strength,
    verify_password,
)
from apps.core.utils.datetime import (
    days_ago,
    days_from_now,
    end_of_day,
    format_datetime,
    format_iso,
    hours_ago,
    is_future,
    is_past,
    minutes_ago,
    parse_iso,
    start_of_day,
    start_of_month,
    start_of_week,
    time_since,
    time_until,
    to_user_timezone,
    to_utc,
    today_utc,
    utc_now,
)


# =============================================================================
# JWT UTILITIES — encode_token
# =============================================================================


class TestEncodeToken:
    """Tests for encode_token function."""

    def test_encode_token_returns_string(self):
        """encode_token returns a non-empty string."""
        token = encode_token(payload={"user_id": 1})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_encode_token_contains_payload_claims(self):
        """Encoded token contains the provided payload claims."""
        payload = {"user_id": 42, "type": "access"}
        token = encode_token(payload=payload)
        decoded = pyjwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

        assert decoded["user_id"] == 42
        assert decoded["type"] == "access"

    def test_encode_token_adds_exp_claim(self):
        """Encoded token contains an 'exp' (expiration) claim."""
        token = encode_token(payload={"user_id": 1})
        decoded = pyjwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"],
            options={"verify_exp": False},
        )
        assert "exp" in decoded

    def test_encode_token_adds_iat_claim(self):
        """Encoded token contains an 'iat' (issued at) claim."""
        token = encode_token(payload={"user_id": 1})
        decoded = pyjwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"],
            options={"verify_exp": False},
        )
        assert "iat" in decoded

    def test_encode_token_default_expiry_is_900_seconds(self):
        """Default expiry is 900 seconds (15 minutes) from issued time."""
        token = encode_token(payload={"user_id": 1})
        decoded = pyjwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"],
            options={"verify_exp": False},
        )
        # exp should be iat + 900
        assert decoded["exp"] - decoded["iat"] == 900

    def test_encode_token_custom_expiry(self):
        """Custom expires_in value is respected."""
        token = encode_token(payload={"user_id": 1}, expires_in=3600)
        decoded = pyjwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"],
            options={"verify_exp": False},
        )
        assert decoded["exp"] - decoded["iat"] == 3600

    def test_encode_token_custom_secret(self):
        """Token encoded with custom secret cannot be decoded with default."""
        custom_secret = "my-custom-secret-key-for-testing"
        token = encode_token(payload={"user_id": 1}, secret=custom_secret)

        # Should decode with custom secret
        decoded = pyjwt.decode(token, custom_secret, algorithms=["HS256"])
        assert decoded["user_id"] == 1

        # Should NOT decode with default secret (unless they happen to match)
        if custom_secret != settings.SECRET_KEY:
            with pytest.raises(pyjwt.InvalidSignatureError):
                pyjwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

    def test_encode_token_uses_settings_secret_key_by_default(self):
        """Token encoded without explicit secret uses settings.SECRET_KEY."""
        token = encode_token(payload={"user_id": 1})
        # Should decode successfully with settings.SECRET_KEY
        decoded = pyjwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert decoded["user_id"] == 1

    def test_encode_token_empty_payload(self):
        """Encoding an empty payload succeeds (exp and iat are still added)."""
        token = encode_token(payload={})
        decoded = pyjwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"],
            options={"verify_exp": False},
        )
        assert "exp" in decoded
        assert "iat" in decoded

    def test_encode_token_preserves_nested_payload(self):
        """Nested dictionaries and lists in payload are preserved."""
        payload = {
            "user_id": 1,
            "permissions": ["read", "write"],
            "meta": {"org_id": 5},
        }
        token = encode_token(payload=payload)
        decoded = pyjwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"],
            options={"verify_exp": False},
        )
        assert decoded["permissions"] == ["read", "write"]
        assert decoded["meta"] == {"org_id": 5}

    def test_encode_token_iat_is_close_to_now(self):
        """The 'iat' claim is approximately the current UTC time."""
        before = datetime.now(timezone.utc).timestamp()
        token = encode_token(payload={"user_id": 1})
        after = datetime.now(timezone.utc).timestamp()

        decoded = pyjwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"],
            options={"verify_exp": False},
        )
        # iat is an int (truncated), before/after are floats — allow 1s margin
        assert int(before) <= decoded["iat"] <= int(after) + 1


# =============================================================================
# JWT UTILITIES — decode_token
# =============================================================================


class TestDecodeToken:
    """Tests for decode_token function."""

    def test_decode_token_returns_payload(self):
        """decode_token returns the original payload claims."""
        token = encode_token(payload={"user_id": 99, "type": "access"})
        decoded = decode_token(token)
        assert decoded["user_id"] == 99
        assert decoded["type"] == "access"

    def test_decode_token_includes_exp_and_iat(self):
        """Decoded payload includes exp and iat standard claims."""
        token = encode_token(payload={"user_id": 1})
        decoded = decode_token(token)
        assert "exp" in decoded
        assert "iat" in decoded

    def test_decode_token_expired_raises_token_expired(self):
        """Decoding an expired token raises TokenExpired."""
        # Create a token that expired 10 seconds ago
        token = encode_token(payload={"user_id": 1}, expires_in=-10)
        with pytest.raises(TokenExpired):
            decode_token(token)

    def test_decode_token_invalid_signature_raises_token_invalid(self):
        """Decoding a token with wrong secret raises TokenInvalid."""
        token = encode_token(payload={"user_id": 1}, secret="correct-secret")
        with pytest.raises(TokenInvalid):
            decode_token(token, secret="wrong-secret")

    def test_decode_token_malformed_raises_token_invalid(self):
        """Decoding a malformed token raises TokenInvalid."""
        with pytest.raises(TokenInvalid):
            decode_token("not-a-valid-jwt-token")

    def test_decode_token_empty_string_raises_token_invalid(self):
        """Decoding an empty string raises TokenInvalid."""
        with pytest.raises(TokenInvalid):
            decode_token("")

    def test_decode_token_with_custom_secret(self):
        """Token encoded and decoded with the same custom secret works."""
        secret = "shared-test-secret"
        token = encode_token(payload={"user_id": 7}, secret=secret)
        decoded = decode_token(token, secret=secret)
        assert decoded["user_id"] == 7

    def test_decode_token_verify_exp_false_allows_expired(self):
        """Setting verify_exp=False decodes expired tokens without error."""
        token = encode_token(payload={"user_id": 1}, expires_in=-10)
        decoded = decode_token(token, verify_exp=False)
        assert decoded["user_id"] == 1

    def test_decode_token_with_explicit_algorithms(self):
        """Specifying algorithms works for decoding."""
        token = encode_token(payload={"user_id": 1})
        decoded = decode_token(token, algorithms=["HS256"])
        assert decoded["user_id"] == 1

    def test_decode_token_defaults_to_allowed_algorithms(self):
        """Default algorithms list matches module-level ALLOWED_ALGORITHMS."""
        # This implicitly tests that the default algorithms work
        token = encode_token(payload={"user_id": 1})
        decoded = decode_token(token)
        assert decoded["user_id"] == 1
        # Verify the constant is as expected
        assert "HS256" in ALLOWED_ALGORITHMS

    def test_decode_token_tampered_payload_raises_token_invalid(self):
        """A token with a tampered payload fails signature verification."""
        token = encode_token(payload={"user_id": 1})
        # Split the JWT and modify the payload portion
        parts = token.split(".")
        assert len(parts) == 3
        # Corrupt the payload by changing a character
        corrupted_payload = parts[1] + "x"
        tampered_token = f"{parts[0]}.{corrupted_payload}.{parts[2]}"
        with pytest.raises(TokenInvalid):
            decode_token(tampered_token)


# =============================================================================
# JWT UTILITIES — decode_token_unverified
# =============================================================================


class TestDecodeTokenUnverified:
    """Tests for decode_token_unverified function."""

    def test_decode_token_unverified_returns_payload(self):
        """Unverified decode returns the original payload."""
        token = encode_token(payload={"user_id": 5, "role": "admin"})
        decoded = decode_token_unverified(token)
        assert decoded["user_id"] == 5
        assert decoded["role"] == "admin"

    def test_decode_token_unverified_ignores_expiry(self):
        """Unverified decode succeeds even for expired tokens."""
        token = encode_token(payload={"user_id": 1}, expires_in=-100)
        decoded = decode_token_unverified(token)
        assert decoded["user_id"] == 1

    def test_decode_token_unverified_ignores_signature(self):
        """Unverified decode succeeds even with wrong secret."""
        token = encode_token(payload={"user_id": 1}, secret="some-secret")
        # Should decode even without knowing the secret
        decoded = decode_token_unverified(token)
        assert decoded["user_id"] == 1

    def test_decode_token_unverified_malformed_raises_token_invalid(self):
        """Unverified decode of a completely malformed string raises TokenInvalid."""
        with pytest.raises(TokenInvalid):
            decode_token_unverified("completely-garbage-input")

    def test_decode_token_unverified_empty_raises_token_invalid(self):
        """Unverified decode of an empty string raises TokenInvalid."""
        with pytest.raises(TokenInvalid):
            decode_token_unverified("")

    def test_decode_token_unverified_includes_standard_claims(self):
        """Unverified decode includes exp and iat claims."""
        token = encode_token(payload={"user_id": 1})
        decoded = decode_token_unverified(token)
        assert "exp" in decoded
        assert "iat" in decoded


# =============================================================================
# JWT UTILITIES — get_token_expiry
# =============================================================================


class TestGetTokenExpiry:
    """Tests for get_token_expiry function."""

    def test_get_token_expiry_returns_datetime(self):
        """Returns a timezone-aware datetime for tokens with exp claim."""
        token = encode_token(payload={"user_id": 1}, expires_in=3600)
        expiry = get_token_expiry(token)
        assert isinstance(expiry, datetime)
        assert expiry.tzinfo is not None

    def test_get_token_expiry_matches_encoded_expiry(self):
        """Returned expiry matches the encoded expiration time."""
        token = encode_token(payload={"user_id": 1}, expires_in=3600)
        expiry = get_token_expiry(token)

        # Expiry should be approximately now + 3600 seconds
        expected = datetime.now(timezone.utc) + timedelta(seconds=3600)
        # Allow 5 seconds tolerance for execution time
        assert abs((expiry - expected).total_seconds()) < 5

    def test_get_token_expiry_returns_utc(self):
        """Returned datetime is in UTC."""
        token = encode_token(payload={"user_id": 1})
        expiry = get_token_expiry(token)
        assert expiry.tzinfo == timezone.utc

    def test_get_token_expiry_no_exp_claim_returns_none(self):
        """Returns None for tokens without an exp claim."""
        # Manually create a token without exp
        payload = {"user_id": 1, "iat": datetime.now(timezone.utc)}
        token = pyjwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        expiry = get_token_expiry(token)
        assert expiry is None

    def test_get_token_expiry_malformed_token_raises_token_invalid(self):
        """Raises TokenInvalid for malformed tokens."""
        with pytest.raises(TokenInvalid):
            get_token_expiry("not-a-token")

    def test_get_token_expiry_expired_token_still_returns_expiry(self):
        """Returns the expiry datetime even for already-expired tokens."""
        token = encode_token(payload={"user_id": 1}, expires_in=-100)
        expiry = get_token_expiry(token)
        assert isinstance(expiry, datetime)
        # The expiry should be in the past
        assert expiry < datetime.now(timezone.utc)


# =============================================================================
# JWT UTILITIES — is_token_expired
# =============================================================================


class TestIsTokenExpired:
    """Tests for is_token_expired function."""

    def test_is_token_expired_false_for_valid_token(self):
        """Returns False for a token that has not yet expired."""
        token = encode_token(payload={"user_id": 1}, expires_in=3600)
        assert is_token_expired(token) is False

    def test_is_token_expired_true_for_expired_token(self):
        """Returns True for a token that has already expired."""
        token = encode_token(payload={"user_id": 1}, expires_in=-10)
        assert is_token_expired(token) is True

    def test_is_token_expired_with_buffer_seconds(self):
        """Buffer makes a soon-to-expire token appear expired."""
        # Token expires in 30 seconds
        token = encode_token(payload={"user_id": 1}, expires_in=30)
        # Without buffer it should not be expired
        assert is_token_expired(token, buffer_seconds=0) is False
        # With a 60-second buffer it should be treated as expired
        assert is_token_expired(token, buffer_seconds=60) is True

    def test_is_token_expired_no_exp_claim_returns_true(self):
        """Returns True for tokens without an exp claim (safety default)."""
        payload = {"user_id": 1, "iat": datetime.now(timezone.utc)}
        token = pyjwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        assert is_token_expired(token) is True

    def test_is_token_expired_zero_buffer_for_far_future(self):
        """Token expiring far in the future is not expired even with zero buffer."""
        token = encode_token(payload={"user_id": 1}, expires_in=86400)  # 24 hours
        assert is_token_expired(token, buffer_seconds=0) is False

    def test_is_token_expired_malformed_token_raises(self):
        """Malformed token raises TokenInvalid (propagated from get_token_expiry)."""
        with pytest.raises(TokenInvalid):
            is_token_expired("garbage-token")


# =============================================================================
# PASSWORD UTILITIES — hash_password
# =============================================================================


class TestHashPassword:
    """Tests for hash_password function."""

    def test_hash_password_returns_non_empty_string(self):
        """hash_password returns a non-empty string."""
        hashed = hash_password("MySecurePass123!")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_differs_from_plaintext(self):
        """Hashed password is not the same as the plaintext."""
        password = "MySecurePass123!"
        hashed = hash_password(password)
        assert hashed != password

    def test_hash_password_different_salts_produce_different_hashes(self):
        """Hashing the same password twice produces different results (due to salt)."""
        password = "MySecurePass123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_hash_password_empty_string(self):
        """Hashing an empty string still returns a hash (Django allows it)."""
        hashed = hash_password("")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_unicode_characters(self):
        """Hashing passwords with unicode characters works."""
        hashed = hash_password("P@ssw0rd_unicorn")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_long_password(self):
        """Very long passwords are hashed without error."""
        long_password = "A" * 1000
        hashed = hash_password(long_password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0


# =============================================================================
# PASSWORD UTILITIES — verify_password
# =============================================================================


class TestVerifyPassword:
    """Tests for verify_password function."""

    def test_verify_password_correct_password_returns_true(self):
        """Correct password returns True."""
        password = "MySecurePass123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_wrong_password_returns_false(self):
        """Incorrect password returns False."""
        hashed = hash_password("MySecurePass123!")
        assert verify_password("WrongPassword!", hashed) is False

    def test_verify_password_empty_password_returns_false(self):
        """Empty password returns False (guard clause)."""
        hashed = hash_password("MySecurePass123!")
        assert verify_password("", hashed) is False

    def test_verify_password_empty_hash_returns_false(self):
        """Empty hash returns False (guard clause)."""
        assert verify_password("MySecurePass123!", "") is False

    def test_verify_password_both_empty_returns_false(self):
        """Both empty password and hash returns False."""
        assert verify_password("", "") is False

    def test_verify_password_none_password_returns_false(self):
        """None password returns False."""
        hashed = hash_password("test")
        assert verify_password(None, hashed) is False

    def test_verify_password_none_hash_returns_false(self):
        """None hash returns False."""
        assert verify_password("test", None) is False

    def test_verify_password_case_sensitive(self):
        """Password verification is case-sensitive."""
        hashed = hash_password("CaseSensitive!")
        assert verify_password("CaseSensitive!", hashed) is True
        assert verify_password("casesensitive!", hashed) is False
        assert verify_password("CASESENSITIVE!", hashed) is False

    def test_verify_password_with_unicode(self):
        """Password verification works with unicode."""
        password = "P@ss_secure_2024"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_with_different_hash(self):
        """Same password, different hash (different salt) both verify."""
        password = "MySecurePass123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


# =============================================================================
# PASSWORD UTILITIES — validate_password_strength
# =============================================================================


class TestValidatePasswordStrength:
    """Tests for validate_password_strength function."""

    def test_validate_strong_password_returns_empty_list(self):
        """A strong password produces no errors."""
        errors = validate_password_strength("X9k$mP2qR#vL")
        assert errors == []

    def test_validate_short_password_returns_errors(self):
        """A password shorter than minimum length produces errors."""
        errors = validate_password_strength("Ab1!")
        assert len(errors) > 0

    def test_validate_common_password_returns_errors(self):
        """A common password like 'password' produces errors."""
        errors = validate_password_strength("password")
        assert len(errors) > 0

    def test_validate_numeric_only_password_returns_errors(self):
        """An all-numeric password produces errors."""
        errors = validate_password_strength("12345678901234")
        assert len(errors) > 0

    def test_validate_returns_list_of_strings(self):
        """Errors are returned as a list of strings."""
        errors = validate_password_strength("bad")
        assert isinstance(errors, list)
        for error in errors:
            assert isinstance(error, str)

    def test_validate_empty_password_returns_errors(self):
        """An empty password produces errors."""
        errors = validate_password_strength("")
        assert len(errors) > 0

    def test_validate_minimum_length_boundary(self):
        """Password exactly at minimum length (8) with good complexity passes."""
        # 8 characters, mixed case, digit, not common
        errors = validate_password_strength("Xk3$mP2q")
        assert errors == []

    def test_validate_with_user_object_similar_attribute(self):
        """Password similar to user attributes produces errors (if validator enabled)."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User(
            email="johndoe@example.com",
            username="johndoe",
        )
        # Password is very similar to the username attribute
        errors = validate_password_strength("johndoe123", user=user)
        # UserAttributeSimilarityValidator should flag this
        assert len(errors) > 0


# =============================================================================
# PASSWORD UTILITIES — is_password_valid
# =============================================================================


class TestIsPasswordValid:
    """Tests for is_password_valid function."""

    def test_is_password_valid_true_for_strong_password(self):
        """Returns True for a password meeting all requirements."""
        assert is_password_valid("X9k$mP2qR#vL") is True

    def test_is_password_valid_false_for_weak_password(self):
        """Returns False for a weak password."""
        assert is_password_valid("123") is False

    def test_is_password_valid_false_for_common_password(self):
        """Returns False for a common password."""
        assert is_password_valid("password") is False

    def test_is_password_valid_false_for_numeric_only(self):
        """Returns False for a purely numeric password."""
        assert is_password_valid("12345678901234") is False

    def test_is_password_valid_false_for_empty(self):
        """Returns False for an empty password."""
        assert is_password_valid("") is False

    def test_is_password_valid_consistent_with_validate_password_strength(self):
        """is_password_valid returns True iff validate_password_strength returns empty list."""
        test_passwords = [
            "X9k$mP2qR#vL",  # strong
            "password",       # common
            "123",            # short
            "12345678901234", # numeric
        ]
        for pwd in test_passwords:
            errors = validate_password_strength(pwd)
            valid = is_password_valid(pwd)
            assert valid == (len(errors) == 0), (
                f"Mismatch for '{pwd}': errors={errors}, valid={valid}"
            )


# =============================================================================
# PASSWORD UTILITIES — generate_temporary_password
# =============================================================================


class TestGenerateTemporaryPassword:
    """Tests for generate_temporary_password function."""

    def test_generate_temporary_password_default_length(self):
        """Default password length is 12."""
        password = generate_temporary_password()
        assert len(password) == 12

    def test_generate_temporary_password_custom_length(self):
        """Custom length is respected when >= 8."""
        password = generate_temporary_password(length=20)
        assert len(password) == 20

    def test_generate_temporary_password_minimum_length_8(self):
        """Length is clamped to minimum of 8 even if smaller is requested."""
        password = generate_temporary_password(length=4)
        assert len(password) == 8

    def test_generate_temporary_password_length_exactly_8(self):
        """Length of exactly 8 is respected."""
        password = generate_temporary_password(length=8)
        assert len(password) == 8

    def test_generate_temporary_password_contains_lowercase(self):
        """Generated password contains at least one lowercase letter."""
        # Run multiple times to reduce flakiness (shuffle is random)
        for _ in range(10):
            password = generate_temporary_password()
            assert any(c in string.ascii_lowercase for c in password), (
                f"No lowercase in: {password}"
            )

    def test_generate_temporary_password_contains_uppercase(self):
        """Generated password contains at least one uppercase letter."""
        for _ in range(10):
            password = generate_temporary_password()
            assert any(c in string.ascii_uppercase for c in password), (
                f"No uppercase in: {password}"
            )

    def test_generate_temporary_password_contains_digit(self):
        """Generated password contains at least one digit."""
        for _ in range(10):
            password = generate_temporary_password()
            assert any(c in string.digits for c in password), (
                f"No digit in: {password}"
            )

    def test_generate_temporary_password_contains_special_char(self):
        """Generated password contains at least one special character."""
        special_chars = "!@#$%^&*"
        for _ in range(10):
            password = generate_temporary_password()
            assert any(c in special_chars for c in password), (
                f"No special char in: {password}"
            )

    def test_generate_temporary_password_unique_outputs(self):
        """Multiple calls produce different passwords (with high probability)."""
        passwords = {generate_temporary_password() for _ in range(20)}
        # With 12-char random passwords, collisions are astronomically unlikely
        assert len(passwords) == 20

    def test_generate_temporary_password_returns_string(self):
        """Returns a string."""
        password = generate_temporary_password()
        assert isinstance(password, str)

    def test_generate_temporary_password_zero_length_uses_minimum(self):
        """Length of 0 is clamped to minimum of 8."""
        password = generate_temporary_password(length=0)
        assert len(password) == 8

    def test_generate_temporary_password_negative_length_uses_minimum(self):
        """Negative length is clamped to minimum of 8."""
        password = generate_temporary_password(length=-5)
        assert len(password) == 8


# =============================================================================
# DATETIME UTILITIES — utc_now
# =============================================================================


class TestUtcNow:
    """Tests for utc_now function."""

    def test_utc_now_returns_datetime(self):
        """Returns a datetime instance."""
        result = utc_now()
        assert isinstance(result, datetime)

    def test_utc_now_is_timezone_aware(self):
        """Returned datetime is timezone-aware."""
        result = utc_now()
        assert result.tzinfo is not None

    def test_utc_now_is_close_to_current_time(self):
        """Returned datetime is approximately the current time."""
        before = datetime.now(timezone.utc)
        result = utc_now()
        after = datetime.now(timezone.utc)
        assert before <= result <= after

    def test_utc_now_successive_calls_non_decreasing(self):
        """Successive calls return non-decreasing values."""
        t1 = utc_now()
        t2 = utc_now()
        assert t2 >= t1


# =============================================================================
# DATETIME UTILITIES — today_utc
# =============================================================================


class TestTodayUtc:
    """Tests for today_utc function."""

    def test_today_utc_returns_date(self):
        """Returns a date instance (not datetime)."""
        result = today_utc()
        assert isinstance(result, date)
        assert not isinstance(result, datetime)

    def test_today_utc_matches_utc_now_date(self):
        """Returns the same date as utc_now().date()."""
        result = today_utc()
        expected = utc_now().date()
        assert result == expected


# =============================================================================
# DATETIME UTILITIES — to_user_timezone
# =============================================================================


class TestToUserTimezone:
    """Tests for to_user_timezone function."""

    def test_to_user_timezone_converts_to_target(self):
        """Converts UTC time to specified timezone."""
        utc_dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = to_user_timezone(utc_dt, "America/New_York")
        # New York is UTC-4 in June (EDT)
        assert result.hour == 8
        assert result.day == 15

    def test_to_user_timezone_default_is_utc(self):
        """Default timezone is UTC (no conversion)."""
        utc_dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = to_user_timezone(utc_dt)
        assert result.hour == 12

    def test_to_user_timezone_invalid_timezone_falls_back_to_utc(self):
        """Invalid timezone string falls back to UTC."""
        utc_dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = to_user_timezone(utc_dt, "Invalid/Timezone")
        assert result.hour == 12

    def test_to_user_timezone_naive_datetime_assumed_utc(self):
        """Naive datetime is made UTC-aware before conversion."""
        naive_dt = datetime(2024, 6, 15, 12, 0, 0)
        result = to_user_timezone(naive_dt, "America/Chicago")
        # Chicago is UTC-5 in June (CDT)
        assert result.hour == 7

    def test_to_user_timezone_preserves_instant(self):
        """Conversion preserves the same point in time."""
        utc_dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = to_user_timezone(utc_dt, "Asia/Tokyo")
        # Converting back to UTC should yield the same time
        back_to_utc = result.astimezone(timezone.utc)
        assert back_to_utc.hour == utc_dt.hour
        assert back_to_utc.minute == utc_dt.minute

    def test_to_user_timezone_various_timezones(self):
        """Conversion works for various well-known timezones."""
        utc_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        timezones_to_test = [
            "Europe/London",
            "Europe/Paris",
            "Asia/Tokyo",
            "Australia/Sydney",
            "America/Los_Angeles",
        ]
        for tz_name in timezones_to_test:
            result = to_user_timezone(utc_dt, tz_name)
            assert result.tzinfo is not None


# =============================================================================
# DATETIME UTILITIES — to_utc
# =============================================================================


class TestToUtc:
    """Tests for to_utc function."""

    def test_to_utc_from_aware_datetime(self):
        """Converts aware datetime from another timezone to UTC."""
        import zoneinfo
        eastern = zoneinfo.ZoneInfo("America/New_York")
        # January 15, 2024 at noon Eastern (EST = UTC-5)
        eastern_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=eastern)
        result = to_utc(eastern_dt)
        assert result.hour == 17  # 12 + 5 = 17 UTC

    def test_to_utc_from_utc_is_idempotent(self):
        """Converting a UTC datetime to UTC changes nothing."""
        utc_dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = to_utc(utc_dt)
        assert result.hour == 12
        assert result.minute == 0

    def test_to_utc_from_naive_datetime(self):
        """Naive datetime is made aware (assumed default tz) then converted to UTC."""
        naive_dt = datetime(2024, 6, 15, 12, 0, 0)
        result = to_utc(naive_dt)
        assert result.tzinfo is not None

    def test_to_utc_result_is_timezone_aware(self):
        """Returned datetime is timezone-aware."""
        dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = to_utc(dt)
        assert result.tzinfo is not None


# =============================================================================
# DATETIME UTILITIES — start_of_day
# =============================================================================


class TestStartOfDay:
    """Tests for start_of_day function."""

    def test_start_of_day_sets_time_to_midnight(self):
        """Sets time to 00:00:00.000000."""
        dt = datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=timezone.utc)
        result = start_of_day(dt)
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0

    def test_start_of_day_preserves_date(self):
        """Date portion is preserved."""
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = start_of_day(dt)
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_start_of_day_preserves_timezone(self):
        """Timezone info is preserved."""
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = start_of_day(dt)
        assert result.tzinfo == timezone.utc

    def test_start_of_day_default_uses_now(self):
        """Without argument, uses current UTC time."""
        result = start_of_day()
        now = utc_now()
        assert result.date() == now.date()
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_start_of_day_already_midnight(self):
        """Already-midnight datetime is unchanged."""
        dt = datetime(2024, 6, 15, 0, 0, 0, 0, tzinfo=timezone.utc)
        result = start_of_day(dt)
        assert result == dt


# =============================================================================
# DATETIME UTILITIES — end_of_day
# =============================================================================


class TestEndOfDay:
    """Tests for end_of_day function."""

    def test_end_of_day_sets_time_to_end(self):
        """Sets time to 23:59:59.999999."""
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = end_of_day(dt)
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59
        assert result.microsecond == 999999

    def test_end_of_day_preserves_date(self):
        """Date portion is preserved."""
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = end_of_day(dt)
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_end_of_day_preserves_timezone(self):
        """Timezone info is preserved."""
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = end_of_day(dt)
        assert result.tzinfo == timezone.utc

    def test_end_of_day_default_uses_now(self):
        """Without argument, uses current UTC time."""
        result = end_of_day()
        now = utc_now()
        assert result.date() == now.date()
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59
        assert result.microsecond == 999999

    def test_end_of_day_already_end_of_day(self):
        """Already end-of-day datetime is unchanged."""
        dt = datetime(2024, 6, 15, 23, 59, 59, 999999, tzinfo=timezone.utc)
        result = end_of_day(dt)
        assert result == dt

    def test_start_and_end_of_day_same_date(self):
        """start_of_day and end_of_day for the same input share the same date."""
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        assert start_of_day(dt).date() == end_of_day(dt).date()

    def test_start_of_day_before_end_of_day(self):
        """start_of_day is always before end_of_day for the same date."""
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        assert start_of_day(dt) < end_of_day(dt)


# =============================================================================
# DATETIME UTILITIES — start_of_week
# =============================================================================


class TestStartOfWeek:
    """Tests for start_of_week function."""

    def test_start_of_week_returns_monday(self):
        """Returns the Monday of the given date's week."""
        # Wednesday June 19, 2024
        dt = datetime(2024, 6, 19, 14, 30, 0, tzinfo=timezone.utc)
        result = start_of_week(dt)
        # Monday is June 17
        assert result.weekday() == 0  # Monday
        assert result.day == 17

    def test_start_of_week_monday_returns_same_date(self):
        """If the date is already Monday, returns same date at midnight."""
        # Monday June 17, 2024
        dt = datetime(2024, 6, 17, 14, 30, 0, tzinfo=timezone.utc)
        result = start_of_week(dt)
        assert result.day == 17
        assert result.hour == 0
        assert result.minute == 0

    def test_start_of_week_sunday_returns_previous_monday(self):
        """Sunday returns the previous Monday."""
        # Sunday June 23, 2024
        dt = datetime(2024, 6, 23, 14, 30, 0, tzinfo=timezone.utc)
        result = start_of_week(dt)
        assert result.weekday() == 0
        assert result.day == 17

    def test_start_of_week_time_is_midnight(self):
        """Time is set to 00:00:00."""
        dt = datetime(2024, 6, 19, 14, 30, 45, 123456, tzinfo=timezone.utc)
        result = start_of_week(dt)
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0

    def test_start_of_week_default_uses_now(self):
        """Without argument, uses current UTC time."""
        result = start_of_week()
        assert result.weekday() == 0  # Monday
        assert result.hour == 0

    def test_start_of_week_saturday_returns_previous_monday(self):
        """Saturday returns the previous Monday."""
        # Saturday June 22, 2024
        dt = datetime(2024, 6, 22, 10, 0, 0, tzinfo=timezone.utc)
        result = start_of_week(dt)
        assert result.weekday() == 0
        assert result.day == 17


# =============================================================================
# DATETIME UTILITIES — start_of_month
# =============================================================================


class TestStartOfMonth:
    """Tests for start_of_month function."""

    def test_start_of_month_returns_first_day(self):
        """Returns the first day of the month."""
        dt = datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
        result = start_of_month(dt)
        assert result.day == 1

    def test_start_of_month_preserves_year_and_month(self):
        """Year and month are preserved."""
        dt = datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
        result = start_of_month(dt)
        assert result.year == 2024
        assert result.month == 6

    def test_start_of_month_time_is_midnight(self):
        """Time is set to 00:00:00.000000."""
        dt = datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=timezone.utc)
        result = start_of_month(dt)
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0

    def test_start_of_month_already_first_day(self):
        """First day at midnight returns effectively the same date."""
        dt = datetime(2024, 6, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
        result = start_of_month(dt)
        assert result == dt

    def test_start_of_month_last_day_of_month(self):
        """Last day of month returns first day of same month."""
        dt = datetime(2024, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
        result = start_of_month(dt)
        assert result.day == 1
        assert result.month == 6

    def test_start_of_month_default_uses_now(self):
        """Without argument, uses current UTC time."""
        result = start_of_month()
        now = utc_now()
        assert result.year == now.year
        assert result.month == now.month
        assert result.day == 1

    def test_start_of_month_february_leap_year(self):
        """Works correctly for February in a leap year."""
        dt = datetime(2024, 2, 29, 12, 0, 0, tzinfo=timezone.utc)
        result = start_of_month(dt)
        assert result.day == 1
        assert result.month == 2


# =============================================================================
# DATETIME UTILITIES — days_ago
# =============================================================================


class TestDaysAgo:
    """Tests for days_ago function."""

    def test_days_ago_returns_past_datetime(self):
        """Returns a datetime in the past."""
        result = days_ago(5)
        now = utc_now()
        assert result < now

    def test_days_ago_correct_offset(self):
        """Offset is approximately correct."""
        before = utc_now()
        result = days_ago(3)
        after = utc_now()
        expected_min = before - timedelta(days=3)
        expected_max = after - timedelta(days=3)
        assert expected_min <= result <= expected_max

    def test_days_ago_zero(self):
        """Zero days ago is approximately now."""
        before = utc_now()
        result = days_ago(0)
        after = utc_now()
        assert before <= result <= after

    def test_days_ago_is_timezone_aware(self):
        """Result is timezone-aware."""
        result = days_ago(1)
        assert result.tzinfo is not None


# =============================================================================
# DATETIME UTILITIES — hours_ago
# =============================================================================


class TestHoursAgo:
    """Tests for hours_ago function."""

    def test_hours_ago_returns_past_datetime(self):
        """Returns a datetime in the past."""
        result = hours_ago(2)
        now = utc_now()
        assert result < now

    def test_hours_ago_correct_offset(self):
        """Offset is approximately correct."""
        before = utc_now()
        result = hours_ago(6)
        after = utc_now()
        expected_min = before - timedelta(hours=6)
        expected_max = after - timedelta(hours=6)
        assert expected_min <= result <= expected_max

    def test_hours_ago_zero(self):
        """Zero hours ago is approximately now."""
        before = utc_now()
        result = hours_ago(0)
        after = utc_now()
        assert before <= result <= after

    def test_hours_ago_is_timezone_aware(self):
        """Result is timezone-aware."""
        result = hours_ago(1)
        assert result.tzinfo is not None


# =============================================================================
# DATETIME UTILITIES — minutes_ago
# =============================================================================


class TestMinutesAgo:
    """Tests for minutes_ago function."""

    def test_minutes_ago_returns_past_datetime(self):
        """Returns a datetime in the past."""
        result = minutes_ago(30)
        now = utc_now()
        assert result < now

    def test_minutes_ago_correct_offset(self):
        """Offset is approximately correct."""
        before = utc_now()
        result = minutes_ago(45)
        after = utc_now()
        expected_min = before - timedelta(minutes=45)
        expected_max = after - timedelta(minutes=45)
        assert expected_min <= result <= expected_max

    def test_minutes_ago_zero(self):
        """Zero minutes ago is approximately now."""
        before = utc_now()
        result = minutes_ago(0)
        after = utc_now()
        assert before <= result <= after

    def test_minutes_ago_is_timezone_aware(self):
        """Result is timezone-aware."""
        result = minutes_ago(10)
        assert result.tzinfo is not None


# =============================================================================
# DATETIME UTILITIES — days_from_now
# =============================================================================


class TestDaysFromNow:
    """Tests for days_from_now function."""

    def test_days_from_now_returns_future_datetime(self):
        """Returns a datetime in the future."""
        result = days_from_now(5)
        now = utc_now()
        assert result > now

    def test_days_from_now_correct_offset(self):
        """Offset is approximately correct."""
        before = utc_now()
        result = days_from_now(7)
        after = utc_now()
        expected_min = before + timedelta(days=7)
        expected_max = after + timedelta(days=7)
        assert expected_min <= result <= expected_max

    def test_days_from_now_zero(self):
        """Zero days from now is approximately now."""
        before = utc_now()
        result = days_from_now(0)
        after = utc_now()
        assert before <= result <= after

    def test_days_from_now_is_timezone_aware(self):
        """Result is timezone-aware."""
        result = days_from_now(1)
        assert result.tzinfo is not None


# =============================================================================
# DATETIME UTILITIES — format_datetime
# =============================================================================


class TestFormatDatetime:
    """Tests for format_datetime function."""

    def test_format_datetime_default_format(self):
        """Default format is '%Y-%m-%d %H:%M:%S'."""
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = format_datetime(dt)
        assert result == "2024-06-15 14:30:45"

    def test_format_datetime_custom_format(self):
        """Custom format string is respected."""
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = format_datetime(dt, format_string="%d/%m/%Y")
        assert result == "15/06/2024"

    def test_format_datetime_date_only(self):
        """Can format date-only."""
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = format_datetime(dt, format_string="%Y-%m-%d")
        assert result == "2024-06-15"

    def test_format_datetime_time_only(self):
        """Can format time-only."""
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = format_datetime(dt, format_string="%H:%M:%S")
        assert result == "14:30:45"

    def test_format_datetime_returns_string(self):
        """Returns a string."""
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = format_datetime(dt)
        assert isinstance(result, str)


# =============================================================================
# DATETIME UTILITIES — format_iso
# =============================================================================


class TestFormatIso:
    """Tests for format_iso function."""

    def test_format_iso_utc_datetime(self):
        """Formats UTC datetime as ISO 8601 with 'Z' suffix."""
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = format_iso(dt)
        assert result == "2024-06-15T14:30:45Z"

    def test_format_iso_non_utc_converted_to_utc(self):
        """Non-UTC datetime is converted to UTC before formatting."""
        import zoneinfo
        eastern = zoneinfo.ZoneInfo("America/New_York")
        # January 15, 2024 noon EST = 5pm UTC
        dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=eastern)
        result = format_iso(dt)
        assert result == "2024-01-15T17:00:00Z"

    def test_format_iso_returns_string(self):
        """Returns a string."""
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = format_iso(dt)
        assert isinstance(result, str)

    def test_format_iso_midnight(self):
        """Midnight is formatted correctly."""
        dt = datetime(2024, 6, 15, 0, 0, 0, tzinfo=timezone.utc)
        result = format_iso(dt)
        assert result == "2024-06-15T00:00:00Z"


# =============================================================================
# DATETIME UTILITIES — parse_iso
# =============================================================================


class TestParseIso:
    """Tests for parse_iso function."""

    def test_parse_iso_with_z_suffix(self):
        """Parses ISO string with 'Z' suffix."""
        result = parse_iso("2024-06-15T14:30:45Z")
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45

    def test_parse_iso_with_offset(self):
        """Parses ISO string with explicit UTC offset."""
        result = parse_iso("2024-06-15T14:30:45+00:00")
        assert result.year == 2024
        assert result.hour == 14

    def test_parse_iso_with_non_utc_offset(self):
        """Parses ISO string with non-UTC offset."""
        result = parse_iso("2024-06-15T14:30:45+05:00")
        assert result.hour == 14
        assert result.tzinfo is not None

    def test_parse_iso_returns_timezone_aware(self):
        """Parsed result is timezone-aware."""
        result = parse_iso("2024-06-15T14:30:45Z")
        assert result.tzinfo is not None

    def test_parse_iso_invalid_string_raises_value_error(self):
        """Invalid ISO string raises ValueError."""
        with pytest.raises(ValueError):
            parse_iso("not-a-date")

    def test_parse_iso_roundtrip_with_format_iso(self):
        """parse_iso reverses format_iso."""
        original = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        iso_str = format_iso(original)
        parsed = parse_iso(iso_str)
        assert parsed.year == original.year
        assert parsed.month == original.month
        assert parsed.day == original.day
        assert parsed.hour == original.hour
        assert parsed.minute == original.minute
        assert parsed.second == original.second

    def test_parse_iso_date_only_string(self):
        """Parses date-only ISO string (no time component)."""
        result = parse_iso("2024-06-15")
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15


# =============================================================================
# DATETIME UTILITIES — time_until
# =============================================================================


class TestTimeUntil:
    """Tests for time_until function."""

    def test_time_until_future_is_positive(self):
        """Time until a future datetime is a positive timedelta."""
        future = utc_now() + timedelta(hours=2)
        result = time_until(future)
        assert result.total_seconds() > 0

    def test_time_until_past_is_negative(self):
        """Time until a past datetime is a negative timedelta."""
        past = utc_now() - timedelta(hours=2)
        result = time_until(past)
        assert result.total_seconds() < 0

    def test_time_until_returns_timedelta(self):
        """Returns a timedelta instance."""
        future = utc_now() + timedelta(hours=1)
        result = time_until(future)
        assert isinstance(result, timedelta)

    def test_time_until_approximately_correct(self):
        """Returned timedelta is approximately correct."""
        future = utc_now() + timedelta(hours=3)
        result = time_until(future)
        # Should be close to 3 hours (within a few seconds)
        assert abs(result.total_seconds() - 3 * 3600) < 5


# =============================================================================
# DATETIME UTILITIES — time_since
# =============================================================================


class TestTimeSince:
    """Tests for time_since function."""

    def test_time_since_past_is_positive(self):
        """Time since a past datetime is a positive timedelta."""
        past = utc_now() - timedelta(hours=2)
        result = time_since(past)
        assert result.total_seconds() > 0

    def test_time_since_future_is_negative(self):
        """Time since a future datetime is a negative timedelta."""
        future = utc_now() + timedelta(hours=2)
        result = time_since(future)
        assert result.total_seconds() < 0

    def test_time_since_returns_timedelta(self):
        """Returns a timedelta instance."""
        past = utc_now() - timedelta(hours=1)
        result = time_since(past)
        assert isinstance(result, timedelta)

    def test_time_since_approximately_correct(self):
        """Returned timedelta is approximately correct."""
        past = utc_now() - timedelta(hours=5)
        result = time_since(past)
        assert abs(result.total_seconds() - 5 * 3600) < 5


# =============================================================================
# DATETIME UTILITIES — is_past
# =============================================================================


class TestIsPast:
    """Tests for is_past function."""

    def test_is_past_for_past_datetime(self):
        """Returns True for a datetime in the past."""
        past = utc_now() - timedelta(hours=1)
        assert is_past(past) is True

    def test_is_past_for_future_datetime(self):
        """Returns False for a datetime in the future."""
        future = utc_now() + timedelta(hours=1)
        assert is_past(future) is False

    def test_is_past_for_far_past(self):
        """Returns True for a datetime far in the past."""
        far_past = datetime(2000, 1, 1, tzinfo=timezone.utc)
        assert is_past(far_past) is True

    def test_is_past_for_far_future(self):
        """Returns False for a datetime far in the future."""
        far_future = datetime(2099, 12, 31, tzinfo=timezone.utc)
        assert is_past(far_future) is False


# =============================================================================
# DATETIME UTILITIES — is_future
# =============================================================================


class TestIsFuture:
    """Tests for is_future function."""

    def test_is_future_for_future_datetime(self):
        """Returns True for a datetime in the future."""
        future = utc_now() + timedelta(hours=1)
        assert is_future(future) is True

    def test_is_future_for_past_datetime(self):
        """Returns False for a datetime in the past."""
        past = utc_now() - timedelta(hours=1)
        assert is_future(past) is False

    def test_is_future_for_far_future(self):
        """Returns True for a datetime far in the future."""
        far_future = datetime(2099, 12, 31, tzinfo=timezone.utc)
        assert is_future(far_future) is True

    def test_is_future_for_far_past(self):
        """Returns False for a datetime far in the past."""
        far_past = datetime(2000, 1, 1, tzinfo=timezone.utc)
        assert is_future(far_past) is False

    def test_is_past_and_is_future_are_complementary(self):
        """For datetimes sufficiently far from now, is_past and is_future are complementary."""
        past = utc_now() - timedelta(hours=1)
        future = utc_now() + timedelta(hours=1)
        assert is_past(past) is True
        assert is_future(past) is False
        assert is_past(future) is False
        assert is_future(future) is True


# =============================================================================
# CROSS-MODULE INTEGRATION TESTS
# =============================================================================


class TestJwtEncodeDecodeRoundtrip:
    """Integration tests for JWT encode/decode roundtrip."""

    def test_encode_then_decode_preserves_payload(self):
        """Encoding then decoding preserves all payload claims."""
        payload = {
            "user_id": 42,
            "type": "access",
            "org_id": 7,
        }
        token = encode_token(payload=payload, expires_in=3600)
        decoded = decode_token(token)
        assert decoded["user_id"] == 42
        assert decoded["type"] == "access"
        assert decoded["org_id"] == 7

    def test_encode_decode_with_matching_custom_secret(self):
        """Custom secret works for both encode and decode."""
        secret = "my-shared-service-secret"
        token = encode_token(
            payload={"service": "billing"},
            secret=secret,
        )
        decoded = decode_token(token, secret=secret)
        assert decoded["service"] == "billing"

    def test_expired_token_can_be_inspected_unverified(self):
        """Expired token can still be inspected via decode_token_unverified."""
        token = encode_token(
            payload={"user_id": 99, "type": "refresh"},
            expires_in=-60,
        )
        # Verified decode should fail
        with pytest.raises(TokenExpired):
            decode_token(token)
        # Unverified decode should succeed
        decoded = decode_token_unverified(token)
        assert decoded["user_id"] == 99
        assert decoded["type"] == "refresh"

    def test_is_token_expired_matches_decode_behavior(self):
        """is_token_expired True correlates with decode_token raising TokenExpired."""
        expired_token = encode_token(payload={"user_id": 1}, expires_in=-10)
        valid_token = encode_token(payload={"user_id": 1}, expires_in=3600)

        assert is_token_expired(expired_token) is True
        with pytest.raises(TokenExpired):
            decode_token(expired_token)

        assert is_token_expired(valid_token) is False
        decoded = decode_token(valid_token)
        assert decoded["user_id"] == 1


class TestPasswordHashVerifyRoundtrip:
    """Integration tests for password hash/verify roundtrip."""

    def test_hash_then_verify_correct_password(self):
        """Hashed password can be verified with the correct plaintext."""
        password = "Str0ng#Pass!2024"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_hash_then_verify_wrong_password(self):
        """Hashed password rejects incorrect plaintext."""
        hashed = hash_password("Str0ng#Pass!2024")
        assert verify_password("DifferentPass!2024", hashed) is False

    def test_generated_password_passes_validation(self):
        """Generated temporary passwords pass strength validation."""
        for _ in range(10):
            password = generate_temporary_password(length=12)
            # Generated passwords should be strong enough to pass validation
            # (they have mixed case, digits, and special chars)
            valid = is_password_valid(password)
            if not valid:
                errors = validate_password_strength(password)
                # The only acceptable failure would be CommonPasswordValidator
                # (astronomically unlikely but theoretically possible)
                for error in errors:
                    assert "common" in error.lower() or "similar" in error.lower(), (
                        f"Generated password '{password}' failed unexpected validation: {errors}"
                    )

    def test_generated_password_can_be_hashed_and_verified(self):
        """Generated temporary password can be hashed and later verified."""
        password = generate_temporary_password()
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True


class TestDatetimeConsistency:
    """Tests for consistency between datetime utility functions."""

    def test_days_ago_and_days_from_now_symmetric(self):
        """days_ago(n) and days_from_now(n) are approximately 2*n days apart."""
        past = days_ago(5)
        future = days_from_now(5)
        diff = (future - past).total_seconds()
        expected = 10 * 86400  # 10 days in seconds
        assert abs(diff - expected) < 10  # within 10 seconds tolerance

    def test_start_of_day_lte_end_of_day(self):
        """start_of_day is always before or equal to end_of_day."""
        for day_offset in range(7):
            dt = utc_now() - timedelta(days=day_offset)
            assert start_of_day(dt) <= end_of_day(dt)

    def test_start_of_week_is_start_of_day(self):
        """start_of_week returns a midnight datetime."""
        result = start_of_week()
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0

    def test_start_of_month_is_start_of_day(self):
        """start_of_month returns a midnight datetime."""
        result = start_of_month()
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0

    def test_format_iso_and_parse_iso_roundtrip(self):
        """format_iso then parse_iso preserves the datetime."""
        original = utc_now().replace(microsecond=0)  # ISO format drops microseconds
        iso_str = format_iso(original)
        parsed = parse_iso(iso_str)
        # Compare as UTC timestamps
        original_utc = to_utc(original)
        parsed_utc = to_utc(parsed)
        assert abs((original_utc - parsed_utc).total_seconds()) < 1

    def test_to_utc_then_to_user_timezone_roundtrip(self):
        """Converting to UTC and back to original timezone preserves the instant."""
        import zoneinfo
        tokyo = zoneinfo.ZoneInfo("Asia/Tokyo")
        original = datetime(2024, 6, 15, 21, 0, 0, tzinfo=tokyo)
        utc_dt = to_utc(original)
        back = to_user_timezone(utc_dt, "Asia/Tokyo")
        assert back.hour == original.hour
        assert back.minute == original.minute
