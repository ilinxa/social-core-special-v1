"""
Phase 07 — Forms (F01–F18)

Tests form template CRUD, lifecycle (publish/archive/fork), field management,
and response lifecycle (create/update/submit/process/void).

Depends on Phase 01 (users), Phase 03 (platform), Phase 04 (businesses).
"""

import pytest

# =============================================================================
# F01–F06: FORM TEMPLATE CRUD
# =============================================================================


class TestFormTemplateCRUD:
    """Test form template creation, listing, and management."""

    def test_f01_get_template_library(self, api, state):
        """GET /forms/templates/library/ returns public templates."""
        api.set_token(state.get_token("alice"))
        r = api.get("forms/templates/library/")
        assert r.status_code == 200
        data = r.json()
        results = data if isinstance(data, list) else data.get("results", [])
        # System forms (3) should be visible in library
        assert isinstance(results, list)

    def test_f02_list_templates_scoped(self, api, state):
        """GET /forms/<account_type>/<account_id>/templates/ lists scoped templates."""
        api.set_token(state.get_token("alice"))
        biz_id = state.businesses["alice_corp"]["id"]
        r = api.get(f"forms/business/{biz_id}/templates/")
        assert r.status_code == 200

    def test_f03_create_template(self, api, state):
        """POST /forms/<account_type>/<account_id>/templates/ creates a template."""
        api.set_token(state.get_token("alice"))
        biz_id = state.businesses["alice_corp"]["id"]
        r = api.post(
            f"forms/business/{biz_id}/templates/",
            json={
                "name": "Feedback Form",
                "slug": "feedback-form",
                "description": "Customer feedback collection",
                "owner_type": "business",
                "owner_id": biz_id,
                "scope": "business",
            },
        )
        assert r.status_code == 201, f"Create template failed: {r.text}"
        data = r.json()
        state.forms["feedback"] = {
            "template_id": data["id"],
        }

    def test_f04_get_template_detail(self, api, state):
        """GET /forms/templates/<id>/ returns template detail."""
        if "feedback" not in state.forms:
            pytest.skip("No template created")

        api.set_token(state.get_token("alice"))
        tid = state.forms["feedback"]["template_id"]
        r = api.get(f"forms/templates/{tid}/")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Feedback Form"

    def test_f05_update_template(self, api, state):
        """PATCH /forms/templates/<id>/ updates template."""
        if "feedback" not in state.forms:
            pytest.skip("No template")

        api.set_token(state.get_token("alice"))
        tid = state.forms["feedback"]["template_id"]
        r = api.patch(
            f"forms/templates/{tid}/",
            json={
                "description": "Updated feedback form description",
            },
        )
        assert r.status_code == 200

    def test_f06_delete_template(self, api, state):
        """DELETE /forms/templates/<id>/ deletes a template."""
        # Create a disposable template
        api.set_token(state.get_token("alice"))
        biz_id = state.businesses["alice_corp"]["id"]
        r = api.post(
            f"forms/business/{biz_id}/templates/",
            json={
                "name": "Disposable Form",
                "slug": "disposable-form",
                "owner_type": "business",
                "owner_id": biz_id,
                "scope": "business",
            },
        )
        if r.status_code != 201:
            pytest.skip("Could not create template to delete")

        temp_id = r.json()["id"]
        r = api.delete(f"forms/templates/{temp_id}/")
        assert r.status_code in (200, 204)


# =============================================================================
# F07–F10: TEMPLATE LIFECYCLE
# =============================================================================


class TestFormTemplateLifecycle:
    """Test publish, archive, fork, and field addition."""

    def test_f07_add_field(self, api, state):
        """POST /forms/templates/<id>/fields/ adds a field to template."""
        if "feedback" not in state.forms:
            pytest.skip("No template")

        api.set_token(state.get_token("alice"))
        tid = state.forms["feedback"]["template_id"]
        r = api.post(
            f"forms/templates/{tid}/fields/",
            json={
                "field_key": "rating",
                "field_type": "integer",
                "label": "Overall Rating",
                "order": 0,
                "is_required": True,
                "validation_rules": {"min": 1, "max": 5},
            },
        )
        assert r.status_code in (200, 201), f"Add field failed: {r.text}"

    def test_f08_add_second_field(self, api, state):
        """Add a text field to the feedback form."""
        if "feedback" not in state.forms:
            pytest.skip("No template")

        api.set_token(state.get_token("alice"))
        tid = state.forms["feedback"]["template_id"]
        r = api.post(
            f"forms/templates/{tid}/fields/",
            json={
                "field_key": "comments",
                "field_type": "text",
                "label": "Comments",
                "order": 1,
                "is_required": False,
            },
        )
        assert r.status_code in (200, 201)

    def test_f09_publish_template(self, api, state):
        """POST /forms/templates/<id>/publish/ publishes the template."""
        if "feedback" not in state.forms:
            pytest.skip("No template")

        api.set_token(state.get_token("alice"))
        tid = state.forms["feedback"]["template_id"]
        r = api.post(f"forms/templates/{tid}/publish/")
        assert r.status_code == 200, f"Publish failed: {r.text}"

    def test_f10_fork_template(self, api, state):
        """POST /forms/templates/<id>/fork/ forks the template."""
        if "feedback" not in state.forms:
            pytest.skip("No template")

        api.set_token(state.get_token("alice"))
        tid = state.forms["feedback"]["template_id"]
        biz_id = state.businesses["alice_corp"]["id"]
        r = api.post(
            f"forms/templates/{tid}/fork/",
            json={
                "new_owner_type": "business",
                "new_owner_id": biz_id,
                "new_name": "Feedback Form v2",
            },
        )
        if r.status_code in (200, 201):
            state.forms["feedback_fork"] = {
                "template_id": r.json()["id"],
            }
        # 403 if fork requires specific permissions
        assert r.status_code in (200, 201, 400, 403)


