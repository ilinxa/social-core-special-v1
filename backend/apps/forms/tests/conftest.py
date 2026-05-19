# apps/forms/tests/conftest.py
"""
Pytest fixtures for Forms app tests.

Provides:
- API clients (anonymous + authenticated)
- Users, accounts, roles, memberships
- Form-specific permissions and actor contexts
- Pre-built form templates, fields, and responses
- URL helper functions for all form endpoints
"""

import pytest

from apps.core.constants import AccountType, FormScope
from apps.forms.tests.factories import (
    ActiveFormTemplateFactory,
    FormFieldFactory,
    FormResponseFactory,
    FormTemplateFactory,
    SubmittedFormResponseFactory,
)
from apps.rbac.models import Permission, RolePermission
from apps.rbac.services import RBACService
from apps.rbac.tests.factories import (
    BaseMemberRoleFactory,
    BusinessAccountFactory,
    MembershipFactory,
    OwnerRoleFactory,
    PlatformAccountFactory,
)
from apps.users.tests.factories import UserFactory

# =========================================================================
# Users
# =========================================================================


@pytest.fixture
def user(db):
    """Forms-specific user override — collision-free email for paired ``another_user``."""
    return UserFactory(email="forms_user@test.com")


@pytest.fixture
def another_user(db):
    return UserFactory(email="forms_another@test.com")


# =========================================================================
# Accounts + Roles + Memberships
# =========================================================================


@pytest.fixture
def business(db, user):
    return BusinessAccountFactory(created_by=user)


@pytest.fixture
def owner_role(db, business):
    return OwnerRoleFactory(
        account_type=AccountType.BUSINESS,
        account_id=business.id,
    )


@pytest.fixture
def base_member_role(db, business):
    return BaseMemberRoleFactory(
        account_type=AccountType.BUSINESS,
        account_id=business.id,
    )


@pytest.fixture
def owner_membership(db, user, business, owner_role):
    return MembershipFactory(
        user=user,
        account_type=AccountType.BUSINESS,
        account_id=business.id,
        role=owner_role,
        is_owner=True,
    )


@pytest.fixture
def member_membership(db, another_user, business, base_member_role):
    return MembershipFactory(
        user=another_user,
        account_type=AccountType.BUSINESS,
        account_id=business.id,
        role=base_member_role,
        is_owner=False,
    )


# =========================================================================
# Form Permissions
# =========================================================================


@pytest.fixture
def can_create_form_perm(db):
    perm, _ = Permission.objects.get_or_create(
        code="can_create_form",
        defaults={
            "name": "Create Form",
            "description": "Create form templates",
            "category": "forms",
            "applicable_scopes": ["business", "platform_only", "global_only"],
        },
    )
    return perm


@pytest.fixture
def can_edit_form_perm(db):
    perm, _ = Permission.objects.get_or_create(
        code="can_edit_form",
        defaults={
            "name": "Edit Form",
            "description": "Edit form templates",
            "category": "forms",
            "applicable_scopes": ["business", "platform_only", "global_only"],
        },
    )
    return perm


@pytest.fixture
def can_delete_form_perm(db):
    perm, _ = Permission.objects.get_or_create(
        code="can_delete_form",
        defaults={
            "name": "Delete Form",
            "description": "Delete form templates",
            "category": "forms",
            "applicable_scopes": ["business", "platform_only", "global_only"],
        },
    )
    return perm


@pytest.fixture
def can_view_responses_perm(db):
    perm, _ = Permission.objects.get_or_create(
        code="can_view_responses",
        defaults={
            "name": "View Responses",
            "description": "View form responses",
            "category": "forms",
            "applicable_scopes": ["business", "platform_only", "global_only"],
        },
    )
    return perm


@pytest.fixture
def can_process_response_perm(db):
    perm, _ = Permission.objects.get_or_create(
        code="can_process_response",
        defaults={
            "name": "Process Response",
            "description": "Process form responses",
            "category": "forms",
            "applicable_scopes": ["business", "platform_only", "global_only"],
        },
    )
    return perm


@pytest.fixture
def can_export_responses_perm(db):
    perm, _ = Permission.objects.get_or_create(
        code="can_export_responses",
        defaults={
            "name": "Export Responses",
            "description": "Export form responses",
            "category": "forms",
            "applicable_scopes": ["business", "platform_only", "global_only"],
        },
    )
    return perm


# =========================================================================
# Owner with all form permissions
# =========================================================================


