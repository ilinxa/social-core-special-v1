# apps/forms/tests/test_policies.py
"""
Tests for Form Builder policies (FormTemplatePolicy, FormResponsePolicy).

Covers permission checks for CRUD operations on form templates and responses,
including system-form guard clauses and owner-based access control.
"""

import pytest

from apps.core.constants import OwnerType, ResponseStatus, FormStatus
from apps.core.exceptions import PermissionDenied
from apps.forms.policies import FormTemplatePolicy, FormResponsePolicy
from apps.forms.tests.factories import (
    FormTemplateFactory,
    SystemFormTemplateFactory,
    ActiveFormTemplateFactory,
    FormResponseFactory,
    SubmittedFormResponseFactory,
)
from apps.users.tests.factories import UserFactory


# =============================================================================
# FormTemplatePolicy
# =============================================================================


@pytest.mark.django_db
class TestFormTemplatePolicy:
    """Tests for FormTemplatePolicy authorization checks."""

    # -----------------------------------------------------------------
    # can_create_form
    # -----------------------------------------------------------------

    def test_can_create_form_allowed(self, owner_actor_context):
        """Owner with can_create_form permission does not raise."""
        FormTemplatePolicy.can_create_form(
            actor_context=owner_actor_context,
            owner_type=OwnerType.BUSINESS,
        )

    def test_can_create_form_denied(self, no_perms_actor_context):
        """Actor without can_create_form permission raises PermissionDenied."""
        with pytest.raises(PermissionDenied):
            FormTemplatePolicy.can_create_form(
                actor_context=no_perms_actor_context,
                owner_type=OwnerType.BUSINESS,
            )

    # -----------------------------------------------------------------
    # can_edit_form
    # -----------------------------------------------------------------

    def test_can_edit_form_allowed(self, owner_actor_context, draft_form):
        """Owner with permission on a non-system form does not raise."""
        FormTemplatePolicy.can_edit_form(
            actor_context=owner_actor_context,
            form_template=draft_form,
        )

    def test_can_edit_form_denied_no_perms(self, no_perms_actor_context, draft_form):
        """Actor without can_edit_form permission raises PermissionDenied."""
        with pytest.raises(PermissionDenied):
            FormTemplatePolicy.can_edit_form(
                actor_context=no_perms_actor_context,
                form_template=draft_form,
            )

    def test_can_edit_form_system_form_raises(self, owner_actor_context):
        """Editing a system form raises PermissionDenied even with permissions."""
        system_form = SystemFormTemplateFactory()
        with pytest.raises(PermissionDenied, match="System forms cannot be edited"):
            FormTemplatePolicy.can_edit_form(
                actor_context=owner_actor_context,
                form_template=system_form,
            )

    # -----------------------------------------------------------------
    # can_delete_form
    # -----------------------------------------------------------------

    def test_can_delete_form_allowed(self, owner_actor_context, draft_form):
        """Owner with permission on a non-system form does not raise."""
        FormTemplatePolicy.can_delete_form(
            actor_context=owner_actor_context,
            form_template=draft_form,
        )

    def test_can_delete_form_denied(self, no_perms_actor_context, draft_form):
        """Actor without can_delete_form permission raises PermissionDenied."""
        with pytest.raises(PermissionDenied):
            FormTemplatePolicy.can_delete_form(
                actor_context=no_perms_actor_context,
                form_template=draft_form,
            )

    def test_can_delete_form_system_form_raises(self, owner_actor_context):
        """Deleting a system form raises PermissionDenied even with permissions."""
        system_form = SystemFormTemplateFactory()
        with pytest.raises(PermissionDenied, match="System forms cannot be deleted"):
            FormTemplatePolicy.can_delete_form(
                actor_context=owner_actor_context,
                form_template=system_form,
            )

    # -----------------------------------------------------------------
    # can_publish_form
    # -----------------------------------------------------------------

    def test_can_publish_form_allowed(self, owner_actor_context, draft_form):
        """Owner with permission on a non-system form does not raise."""
        FormTemplatePolicy.can_publish_form(
            actor_context=owner_actor_context,
            form_template=draft_form,
        )

    def test_can_publish_form_system_form_raises(self, owner_actor_context):
        """Publishing a system form raises PermissionDenied."""
        system_form = SystemFormTemplateFactory()
        with pytest.raises(PermissionDenied, match="System forms cannot be published"):
            FormTemplatePolicy.can_publish_form(
                actor_context=owner_actor_context,
                form_template=system_form,
            )

    def test_can_publish_form_denied(self, no_perms_actor_context, draft_form):
        """Actor without can_edit_form permission cannot publish."""
        with pytest.raises(PermissionDenied):
            FormTemplatePolicy.can_publish_form(
                actor_context=no_perms_actor_context,
                form_template=draft_form,
            )

    # -----------------------------------------------------------------
    # can_archive_form
    # -----------------------------------------------------------------

    def test_can_archive_form_allowed(self, owner_actor_context, active_form):
        """Owner with permission on a non-system form does not raise."""
        FormTemplatePolicy.can_archive_form(
            actor_context=owner_actor_context,
            form_template=active_form,
        )

    def test_can_archive_form_system_raises(self, owner_actor_context):
        """Archiving a system form raises PermissionDenied."""
        system_form = SystemFormTemplateFactory()
        with pytest.raises(PermissionDenied, match="System forms cannot be archived"):
            FormTemplatePolicy.can_archive_form(
                actor_context=owner_actor_context,
                form_template=system_form,
            )

    def test_can_archive_form_denied(self, no_perms_actor_context, active_form):
        """Actor without can_edit_form permission cannot archive."""
        with pytest.raises(PermissionDenied):
            FormTemplatePolicy.can_archive_form(
                actor_context=no_perms_actor_context,
                form_template=active_form,
            )

    # -----------------------------------------------------------------
    # can_view_responses
    # -----------------------------------------------------------------

    def test_can_view_responses_allowed(self, owner_actor_context, active_form):
        """Owner with can_view_responses permission does not raise."""
        FormTemplatePolicy.can_view_responses(
            actor_context=owner_actor_context,
            form_template=active_form,
        )

    def test_can_view_responses_denied(self, no_perms_actor_context, active_form):
        """Actor without can_view_responses permission raises PermissionDenied."""
        with pytest.raises(PermissionDenied):
            FormTemplatePolicy.can_view_responses(
                actor_context=no_perms_actor_context,
                form_template=active_form,
            )

    # -----------------------------------------------------------------
    # can_fork_template
    # -----------------------------------------------------------------

    def test_can_fork_template_allowed(self, owner_actor_context):
        """Owner with can_create_form permission can fork templates."""
        FormTemplatePolicy.can_fork_template(
            actor_context=owner_actor_context,
        )

    def test_can_fork_template_denied(self, no_perms_actor_context):
        """Actor without can_create_form permission cannot fork."""
        with pytest.raises(PermissionDenied):
            FormTemplatePolicy.can_fork_template(
                actor_context=no_perms_actor_context,
            )


