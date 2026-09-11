"""
QueryPilot — Auth Middleware

Optional ASGI middleware that extracts Bearer JWT tokens from request headers,
decodes the payload, and attaches user info to request.state.
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.security import decode_access_token

logger = logging.getLogger(__name__)


class AuthStateMiddleware(BaseHTTPMiddleware):
    """
    Middleware that populates request.state.user_id and request.state.user_role
    when a valid Authorization header is present.
    """

    async def dispatch(self, request: Request, call_next):
        request.state.user_id = None
        request.state.user_role = None

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            try:
                payload = decode_access_token(token)
                request.state.user_id = payload.get("sub")
                request.state.user_role = payload.get("role")
            except Exception:
                # Let endpoints / dependencies handle rejection
                pass

        return await call_next(request)