@pytest.fixture
def owner_with_form_perms(
    owner_membership,
    owner_role,
    can_create_form_perm,
    can_edit_form_perm,
    can_delete_form_perm,
    can_view_responses_perm,
    can_process_response_perm,
    can_export_responses_perm,
):
    for perm in [
        can_create_form_perm,
        can_edit_form_perm,
        can_delete_form_perm,
        can_view_responses_perm,
        can_process_response_perm,
        can_export_responses_perm,
    ]:
        RolePermission.objects.get_or_create(
            role=owner_role,
            permission=perm,
            defaults={"scope": "business"},
        )
    return owner_membership


# =========================================================================
# Actor Contexts
# =========================================================================


@pytest.fixture
def owner_actor_context(owner_with_form_perms):
    return RBACService.build_actor_context(
        membership=owner_with_form_perms,
        request=None,
    )


@pytest.fixture
def no_perms_actor_context(member_membership):
    return RBACService.build_actor_context(
        membership=member_membership,
        request=None,
    )


# =========================================================================
# Form Templates (scoped to the business)
# =========================================================================


@pytest.fixture
def draft_form(db, user, business):
    return FormTemplateFactory(
        owner_type=AccountType.BUSINESS,
        owner_id=business.id,
        scope=FormScope.BUSINESS,
        created_by=user,
    )


@pytest.fixture
def active_form(db, user, business):
    return ActiveFormTemplateFactory(
        owner_type=AccountType.BUSINESS,
        owner_id=business.id,
        scope=FormScope.BUSINESS,
        created_by=user,
    )


# =========================================================================
# Form Responses
# =========================================================================


@pytest.fixture
def draft_response(db, active_form, user):
    return FormResponseFactory(
        form_template=active_form,
        submitted_by=user,
        data={"field_1": "value1"},
    )


@pytest.fixture
def submitted_response(db, active_form, user):
    return SubmittedFormResponseFactory(
        form_template=active_form,
        submitted_by=user,
        data={"field_1": "value1"},
    )


# =========================================================================
# URL Helpers
# =========================================================================


def template_list_url(account_type, account_id):
    return f"/api/v1/forms/{account_type}/{account_id}/templates/"


def template_detail_url(form_id):
    return f"/api/v1/forms/templates/{form_id}/"


def template_publish_url(form_id):
    return f"/api/v1/forms/templates/{form_id}/publish/"


def template_archive_url(form_id):
    return f"/api/v1/forms/templates/{form_id}/archive/"


def template_fork_url(form_id):
    return f"/api/v1/forms/templates/{form_id}/fork/"


def template_fields_url(form_id):
    return f"/api/v1/forms/templates/{form_id}/fields/"


def response_list_url(form_id):
    return f"/api/v1/forms/templates/{form_id}/responses/"


def response_detail_url(response_id):
    return f"/api/v1/forms/responses/{response_id}/"


def response_submit_url(response_id):
    return f"/api/v1/forms/responses/{response_id}/submit/"


def response_process_url(response_id):
    return f"/api/v1/forms/responses/{response_id}/process/"


def response_void_url(response_id):
    return f"/api/v1/forms/responses/{response_id}/void/"


def field_detail_url(template_id, field_id):
    return f"/api/v1/forms/templates/{template_id}/fields/{field_id}/"


def field_reorder_url(template_id):
    return f"/api/v1/forms/templates/{template_id}/fields/reorder/"


PUBLIC_LIBRARY_URL = "/api/v1/forms/templates/library/"
MY_RESPONSES_URL = "/api/v1/forms/me/responses/"


# =========================================================================
# Platform Fixtures
# =========================================================================


@pytest.fixture
def platform(db):
    return PlatformAccountFactory()


@pytest.fixture
def platform_owner_role(db, platform):
    return OwnerRoleFactory(
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
    )


@pytest.fixture
def platform_owner_membership(db, user, platform, platform_owner_role):
    return MembershipFactory(
        user=user,
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
        role=platform_owner_role,
        is_owner=True,
    )


@pytest.fixture
def platform_owner_with_form_perms(
    platform_owner_membership,
    platform_owner_role,
    can_create_form_perm,
    can_edit_form_perm,
    can_delete_form_perm,
    can_view_responses_perm,
    can_process_response_perm,
    can_export_responses_perm,
):
    for perm in [
        can_create_form_perm,
        can_edit_form_perm,
        can_delete_form_perm,
        can_view_responses_perm,
        can_process_response_perm,
        can_export_responses_perm,
    ]:
        RolePermission.objects.get_or_create(
            role=platform_owner_role,
            permission=perm,
            defaults={"scope": "platform_only"},
        )
    return platform_owner_membership
