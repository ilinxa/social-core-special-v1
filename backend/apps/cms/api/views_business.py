# apps/cms/api/views_business.py
"""
CMS Business API Views
========================
Business-scoped CMS views. Uses BusinessContextMixin for org scoping.

Three-layer access check:
1. FeatureRequired("business.cms.enabled") — deployment allows business CMS
2. BusinessContextMixin.get_actor_context() — user is active business member
3. business.cms_enabled == True — THIS business has CMS
"""

from django.db.models import Count
from rest_framework import status as http_status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cms.api.serializers import (
    ApiKeyCreatedOutputSerializer,
    ApiKeyCreateSerializer,
    ApiKeyOutputSerializer,
    BlockActivationOutputSerializer,
    BlockPlacementOutputSerializer,
    ContentVersionOutputSerializer,
    DraftContentUpdateSerializer,
    MediaFileOutputSerializer,
    MediaUpdateSerializer,
    MediaUploadSerializer,
    PageCreateSerializer,
    PageDetailOutputSerializer,
    PageImportSerializer,
    PageOutputSerializer,
    SectionActivationOutputSerializer,
    SiteCreateSerializer,
    SiteOutputSerializer,
    SiteUpdateSerializer,
    TemplateActivationInputSerializer,
    TemplateCatalogBlockSerializer,
    TemplateCatalogSectionSerializer,
)
from apps.cms.policies import CMSPolicy
from apps.cms.selectors import (
    CMSApiKeySelector,
    CMSBlockPlacementSelector,
    CMSContentVersionSelector,
    CMSMediaSelector,
    CMSPageSelector,
    CMSSiteSelector,
    CMSTemplateActivationSelector,
)
from apps.cms.services import (
    CMSApiKeyService,
    CMSContentService,
    CMSMediaService,
    CMSPageService,
    CMSSiteService,
    CMSTemplateActivationService,
)
from apps.core.exceptions import FeatureDisabled
from apps.core.pagination import StandardPagination
from apps.core.permissions import FeatureRequired, IsAuthenticated
from apps.core.views import PermissionInjectMixin
from apps.rbac.views import BusinessContextMixin

_BusinessCmsGate = FeatureRequired("business.cms.enabled")


class BusinessCMSMixin(BusinessContextMixin):
    """
    Base mixin for all business CMS views.
    Checks: feature gate → business membership → cms_enabled flag.
    """

    permission_classes = [IsAuthenticated, _BusinessCmsGate]

    def get_actor_context(self):
        ctx = super().get_actor_context()
        business = self.get_business()
        if not business.cms_enabled:
            raise FeatureDisabled(feature="business.cms")
        return ctx


# ---------------------------------------------------------------------------
# Business — Template Catalog (browse available templates)
# ---------------------------------------------------------------------------


