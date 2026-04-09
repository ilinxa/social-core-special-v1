# apps/cms/api/urls_business.py
"""
CMS Business URL Configuration
================================
Business-scoped API endpoints — requires authentication + business membership
+ business.cms.enabled feature gate + business.cms_enabled flag.

URL kwarg: <slug:business_slug> — resolved by BusinessContextMixin.get_business().

Include in urls/cms.py:
    path("api/v1/cms/business/", include("apps.cms.api.urls_business", namespace="cms-business")),
"""

from django.urls import path

from apps.cms.api import views_business as views

app_name = "cms-business"

urlpatterns = [
    # Template Catalog (browse available templates)
    path(
        "<slug:business_slug>/catalog/sections/",
        views.BusinessCatalogSectionView.as_view(),
        name="catalog-sections",
    ),
    path(
        "<slug:business_slug>/catalog/blocks/",
        views.BusinessCatalogBlockView.as_view(),
        name="catalog-blocks",
    ),
    # Template Library (manage activations)
    path(
        "<slug:business_slug>/library/sections/",
        views.BusinessLibrarySectionListCreateView.as_view(),
        name="library-sections-list-create",
    ),
    path(
        "<slug:business_slug>/library/sections/<uuid:uuid>/",
        views.BusinessLibrarySectionDetailView.as_view(),
        name="library-sections-detail",
    ),
    path(
        "<slug:business_slug>/library/blocks/",
        views.BusinessLibraryBlockListCreateView.as_view(),
        name="library-blocks-list-create",
    ),
    path(
        "<slug:business_slug>/library/blocks/<uuid:uuid>/",
        views.BusinessLibraryBlockDetailView.as_view(),
        name="library-blocks-detail",
    ),
    # Sites
    path(
        "<slug:business_slug>/sites/",
        views.BusinessSiteListCreateView.as_view(),
        name="site-list-create",
    ),
    path(
        "<slug:business_slug>/sites/<slug:slug>/",
        views.BusinessSiteDetailView.as_view(),
        name="site-detail",
    ),
    # Pages
    path(
        "<slug:business_slug>/pages/",
        views.BusinessPageListCreateView.as_view(),
        name="page-list-create",
    ),
    path(
        "<slug:business_slug>/pages/<slug:slug>/",
        views.BusinessPageDetailView.as_view(),
        name="page-detail",
    ),
    path(
        "<slug:business_slug>/pages/<slug:slug>/publish/",
        views.BusinessPagePublishView.as_view(),
        name="page-publish",
    ),
    path(
        "<slug:business_slug>/pages/<slug:slug>/unpublish/",
        views.BusinessPageUnpublishView.as_view(),
        name="page-unpublish",
    ),
    path(
        "<slug:business_slug>/pages/<slug:slug>/export/",
        views.BusinessPageExportView.as_view(),
        name="page-export",
    ),
    path(
        "<slug:business_slug>/pages/<slug:slug>/import/",
        views.BusinessPageImportView.as_view(),
        name="page-import",
    ),
    # Block Placements
    path(
        "<slug:business_slug>/block-placements/<uuid:uuid>/",
        views.BusinessBlockPlacementDetailView.as_view(),
        name="block-placement-detail",
    ),
    path(
        "<slug:business_slug>/block-placements/<uuid:uuid>/history/",
        views.BusinessBlockPlacementHistoryView.as_view(),
        name="block-placement-history",
    ),
    path(
        "<slug:business_slug>/block-placements/<uuid:uuid>/rollback/<int:version_number>/",
        views.BusinessBlockPlacementRollbackView.as_view(),
        name="block-placement-rollback",
    ),
    # Media
    path(
        "<slug:business_slug>/media/files/",
        views.BusinessMediaFileListCreateView.as_view(),
        name="media-file-list-create",
    ),
    path(
        "<slug:business_slug>/media/files/<uuid:uuid>/",
        views.BusinessMediaFileDetailView.as_view(),
        name="media-file-detail",
    ),
    # API Keys
    path(
        "<slug:business_slug>/api-keys/",
        views.BusinessApiKeyListCreateView.as_view(),
        name="api-key-list-create",
    ),
    path(
        "<slug:business_slug>/api-keys/<uuid:uuid>/",
        views.BusinessApiKeyDetailView.as_view(),
        name="api-key-detail",
    ),
]
