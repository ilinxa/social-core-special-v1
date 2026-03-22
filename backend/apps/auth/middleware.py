"""
Auth Middleware
===============
Middleware for authentication in different contexts.

Includes:
    - JWTAuthMiddleware: For Django Channels WebSocket authentication
    - TokenAuthMiddlewareStack: Middleware stack for Channels

Usage in asgi.py:
    from apps.auth.middleware import JWTAuthMiddleware

    application = ProtocolTypeRouter({
        'http': django_asgi_app,
        'websocket': AllowedHostsOriginValidator(
            JWTAuthMiddleware(
                URLRouter(websocket_urlpatterns)
            )
        ),
    })
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

from apps.core.observability import get_logger

logger = get_logger(__name__)


class JWTAuthMiddleware(BaseMiddleware):
    """
    JWT authentication middleware for Django Channels.

    Supports token in query parameter:
        ws://example.com/ws/chat/?token=<access_token>

    Usage:
        application = ProtocolTypeRouter({
            'websocket': JWTAuthMiddleware(
                URLRouter([...])
            )
        })
    """

    async def __call__(self, scope, receive, send):
        # Try query parameter auth
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        if token:
            scope["user"] = await self.get_user_from_token(token)
            if scope["user"].is_authenticated:
                logger.debug("ws.auth.success", extra={"user_id": scope["user"].id})
            else:
                logger.debug("ws.auth.failed", extra={"reason": "invalid_token"})
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user_from_token(self, token: str):
        """Validate token and return user."""
        try:
            from apps.auth.services import AuthService

            user, payload = AuthService.validate_access_token(token)
            return user
        except Exception as e:
            logger.debug(f"WS token validation failed: {e}")
            return AnonymousUser()


class TokenAuthMiddleware(BaseMiddleware):
    """
    First-message authentication middleware for WebSockets.

    Alternative to query param auth - more secure but more complex.

    The client connects anonymously, then sends an auth message:
        {"type": "authenticate", "token": "<access_token>"}

    Usage in consumer:
        async def receive_json(self, content):
            if content.get('type') == 'authenticate':
                await self.authenticate(content['token'])
                return

            if not self.scope['user'].is_authenticated:
                await self.close()
                return

            # Handle message...
    """

    async def __call__(self, scope, receive, send):
        # Start with anonymous user
        scope["user"] = AnonymousUser()
        scope["auth_token"] = None
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """
    Convenience function to create JWT auth middleware stack.

    Usage in asgi.py:
        from apps.auth.middleware import JWTAuthMiddlewareStack

        application = ProtocolTypeRouter({
            'websocket': JWTAuthMiddlewareStack(
                URLRouter([...])
            ),
        })
    """
    return JWTAuthMiddleware(inner)
