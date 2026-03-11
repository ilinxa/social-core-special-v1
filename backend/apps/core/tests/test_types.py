# apps/core/tests/test_types.py
"""
Tests for ActorContext dataclass in apps.core.types.

Covers:
- Construction with all fields and defaults
- Permission checking methods
- Serialization / deserialization round-trips
- Factory classmethods (for_user_context, for_anonymous, for_system)
"""

import pytest
from datetime import datetime, timezone as dt_timezone
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from django.utils import timezone

from apps.core.types import ActorContext


# =============================================================================
# HELPERS
# =============================================================================


def _make_context(**overrides) -> ActorContext:
    """Build an ActorContext with sensible defaults, overridable per-field."""
    defaults = dict(
        user_id=uuid4(),
        account_type="business",
        account_id=uuid4(),
        membership_id=uuid4(),
        role_id=uuid4(),
        role_name="Editor",
        role_level=5,
        is_owner=False,
        permissions_snapshot=[
            ("can_view_members", "business"),
            ("can_edit_posts", "business"),
            ("can_remove_member", "global_only"),
        ],
        ip_address="192.168.1.1",
        user_agent="TestAgent/1.0",
    )
    defaults.update(overrides)
    return ActorContext(**defaults)


def _make_request(ip="10.0.0.1", user_agent="Mozilla/5.0"):
    """Build a minimal mock request with META dict."""
    request = MagicMock()
    request.META = {
        "REMOTE_ADDR": ip,
        "HTTP_USER_AGENT": user_agent,
    }
    return request


# =============================================================================
# CONSTRUCTION
# =============================================================================


class TestActorContextConstruction:
    """Tests for ActorContext dataclass construction."""

    def test_construct_with_all_fields(self):
        uid = uuid4()
        aid = uuid4()
        mid = uuid4()
        rid = uuid4()
        now = timezone.now()
        perms = [("can_view", "business"), ("can_edit", "global_only")]

        ctx = ActorContext(
            user_id=uid,
            account_type="platform",
            account_id=aid,
            membership_id=mid,
            role_id=rid,
            role_name="Admin",
            role_level=1,
            is_owner=True,
            permissions_snapshot=perms,
            captured_at=now,
            ip_address="127.0.0.1",
            user_agent="TestBrowser/2.0",
        )

        assert ctx.user_id == uid
        assert ctx.account_type == "platform"
        assert ctx.account_id == aid
        assert ctx.membership_id == mid
        assert ctx.role_id == rid
        assert ctx.role_name == "Admin"
        assert ctx.role_level == 1
        assert ctx.is_owner is True
        assert ctx.permissions_snapshot == perms
        assert ctx.captured_at == now
        assert ctx.ip_address == "127.0.0.1"
        assert ctx.user_agent == "TestBrowser/2.0"

    def test_default_permissions_snapshot_is_empty_list(self):
        ctx = ActorContext(
            user_id=uuid4(),
            account_type="business",
            account_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Viewer",
            role_level=10,
            is_owner=False,
        )

        assert ctx.permissions_snapshot == []

    def test_default_captured_at_is_populated(self):
        before = timezone.now()
        ctx = ActorContext(
            user_id=uuid4(),
            account_type="business",
            account_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            role_name="Viewer",
            role_level=10,
            is_owner=False,
        )
        after = timezone.now()

        assert before <= ctx.captured_at <= after

    def test_default_ip_address_is_none(self):
        ctx = _make_context(ip_address=None)
        assert ctx.ip_address is None

    def test_default_user_agent_is_none(self):
        ctx = _make_context(user_agent=None)
        assert ctx.user_agent is None

    def test_each_instance_gets_own_permissions_list(self):
        """Ensure default mutable field is not shared across instances."""
        ctx_a = ActorContext(
            user_id=uuid4(),
            account_type=None,
            account_id=None,
            membership_id=None,
            role_id=None,
            role_name=None,
            role_level=None,
            is_owner=False,
        )
        ctx_b = ActorContext(
            user_id=uuid4(),
            account_type=None,
            account_id=None,
            membership_id=None,
            role_id=None,
            role_name=None,
            role_level=None,
            is_owner=False,
        )
        ctx_a.permissions_snapshot.append(("foo", "bar"))

        assert ctx_b.permissions_snapshot == []