# =============================================================================
# FormResponsePolicy
# =============================================================================


@pytest.mark.django_db
class TestFormResponsePolicy:
    """Tests for FormResponsePolicy authorization checks."""

    # -----------------------------------------------------------------
    # can_view_own_response
    # -----------------------------------------------------------------

    def test_can_view_own_response_allowed(self, user):
        """User can view a response they submitted."""
        response = FormResponseFactory(submitted_by=user)
        FormResponsePolicy.can_view_own_response(
            user=user,
            response=response,
        )

    def test_can_view_own_response_denied(self, user, another_user):
        """User cannot view a response submitted by another user."""
        response = FormResponseFactory(submitted_by=another_user)
        with pytest.raises(PermissionDenied, match="You can only view your own responses"):
            FormResponsePolicy.can_view_own_response(
                user=user,
                response=response,
            )

    # -----------------------------------------------------------------
    # can_edit_response
    # -----------------------------------------------------------------

    def test_can_edit_response_allowed(self, user):
        """Owner can edit a response with draft status (editable)."""
        response = FormResponseFactory(
            submitted_by=user,
            status=ResponseStatus.DRAFT,
        )
        FormResponsePolicy.can_edit_response(
            user=user,
            response=response,
        )

    def test_can_edit_response_not_owner_raises(self, user, another_user):
        """Different user cannot edit another user's response."""
        response = FormResponseFactory(
            submitted_by=another_user,
            status=ResponseStatus.DRAFT,
        )
        with pytest.raises(PermissionDenied, match="You can only edit your own responses"):
            FormResponsePolicy.can_edit_response(
                user=user,
                response=response,
            )

    def test_can_edit_response_not_editable_raises(self, user):
        """Owner cannot edit a response with PROCESSED status (not editable)."""
        response = FormResponseFactory(
            submitted_by=user,
            status=ResponseStatus.PROCESSED,
        )
        with pytest.raises(PermissionDenied, match="This response cannot be edited"):
            FormResponsePolicy.can_edit_response(
                user=user,
                response=response,
            )

    # -----------------------------------------------------------------
    # can_process_response
    # -----------------------------------------------------------------

    def test_can_process_response_allowed(self, owner_actor_context, user):
        """Actor with can_process_response permission does not raise."""
        response = SubmittedFormResponseFactory(submitted_by=user)
        FormResponsePolicy.can_process_response(
            actor_context=owner_actor_context,
            response=response,
        )

    def test_can_process_response_denied(self, no_perms_actor_context, user):
        """Actor without can_process_response permission raises PermissionDenied."""
        response = SubmittedFormResponseFactory(submitted_by=user)
        with pytest.raises(PermissionDenied):
            FormResponsePolicy.can_process_response(
                actor_context=no_perms_actor_context,
                response=response,
            )

    # -----------------------------------------------------------------
    # can_export_responses
    # -----------------------------------------------------------------

    def test_can_export_responses_allowed(self, owner_actor_context, active_form):
        """Actor with can_export_responses permission does not raise."""
        FormResponsePolicy.can_export_responses(
            actor_context=owner_actor_context,
            form_template=active_form,
        )

    def test_can_export_responses_denied(self, no_perms_actor_context, active_form):
        """Actor without can_export_responses permission raises PermissionDenied."""
        with pytest.raises(PermissionDenied):
            FormResponsePolicy.can_export_responses(
                actor_context=no_perms_actor_context,
                form_template=active_form,
            )
