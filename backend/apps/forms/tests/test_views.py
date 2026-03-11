# apps/forms/tests/test_views.py
"""
Comprehensive API view tests for Form Builder.

Tests cover all form template and form response endpoints:
- FormTemplateListView (GET / POST)
- FormTemplateDetailView (GET / PATCH / DELETE)
- FormTemplatePublishView (POST)
- FormTemplateArchiveView (POST)
- FormTemplateForkView (POST)
- PublicTemplateLibraryView (GET)
- FormFieldAddView (POST)
- FormResponseListView (GET / POST)
- FormResponseDetailView (GET / PATCH)
- FormResponseSubmitView (POST)
- FormResponseProcessView (POST)
- FormResponseVoidView (POST)
- MyResponsesView (GET)
"""

import pytest

from apps.core.constants import (
    AccountType,
    FieldType,
    FormScope,
    FormStatus,
    OwnerType,
    ResponseStatus,
)
from apps.forms.models import FormField, FormResponse, FormTemplate
from apps.forms.tests.conftest import (
    PUBLIC_LIBRARY_URL,
    MY_RESPONSES_URL,
    template_list_url,
    template_detail_url,
    template_publish_url,
    template_archive_url,
    template_fork_url,
    template_fields_url,
    field_detail_url,
    field_reorder_url,
    response_list_url,
    response_detail_url,
    response_submit_url,
    response_process_url,
    response_void_url,
)
from apps.forms.tests.factories import (
    ActiveFormTemplateFactory,
    FormFieldFactory,
    FormResponseFactory,
    FormTemplateFactory,
    PublicFormTemplateFactory,
    SubmittedFormResponseFactory,
)
from apps.users.tests.factories import UserFactory


# =============================================================================
# FORM TEMPLATE LIST VIEW
# =============================================================================


@pytest.mark.django_db
class TestFormTemplateListView:
    """Tests for GET/POST /api/v1/forms/{account_type}/{account_id}/templates/"""

    def test_list_templates_authenticated(
        self, authenticated_client, owner_with_form_perms, business,
    ):
        """Authenticated user with membership can list templates."""
        url = template_list_url(AccountType.BUSINESS, business.id)
        response = authenticated_client.get(url)
        assert response.status_code == 200

    def test_list_templates_unauthenticated(self, api_client, business):
        """Unauthenticated request returns 401."""
        url = template_list_url(AccountType.BUSINESS, business.id)
        response = api_client.get(url)
        assert response.status_code == 401

    def test_list_returns_own_templates(
        self, authenticated_client, owner_with_form_perms, user, business,
    ):
        """GET returns templates owned by the business."""
        FormTemplateFactory(
            owner_type=AccountType.BUSINESS,
            owner_id=business.id,
            scope=FormScope.BUSINESS,
            created_by=user,
            name="Form A",
        )
        FormTemplateFactory(
            owner_type=AccountType.BUSINESS,
            owner_id=business.id,
            scope=FormScope.BUSINESS,
            created_by=user,
            name="Form B",
        )
        url = template_list_url(AccountType.BUSINESS, business.id)
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] == 2

    def test_create_template(
        self, authenticated_client, owner_with_form_perms, business,
    ):
        """POST with valid data creates a new draft form template."""
        url = template_list_url(AccountType.BUSINESS, business.id)
        payload = {
            "name": "New Form",
            "owner_type": "business",
            "owner_id": str(business.id),
            "scope": "business",
        }
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 201
        assert response.data["name"] == "New Form"
        assert response.data["status"] == FormStatus.DRAFT
        assert FormTemplate.objects.filter(name="New Form").exists()

    def test_create_template_missing_required_field(
        self, authenticated_client, owner_with_form_perms, business,
    ):
        """POST without required 'name' field returns 400."""
        url = template_list_url(AccountType.BUSINESS, business.id)
        payload = {
            "owner_type": "business",
            "owner_id": str(business.id),
            "scope": "business",
        }
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 400


