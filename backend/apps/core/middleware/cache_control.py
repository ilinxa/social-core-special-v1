# apps/core/middleware/cache_control.py
"""
Cache-Control middleware for API responses.
"""


class CacheControlMiddleware:
    """
    Set Cache-Control headers on API responses.

    - Authenticated requests: ``private, no-store`` (never cache sensitive data)
    - Anonymous requests: ``public, max-age=60`` (light caching for public endpoints)

    Only applies to ``/api/`` paths and does NOT overwrite headers already set by views.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.path.startswith("/api/") and not response.get("Cache-Control"):
            if hasattr(request, "user") and request.user.is_authenticated:
                response["Cache-Control"] = "private, no-store"
            else:
                response["Cache-Control"] = "public, max-age=60"

        return response
