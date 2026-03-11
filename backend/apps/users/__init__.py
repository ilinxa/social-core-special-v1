"""
Users App
=========
Core user identity and profile management.

Provides:
    - Custom User model (email-based authentication)
    - UserProfile model (extended user data)
    - UserService for all write operations
    - UserSelector for all read operations

Usage:
    from apps.users.models import User, UserProfile
    from apps.users.services import UserService
    from apps.users.selectors import UserSelector
"""

default_app_config = 'apps.users.apps.UsersConfig'