# =============================================================================
# FORM TEMPLATE DETAIL VIEW
# =============================================================================


@pytest.mark.django_db
class TestFormTemplateDetailView:
    """Tests for GET/PATCH/DELETE /api/v1/forms/templates/{form_id}/"""

    def test_get_template_detail(
        self, authenticated_client, owner_with_form_perms, draft_form,
    ):
        """Authenticated member can retrieve form template details."""
        url = template_detail_url(draft_form.id)
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.data["id"] == str(draft_form.id)
        assert response.data["name"] == draft_form.name

    def test_get_public_template_no_membership(
        self, api_client, another_user,
    ):
        """Any authenticated user can view a public template without membership."""
        public_form = PublicFormTemplateFactory()
        api_client.force_authenticate(user=another_user)
        url = template_detail_url(public_form.id)
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["id"] == str(public_form.id)

    def test_update_template(
        self, authenticated_client, owner_with_form_perms, draft_form,
    ):
        """PATCH updates form template name."""
        url = template_detail_url(draft_form.id)
        payload = {"name": "Updated Form Name"}
        response = authenticated_client.patch(url, payload, format="json")
        assert response.status_code == 200
        assert response.data["name"] == "Updated Form Name"
        draft_form.refresh_from_db()
        assert draft_form.name == "Updated Form Name"

    def test_delete_template(
        self, authenticated_client, owner_with_form_perms, draft_form,
    ):
        """DELETE soft-deletes the form template."""
        url = template_detail_url(draft_form.id)
        response = authenticated_client.delete(url)
        assert response.status_code == 204
        # Soft-deleted: not visible via default manager
        assert not FormTemplate.objects.filter(id=draft_form.id).exists()


# =============================================================================
# FORM TEMPLATE PUBLISH VIEW
# =============================================================================


@pytest.mark.django_db
class TestFormTemplatePublishView:
    """Tests for POST /api/v1/forms/templates/{form_id}/publish/"""

    def test_publish_template(
        self, authenticated_client, owner_with_form_perms, draft_form,
    ):
        """Publishing a draft form transitions it to ACTIVE."""
        url = template_publish_url(draft_form.id)
        response = authenticated_client.post(url)
        assert response.status_code == 200
        assert response.data["status"] == FormStatus.ACTIVE
        draft_form.refresh_from_db()
        assert draft_form.status == FormStatus.ACTIVE

    def test_publish_non_draft_fails(
        self, authenticated_client, owner_with_form_perms, active_form,
    ):
        """Publishing an already-active form returns 400 (BusinessRuleViolation)."""
        url = template_publish_url(active_form.id)
        response = authenticated_client.post(url)
        assert response.status_code == 400


# =============================================================================
# FORM TEMPLATE ARCHIVE VIEW
# =============================================================================


@pytest.mark.django_db
class TestFormTemplateArchiveView:
    """Tests for POST /api/v1/forms/templates/{form_id}/archive/"""

    def test_archive_template(
        self, authenticated_client, owner_with_form_perms, active_form,
    ):
        """Archiving an active form transitions it to ARCHIVED."""
        url = template_archive_url(active_form.id)
        response = authenticated_client.post(url)
        assert response.status_code == 200
        assert response.data["status"] == FormStatus.ARCHIVED
        active_form.refresh_from_db()
        assert active_form.status == FormStatus.ARCHIVED

    def test_archive_non_active_fails(
        self, authenticated_client, owner_with_form_perms, draft_form,
    ):
        """Archiving a draft form returns 400 (BusinessRuleViolation)."""
        url = template_archive_url(draft_form.id)
        response = authenticated_client.post(url)
        assert response.status_code == 400


# =============================================================================
# FORM TEMPLATE FORK VIEW
# =============================================================================