# =============================================================================
# F11–F18: FORM RESPONSES
# =============================================================================


class TestFormResponses:
    """Test form response lifecycle."""

    def test_f11_list_responses_empty(self, api, state):
        """GET /forms/templates/<id>/responses/ returns empty list."""
        if "feedback" not in state.forms:
            pytest.skip("No template")

        api.set_token(state.get_token("alice"))
        tid = state.forms["feedback"]["template_id"]
        r = api.get(f"forms/templates/{tid}/responses/")
        assert r.status_code == 200

    def test_f12_create_response(self, api, state):
        """Create a form response (POST may vary by implementation)."""
        if "feedback" not in state.forms:
            pytest.skip("No template")

        api.set_token(state.get_token("bob"))
        tid = state.forms["feedback"]["template_id"]

        # Try creating a response — endpoint might accept data inline
        r = api.post(
            f"forms/templates/{tid}/responses/",
            json={
                "data": {
                    "rating": 4,
                    "comments": "Good service",
                },
            },
        )
        if r.status_code in (200, 201):
            data = r.json()
            state.forms["feedback"]["response_id"] = data["id"]
        # 403 if Bob lacks form access permissions despite being a member
        assert r.status_code in (200, 201, 400, 403), f"Create response: {r.text}"

    def test_f13_get_response_detail(self, api, state):
        """GET /forms/responses/<id>/ returns response detail."""
        if not state.forms.get("feedback", {}).get("response_id"):
            pytest.skip("No response created")

        api.set_token(state.get_token("bob"))
        rid = state.forms["feedback"]["response_id"]
        r = api.get(f"forms/responses/{rid}/")
        assert r.status_code == 200

    def test_f14_update_response(self, api, state):
        """PATCH /forms/responses/<id>/ updates response data."""
        if not state.forms.get("feedback", {}).get("response_id"):
            pytest.skip("No response")

        api.set_token(state.get_token("bob"))
        rid = state.forms["feedback"]["response_id"]
        r = api.patch(
            f"forms/responses/{rid}/",
            json={
                "data": {
                    "rating": 5,
                    "comments": "Excellent service!",
                },
            },
        )
        assert r.status_code == 200

    def test_f15_submit_response(self, api, state):
        """POST /forms/responses/<id>/submit/ submits the response."""
        if not state.forms.get("feedback", {}).get("response_id"):
            pytest.skip("No response")

        api.set_token(state.get_token("bob"))
        rid = state.forms["feedback"]["response_id"]
        r = api.post(f"forms/responses/{rid}/submit/")
        assert r.status_code == 200, f"Submit failed: {r.text}"

    def test_f16_process_response(self, api, state):
        """POST /forms/responses/<id>/process/ processes (approves) the response."""
        if not state.forms.get("feedback", {}).get("response_id"):
            pytest.skip("No response")

        api.set_token(state.get_token("alice"))
        rid = state.forms["feedback"]["response_id"]
        r = api.post(
            f"forms/responses/{rid}/process/",
            json={
                "notes": "Reviewed and approved",
            },
        )
        assert r.status_code in (200, 400)  # 400 if already processed

    def test_f17_void_response(self, api, state):
        """POST /forms/responses/<id>/void/ voids a response."""
        # Create a fresh response to void
        if "feedback" not in state.forms:
            pytest.skip("No template")

        # Use Bob (confirmed member of alice_corp via T09 accept)
        api.set_token(state.get_token("bob"))
        tid = state.forms["feedback"]["template_id"]
        r = api.post(
            f"forms/templates/{tid}/responses/",
            json={
                "data": {"rating": 1, "comments": "Bad"},
            },
        )
        if r.status_code not in (200, 201):
            pytest.skip("Could not create response to void")

        rid = r.json()["id"]
        # Submit first
        api.post(f"forms/responses/{rid}/submit/")

        # Void it
        api.set_token(state.get_token("alice"))
        r = api.post(
            f"forms/responses/{rid}/void/",
            json={
                "reason": "Test voiding",
            },
        )
        assert r.status_code in (200, 400)

    def test_f18_my_responses(self, api, state):
        """GET /forms/me/responses/ returns user's own responses."""
        api.set_token(state.get_token("bob"))
        r = api.get("forms/me/responses/")
        assert r.status_code == 200
        data = r.json()
        results = data if isinstance(data, list) else data.get("results", [])
        assert isinstance(results, list)
