# apps/cms/middleware.py
"""
CMS API Key Authentication Middleware
======================================
Authenticates public CMS API requests via X-CMS-API-Key header.
Validates: key exists, is active, not expired, origin matches.
"""

from django.http import JsonResponse
from django.utils import timezone

from apps.cms.models import CMSApiKey
from apps.core.observability import get_logger

logger = get_logger(__name__)

CMS_PUBLIC_PREFIX = "/api/v1/cms/public/"
API_KEY_HEADER = "HTTP_X_CMS_API_KEY"


class CMSApiKeyMiddleware:
    """
    Middleware that authenticates public CMS API requests.
    Only active on /api/v1/cms/public/ prefix.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(CMS_PUBLIC_PREFIX):
            return self.get_response(request)

        # Extract API key from header
        api_key_value = request.META.get(API_KEY_HEADER)
        if not api_key_value:
            return JsonResponse(
                {"error": "Missing X-CMS-API-Key header"},
                status=401,
            )

        # Validate key
        key_hash = CMSApiKey.hash_key(api_key_value)
        api_key = (
            CMSApiKey.objects
            .filter(key_hash=key_hash, is_deleted=False)
            .select_related("site")
            .first()
        )

        if not api_key:
            return JsonResponse({"error": "Invalid API key"}, status=401)

        if not api_key.is_active:
            return JsonResponse({"error": "API key is inactive"}, status=403)

        if api_key.expires_at and api_key.expires_at < timezone.now():
            return JsonResponse({"error": "API key has expired"}, status=403)

        # Origin validation
        if api_key.allowed_origins:
            origin = request.META.get("HTTP_ORIGIN", "")
            referer = request.META.get("HTTP_REFERER", "")
            allowed = False
            for allowed_origin in api_key.allowed_origins:
                normalized = allowed_origin.lower().rstrip("/")
                if origin.lower().rstrip("/") == normalized:
                    allowed = True
                    break
                if referer.lower().startswith(normalized):
                    allowed = True
                    break
            if not allowed:
                return JsonResponse({"error": "Origin not allowed"}, status=403)

        # Set site on request for downstream views
        request.cms_site = api_key.site
        request.cms_api_key = api_key

        # Update last_used_at
        CMSApiKey.objects.filter(id=api_key.id).update(last_used_at=timezone.now())

        return self.get_response(request)