# =============================================================================
# has_permission()
# =============================================================================


class TestHasPermission:
    """Tests for ActorContext.has_permission()."""

    def test_returns_true_for_matching_code(self):
        ctx = _make_context(
            permissions_snapshot=[
                ("can_view_members", "business"),
                ("can_edit_posts", "global_only"),
            ]
        )
        assert ctx.has_permission("can_view_members") is True

    def test_returns_true_regardless_of_scope(self):
        ctx = _make_context(
            permissions_snapshot=[("can_delete", "global_only")]
        )
        assert ctx.has_permission("can_delete") is True

    def test_returns_false_for_non_matching_code(self):
        ctx = _make_context(
            permissions_snapshot=[("can_view_members", "business")]
        )
        assert ctx.has_permission("can_delete_account") is False

    def test_returns_false_for_empty_permissions(self):
        ctx = _make_context(permissions_snapshot=[])
        assert ctx.has_permission("anything") is False

    def test_matches_first_occurrence_among_duplicates(self):
        ctx = _make_context(
            permissions_snapshot=[
                ("can_view", "business"),
                ("can_view", "global_only"),
            ]
        )
        assert ctx.has_permission("can_view") is True

    def test_code_matching_is_exact(self):
        ctx = _make_context(
            permissions_snapshot=[("can_view_members", "business")]
        )
        assert ctx.has_permission("can_view") is False
        assert ctx.has_permission("can_view_members_all") is False


# =============================================================================
# has_permission_with_scope()
# =============================================================================


class TestHasPermissionWithScope:
    """Tests for ActorContext.has_permission_with_scope()."""

    def test_returns_true_for_exact_match(self):
        ctx = _make_context(
            permissions_snapshot=[("can_edit_posts", "business")]
        )
        assert ctx.has_permission_with_scope("can_edit_posts", "business") is True

    def test_returns_false_when_code_matches_but_scope_differs(self):
        ctx = _make_context(
            permissions_snapshot=[("can_edit_posts", "business")]
        )
        assert ctx.has_permission_with_scope("can_edit_posts", "global_only") is False

    def test_returns_false_when_scope_matches_but_code_differs(self):
        ctx = _make_context(
            permissions_snapshot=[("can_edit_posts", "business")]
        )
        assert ctx.has_permission_with_scope("can_delete_posts", "business") is False

    def test_returns_false_for_empty_permissions(self):
        ctx = _make_context(permissions_snapshot=[])
        assert ctx.has_permission_with_scope("any_code", "any_scope") is False

    def test_distinguishes_similar_tuples(self):
        ctx = _make_context(
            permissions_snapshot=[
                ("can_view", "business"),
                ("can_edit", "global_only"),
            ]
        )
        assert ctx.has_permission_with_scope("can_view", "global_only") is False
        assert ctx.has_permission_with_scope("can_edit", "business") is False


# =============================================================================
# has_global_permission()
# =============================================================================


class TestHasGlobalPermission:
    """Tests for ActorContext.has_global_permission()."""

    def test_returns_true_for_global_only_scope(self):
        ctx = _make_context(
            permissions_snapshot=[("can_remove_member", "global_only")]
        )
        assert ctx.has_global_permission("can_remove_member") is True

    def test_returns_true_for_platform_and_global_scope(self):
        ctx = _make_context(
            permissions_snapshot=[("can_manage_users", "platform_and_global")]
        )
        assert ctx.has_global_permission("can_manage_users") is True

    def test_returns_false_for_business_scope(self):
        ctx = _make_context(
            permissions_snapshot=[("can_view_members", "business")]
        )
        assert ctx.has_global_permission("can_view_members") is False

    def test_returns_false_for_non_existent_code(self):
        ctx = _make_context(
            permissions_snapshot=[("can_remove_member", "global_only")]
        )
        assert ctx.has_global_permission("can_fly") is False

    def test_returns_false_for_empty_permissions(self):
        ctx = _make_context(permissions_snapshot=[])
        assert ctx.has_global_permission("anything") is False

    def test_matches_across_multiple_scopes(self):
        """If the same code appears with both business and global_only, global check passes."""
        ctx = _make_context(
            permissions_snapshot=[
                ("can_edit", "business"),
                ("can_edit", "global_only"),
            ]
        )
        assert ctx.has_global_permission("can_edit") is True


