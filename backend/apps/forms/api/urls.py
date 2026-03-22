from django.urls import path

from apps.forms.api.views import (
    FormFieldAddView,
    FormFieldDetailView,
    FormFieldReorderView,
    FormFileUploadView,
    FormResponseDetailView,
    FormResponseListView,
    FormResponseProcessView,
    FormResponseSubmitView,
    FormResponseVoidView,
    FormTemplateArchiveView,
    FormTemplateCreateDraftView,
    FormTemplateDetailView,
    FormTemplateForkView,
    FormTemplateListView,
    FormTemplatePublishView,
    FormTemplateUnarchiveView,
    MyResponsesView,
    PublicTemplateLibraryView,
    SystemFormTemplateView,
)

app_name = "forms"

urlpatterns = [
    # System template lookup by slug
    path(
        "templates/system/<str:slug>/",
        SystemFormTemplateView.as_view(),
        name="system-template",
    ),
    # Public template library
    path(
        "templates/library/",
        PublicTemplateLibraryView.as_view(),
        name="template-library",
    ),
    # Form templates (scoped by account)
    path(
        "<str:account_type>/<uuid:account_id>/templates/",
        FormTemplateListView.as_view(),
        name="template-list",
    ),
    # Form template operations
    path(
        "templates/<uuid:form_id>/",
        FormTemplateDetailView.as_view(),
        name="template-detail",
    ),
    path(
        "templates/<uuid:form_id>/publish/",
        FormTemplatePublishView.as_view(),
        name="template-publish",
    ),
    path(
        "templates/<uuid:form_id>/archive/",
        FormTemplateArchiveView.as_view(),
        name="template-archive",
    ),
    path(
        "templates/<uuid:form_id>/unarchive/",
        FormTemplateUnarchiveView.as_view(),
        name="template-unarchive",
    ),
    path(
        "templates/<uuid:form_id>/edit-draft/",
        FormTemplateCreateDraftView.as_view(),
        name="template-edit-draft",
    ),
    path(
        "templates/<uuid:form_id>/fork/",
        FormTemplateForkView.as_view(),
        name="template-fork",
    ),
    path(
        "templates/<uuid:form_id>/fields/",
        FormFieldAddView.as_view(),
        name="field-add",
    ),
    path(
        "templates/<uuid:template_id>/fields/reorder/",
        FormFieldReorderView.as_view(),
        name="field-reorder",
    ),
    path(
        "templates/<uuid:template_id>/fields/<uuid:field_id>/",
        FormFieldDetailView.as_view(),
        name="field-detail",
    ),
    # Form responses
    path(
        "templates/<uuid:form_id>/responses/",
        FormResponseListView.as_view(),
        name="response-list",
    ),
    path(
        "responses/<uuid:response_id>/",
        FormResponseDetailView.as_view(),
        name="response-detail",
    ),
    path(
        "responses/<uuid:response_id>/submit/",
        FormResponseSubmitView.as_view(),
        name="response-submit",
    ),
    path(
        "responses/<uuid:response_id>/process/",
        FormResponseProcessView.as_view(),
        name="response-process",
    ),
    path(
        "responses/<uuid:response_id>/void/",
        FormResponseVoidView.as_view(),
        name="response-void",
    ),
    # User's own responses
    path("me/responses/", MyResponsesView.as_view(), name="my-responses"),
    # File upload for form fields
    path("upload/", FormFileUploadView.as_view(), name="file-upload"),
]
