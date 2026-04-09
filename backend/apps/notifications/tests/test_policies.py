# apps/notifications/tests/test_policies.py
"""
Tests for NotificationPolicy.

Covers:
    - can_view_scoped_notifications: membership check for org scopes
    - can_manage_notifications: RBAC permission check
    - get_viewer_permissions: Tier 1.5 permission dict
"""

import uuid
from unittest.mock import patch

import pytest

from apps.notifications.policies import NotificationPolicy
from apps.users.tests.factories import UserFactory

# =============================================================================
# can_view_scoped_notifications
# =============================================================================


@pytest.mark.django_db
class TestCanViewScopedNotifications:
    def test_user_scope_always_true(self):
        user = UserFactory()
        assert NotificationPolicy.can_view_scoped_notifications(
            user=user, scope_type="user", scope_id=uuid.uuid4()
        )

    @patch("apps.rbac.selectors.MembershipSelector.is_user_member_of_account")
    def test_business_scope_member(self, mock_is_member):
        mock_is_member.return_value = True
        user = UserFactory()
        biz_id = uuid.uuid4()

        result = NotificationPolicy.can_view_scoped_notifications(
            user=user, scope_type="business", scope_id=biz_id
        )

        assert result is True
        mock_is_member.assert_called_once_with(
            user=user, account_type="business", account_id=biz_id
        )

    @patch("apps.rbac.selectors.MembershipSelector.is_user_member_of_account")
    def test_business_scope_non_member(self, mock_is_member):
        mock_is_member.return_value = False
        user = UserFactory()

        result = NotificationPolicy.can_view_scoped_notifications(
            user=user, scope_type="business", scope_id=uuid.uuid4()
        )

        assert result is False

    @patch("apps.rbac.selectors.MembershipSelector.is_user_member_of_account")
    def test_platform_scope_member(self, mock_is_member):
        mock_is_member.return_value = True
        user = UserFactory()

        result = NotificationPolicy.can_view_scoped_notifications(
            user=user, scope_type="platform", scope_id=uuid.uuid4()
        )

        assert result is True


# =============================================================================
# can_manage_notifications
# =============================================================================


@pytest.mark.django_db
class TestCanManageNotifications:
    def test_user_scope_always_true(self):
        user = UserFactory()
        assert NotificationPolicy.can_manage_notifications(
            user=user, scope_type="user", scope_id=uuid.uuid4()
        )

    @patch("apps.rbac.selectors.PermissionSelector.get_permissions_for_membership")
    @patch(
        "apps.rbac.selectors.MembershipSelector.get_active_membership_for_user_account"
    )
    def test_with_permission(self, mock_get_membership, mock_get_perms):
        from unittest.mock import MagicMock

        membership = MagicMock()
        membership.id = uuid.uuid4()
        mock_get_membership.return_value = membership
        mock_get_perms.return_value = [
            ("can_manage_notifications", "business"),
            ("can_view_members", "business"),
        ]

        user = UserFactory()
        result = NotificationPolicy.can_manage_notifications(
            user=user, scope_type="business", scope_id=uuid.uuid4()
        )

        assert result is True

    @patch("apps.rbac.selectors.PermissionSelector.get_permissions_for_membership")
    @patch(
        "apps.rbac.selectors.MembershipSelector.get_active_membership_for_user_account"
    )
    def test_without_permission(self, mock_get_membership, mock_get_perms):
        from unittest.mock import MagicMock

        membership = MagicMock()
        membership.id = uuid.uuid4()
        mock_get_membership.return_value = membership
        mock_get_perms.return_value = [("can_view_members", "business")]

        user = UserFactory()
        result = NotificationPolicy.can_manage_notifications(
            user=user, scope_type="business", scope_id=uuid.uuid4()
        )

        assert result is False

    @patch(
        "apps.rbac.selectors.MembershipSelector.get_active_membership_for_user_account"
    )
    def test_non_member(self, mock_get_membership):
        mock_get_membership.return_value = None

        user = UserFactory()
        result = NotificationPolicy.can_manage_notifications(
            user=user, scope_type="business", scope_id=uuid.uuid4()
        )

        assert result is False


# =============================================================================
# get_viewer_permissions (Tier 1.5)
# =============================================================================


@pytest.mark.django_db
class TestGetViewerPermissions:
    def test_user_scope_returns_user_defaults(self):
        user = UserFactory()
        perms = NotificationPolicy.get_viewer_permissions(
            user=user, scope_type="user", scope_id=None
        )

        assert perms["can_view_notifications"] is True
        assert perms["can_manage_preferences"] is True
        assert perms["can_manage_org_notifications"] is False

    @patch("apps.rbac.selectors.MembershipSelector.is_user_member_of_account")
    def test_business_scope_member(self, mock_is_member):
        mock_is_member.return_value = True
        user = UserFactory()

        with patch.object(
            NotificationPolicy, "can_manage_notifications", return_value=False
        ):
            perms = NotificationPolicy.get_viewer_permissions(
                user=user, scope_type="business", scope_id=uuid.uuid4()
            )

        assert perms["can_view_notifications"] is True
        assert perms["can_manage_preferences"] is True
        assert perms["can_manage_org_notifications"] is False

    @patch("apps.rbac.selectors.MembershipSelector.is_user_member_of_account")
    def test_business_scope_non_member(self, mock_is_member):
        mock_is_member.return_value = False
        user = UserFactory()

        perms = NotificationPolicy.get_viewer_permissions(
            user=user, scope_type="business", scope_id=uuid.uuid4()
        )

        assert perms["can_view_notifications"] is False
        assert perms["can_manage_preferences"] is False
        assert perms["can_manage_org_notifications"] is False

    def test_null_scope_id_returns_user_defaults(self):
        user = UserFactory()
        perms = NotificationPolicy.get_viewer_permissions(
            user=user, scope_type="business", scope_id=None
        )

        assert perms["can_view_notifications"] is True
        assert perms["can_manage_preferences"] is True
