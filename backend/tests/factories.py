# tests/factories.py
"""
Factory Boy factories for generating test data.

All user-related factories are defined in apps/users/tests/factories.py
(single source of truth). This file re-exports them for convenience.

Usage:
    from tests.factories import UserFactory, AdminFactory
"""

from apps.users.tests.factories import (  # noqa: F401
    UserFactory,
    VerifiedUserFactory,
    StaffUserFactory,
    SuperuserFactory as AdminFactory,
)
