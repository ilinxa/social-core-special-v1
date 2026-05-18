import uuid
from uuid import UUID

from django.core.files.storage import default_storage
from drf_spectacular.utils import extend_schema
from rest_framework import status as http_status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination
from apps.core.permissions import FeatureRequired, IsAuthenticated
from apps.core.views import PermissionInjectMixin
from apps.forms.api.serializers import (
    ForkTemplateInputSerializer,
    FormFieldCreateInputSerializer,
    FormFieldOutputSerializer,
    FormResponseCreateInputSerializer,
    FormResponseDetailOutputSerializer,
    FormResponseListOutputSerializer,
    FormResponseProcessInputSerializer,
    FormResponseUpdateInputSerializer,
    FormResponseVoidInputSerializer,
    FormTemplateCreateInputSerializer,
    FormTemplateDetailOutputSerializer,
    FormTemplateListOutputSerializer,
    FormTemplateUpdateInputSerializer,
    ReorderFieldsInputSerializer,
    UpdateFieldInputSerializer,
)
from apps.forms.policies import FormResponsePolicy, FormTemplatePolicy
from apps.forms.selectors import (
    FormFieldSelector,
    FormResponseSelector,
    FormTemplateSelector,
)
from apps.forms.services import FormBuilderService, FormResponseService
from apps.rbac.selectors import MembershipSelector
from apps.rbac.services import RBACService


class FormViewMixin:
    """Resolve membership and ActorContext for form views."""

    _FORMS_GATE_PATHS = {
        "business": "business.forms.enabled",
        "platform": "platform.forms",
    }

    def _check_forms_feature_gate(self, account_type):
        """FG module gate: check forms feature for the account type."""
        path = self._FORMS_GATE_PATHS.get(account_type)
        if path:
            from apps.core.exceptions import FeatureDisabled
            from apps.core.feature_config import feature_config

            if not feature_config.is_feature_enabled(path):
                raise FeatureDisabled(feature=path)

    def get_membership_or_403(self, request, account_type, account_id):
        self._check_forms_feature_gate(account_type)
        membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=account_type,
            account_id=account_id,
        )
        if not membership:
            from apps.core.exceptions import PermissionDenied

            raise PermissionDenied(
                message="Not a member of this account",
                action="access",
                resource="FormTemplate",
            )
        return membership

    def get_actor_context(self, membership, request):
        return RBACService.build_actor_context(
            membership=membership,
            request=request,
        )

    def resolve_form_context(self, request, form):
        """
        Resolve membership and actor context for form operations.

        System forms: any authenticated user gets user-level context (no membership).
        Account forms: requires active membership in the owning account.

        Returns: (membership_or_None, actor_context)
        """
        if form.is_system_form:
            from apps.core.types import ActorContext

            return None, ActorContext.for_user_context(request.user, request)

        membership = self.get_membership_or_403(
            request,
            form.owner_type,
            form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)
        return membership, actor_context


# =============================================================================
# SYSTEM TEMPLATE LOOKUP
# =============================================================================


class SystemFormTemplateView(APIView):
    """Look up a system form template by slug. Read-only, authenticated."""

    permission_classes = [IsAuthenticated, FeatureRequired("user.forms")]

    @extend_schema(
        summary="Get system form template by slug",
        responses={200: FormTemplateDetailOutputSerializer},
        tags=["Forms"],
    )
    def get(self, request, slug: str):
        from apps.core.constants import OwnerType

        form = FormTemplateSelector.get_by_slug(
            owner_type=OwnerType.SYSTEM,
            owner_id=None,
            slug=slug,
        )
        # Prefetch fields
        form = FormTemplateSelector.get_with_fields(form_template_id=form.id)
        serializer = FormTemplateDetailOutputSerializer(form)
        return Response(serializer.data)


# =============================================================================
# FORM TEMPLATE VIEWS
# =============================================================================


class FormTemplateListView(FormViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List form templates",
        responses={200: FormTemplateListOutputSerializer(many=True)},
        tags=["Forms"],
    )
    def get(self, request, account_type: str, account_id: UUID):
        self.get_membership_or_403(request, account_type, account_id)
        forms = FormTemplateSelector.list_by_owner(
            owner_type=account_type,
            owner_id=account_id,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(forms, request)
        serializer = FormTemplateListOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create form template",
        request=FormTemplateCreateInputSerializer,
        responses={201: FormTemplateDetailOutputSerializer},
        tags=["Forms"],
    )
    def post(self, request, account_type: str, account_id: UUID):
        input_serializer = FormTemplateCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        membership = self.get_membership_or_403(request, account_type, account_id)
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_create_form(
            actor_context=actor_context,
            owner_type=input_serializer.validated_data["owner_type"],
        )

        form = FormBuilderService.create_form_template(
            actor_context=actor_context,
            actor=membership.user,
            request=request,
            **input_serializer.validated_data,
        )

        output = FormTemplateDetailOutputSerializer(form)
        return Response(output.data, status=http_status.HTTP_201_CREATED)