class BusinessCatalogSectionView(BusinessCMSMixin, APIView):
    """GET /api/v1/cms/business/<slug>/catalog/sections/ -> Browse eligible section templates."""

    def get(self, request, business_slug):
        actor_context = self.get_actor_context()
        templates = CMSTemplateActivationSelector.list_available_section_templates(
            org_type=actor_context.account_type,
            org_id=actor_context.account_id,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(templates, request)
        serializer = TemplateCatalogSectionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class BusinessCatalogBlockView(BusinessCMSMixin, APIView):
    """GET /api/v1/cms/business/<slug>/catalog/blocks/ -> Browse eligible block templates."""

    def get(self, request, business_slug):
        actor_context = self.get_actor_context()
        templates = CMSTemplateActivationSelector.list_available_block_templates(
            org_type=actor_context.account_type,
            org_id=actor_context.account_id,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(templates, request)
        serializer = TemplateCatalogBlockSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


# ---------------------------------------------------------------------------
# Business — Template Library (manage activations)
# ---------------------------------------------------------------------------


class BusinessLibrarySectionListCreateView(BusinessCMSMixin, APIView):
    """
    GET  -> List activated section templates
    POST -> Activate a section template
    """

    def get(self, request, business_slug):
        actor_context = self.get_actor_context()
        activations = CMSTemplateActivationSelector.list_activated_section_templates(
            org_type=actor_context.account_type,
            org_id=actor_context.account_id,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(activations, request)
        serializer = SectionActivationOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, business_slug):
        serializer = TemplateActivationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        activation = CMSTemplateActivationService.activate_section_template(
            actor_context=actor_context,
            template_id=serializer.validated_data["template_id"],
            request=request,
        )
        return Response(
            SectionActivationOutputSerializer(activation).data,
            status=http_status.HTTP_201_CREATED,
        )


class BusinessLibrarySectionDetailView(BusinessCMSMixin, APIView):
    """DELETE -> Deactivate a section template."""

    def delete(self, request, business_slug, uuid):
        actor_context = self.get_actor_context()
        CMSTemplateActivationService.deactivate_section_template(
            actor_context=actor_context,
            activation_id=uuid,
            request=request,
        )
        return Response(status=http_status.HTTP_204_NO_CONTENT)


class BusinessLibraryBlockListCreateView(BusinessCMSMixin, APIView):
    """
    GET  -> List activated block templates
    POST -> Activate a block template
    """

    def get(self, request, business_slug):
        actor_context = self.get_actor_context()
        activations = CMSTemplateActivationSelector.list_activated_block_templates(
            org_type=actor_context.account_type,
            org_id=actor_context.account_id,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(activations, request)
        serializer = BlockActivationOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, business_slug):
        serializer = TemplateActivationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        activation = CMSTemplateActivationService.activate_block_template(
            actor_context=actor_context,
            template_id=serializer.validated_data["template_id"],
            request=request,
        )
        return Response(
            BlockActivationOutputSerializer(activation).data,
            status=http_status.HTTP_201_CREATED,
        )


class BusinessLibraryBlockDetailView(BusinessCMSMixin, APIView):
    """DELETE -> Deactivate a block template."""

    def delete(self, request, business_slug, uuid):
        actor_context = self.get_actor_context()
        CMSTemplateActivationService.deactivate_block_template(
            actor_context=actor_context,
            activation_id=uuid,
            request=request,
        )
        return Response(status=http_status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Business — Sites
# ---------------------------------------------------------------------------


class BusinessSiteListCreateView(BusinessCMSMixin, APIView):
    """
    GET  -> List business's sites
    POST -> Create site for business
    """

    def get(self, request, business_slug):
        actor_context = self.get_actor_context()
        sites = CMSSiteSelector.list_for_owner(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(sites, request)
        serializer = SiteOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, business_slug):
        serializer = SiteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        site = CMSSiteService.create_site(
            actor_context=actor_context,
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            request=request,
            **serializer.validated_data,
        )
        return Response(
            SiteOutputSerializer(site).data, status=http_status.HTTP_201_CREATED
        )


class BusinessSiteDetailView(PermissionInjectMixin, BusinessCMSMixin, APIView):
    """
    GET    -> Get site details (with _permissions)
    PATCH  -> Update site
    DELETE -> Delete site
    """

    policy_class = CMSPolicy

    def _build_policy_kwargs(self):
        return {"user": self.request.user, "actor_context": self._actor_context}

    def get(self, request, business_slug, slug):
        self._actor_context = self.get_actor_context()
        site = CMSSiteSelector.get_by_slug(
            owner_type=self._actor_context.account_type,
            owner_id=self._actor_context.account_id,
            slug=slug,
        )
        self._inject_permissions = True
        return Response(SiteOutputSerializer(site).data)

    def patch(self, request, business_slug, slug):
        serializer = SiteUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        site = CMSSiteService.update_site(
            actor_context=actor_context,
            slug=slug,
            request=request,
            **serializer.validated_data,
        )
        return Response(SiteOutputSerializer(site).data)

    def delete(self, request, business_slug, slug):
        actor_context = self.get_actor_context()
        CMSSiteService.delete_site(
            actor_context=actor_context,
            slug=slug,
            request=request,
        )
        return Response(status=http_status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Business — Pages
# ---------------------------------------------------------------------------


class BusinessPageListCreateView(BusinessCMSMixin, APIView):
    """
    GET  -> List pages (filterable by site, status)
    POST -> Create page
    """

    def get(self, request, business_slug):
        site_slug = request.query_params.get("site")
        status_filter = request.query_params.get("status")
        actor_context = self.get_actor_context()

        if site_slug:
            site = CMSSiteSelector.get_by_slug(
                owner_type=actor_context.account_type,
                owner_id=actor_context.account_id,
                slug=site_slug,
            )
            pages = CMSPageSelector.list_by_site(
                site_id=site.id,
                status=status_filter,
            )
        else:
            from apps.cms.models import Page

            pages = Page.objects.filter(
                site__owner_type=actor_context.account_type,
                site__owner_id=actor_context.account_id,
            )
            if status_filter:
                pages = pages.filter(status=status_filter)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(pages, request)
        serializer = PageOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, business_slug):
        serializer = PageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        page = CMSPageService.create_page(
            actor_context=actor_context,
            request=request,
            **serializer.validated_data,
        )
        return Response(
            PageOutputSerializer(page).data, status=http_status.HTTP_201_CREATED
        )


class BusinessPageDetailView(PermissionInjectMixin, BusinessCMSMixin, APIView):
    """
    GET    -> Get page (with optional depth, with _permissions)
    PATCH  -> Update page metadata
    DELETE -> Delete page
    """

    policy_class = CMSPolicy

    def _build_policy_kwargs(self):
        return {"user": self.request.user, "actor_context": self._actor_context}

    def patch(self, request, business_slug, slug):
        from apps.cms.api.serializers import PageUpdateSerializer

        serializer = PageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        site_slug = request.query_params.get("site")
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        )
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        page = CMSPageService.update_page(
            actor_context=actor_context,
            page_id=page.id,
            request=request,
            **serializer.validated_data,
        )
        return Response(PageOutputSerializer(page).data)

    def delete(self, request, business_slug, slug):
        actor_context = self.get_actor_context()
        site_slug = request.query_params.get("site")
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        )
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        CMSPageService.delete_page(
            actor_context=actor_context,
            page_id=page.id,
            request=request,
        )
        return Response(status=http_status.HTTP_204_NO_CONTENT)

    def get(self, request, business_slug, slug):
        self._actor_context = self.get_actor_context()
        self._inject_permissions = True
        actor_context = self._actor_context
        depth = request.query_params.get("depth")
        site_slug = request.query_params.get("site")

        site = (
            CMSSiteSelector.get_by_slug(
                owner_type=actor_context.account_type,
                owner_id=actor_context.account_id,
                slug=site_slug,
            )
            if site_slug
            else None
        )

        if depth == "full" and site:
            page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
            page = CMSPageSelector.get_with_full_tree(page_id=page.id)
            return Response(PageDetailOutputSerializer(page).data)

        if site:
            page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        else:
            from apps.cms.models import Page
            from apps.core.exceptions import NotFound

            page = Page.objects.filter(slug=slug).first()
            if not page:
                raise NotFound(resource="Page", resource_id=slug)

        return Response(PageOutputSerializer(page).data)


class BusinessPagePublishView(BusinessCMSMixin, APIView):
    """POST -> Validate & publish page."""

    def post(self, request, business_slug, slug):
        actor_context = self.get_actor_context()
        site_slug = request.query_params.get("site")
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        )
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        page = CMSPageService.publish_page(
            actor_context=actor_context,
            page_id=page.id,
            request=request,
        )
        return Response(PageOutputSerializer(page).data)


