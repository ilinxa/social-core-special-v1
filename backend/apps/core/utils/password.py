"""
Password Utilities
==================
Secure password hashing and validation utilities.

Uses Django's built-in password hashing with Argon2 (configured in PASSWORD_HASHERS).
This module provides a cleaner interface and additional validation helpers.

Security Notes:
    - Never store plaintext passwords
    - Use constant-time comparison to prevent timing attacks (Django handles this)
    - Validate password strength before hashing
    - Log failed attempts but NOT the passwords themselves

Configuration:
    Password validators are configured in settings.AUTH_PASSWORD_VALIDATORS.
    This module uses those validators for strength checking.

Usage:
    from apps.core.utils.password import hash_password, verify_password

    # Hash a password for storage
    hashed = hash_password("user_password")

    # Verify a password
    if verify_password("user_password", hashed):
        # Password matches
        pass

    # Validate password strength
    errors = validate_password_strength("weak")
    if errors:
        # Password too weak
        pass
"""

from typing import List

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

# =============================================================================
# PASSWORD HASHING
# =============================================================================


def hash_password(password: str) -> str:
    """
    Hash a password for secure storage.

    Uses Django's make_password which:
        - Uses the first hasher in PASSWORD_HASHERS (Argon2)
        - Includes automatic salting
        - Produces a string safe for database storage

    Args:
        password: Plaintext password to hash

    Returns:
        Hashed password string (includes algorithm, salt, and hash)

    Example:
        user.password_hash = hash_password("secure_password_123")
        user.save()
    """
    return make_password(password)


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against a stored hash.

    Uses Django's check_password which:
        - Performs constant-time comparison (prevents timing attacks)
        - Handles algorithm detection from hash string
        - Returns False for None/empty passwords

    Args:
        password: Plaintext password to verify
        hashed: Previously hashed password from storage

    Returns:
        True if password matches, False otherwise

    Example:
        if verify_password(request.data["password"], user.password_hash):
            # Password correct
            pass
        else:
            raise InvalidCredentials()
    """
    if not password or not hashed:
        return False
    return check_password(password, hashed)


# =============================================================================
# PASSWORD VALIDATION
# =============================================================================


def validate_password_strength(password: str, user=None) -> List[str]:
    """
    Validate password against strength requirements.

    Uses validators configured in settings.AUTH_PASSWORD_VALIDATORS:
        - UserAttributeSimilarityValidator: Not similar to user info
        - MinimumLengthValidator: At least N characters
        - CommonPasswordValidator: Not a common password
        - NumericPasswordValidator: Not entirely numeric

    Args:
        password: Password to validate
        user: Optional user object (for similarity check)

    Returns:
        List of error messages (empty if valid)

    Example:
        errors = validate_password_strength("password123")
        if errors:
            raise ValidationError(
                message="Password does not meet requirements",
                field="password",
                details={"errors": errors}
            )
    """
    try:
        validate_password(password, user=user)
        return []
    except DjangoValidationError as e:
        return list(e.messages)


def is_password_valid(password: str, user=None) -> bool:
    """
    Check if password meets strength requirements.

    Convenience function when you just need a boolean.

    Args:
        password: Password to validate
        user: Optional user object (for similarity check)

    Returns:
        True if password is valid, False otherwise
    """
    return len(validate_password_strength(password, user)) == 0


# =============================================================================
# PASSWORD REQUIREMENTS INFO
# =============================================================================


def get_password_requirements() -> List[str]:
    """
    Get human-readable password requirements.

    Returns the requirements configured in settings for display to users.
    Useful for registration forms and password change pages.

    Returns:
        List of requirement descriptions

    Example:
        requirements = get_password_requirements()
        # ["At least 8 characters", "Not a common password", ...]
    """
    from django.contrib.auth.password_validation import get_default_password_validators

    requirements = []

    for validator in get_default_password_validators():
        # Try to get help text from validator
        if hasattr(validator, "get_help_text"):
            requirements.append(validator.get_help_text())

    return requirements


# =============================================================================
# PASSWORD GENERATION (for temporary passwords)
# =============================================================================


def generate_temporary_password(length: int = 12) -> str:
    """
    Generate a secure temporary password.

    Use for:
        - Password reset tokens (though random tokens are often better)
        - Temporary passwords for new accounts
        - Admin-created user accounts

    Args:
        length: Password length (default: 12, minimum: 8)

    Returns:
        Random password string

    Note:
        Generated passwords should be immediately sent to user
        and never logged or stored in plaintext.
    """
    import secrets
    import string

    if length < 8:
        length = 8

    # Character set: letters, digits, and some punctuation
    # Excludes ambiguous characters (0, O, l, 1, I)
    alphabet = "abcdefghjkmnpqrstuvwxyz" "ABCDEFGHJKMNPQRSTUVWXYZ" "23456789" "!@#$%^&*"

    # Ensure at least one of each type
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]

    # Fill rest with random characters
    password += [secrets.choice(alphabet) for _ in range(length - 4)]

    # Shuffle to randomize position of required characters
    secrets.SystemRandom().shuffle(password)

    return "".join(password)