class FormTemplateDetailView(PermissionInjectMixin, FormViewMixin, APIView):
    permission_classes = [IsAuthenticated]
    policy_class = FormTemplatePolicy

    def _build_policy_kwargs(self):
        return {
            "actor_context": self._actor_context,
            "form_template": self._form_template,
        }

    @extend_schema(
        summary="Get form template details",
        responses={200: FormTemplateDetailOutputSerializer},
        tags=["Forms"],
    )
    def get(self, request, form_id: UUID):
        form = FormTemplateSelector.get_with_fields(form_template_id=form_id)
        self._form_template = form

        if form.is_template_public:
            from apps.core.types import ActorContext

            membership = MembershipSelector.get_active_membership_for_user_account(
                user=request.user,
                account_type=form.owner_type,
                account_id=form.owner_id,
            )
            if membership:
                self._actor_context = RBACService.build_actor_context(
                    membership=membership,
                    request=request,
                )
            else:
                self._actor_context = ActorContext.for_user_context(
                    request.user, request
                )
        else:
            membership = self.get_membership_or_403(
                request, form.owner_type, form.owner_id
            )
            self._actor_context = self.get_actor_context(membership, request)

        self._inject_permissions = True
        serializer = FormTemplateDetailOutputSerializer(form)
        return Response(serializer.data)

    @extend_schema(
        summary="Update form template",
        request=FormTemplateUpdateInputSerializer,
        responses={200: FormTemplateDetailOutputSerializer},
        tags=["Forms"],
    )
    def patch(self, request, form_id: UUID):
        form = FormTemplateSelector.get_by_id(form_template_id=form_id)
        membership = self.get_membership_or_403(
            request,
            form.owner_type,
            form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_edit_form(
            actor_context=actor_context,
            form_template=form,
        )

        input_serializer = FormTemplateUpdateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        form = FormBuilderService.update_form_template(
            form_template=form,
            updated_by=membership.user,
            request=request,
            **input_serializer.validated_data,
        )

        output = FormTemplateDetailOutputSerializer(form)
        return Response(output.data)

    @extend_schema(
        summary="Delete form template",
        responses={204: None},
        tags=["Forms"],
    )
    def delete(self, request, form_id: UUID):
        form = FormTemplateSelector.get_by_id(form_template_id=form_id)
        membership = self.get_membership_or_403(
            request,
            form.owner_type,
            form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_delete_form(
            actor_context=actor_context,
            form_template=form,
        )

        FormBuilderService.delete_form(
            form_template=form,
            deleted_by=membership.user,
            request=request,
        )

        return Response(status=http_status.HTTP_204_NO_CONTENT)


class FormTemplatePublishView(FormViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Publish form template",
        responses={200: FormTemplateDetailOutputSerializer},
        tags=["Forms"],
    )
    def post(self, request, form_id: UUID):
        form = FormTemplateSelector.get_by_id(form_template_id=form_id)
        membership = self.get_membership_or_403(
            request,
            form.owner_type,
            form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_publish_form(
            actor_context=actor_context,
            form_template=form,
        )

        form = FormBuilderService.publish_form(
            form_template=form,
            published_by=membership.user,
            request=request,
        )

        serializer = FormTemplateDetailOutputSerializer(form)
        return Response(serializer.data)


class FormTemplateArchiveView(FormViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Archive form template",
        responses={200: FormTemplateDetailOutputSerializer},
        tags=["Forms"],
    )
    def post(self, request, form_id: UUID):
        form = FormTemplateSelector.get_by_id(form_template_id=form_id)
        membership = self.get_membership_or_403(
            request,
            form.owner_type,
            form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_archive_form(
            actor_context=actor_context,
            form_template=form,
        )

        form = FormBuilderService.archive_form(
            form_template=form,
            archived_by=membership.user,
            request=request,
        )

        serializer = FormTemplateDetailOutputSerializer(form)
        return Response(serializer.data)


class FormTemplateUnarchiveView(FormViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Restore archived form template to draft",
        responses={200: FormTemplateDetailOutputSerializer},
        tags=["Forms"],
    )
    def post(self, request, form_id: UUID):
        form = FormTemplateSelector.get_by_id(form_template_id=form_id)
        membership = self.get_membership_or_403(
            request,
            form.owner_type,
            form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_edit_form(
            actor_context=actor_context,
            form_template=form,
        )

        form = FormBuilderService.unarchive_form(
            form_template=form,
            unarchived_by=membership.user,
            request=request,
        )

        serializer = FormTemplateDetailOutputSerializer(form)
        return Response(serializer.data)


class FormTemplateCreateDraftView(FormViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Create edit draft from active form",
        description="Create a new DRAFT version (v+1) from an active form for editing fields.",
        responses={201: FormTemplateDetailOutputSerializer},
        tags=["Forms"],
    )
    def post(self, request, form_id: UUID):
        form = FormTemplateSelector.get_by_id(form_template_id=form_id)
        membership = self.get_membership_or_403(
            request,
            form.owner_type,
            form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_edit_form(
            actor_context=actor_context,
            form_template=form,
        )

        new_draft = FormBuilderService.create_edit_draft(
            form_template=form,
            created_by=membership.user,
            request=request,
        )

        serializer = FormTemplateDetailOutputSerializer(new_draft)
        return Response(serializer.data, status=http_status.HTTP_201_CREATED)


class FormTemplateForkView(FormViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Fork a public template",
        request=ForkTemplateInputSerializer,
        responses={201: FormTemplateDetailOutputSerializer},
        tags=["Forms"],
    )
    def post(self, request, form_id: UUID):
        source = FormTemplateSelector.get_by_id(form_template_id=form_id)
        input_serializer = ForkTemplateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        membership = self.get_membership_or_403(
            request,
            data["new_owner_type"],
            data["new_owner_id"],
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_fork_template(actor_context=actor_context)

        forked = FormBuilderService.fork_template(
            source_template=source,
            actor_context=actor_context,
            actor=membership.user,
            request=request,
            **data,
        )

        serializer = FormTemplateDetailOutputSerializer(forked)
        return Response(serializer.data, status=http_status.HTTP_201_CREATED)


class PublicTemplateLibraryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List public templates",
        responses={200: FormTemplateListOutputSerializer(many=True)},
        tags=["Forms"],
    )
    def get(self, request):
        scope = request.query_params.get("scope")
        templates = FormTemplateSelector.list_public_templates(scope=scope)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(templates, request)
        serializer = FormTemplateListOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class FormFieldAddView(FormViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Add field to form",
        request=FormFieldCreateInputSerializer,
        responses={201: FormFieldOutputSerializer},
        tags=["Forms"],
    )
    def post(self, request, form_id: UUID):
        form = FormTemplateSelector.get_by_id(form_template_id=form_id)
        membership = self.get_membership_or_403(
            request,
            form.owner_type,
            form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_edit_form(
            actor_context=actor_context,
            form_template=form,
        )

        input_serializer = FormFieldCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        field = FormBuilderService.add_field(
            form_template=form,
            added_by=membership.user,
            request=request,
            **input_serializer.validated_data,
        )

        serializer = FormFieldOutputSerializer(field)
        return Response(serializer.data, status=http_status.HTTP_201_CREATED)


class FormFieldDetailView(FormViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get field details",
        responses={200: FormFieldOutputSerializer},
        tags=["Forms"],
    )
    def get(self, request, template_id: UUID, field_id: UUID):
        field = FormFieldSelector.get_by_id(field_id=field_id)
        if field.form_template_id != template_id:
            from apps.core.exceptions import NotFound

            raise NotFound(resource="FormField", resource_id=field_id)

        form = field.form_template
        self.get_membership_or_403(
            request,
            form.owner_type,
            form.owner_id,
        )
        serializer = FormFieldOutputSerializer(field)
        return Response(serializer.data)

    @extend_schema(
        summary="Update form field",
        request=UpdateFieldInputSerializer,
        responses={200: FormFieldOutputSerializer},
        tags=["Forms"],
    )
    def patch(self, request, template_id: UUID, field_id: UUID):
        field = FormFieldSelector.get_by_id(field_id=field_id)
        if field.form_template_id != template_id:
            from apps.core.exceptions import NotFound

            raise NotFound(resource="FormField", resource_id=field_id)

        form = field.form_template
        membership = self.get_membership_or_403(
            request,
            form.owner_type,
            form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_edit_form(
            actor_context=actor_context,
            form_template=form,
        )

        input_serializer = UpdateFieldInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        field = FormBuilderService.update_field(
            field=field,
            updated_by=membership.user,
            request=request,
            data=input_serializer.validated_data,
        )

        serializer = FormFieldOutputSerializer(field)
        return Response(serializer.data)

    @extend_schema(
        summary="Delete form field",
        responses={204: None},
        tags=["Forms"],
    )
    def delete(self, request, template_id: UUID, field_id: UUID):
        field = FormFieldSelector.get_by_id(field_id=field_id)
        if field.form_template_id != template_id:
            from apps.core.exceptions import NotFound

            raise NotFound(resource="FormField", resource_id=field_id)

        form = field.form_template
        membership = self.get_membership_or_403(
            request,
            form.owner_type,
            form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_edit_form(
            actor_context=actor_context,
            form_template=form,
        )

        FormBuilderService.delete_field(
            field=field,
            deleted_by=membership.user,
            request=request,
        )

        return Response(status=http_status.HTTP_204_NO_CONTENT)


class FormFieldReorderView(FormViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Reorder form fields",
        request=ReorderFieldsInputSerializer,
        responses={200: FormFieldOutputSerializer(many=True)},
        tags=["Forms"],
    )
    def post(self, request, template_id: UUID):
        form = FormTemplateSelector.get_by_id(form_template_id=template_id)
        membership = self.get_membership_or_403(
            request,
            form.owner_type,
            form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_edit_form(
            actor_context=actor_context,
            form_template=form,
        )

        input_serializer = ReorderFieldsInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        fields = FormBuilderService.reorder_fields(
            form_template=form,
            field_orders=input_serializer.validated_data["fields"],
            reordered_by=membership.user,
            request=request,
        )

        serializer = FormFieldOutputSerializer(fields, many=True)
        return Response(serializer.data)


# =============================================================================
# FORM RESPONSE VIEWS
# =============================================================================


class FormResponseListView(FormViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List responses for a form",
        responses={200: FormResponseListOutputSerializer(many=True)},
        tags=["Form Responses"],
    )
    def get(self, request, form_id: UUID):
        form = FormTemplateSelector.get_by_id(form_template_id=form_id)
        membership = self.get_membership_or_403(
            request,
            form.owner_type,
            form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_view_responses(
            actor_context=actor_context,
            form_template=form,
        )

        status_filter = request.query_params.get("status")
        responses = FormResponseSelector.list_by_form(
            form_template_id=form_id,
            status=status_filter,
        )

        paginator = StandardPagination()
        page = paginator.paginate_queryset(responses, request)
        serializer = FormResponseListOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create form response",
        request=FormResponseCreateInputSerializer,
        responses={201: FormResponseDetailOutputSerializer},
        tags=["Form Responses"],
    )
    def post(self, request, form_id: UUID):
        form = FormTemplateSelector.get_by_id(form_template_id=form_id)
        input_serializer = FormResponseCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        membership, actor_context = self.resolve_form_context(request, form)
        actor = membership.user if membership else request.user

        response = FormResponseService.create_response(
            form_template=form,
            actor_context=actor_context,
            actor=actor,
            request=request,
            **input_serializer.validated_data,
        )

        output = FormResponseDetailOutputSerializer(response)
        return Response(output.data, status=http_status.HTTP_201_CREATED)


class FormResponseDetailView(PermissionInjectMixin, APIView):
    permission_classes = [IsAuthenticated]
    policy_class = FormResponsePolicy

    def _build_policy_kwargs(self) -> dict:
        return {
            "user": self.request.user,
            "response": self._response,
            "actor_context": getattr(self, "_actor_context", None),
        }

    @extend_schema(
        summary="Get response details",
        responses={200: FormResponseDetailOutputSerializer},
        tags=["Form Responses"],
    )
    def get(self, request, response_id: UUID):
        response = FormResponseSelector.get_by_id(response_id=response_id)
        actor_context = None
        if response.submitted_by_id != request.user.id:
            form = response.form_template
            membership = MembershipSelector.get_active_membership_for_user_account(
                user=request.user,
                account_type=form.owner_type,
                account_id=form.owner_id,
            )
            if not membership:
                from apps.core.exceptions import PermissionDenied

                raise PermissionDenied(
                    message="Not a member of this account",
                    action="view",
                    resource="FormResponse",
                )
            actor_context = RBACService.build_actor_context(
                membership=membership,
                request=request,
            )
            FormTemplatePolicy.can_view_responses(
                actor_context=actor_context,
                form_template=form,
            )

        self._response = response
        self._actor_context = actor_context
        self._inject_permissions = True

        serializer = FormResponseDetailOutputSerializer(response)
        return Response(serializer.data)

    @extend_schema(
        summary="Update response data",
        request=FormResponseUpdateInputSerializer,
        responses={200: FormResponseDetailOutputSerializer},
        tags=["Form Responses"],
    )
    def patch(self, request, response_id: UUID):
        response = FormResponseSelector.get_by_id(response_id=response_id)
        FormResponsePolicy.can_edit_response(
            user=request.user,
            response=response,
        )
        input_serializer = FormResponseUpdateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        response = FormResponseService.update_response(
            response=response,
            updated_by=request.user,
            request=request,
            **input_serializer.validated_data,
        )

        output = FormResponseDetailOutputSerializer(response)
        return Response(output.data)


class FormResponseSubmitView(FormViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Submit response",
        responses={200: FormResponseDetailOutputSerializer},
        tags=["Form Responses"],
    )
    def post(self, request, response_id: UUID):
        response = FormResponseSelector.get_by_id(response_id=response_id)
        FormResponsePolicy.can_edit_response(
            user=request.user,
            response=response,
        )
        form = response.form_template

        membership, actor_context = self.resolve_form_context(request, form)
        actor = membership.user if membership else request.user

        response = FormResponseService.submit_response(
            response=response,
            actor_context=actor_context,
            actor=actor,
            request=request,
        )

        serializer = FormResponseDetailOutputSerializer(response)
        return Response(serializer.data)


class FormResponseProcessView(FormViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Process response",
        request=FormResponseProcessInputSerializer,
        responses={200: FormResponseDetailOutputSerializer},
        tags=["Form Responses"],
    )
    def post(self, request, response_id: UUID):
        response = FormResponseSelector.get_by_id(response_id=response_id)
        form = response.form_template
        membership = self.get_membership_or_403(
            request,
            form.owner_type,
            form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormResponsePolicy.can_process_response(
            actor_context=actor_context,
            response=response,
        )

        input_serializer = FormResponseProcessInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        response = FormResponseService.process_response(
            response=response,
            processed_by=membership.user,
            request=request,
            **input_serializer.validated_data,
        )

        serializer = FormResponseDetailOutputSerializer(response)
        return Response(serializer.data)


class FormResponseVoidView(FormViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Void response",
        request=FormResponseVoidInputSerializer,
        responses={200: FormResponseDetailOutputSerializer},
        tags=["Form Responses"],
    )
    def post(self, request, response_id: UUID):
        response = FormResponseSelector.get_by_id(response_id=response_id)
        if response.submitted_by_id != request.user.id:
            form = response.form_template
            membership = self.get_membership_or_403(
                request,
                form.owner_type,
                form.owner_id,
            )
            actor_context = self.get_actor_context(membership, request)
            FormResponsePolicy.can_process_response(
                actor_context=actor_context,
                response=response,
            )

        input_serializer = FormResponseVoidInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        response = FormResponseService.void_response(
            response=response,
            voided_by=request.user,
            request=request,
            **input_serializer.validated_data,
        )

        serializer = FormResponseDetailOutputSerializer(response)
        return Response(serializer.data)


class MyResponsesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List my responses",
        responses={200: FormResponseListOutputSerializer(many=True)},
        tags=["Form Responses"],
    )
    def get(self, request):
        form_id = request.query_params.get("form_id")
        responses = FormResponseSelector.list_by_submitter(
            user_id=request.user.id,
            form_template_id=form_id,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(responses, request)
        serializer = FormResponseListOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


# =========================================================================
# FILE UPLOAD
# =========================================================================

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_FILE_TYPES = ALLOWED_IMAGE_TYPES | {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/csv",
}


class FormFileUploadView(APIView):
    """Upload a file for use in form responses.

    Accepts a single file via multipart/form-data.
    Returns the URL of the uploaded file.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    @extend_schema(
        summary="Upload file for form field",
        description="Upload a file to be referenced in a form response.",
        tags=["Form Responses"],
    )
    def post(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            from apps.core.exceptions import ValidationError

            raise ValidationError(
                message="No file provided",
                field="file",
            )

        # Size check
        if uploaded.size > MAX_UPLOAD_SIZE:
            from apps.core.exceptions import ValidationError

            raise ValidationError(
                message=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB.",
                field="file",
            )

        # Type check
        if uploaded.content_type not in ALLOWED_FILE_TYPES:
            from apps.core.exceptions import ValidationError

            raise ValidationError(
                message=f"File type '{uploaded.content_type}' is not allowed.",
                field="file",
            )

        # Generate unique path
        ext = uploaded.name.rsplit(".", 1)[-1] if "." in uploaded.name else ""
        filename = (
            f"form_uploads/{uuid.uuid4().hex}.{ext}"
            if ext
            else f"form_uploads/{uuid.uuid4().hex}"
        )

        saved_path = default_storage.save(filename, uploaded)
        file_url = default_storage.url(saved_path)

        return Response(
            {"url": file_url},
            status=http_status.HTTP_201_CREATED,
        )