# =============================================================================
# permission_codes()
# =============================================================================


class TestPermissionCodes:
    """Tests for ActorContext.permission_codes()."""

    def test_returns_unique_codes(self):
        ctx = _make_context(
            permissions_snapshot=[
                ("can_view", "business"),
                ("can_edit", "business"),
                ("can_view", "global_only"),  # duplicate code, different scope
            ]
        )
        codes = ctx.permission_codes()

        assert sorted(codes) == ["can_edit", "can_view"]

    def test_returns_empty_list_for_no_permissions(self):
        ctx = _make_context(permissions_snapshot=[])
        assert ctx.permission_codes() == []

    def test_single_permission(self):
        ctx = _make_context(
            permissions_snapshot=[("can_view", "business")]
        )
        assert ctx.permission_codes() == ["can_view"]

    def test_returns_list_type(self):
        ctx = _make_context(
            permissions_snapshot=[("a", "b"), ("c", "d")]
        )
        result = ctx.permission_codes()
        assert isinstance(result, list)


# =============================================================================
# to_dict()
# =============================================================================


class TestToDict:
    """Tests for ActorContext.to_dict() serialization."""

    def test_all_fields_present(self):
        ctx = _make_context()
        d = ctx.to_dict()

        expected_keys = {
            "user_id",
            "account_type",
            "account_id",
            "membership_id",
            "role_id",
            "role_name",
            "role_level",
            "is_owner",
            "permissions_snapshot",
            "captured_at",
            "ip_address",
            "user_agent",
        }
        assert set(d.keys()) == expected_keys

    def test_uuids_converted_to_strings(self):
        uid = uuid4()
        aid = uuid4()
        mid = uuid4()
        rid = uuid4()

        ctx = _make_context(
            user_id=uid,
            account_id=aid,
            membership_id=mid,
            role_id=rid,
        )
        d = ctx.to_dict()

        assert d["user_id"] == str(uid)
        assert d["account_id"] == str(aid)
        assert d["membership_id"] == str(mid)
        assert d["role_id"] == str(rid)

    def test_none_uuids_remain_none(self):
        ctx = _make_context(
            user_id=None,
            account_id=None,
            membership_id=None,
            role_id=None,
        )
        d = ctx.to_dict()

        assert d["user_id"] is None
        assert d["account_id"] is None
        assert d["membership_id"] is None
        assert d["role_id"] is None

    def test_captured_at_is_iso_string(self):
        now = timezone.now()
        ctx = _make_context(captured_at=now)
        d = ctx.to_dict()

        assert d["captured_at"] == now.isoformat()
        assert isinstance(d["captured_at"], str)

    def test_permissions_snapshot_serialized_as_list_of_pairs(self):
        perms = [("can_view", "business"), ("can_edit", "global_only")]
        ctx = _make_context(permissions_snapshot=perms)
        d = ctx.to_dict()

        assert d["permissions_snapshot"] == [
            ["can_view", "business"],
            ["can_edit", "global_only"],
        ]

    def test_scalar_fields_preserved(self):
        ctx = _make_context(
            account_type="platform",
            role_name="Admin",
            role_level=1,
            is_owner=True,
            ip_address="10.0.0.1",
            user_agent="Chrome/100",
        )
        d = ctx.to_dict()

        assert d["account_type"] == "platform"
        assert d["role_name"] == "Admin"
        assert d["role_level"] == 1
        assert d["is_owner"] is True
        assert d["ip_address"] == "10.0.0.1"
        assert d["user_agent"] == "Chrome/100"

    def test_empty_permissions_serialized_as_empty_list(self):
        ctx = _make_context(permissions_snapshot=[])
        d = ctx.to_dict()

        assert d["permissions_snapshot"] == []