@pytest.mark.django_db
class TestFormTemplateForkView:
    """Tests for POST /api/v1/forms/templates/{form_id}/fork/"""

    def test_fork_public_template(
        self, authenticated_client, owner_with_form_perms, business,
    ):
        """Forking a public template creates a new draft copy."""
        public_form = PublicFormTemplateFactory()
        url = template_fork_url(public_form.id)
        payload = {
            "new_owner_type": AccountType.BUSINESS,
            "new_owner_id": str(business.id),
        }
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 201
        assert response.data["status"] == FormStatus.DRAFT
        assert str(response.data["forked_from"]) == str(public_form.id)

    def test_fork_non_public_fails(
        self, authenticated_client, owner_with_form_perms, business,
    ):
        """Forking a non-public template returns 403 (PermissionDenied)."""
        private_form = ActiveFormTemplateFactory(is_template_public=False)
        url = template_fork_url(private_form.id)
        payload = {
            "new_owner_type": AccountType.BUSINESS,
            "new_owner_id": str(business.id),
        }
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 403


# =============================================================================
# PUBLIC TEMPLATE LIBRARY VIEW
# =============================================================================


@pytest.mark.django_db
class TestPublicTemplateLibraryView:
    """Tests for GET /api/v1/forms/templates/library/"""

    def test_list_public_templates(self, authenticated_client, user):
        """GET returns only public templates (includes seeded system forms)."""
        PublicFormTemplateFactory(name="Public 1")
        PublicFormTemplateFactory(name="Public 2")
        FormTemplateFactory(name="Private", is_template_public=False)
        response = authenticated_client.get(PUBLIC_LIBRARY_URL)
        assert response.status_code == 200
        names = {r["name"] for r in response.data["results"]}
        assert "Public 1" in names
        assert "Public 2" in names
        assert "Private" not in names


# =============================================================================
# FORM FIELD ADD VIEW
# =============================================================================


@pytest.mark.django_db
class TestFormFieldAddView:
    """Tests for POST /api/v1/forms/templates/{form_id}/fields/"""

    def test_add_field(
        self, authenticated_client, owner_with_form_perms, draft_form,
    ):
        """Adding a valid field to a draft form returns 201."""
        url = template_fields_url(draft_form.id)
        payload = {
            "field_key": "full_name",
            "field_type": "text",
            "label": "Full Name",
            "order": 0,
        }
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 201
        assert response.data["field_key"] == "full_name"
        assert FormField.objects.filter(
            form_template=draft_form, field_key="full_name",
        ).exists()

    def test_add_field_duplicate_key_fails(
        self, authenticated_client, owner_with_form_perms, draft_form,
    ):
        """Adding a field with duplicate key returns 409 (ConflictError)."""
        FormFieldFactory(form_template=draft_form, field_key="email_field")
        url = template_fields_url(draft_form.id)
        payload = {
            "field_key": "email_field",
            "field_type": "email",
            "label": "Email Address",
            "order": 1,
        }
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 409


# =============================================================================
# FORM RESPONSE LIST VIEW
# =============================================================================


@pytest.mark.django_db
class TestFormResponseListView:
    """Tests for GET/POST /api/v1/forms/templates/{form_id}/responses/"""

    def test_list_responses(
        self, authenticated_client, owner_with_form_perms, active_form, user,
    ):
        """Listing responses for a form the user owns returns 200."""
        FormResponseFactory(
            form_template=active_form,
            submitted_by=user,
            data={"field_1": "answer"},
        )
        url = response_list_url(active_form.id)
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_create_response(
        self, authenticated_client, owner_with_form_perms, active_form,
    ):
        """Creating a response on an active form returns 201."""
        url = response_list_url(active_form.id)
        payload = {"data": {"field_1": "value1"}}
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 201
        assert response.data["status"] == ResponseStatus.DRAFT
        assert FormResponse.objects.filter(
            form_template=active_form,
        ).exists()


# =============================================================================
# FORM RESPONSE DETAIL VIEW
# =============================================================================


