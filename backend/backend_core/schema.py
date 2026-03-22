"""
OpenAPI Schema Extensions
=========================
Custom extensions for drf_spectacular schema generation.

This module defines:
    - Security schemes (JWT Bearer authentication)
    - Custom schema processing hooks
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class JWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """
    Define JWT Bearer authentication scheme for OpenAPI schema.

    This makes the "Authorize" button in Swagger UI work correctly
    with our JWT authentication.
    """

    target_class = "apps.auth.authentication.JWTAuthentication"
    name = "BearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "JWT access token. Obtain from POST /api/v1/auth/login/ "
                "and include as: `Authorization: Bearer <token>`"
            ),
        }


class JWTAuthenticationOptionalScheme(OpenApiAuthenticationExtension):
    """
    Define optional JWT authentication scheme.

    For endpoints that support both authenticated and anonymous access.
    """

    target_class = "apps.auth.authentication.JWTAuthenticationOptional"
    name = "BearerAuthOptional"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Optional JWT access token. If provided, user context is available. "
                "If not provided, request is treated as anonymous."
            ),
        }
