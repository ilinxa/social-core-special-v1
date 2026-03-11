"""
Auth App
========
Authentication system for JWT-based authentication, session management,
email verification, password reset, and OAuth integration.

Responsibilities:
    - JWT token issuance and validation
    - Refresh token rotation
    - Device session management
    - Email verification flow
    - Password reset flow
    - OAuth (Google, Apple) integration
    - WebSocket authentication

Dependency Direction:
    Auth → Users (for user queries/mutations)
    Auth → Notifications (for sending verification emails)
    Auth NEVER → Email (uses Notifications for all communication)

Key Components:
    - AuthService: Login, logout, token management
    - VerificationService: Email verification
    - PasswordService: Password reset
    - OAuthService: OAuth provider integration
    - JWTAuthentication: DRF authentication class
    - JTIBlacklist: Immediate token revocation

Usage:
    from apps.auth.services import AuthService
    from apps.auth.authentication import JWTAuthentication

    # Login
    user, tokens, session = AuthService.login(
        email='user@example.com',
        password='password',
        device_info=device_info
    )

    # Protected views use JWTAuthentication automatically via settings
"""

default_app_config = 'apps.auth.apps.AuthConfig'