class BusinessPageUnpublishView(BusinessCMSMixin, APIView):
    """POST -> Revert to draft."""

    def post(self, request, business_slug, slug):
        actor_context = self.get_actor_context()
        site_slug = request.query_params.get("site")
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        )
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        page = CMSPageService.unpublish_page(
            actor_context=actor_context,
            page_id=page.id,
            request=request,
        )
        return Response(PageOutputSerializer(page).data)


class BusinessPageExportView(BusinessCMSMixin, APIView):
    """POST -> Export page tree as JSON."""

    def post(self, request, business_slug, slug):
        actor_context = self.get_actor_context()
        site_slug = request.query_params.get("site")
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        )
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        export_data = CMSPageService.export_page(
            actor_context=actor_context,
            page_id=page.id,
            request=request,
        )
        return Response(export_data)


class BusinessPageImportView(BusinessCMSMixin, APIView):
    """POST -> Import page content."""

    def post(self, request, business_slug, slug):
        serializer = PageImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        site_slug = request.query_params.get("site")
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        )
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        page = CMSPageService.import_page(
            actor_context=actor_context,
            page_id=page.id,
            import_data=serializer.validated_data,
            request=request,
        )
        return Response(PageOutputSerializer(page).data)


# ---------------------------------------------------------------------------
# Business — Block Placements
# ---------------------------------------------------------------------------


class BusinessBlockPlacementDetailView(
    PermissionInjectMixin, BusinessCMSMixin, APIView
):
    """
    GET   -> Get block placement (with _permissions)
    PATCH -> Update draft content
    """

    policy_class = CMSPolicy

    def _build_policy_kwargs(self):
        return {"user": self.request.user, "actor_context": self._actor_context}

    def get(self, request, business_slug, uuid):
        self._actor_context = self.get_actor_context()
        self._inject_permissions = True
        placement = CMSBlockPlacementSelector.get_by_id(block_placement_id=uuid)
        return Response(BlockPlacementOutputSerializer(placement).data)

    def patch(self, request, business_slug, uuid):
        serializer = DraftContentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        placement = CMSContentService.update_draft_content(
            actor_context=actor_context,
            block_placement_id=uuid,
            content=serializer.validated_data["draft_content"],
            request=request,
        )
        return Response(BlockPlacementOutputSerializer(placement).data)