# =============================================================================
# from_dict()
# =============================================================================


class TestFromDict:
    """Tests for ActorContext.from_dict() deserialization."""

    def test_round_trip_produces_equivalent_object(self):
        original = _make_context()
        d = original.to_dict()
        restored = ActorContext.from_dict(d)

        assert restored.user_id == original.user_id
        assert restored.account_type == original.account_type
        assert restored.account_id == original.account_id
        assert restored.membership_id == original.membership_id
        assert restored.role_id == original.role_id
        assert restored.role_name == original.role_name
        assert restored.role_level == original.role_level
        assert restored.is_owner == original.is_owner
        assert restored.permissions_snapshot == original.permissions_snapshot
        assert restored.captured_at == original.captured_at
        assert restored.ip_address == original.ip_address
        assert restored.user_agent == original.user_agent

    def test_round_trip_with_none_uuids(self):
        original = _make_context(
            user_id=None,
            account_id=None,
            membership_id=None,
            role_id=None,
        )
        d = original.to_dict()
        restored = ActorContext.from_dict(d)

        assert restored.user_id is None
        assert restored.account_id is None
        assert restored.membership_id is None
        assert restored.role_id is None

    def test_uuid_strings_converted_back_to_uuid_objects(self):
        uid = uuid4()
        ctx = _make_context(user_id=uid)
        d = ctx.to_dict()

        # Confirm it's a string in the dict
        assert isinstance(d["user_id"], str)

        restored = ActorContext.from_dict(d)
        assert isinstance(restored.user_id, UUID)
        assert restored.user_id == uid

    def test_captured_at_restored_as_datetime(self):
        now = timezone.now()
        ctx = _make_context(captured_at=now)
        d = ctx.to_dict()
        restored = ActorContext.from_dict(d)

        assert isinstance(restored.captured_at, datetime)
        assert restored.captured_at == now

    def test_permissions_restored_as_tuples(self):
        perms = [("can_view", "business"), ("can_edit", "global_only")]
        ctx = _make_context(permissions_snapshot=perms)
        d = ctx.to_dict()
        restored = ActorContext.from_dict(d)

        assert restored.permissions_snapshot == perms
        # Verify they are tuples, not lists
        for item in restored.permissions_snapshot:
            assert isinstance(item, tuple)

    def test_legacy_flat_permission_list_handled(self):
        """Old format: flat list of code strings -> converted to (code, 'business') tuples."""
        d = _make_context().to_dict()
        d["permissions_snapshot"] = ["can_view", "can_edit"]

        restored = ActorContext.from_dict(d)

        assert restored.permissions_snapshot == [
            ("can_view", "business"),
            ("can_edit", "business"),
        ]

    def test_empty_permissions_round_trip(self):
        ctx = _make_context(permissions_snapshot=[])
        d = ctx.to_dict()
        restored = ActorContext.from_dict(d)

        assert restored.permissions_snapshot == []

    def test_is_owner_defaults_to_false_when_missing(self):
        d = _make_context().to_dict()
        del d["is_owner"]
        restored = ActorContext.from_dict(d)

        assert restored.is_owner is False


# =============================================================================
# for_user_context()
# =============================================================================


