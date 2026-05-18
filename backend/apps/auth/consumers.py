"""
Auth Consumers
==============
WebSocket consumer base classes with authentication support.

Provides:
    - AuthenticatedConsumer: Base class requiring authentication
    - First-message auth pattern support

Usage:
    class ChatConsumer(AuthenticatedConsumer):
        async def on_authenticated(self):
            # Called when user is authenticated
            await self.channel_layer.group_add('chat', self.channel_name)

        async def receive_authenticated(self, content):
            # Handle authenticated messages
            message = content.get('message')
            await self.channel_layer.group_send(
                'chat',
                {'type': 'chat.message', 'message': message}
            )
"""

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.core.observability import get_logger

logger = get_logger(__name__)


class AuthenticatedConsumer(AsyncJsonWebsocketConsumer):
    """
    Base consumer that requires authentication.

    Supports both:
    1. Query param auth (via JWTAuthMiddleware)
    2. First-message auth pattern

    Query Param Auth:
        ws://example.com/ws/chat/?token=<access_token>
        User is already authenticated when connect() is called.

    First-Message Auth:
        ws://example.com/ws/chat/
        Client sends: {"type": "authenticate", "token": "<access_token>"}
        Then receives: {"type": "authenticated", "status": "success"}
    """

    async def connect(self):
        """Accept connection and check if already authenticated."""
        await self.accept()

        # If already authenticated via query param (JWTAuthMiddleware)
        if self.scope["user"].is_authenticated:
            logger.debug("ws.connect.authenticated", user_id=self.scope["user"].id)
            await self.on_authenticated()
        else:
            # Wait for auth message
            self.authenticated = False
            logger.debug("ws.connect.awaiting_auth")

    async def disconnect(self, close_code):
        """Handle disconnection."""
        if self.scope["user"].is_authenticated:
            await self.on_disconnect()
        logger.debug(
            "ws.disconnect",
            user_id=getattr(self.scope.get("user"), "id", None),
            close_code=close_code,
        )

    async def receive_json(self, content):
        """Handle incoming JSON messages."""
        # Handle authentication message
        if content.get("type") == "authenticate":
            token = content.get("token")
            if await self.authenticate(token):
                await self.send_json(
                    {
                        "type": "authenticated",
                        "status": "success",
                        "user_id": self.scope["user"].id,
                    }
                )
                await self.on_authenticated()
            else:
                await self.send_json(
                    {
                        "type": "authenticated",
                        "status": "failed",
                        "error": "Invalid or expired token",
                    }
                )
                await self.close(code=4001)
            return

        # Reject unauthenticated messages
        if not self.scope["user"].is_authenticated:
            await self.send_json(
                {
                    "type": "error",
                    "code": "not_authenticated",
                    "message": "Authentication required",
                }
            )
            return

        # Process authenticated message
        await self.receive_authenticated(content)

    async def authenticate(self, token: str) -> bool:
        """Validate token and set user on scope."""
        user = await self.get_user_from_token(token)
        if user and user.is_authenticated:
            self.scope["user"] = user
            logger.debug("ws.auth.success", user_id=user.id)
            return True
        logger.debug("ws.auth.failed")
        return False

    @database_sync_to_async
    def get_user_from_token(self, token: str):
        """Validate JWT and return user."""
        try:
            from apps.auth.services import AuthService

            user, payload = AuthService.validate_access_token(token)
            return user
        except Exception as e:
            logger.debug("ws.auth.token_invalid", error=str(e))
            return None

    async def on_authenticated(self):
        """
        Called when user is authenticated.

        Override in subclass to:
            - Join channel groups
            - Send initial data
            - Set up user-specific state
        """
        pass

    async def on_disconnect(self):
        """
        Called when authenticated user disconnects.

        Override in subclass to:
            - Leave channel groups
            - Clean up state
        """
        pass

    async def receive_authenticated(self, content):
        """
        Handle authenticated message.

        Override in subclass to process incoming messages.

        Args:
            content: Parsed JSON content
        """
        pass


class OptionalAuthConsumer(AsyncJsonWebsocketConsumer):
    """
    Consumer that supports optional authentication.

    Use for endpoints that work for both anonymous and authenticated users,
    with different behavior for each.

    Usage:
        class PublicChatConsumer(OptionalAuthConsumer):
            async def receive_json(self, content):
                if self.is_authenticated:
                    # User is logged in
                    sender = self.scope['user'].email
                else:
                    # Anonymous user
                    sender = 'Anonymous'

                await self.send_json({
                    'sender': sender,
                    'message': content.get('message')
                })
    """

    @property
    def is_authenticated(self) -> bool:
        """Check if current user is authenticated."""
        return self.scope["user"].is_authenticated

    @property
    def user(self):
        """Get current user (may be AnonymousUser)."""
        return self.scope["user"]

    async def connect(self):
        """Accept connection (auth is optional)."""
        await self.accept()

        if self.is_authenticated:
            logger.debug("ws.connect.authenticated", user_id=self.scope["user"].id)
        else:
            logger.debug("ws.connect.anonymous")

    async def receive_json(self, content):
        """Handle incoming messages. Override in subclass."""
        pass
