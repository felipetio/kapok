"""Custom Bearer Token Authentication for MCP Server."""

from django.conf import settings

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class MCPBearerUser:
    """Minimal user object for bearer token authentication."""

    is_authenticated = True
    is_active = True

    def __str__(self):
        return "MCP Bearer User"


class MCPBearerTokenAuthentication(BaseAuthentication):
    """
    Bearer token authentication using MCP_BEARER_TOKEN setting.

    Matches the behavior of the original BearerTokenMiddleware:
    - No token configured = allow access (development mode)
    - Invalid/missing token = authentication failed
    """

    def authenticate(self, request):
        mcp_bearer_token = getattr(settings, "MCP_BEARER_TOKEN", "")

        # No token configured = allow access (dev mode)
        if not mcp_bearer_token:
            return (MCPBearerUser(), None)

        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return None  # Let other auth classes try

        token = auth_header[7:]  # Remove "Bearer " prefix

        if token != mcp_bearer_token:
            raise AuthenticationFailed("Invalid Bearer token")

        return (MCPBearerUser(), token)

    def authenticate_header(self, request):
        return 'Bearer realm="mcp"'