@pytest.mark.django_db
class TestFormResponseDetailView:
    """Tests for GET/PATCH /api/v1/forms/responses/{response_id}/"""

    def test_get_own_response(
        self, authenticated_client, owner_with_form_perms, draft_response,
    ):
        """Submitter can GET their own response."""
        url = response_detail_url(draft_response.id)
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.data["id"] == str(draft_response.id)

    def test_update_response(
        self, authenticated_client, owner_with_form_perms, draft_response,
    ):
        """Submitter can PATCH their own draft response with new data."""
        url = response_detail_url(draft_response.id)
        payload = {"data": {"field_1": "updated_value"}}
        response = authenticated_client.patch(url, payload, format="json")
        assert response.status_code == 200
        assert response.data["data"]["field_1"] == "updated_value"


# =============================================================================
# FORM RESPONSE SUBMIT VIEW
# =============================================================================


@pytest.mark.django_db
class TestFormResponseSubmitView:
    """Tests for POST /api/v1/forms/responses/{response_id}/submit/"""

    def test_submit_response(
        self, authenticated_client, owner_with_form_perms, draft_response,
    ):
        """Submitting a draft response transitions to SUBMITTED."""
        url = response_submit_url(draft_response.id)
        response = authenticated_client.post(url)
        assert response.status_code == 200
        assert response.data["status"] == ResponseStatus.SUBMITTED
        draft_response.refresh_from_db()
        assert draft_response.status == ResponseStatus.SUBMITTED
        assert draft_response.submitted_at is not None


# =============================================================================
# FORM RESPONSE PROCESS VIEW
# =============================================================================


@pytest.mark.django_db
class TestFormResponseProcessView:
    """Tests for POST /api/v1/forms/responses/{response_id}/process/"""

    def test_process_response(
        self, authenticated_client, owner_with_form_perms, submitted_response,
    ):
        """Processing a submitted response transitions to PROCESSED with notes."""
        url = response_process_url(submitted_response.id)
        payload = {"notes": "Approved"}
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 200
        assert response.data["status"] == ResponseStatus.PROCESSED
        submitted_response.refresh_from_db()
        assert submitted_response.status == ResponseStatus.PROCESSED
        assert submitted_response.processor_notes == "Approved"
        assert submitted_response.processed_at is not None


# =============================================================================
# FORM RESPONSE VOID VIEW
# =============================================================================


@pytest.mark.django_db
class TestFormResponseVoidView:
    """Tests for POST /api/v1/forms/responses/{response_id}/void/"""

    def test_void_own_response(
        self, authenticated_client, owner_with_form_perms, draft_response,
    ):
        """Submitter can void their own draft response."""
        url = response_void_url(draft_response.id)
        payload = {"reason": "Test void"}
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 200
        assert response.data["status"] == ResponseStatus.VOID
        draft_response.refresh_from_db()
        assert draft_response.status == ResponseStatus.VOID

    def test_void_as_admin(
        self,
        api_client,
        owner_with_form_perms,
        another_user,
        active_form,
        user,
    ):
        """Admin (owner_with_form_perms user) can void another user's response."""
        other_response = FormResponseFactory(
            form_template=active_form,
            submitted_by=another_user,
            data={"field_1": "other_value"},
        )
        # Authenticate as the owner (user), not the submitter (another_user)
        api_client.force_authenticate(user=user)
        url = response_void_url(other_response.id)
        payload = {"reason": "Admin void"}
        response = api_client.post(url, payload, format="json")
        assert response.status_code == 200
        assert response.data["status"] == ResponseStatus.VOID


# =============================================================================
# MY RESPONSES VIEW
# =============================================================================