@pytest.mark.django_db
class TestForUserContext:
    """Tests for ActorContext.for_user_context() classmethod."""

    def test_user_id_populated(self, user):
        ctx = ActorContext.for_user_context(user)
        assert ctx.user_id == user.id

    def test_membership_fields_are_none(self, user):
        ctx = ActorContext.for_user_context(user)

        assert ctx.account_type is None
        assert ctx.account_id is None
        assert ctx.membership_id is None
        assert ctx.role_id is None
        assert ctx.role_name is None
        assert ctx.role_level is None

    def test_is_owner_is_false(self, user):
        ctx = ActorContext.for_user_context(user)
        assert ctx.is_owner is False

    def test_permissions_snapshot_is_empty(self, user):
        ctx = ActorContext.for_user_context(user)
        assert ctx.permissions_snapshot == []

    def test_captured_at_is_recent(self, user):
        before = timezone.now()
        ctx = ActorContext.for_user_context(user)
        after = timezone.now()

        assert before <= ctx.captured_at <= after

    def test_without_request_ip_and_agent_are_none(self, user):
        ctx = ActorContext.for_user_context(user)

        assert ctx.ip_address is None
        assert ctx.user_agent is None

    def test_with_request_extracts_ip_and_agent(self, user):
        request = _make_request(ip="203.0.113.50", user_agent="Safari/16")
        ctx = ActorContext.for_user_context(user, request=request)

        assert ctx.ip_address == "203.0.113.50"
        assert ctx.user_agent == "Safari/16"

    def test_with_request_x_forwarded_for(self, user):
        request = _make_request()
        request.META["HTTP_X_FORWARDED_FOR"] = "198.51.100.1, 10.0.0.1"
        ctx = ActorContext.for_user_context(user, request=request)

        assert ctx.ip_address == "198.51.100.1"


# =============================================================================
# for_anonymous()
# =============================================================================


class TestForAnonymous:
    """Tests for ActorContext.for_anonymous() classmethod."""

    def test_all_identity_fields_are_none(self):
        ctx = ActorContext.for_anonymous()

        assert ctx.user_id is None
        assert ctx.account_type is None
        assert ctx.account_id is None
        assert ctx.membership_id is None
        assert ctx.role_id is None
        assert ctx.role_name is None
        assert ctx.role_level is None

    def test_is_owner_is_false(self):
        ctx = ActorContext.for_anonymous()
        assert ctx.is_owner is False

    def test_permissions_snapshot_is_empty(self):
        ctx = ActorContext.for_anonymous()
        assert ctx.permissions_snapshot == []

    def test_captured_at_is_recent(self):
        before = timezone.now()
        ctx = ActorContext.for_anonymous()
        after = timezone.now()

        assert before <= ctx.captured_at <= after

    def test_without_request_ip_and_agent_are_none(self):
        ctx = ActorContext.for_anonymous()

        assert ctx.ip_address is None
        assert ctx.user_agent is None

    def test_with_request_extracts_ip_and_agent(self):
        request = _make_request(ip="192.0.2.1", user_agent="curl/7.68")
        ctx = ActorContext.for_anonymous(request=request)

        assert ctx.ip_address == "192.0.2.1"
        assert ctx.user_agent == "curl/7.68"


# =============================================================================
# for_system()
# =============================================================================


class TestForSystem:
    """Tests for ActorContext.for_system() classmethod."""

    def test_all_identity_fields_are_none(self):
        ctx = ActorContext.for_system()

        assert ctx.user_id is None
        assert ctx.account_type is None
        assert ctx.account_id is None
        assert ctx.membership_id is None
        assert ctx.role_id is None
        assert ctx.role_level is None

    def test_role_name_is_system(self):
        ctx = ActorContext.for_system()
        assert ctx.role_name == "SYSTEM"

    def test_is_owner_is_false(self):
        ctx = ActorContext.for_system()
        assert ctx.is_owner is False

    def test_permissions_snapshot_is_empty(self):
        ctx = ActorContext.for_system()
        assert ctx.permissions_snapshot == []

    def test_ip_address_is_none(self):
        ctx = ActorContext.for_system()
        assert ctx.ip_address is None

    def test_user_agent_is_none(self):
        ctx = ActorContext.for_system()
        assert ctx.user_agent is None

    def test_captured_at_is_recent(self):
        before = timezone.now()
        ctx = ActorContext.for_system()
        after = timezone.now()

        assert before <= ctx.captured_at <= after
