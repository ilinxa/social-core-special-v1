"""
Core Middleware
===============
Custom middleware classes.

Middleware will be added here as needed:
    - AuthMiddleware: JWT authentication
    - RequestIDMiddleware: Correlation IDs for logging

Usage:
    Add to settings.MIDDLEWARE:
        MIDDLEWARE = [
            ...
            "apps.core.middleware.RequestIDMiddleware",
            ...
        ]
"""

# Middleware will be added here as the authentication system is built
# from apps.core.middleware.auth import AuthMiddleware
# from apps.core.middleware.request_id import RequestIDMiddleware

__all__ = []