@pytest.mark.django_db
class TestMyResponsesView:
    """Tests for GET /api/v1/forms/me/responses/"""

    def test_list_my_responses(
        self, authenticated_client, user,
    ):
        """Authenticated user sees only their own responses."""
        active_tmpl = ActiveFormTemplateFactory()
        FormResponseFactory(
            form_template=active_tmpl,
            submitted_by=user,
            data={"q1": "a1"},
        )
        FormResponseFactory(
            form_template=active_tmpl,
            submitted_by=user,
            data={"q1": "a2"},
        )
        # Response by another user -- should NOT appear
        other_user = UserFactory(email="other_resp@test.com")
        FormResponseFactory(
            form_template=active_tmpl,
            submitted_by=other_user,
            data={"q1": "a3"},
        )
        response = authenticated_client.get(MY_RESPONSES_URL)
        assert response.status_code == 200
        assert response.data["count"] == 2


@pytest.mark.django_db
class TestSystemFormResponseCreation:
    """Tests for creating and submitting responses to system forms.

    System forms (owner_type='system', owner_id=None) must be accessible
    by any authenticated user without a membership check.
    """

    @pytest.fixture
    def system_form(self, db, user):
        """Create a system form template (like system-business-creation)."""
        return ActiveFormTemplateFactory(
            owner_type=OwnerType.SYSTEM,
            owner_id=None,
            scope=FormScope.PLATFORM,
            slug="test-system-form",
        )

    def test_create_response_for_system_form(
        self, authenticated_client, user, system_form,
    ):
        """Any authenticated user can create a response on a system form."""
        url = response_list_url(system_form.id)
        resp = authenticated_client.post(url, {"data": {}}, format="json")

        assert resp.status_code == 201
        assert str(resp.data["submitted_by"]) == str(user.id)

    def test_submit_response_for_system_form(
        self, authenticated_client, user, system_form,
    ):
        """Any authenticated user can submit their system form response."""
        draft = FormResponseFactory(
            form_template=system_form,
            submitted_by=user,
            data={},
        )
        url = response_submit_url(draft.id)
        resp = authenticated_client.post(url)

        assert resp.status_code == 200
        assert resp.data["status"] == ResponseStatus.SUBMITTED

    def test_account_form_still_requires_membership(
        self, authenticated_client, user,
    ):
        """Non-system forms still enforce the membership check."""
        from apps.rbac.tests.factories import BusinessAccountFactory

        other_business = BusinessAccountFactory()
        account_form = ActiveFormTemplateFactory(
            owner_type=AccountType.BUSINESS,
            owner_id=other_business.id,
            scope=FormScope.BUSINESS,
        )
        url = response_list_url(account_form.id)
        resp = authenticated_client.post(url, {"data": {}}, format="json")

        assert resp.status_code == 403


# =============================================================================
# FORM FIELD DETAIL VIEW (GET / PATCH / DELETE)
# =============================================================================