class BusinessBlockPlacementHistoryView(BusinessCMSMixin, APIView):
    """GET -> List content versions."""

    def get(self, request, business_slug, uuid):
        self.get_actor_context()
        versions = CMSContentVersionSelector.list_for_placement(
            block_placement_id=uuid,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(versions, request)
        serializer = ContentVersionOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class BusinessBlockPlacementRollbackView(BusinessCMSMixin, APIView):
    """POST -> Rollback to version."""

    def post(self, request, business_slug, uuid, version_number):
        actor_context = self.get_actor_context()
        placement = CMSContentService.rollback_content(
            actor_context=actor_context,
            block_placement_id=uuid,
            version_number=version_number,
            request=request,
        )
        return Response(BlockPlacementOutputSerializer(placement).data)


# ---------------------------------------------------------------------------
# Business — Media
# ---------------------------------------------------------------------------


class BusinessMediaFileListCreateView(BusinessCMSMixin, APIView):
    """
    GET  -> List files
    POST -> Upload file
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, business_slug):
        actor_context = self.get_actor_context()
        folder_id = request.query_params.get("folder")
        mime_type = request.query_params.get("type")
        files = CMSMediaSelector.list_files(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            folder_id=folder_id,
            mime_type=mime_type,
        ).annotate(_usage_count=Count("usages"))
        paginator = StandardPagination()
        page = paginator.paginate_queryset(files, request)
        serializer = MediaFileOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, business_slug):
        serializer = MediaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        media = CMSMediaService.upload_file(
            actor_context=actor_context,
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            request=request,
            **serializer.validated_data,
        )
        return Response(
            MediaFileOutputSerializer(media).data, status=http_status.HTTP_201_CREATED
        )


class BusinessMediaFileDetailView(PermissionInjectMixin, BusinessCMSMixin, APIView):
    """
    GET    -> Get file details (with _permissions)
    PATCH  -> Update file metadata
    DELETE -> Delete file
    """

    policy_class = CMSPolicy

    def _build_policy_kwargs(self):
        return {"user": self.request.user, "actor_context": self._actor_context}

    def get(self, request, business_slug, uuid):
        self._actor_context = self.get_actor_context()
        self._inject_permissions = True
        media = CMSMediaSelector.get_file_by_id(file_id=uuid)
        return Response(MediaFileOutputSerializer(media).data)

    def patch(self, request, business_slug, uuid):
        serializer = MediaUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        media = CMSMediaService.update_file(
            actor_context=actor_context,
            file_id=uuid,
            request=request,
            **serializer.validated_data,
        )
        return Response(MediaFileOutputSerializer(media).data)

    def delete(self, request, business_slug, uuid):
        actor_context = self.get_actor_context()
        CMSMediaService.delete_file(
            actor_context=actor_context,
            file_id=uuid,
            request=request,
        )
        return Response(status=http_status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Business — API Keys
# ---------------------------------------------------------------------------


class BusinessApiKeyListCreateView(BusinessCMSMixin, APIView):
    """
    GET  -> List API keys for a site
    POST -> Create API key
    """

    def get(self, request, business_slug):
        self.get_actor_context()
        site_id = request.query_params.get("site")
        keys = CMSApiKeySelector.list_for_site(site_id=site_id)
        serializer = ApiKeyOutputSerializer(keys, many=True)
        return Response(serializer.data)

    def post(self, request, business_slug):
        serializer = ApiKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        api_key, plaintext = CMSApiKeyService.create_api_key(
            actor_context=actor_context,
            request=request,
            **serializer.validated_data,
        )
        output = ApiKeyCreatedOutputSerializer(api_key).data
        output["key"] = plaintext
        return Response(output, status=http_status.HTTP_201_CREATED)


class BusinessApiKeyDetailView(BusinessCMSMixin, APIView):
    """DELETE -> Revoke key."""

    def delete(self, request, business_slug, uuid):
        actor_context = self.get_actor_context()
        CMSApiKeyService.revoke_api_key(
            actor_context=actor_context,
            api_key_id=uuid,
            request=request,
        )
        return Response(status=http_status.HTTP_204_NO_CONTENT)
