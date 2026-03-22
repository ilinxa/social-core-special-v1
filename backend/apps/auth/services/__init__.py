"""
Auth Services
=============
Service layer for authentication operations.

Services:
    - AuthService: Core login/logout/token management
    - VerificationService: Email verification
    - PasswordService: Password reset and change
    - OAuthService: OAuth state management and processing
"""

from apps.auth.services.auth_service import AuthService, DeviceInfo, TokenPair
from apps.auth.services.password_service import PasswordService
from apps.auth.services.verification_service import VerificationService

__all__ = [
    "AuthService",
    "DeviceInfo",
    "TokenPair",
    "VerificationService",
    "PasswordService",
]
