# apps/organization/platform/selectors.py
"""
Platform Selectors - Read-only queries for platform data.
"""

from apps.core.exceptions import NotFound
from apps.organization.platform.models import PlatformAccount, PlatformProfile


class PlatformAccountSelector:
    """Read-only queries for PlatformAccount."""

    @staticmethod
    def get() -> PlatformAccount:
        """
        Get the singleton platform account.

        Returns:
            PlatformAccount: The single platform account instance.

        Raises:
            NotFound: If platform account doesn't exist.
        """
        try:
            return PlatformAccount.objects.select_related("profile").get()
        except PlatformAccount.DoesNotExist:
            raise NotFound(
                message="Platform account not configured",
                resource="PlatformAccount",
            )

    @staticmethod
    def exists() -> bool:
        """Check if platform account exists."""
        return PlatformAccount.objects.exists()

    @staticmethod
    def is_configured() -> bool:
        """Check if platform is configured."""
        try:
            platform = PlatformAccount.objects.only("is_configured").get()
            return platform.is_configured
        except PlatformAccount.DoesNotExist:
            return False


class PlatformProfileSelector:
    """Read-only queries for PlatformProfile."""

    @staticmethod
    def get() -> PlatformProfile:
        """
        Get the platform profile.

        Returns:
            PlatformProfile: The platform profile instance.

        Raises:
            NotFound: If platform profile doesn't exist.
        """
        try:
            return PlatformProfile.objects.select_related("platform").get()
        except PlatformProfile.DoesNotExist:
            raise NotFound(
                message="Platform profile not found",
                resource="PlatformProfile",
            )