@pytest.mark.django_db
class TestFormFieldDetailView:
    """Tests for GET/PATCH/DELETE /api/v1/forms/templates/{template_id}/fields/{field_id}/"""

    def test_get_field_detail(
        self, authenticated_client, owner_with_form_perms, draft_form,
    ):
        """Authenticated member can retrieve a single field."""
        field = FormFieldFactory(
            form_template=draft_form, field_key="name_field", order=0,
        )
        url = field_detail_url(draft_form.id, field.id)
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.data["field_key"] == "name_field"

    def test_patch_field_updates_label(
        self, authenticated_client, owner_with_form_perms, draft_form,
    ):
        """PATCH updates the field label successfully."""
        field = FormFieldFactory(
            form_template=draft_form, field_key="email_field",
            label="Old Label", order=0,
        )
        url = field_detail_url(draft_form.id, field.id)
        payload = {"label": "New Label"}
        response = authenticated_client.patch(url, payload, format="json")
        assert response.status_code == 200
        assert response.data["label"] == "New Label"
        field.refresh_from_db()
        assert field.label == "New Label"

    def test_patch_field_updates_multiple_properties(
        self, authenticated_client, owner_with_form_perms, draft_form,
    ):
        """PATCH can update multiple properties at once."""
        field = FormFieldFactory(
            form_template=draft_form, field_key="multi_field",
            label="Old", placeholder="old placeholder", order=0,
        )
        url = field_detail_url(draft_form.id, field.id)
        payload = {
            "label": "Updated",
            "placeholder": "new placeholder",
            "is_required": True,
        }
        response = authenticated_client.patch(url, payload, format="json")
        assert response.status_code == 200
        assert response.data["label"] == "Updated"
        assert response.data["placeholder"] == "new placeholder"
        assert response.data["is_required"] is True

    def test_patch_field_non_draft_returns_400(
        self, authenticated_client, owner_with_form_perms, active_form,
    ):
        """PATCH on a non-draft form field returns 400."""
        field = FormFieldFactory(
            form_template=active_form, field_key="locked_field", order=0,
        )
        url = field_detail_url(active_form.id, field.id)
        payload = {"label": "Attempt Update"}
        response = authenticated_client.patch(url, payload, format="json")
        assert response.status_code == 400

    def test_delete_field_removes_it(
        self, authenticated_client, owner_with_form_perms, draft_form,
    ):
        """DELETE removes the field from the form."""
        field = FormFieldFactory(
            form_template=draft_form, field_key="to_delete", order=0,
        )
        url = field_detail_url(draft_form.id, field.id)
        response = authenticated_client.delete(url)
        assert response.status_code == 204
        assert not FormField.objects.filter(id=field.id).exists()

    def test_delete_field_reorders_remaining(
        self, authenticated_client, owner_with_form_perms, draft_form,
    ):
        """DELETE reorders remaining fields to close the gap."""
        f0 = FormFieldFactory(
            form_template=draft_form, field_key="field_0", order=0,
        )
        f1 = FormFieldFactory(
            form_template=draft_form, field_key="field_1", order=1,
        )
        f2 = FormFieldFactory(
            form_template=draft_form, field_key="field_2", order=2,
        )
        url = field_detail_url(draft_form.id, f1.id)
        response = authenticated_client.delete(url)
        assert response.status_code == 204
        f0.refresh_from_db()
        f2.refresh_from_db()
        assert f0.order == 0
        assert f2.order == 1  # was 2, now shifted down

    def test_delete_field_non_draft_returns_400(
        self, authenticated_client, owner_with_form_perms, active_form,
    ):
        """DELETE on a non-draft form field returns 400."""
        field = FormFieldFactory(
            form_template=active_form, field_key="locked_del", order=0,
        )
        url = field_detail_url(active_form.id, field.id)
        response = authenticated_client.delete(url)
        assert response.status_code == 400

    def test_field_unauthenticated_returns_401(
        self, api_client, draft_form,
    ):
        """Unauthenticated request to field endpoint returns 401."""
        field = FormFieldFactory(
            form_template=draft_form, field_key="auth_test", order=0,
        )
        url = field_detail_url(draft_form.id, field.id)
        response = api_client.get(url)
        assert response.status_code == 401
        response = api_client.patch(url, {"label": "X"}, format="json")
        assert response.status_code == 401
        response = api_client.delete(url)
        assert response.status_code == 401


# =============================================================================
# FORM FIELD REORDER VIEW
# =============================================================================


