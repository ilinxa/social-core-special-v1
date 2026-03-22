# apps/network/serializers.py
"""
Network Serializers — Input/output serializers for follow and connection endpoints.
"""

from rest_framework import serializers

from apps.core.observability import get_logger
from apps.network.models import FolloweeType

logger = get_logger(__name__)


# =============================================================================
# INPUT SERIALIZERS
# =============================================================================


class FollowCreateInput(serializers.Serializer):
    followee_type = serializers.ChoiceField(choices=FolloweeType.choices)
    followee_id = serializers.UUIDField()


class UserConnectionRequestInput(serializers.Serializer):
    target_user_id = serializers.UUIDField()
    note = serializers.CharField(max_length=500, required=False, default="")


class BusinessConnectionRequestInput(serializers.Serializer):
    target_account_type = serializers.CharField(max_length=20)
    target_account_id = serializers.UUIDField()
    note = serializers.CharField(max_length=500, required=False, default="")


# =============================================================================
# EMBEDDED USER SERIALIZER (slim)
# =============================================================================


class NetworkUserOutput(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    display_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    def get_display_name(self, obj):
        return getattr(obj, "display_name", "") or obj.username

    def get_avatar_url(self, obj):
        return getattr(obj, "avatar_url", None) or ""


# =============================================================================
# HELPERS — resolve names/slugs for polymorphic followee/account references
# =============================================================================


def _resolve_followee_name(followee_type, followee_id):
    """Resolve the display name for a followee (business or platform)."""
    try:
        if followee_type == "business":
            from apps.organization.business.models import BusinessAccount

            biz = (
                BusinessAccount.objects.select_related("profile")
                .filter(id=followee_id)
                .first()
            )
            if biz:
                return getattr(biz.profile, "display_name", "") or biz.legal_name
            return ""
        elif followee_type == "platform":
            from apps.organization.platform.models import PlatformAccount

            plat = (
                PlatformAccount.objects.select_related("profile")
                .filter(id=followee_id)
                .first()
            )
            if plat:
                return getattr(plat.profile, "name", "") or "Platform"
            return ""
    except Exception:
        logger.warning(
            "network.serializer.resolve_followee_name_failed",
            followee_type=followee_type,
            followee_id=str(followee_id),
        )
    return ""


def _resolve_followee_slug(followee_type, followee_id):
    """Resolve the slug for a followee (business only; platform has no slug)."""
    try:
        if followee_type == "business":
            from apps.organization.business.models import BusinessAccount

            biz = BusinessAccount.objects.filter(id=followee_id).only("slug").first()
            return biz.slug if biz else ""
    except Exception:
        logger.warning(
            "network.serializer.resolve_followee_slug_failed",
            followee_type=followee_type,
            followee_id=str(followee_id),
        )
    return ""


def _resolve_account_name(account_type, account_id):
    """Resolve account display name for connections."""
    try:
        if account_type == "business":
            from apps.organization.business.models import BusinessAccount

            biz = (
                BusinessAccount.objects.select_related("profile")
                .filter(id=account_id)
                .first()
            )
            if biz:
                return getattr(biz.profile, "display_name", "") or biz.legal_name
            return ""
        elif account_type == "platform":
            from apps.organization.platform.models import PlatformAccount

            plat = (
                PlatformAccount.objects.select_related("profile")
                .filter(id=account_id)
                .first()
            )
            if plat:
                return getattr(plat.profile, "name", "") or "Platform"
            return ""
    except Exception:
        logger.warning(
            "network.serializer.resolve_account_name_failed",
            account_type=account_type,
            account_id=str(account_id),
        )
    return ""


# =============================================================================
# OUTPUT SERIALIZERS
# =============================================================================


class FollowOutput(serializers.Serializer):
    id = serializers.UUIDField()
    follower = NetworkUserOutput()
    followee_type = serializers.CharField()
    followee_id = serializers.UUIDField()
    followee_name = serializers.SerializerMethodField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()

    def get_followee_name(self, obj):
        accounts = self.context.get("followee_accounts")
        if accounts is not None:
            account = accounts.get(obj.followee_id)
            if account:
                profile = getattr(account, "profile", None)
                return (
                    getattr(profile, "display_name", "")
                    or getattr(account, "legal_name", "")
                    or ""
                )
            return ""
        return _resolve_followee_name(obj.followee_type, obj.followee_id)


class FollowingOutput(serializers.Serializer):
    id = serializers.UUIDField()
    followee_type = serializers.CharField()
    followee_id = serializers.UUIDField()
    followee_name = serializers.SerializerMethodField()
    followee_slug = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    def get_followee_name(self, obj):
        accounts = self.context.get("followee_accounts")
        if accounts is not None:
            account = accounts.get(obj.followee_id)
            if account:
                profile = getattr(account, "profile", None)
                return (
                    getattr(profile, "display_name", "")
                    or getattr(account, "legal_name", "")
                    or ""
                )
            return ""
        return _resolve_followee_name(obj.followee_type, obj.followee_id)

    def get_followee_slug(self, obj):
        accounts = self.context.get("followee_accounts")
        if accounts is not None:
            account = accounts.get(obj.followee_id)
            return getattr(account, "slug", "") if account else ""
        return _resolve_followee_slug(obj.followee_type, obj.followee_id)


class UserConnectionOutput(serializers.Serializer):
    id = serializers.UUIDField()
    other_user = serializers.SerializerMethodField()
    note = serializers.CharField()
    status = serializers.CharField()
    connected_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()

    def get_other_user(self, obj):
        request = self.context.get("request")
        if not request or not request.user:
            return None
        viewer_id = request.user.id
        other = obj.user_b if obj.user_a_id == viewer_id else obj.user_a
        return NetworkUserOutput(other).data


class AccountConnectionOutput(serializers.Serializer):
    id = serializers.UUIDField()
    other_account = serializers.SerializerMethodField()
    note = serializers.CharField()
    status = serializers.CharField()
    connected_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()

    def get_other_account(self, obj):
        viewer_account_type = self.context.get("viewer_account_type")
        viewer_account_id = self.context.get("viewer_account_id")
        if obj.account_a_type == viewer_account_type and str(obj.account_a_id) == str(
            viewer_account_id
        ):
            other_type = obj.account_b_type
            other_id = obj.account_b_id
        else:
            other_type = obj.account_a_type
            other_id = obj.account_a_id

        account_data = self.context.get("account_data")
        if account_data is not None:
            account = account_data.get(other_id)
            if account:
                profile = getattr(account, "profile", None)
                name = (
                    getattr(profile, "display_name", "")
                    or getattr(account, "legal_name", "")
                    or ""
                )
            else:
                name = ""
        else:
            name = _resolve_account_name(other_type, other_id)

        return {
            "type": other_type,
            "id": str(other_id),
            "name": name,
        }


class NetworkStatsOutput(serializers.Serializer):
    followers_count = serializers.IntegerField()
    following_count = serializers.IntegerField()
    connections_count = serializers.IntegerField()
