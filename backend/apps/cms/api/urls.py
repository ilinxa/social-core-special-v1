# apps/cms/api/urls.py
"""
CMS Admin URL Configuration
=============================
Admin API endpoints — requires authentication + RBAC permissions.

Include in project urls.py:
    path("api/v1/cms/admin/", include("apps.cms.api.urls", namespace="cms")),
"""

from django.urls import path

from apps.cms.api import views

app_name = "cms"

urlpatterns = [
    # Sites
    path(
        "sites/", views.AdminSiteListCreateView.as_view(), name="admin-site-list-create"
    ),
    path(
        "sites/<slug:slug>/",
        views.AdminSiteDetailView.as_view(),
        name="admin-site-detail",
    ),
    # Pages
    path(
        "pages/", views.AdminPageListCreateView.as_view(), name="admin-page-list-create"
    ),
    path(
        "pages/<slug:slug>/",
        views.AdminPageDetailView.as_view(),
        name="admin-page-detail",
    ),
    path(
        "pages/<slug:slug>/publish/",
        views.AdminPagePublishView.as_view(),
        name="admin-page-publish",
    ),
    path(
        "pages/<slug:slug>/unpublish/",
        views.AdminPageUnpublishView.as_view(),
        name="admin-page-unpublish",
    ),
    path(
        "pages/<slug:slug>/export/",
        views.AdminPageExportView.as_view(),
        name="admin-page-export",
    ),
    path(
        "pages/<slug:slug>/import/",
        views.AdminPageImportView.as_view(),
        name="admin-page-import",
    ),
    # Templates — Sections
    path(
        "templates/sections/",
        views.AdminSectionTemplateListCreateView.as_view(),
        name="admin-section-template-list-create",
    ),
    # Templates — Blocks
    path(
        "templates/blocks/",
        views.AdminBlockTemplateListCreateView.as_view(),
        name="admin-block-template-list-create",
    ),
    # Block Placements (content)
    path(
        "block-placements/<uuid:uuid>/",
        views.AdminBlockPlacementDetailView.as_view(),
        name="admin-block-placement-detail",
    ),
    path(
        "block-placements/<uuid:uuid>/history/",
        views.AdminBlockPlacementHistoryView.as_view(),
        name="admin-block-placement-history",
    ),
    path(
        "block-placements/<uuid:uuid>/rollback/<int:version_number>/",
        views.AdminBlockPlacementRollbackView.as_view(),
        name="admin-block-placement-rollback",
    ),
    # Media
    path(
        "media/files/",
        views.AdminMediaFileListCreateView.as_view(),
        name="admin-media-file-list-create",
    ),
    path(
        "media/files/<uuid:uuid>/",
        views.AdminMediaFileDetailView.as_view(),
        name="admin-media-file-detail",
    ),
    # API Keys
    path(
        "api-keys/",
        views.AdminApiKeyListCreateView.as_view(),
        name="admin-api-key-list-create",
    ),
    path(
        "api-keys/<uuid:uuid>/",
        views.AdminApiKeyDetailView.as_view(),
        name="admin-api-key-detail",
    ),
]