@pytest.mark.django_db
class TestFormFieldReorderView:
    """Tests for POST /api/v1/forms/templates/{template_id}/fields/reorder/"""

    def test_reorder_fields(
        self, authenticated_client, owner_with_form_perms, draft_form,
    ):
        """Reorder successfully updates field orders."""
        f0 = FormFieldFactory(
            form_template=draft_form, field_key="reorder_a", order=0,
        )
        f1 = FormFieldFactory(
            form_template=draft_form, field_key="reorder_b", order=1,
        )
        f2 = FormFieldFactory(
            form_template=draft_form, field_key="reorder_c", order=2,
        )
        url = field_reorder_url(draft_form.id)
        payload = {
            "fields": [
                {"field_id": str(f2.id), "order": 0},
                {"field_id": str(f0.id), "order": 1},
                {"field_id": str(f1.id), "order": 2},
            ],
        }
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 200
        f0.refresh_from_db()
        f1.refresh_from_db()
        f2.refresh_from_db()
        assert f2.order == 0
        assert f0.order == 1
        assert f1.order == 2

    def test_reorder_non_draft_returns_400(
        self, authenticated_client, owner_with_form_perms, active_form,
    ):
        """Reorder on a non-draft form returns 400."""
        field = FormFieldFactory(
            form_template=active_form, field_key="reorder_locked", order=0,
        )
        url = field_reorder_url(active_form.id)
        payload = {
            "fields": [{"field_id": str(field.id), "order": 0}],
        }
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 400

    def test_reorder_unauthenticated_returns_401(
        self, api_client, draft_form,
    ):
        """Unauthenticated request to reorder returns 401."""
        url = field_reorder_url(draft_form.id)
        payload = {"fields": []}
        response = api_client.post(url, payload, format="json")
        assert response.status_code == 401

    def test_reorder_invalid_field_id_returns_400(
        self, authenticated_client, owner_with_form_perms, draft_form,
    ):
        """Reorder with a field_id not belonging to the template returns 400."""
        import uuid
        fake_id = uuid.uuid4()
        url = field_reorder_url(draft_form.id)
        payload = {
            "fields": [{"field_id": str(fake_id), "order": 0}],
        }
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 400


# =============================================================================
# PLATFORM FORM VIEW SMOKE TESTS
# =============================================================================


@pytest.mark.django_db
class TestPlatformFormViews:
    """Smoke tests verifying form views work for platform account_type.

    Forms are fully owner-agnostic — these tests confirm the full chain
    (URL routing → membership check → service → response) works for
    account_type=platform.
    """

    def test_create_form_template_as_platform_member(
        self, authenticated_client, platform_owner_with_form_perms, platform,
    ):
        """POST to platform templates URL creates a form template."""
        url = template_list_url(AccountType.PLATFORM, platform.id)
        payload = {
            "name": "Platform Onboarding Form",
            "owner_type": "platform",
            "owner_id": str(platform.id),
            "scope": "platform",
        }
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 201
        assert response.data["name"] == "Platform Onboarding Form"
        assert response.data["status"] == FormStatus.DRAFT

    def test_list_form_templates_platform_context(
        self, authenticated_client, platform_owner_with_form_perms, platform, user,
    ):
        """GET returns templates owned by the platform."""
        FormTemplateFactory(
            owner_type=AccountType.PLATFORM,
            owner_id=platform.id,
            scope=FormScope.PLATFORM,
            created_by=user,
            name="Platform Form A",
        )
        FormTemplateFactory(
            owner_type=AccountType.PLATFORM,
            owner_id=platform.id,
            scope=FormScope.PLATFORM,
            created_by=user,
            name="Platform Form B",
        )
        url = template_list_url(AccountType.PLATFORM, platform.id)
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] == 2

    def test_non_platform_member_cannot_create(
        self, api_client, platform, another_user,
    ):
        """User without platform membership cannot create templates."""
        api_client.force_authenticate(user=another_user)
        url = template_list_url(AccountType.PLATFORM, platform.id)
        payload = {
            "name": "Unauthorized Form",
            "owner_type": "platform",
            "owner_id": str(platform.id),
            "scope": "platform",
        }
        response = api_client.post(url, payload, format="json")
        assert response.status_code == 403

    def test_platform_form_detail_includes_permissions(
        self, authenticated_client, platform_owner_with_form_perms, platform, user,
    ):
        """GET form detail for a platform-owned form includes _permissions."""
        form = ActiveFormTemplateFactory(
            owner_type=AccountType.PLATFORM,
            owner_id=platform.id,
            scope=FormScope.PLATFORM,
            created_by=user,
        )
        url = template_detail_url(form.id)
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert "_permissions" in response.data
        assert isinstance(response.data["_permissions"], dict)
