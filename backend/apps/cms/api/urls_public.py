# apps/cms/api/urls_public.py
"""
CMS Public URL Configuration
==============================
Public read-only endpoints — authenticated via API key (CMSApiKeyMiddleware).

Include in project urls.py:
    path("api/v1/cms/public/", include("apps.cms.api.urls_public", namespace="cms-public")),
"""

from django.urls import path

from apps.cms.api import views

app_name = "cms-public"

urlpatterns = [
    path("sites/<slug:slug>/", views.PublicSiteView.as_view(), name="public-site"),
    path("pages/<slug:slug>/", views.PublicPageView.as_view(), name="public-page"),
]
