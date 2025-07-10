"""Rate limiting middleware for FastAPI."""

from collections.abc import Callable

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from src.common.services.rate_limit_service import RateLimitExceededError, rate_limit_service


class RateLimitMiddleware:
    """Rate limiting middleware for API endpoints."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)

            # Skip rate limiting for health checks and static files
            if request.url.path in ["/health", "/docs", "/openapi.json"]:
                await self.app(scope, receive, send)
                return

            # Apply rate limiting
            try:
                await self._check_rate_limit(request)
            except RateLimitExceededError as e:
                response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": str(e), "retry_after": e.retry_after},
                    headers={"Retry-After": str(e.retry_after)},
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)

    async def _check_rate_limit(self, request: Request):
        """Check rate limit for the request."""
        # Get user ID from request if authenticated
        user_id = getattr(request.state, "user_id", None)

        # Generate client key
        client_key = rate_limit_service.get_client_key(request, user_id)

        # Apply different limits based on endpoint
        path = request.url.path
        method = request.method

        # Define rate limits for different endpoints
        rate_limits = self._get_rate_limits(path, method)

        if rate_limits:
            limit, window = rate_limits
            rate_limit_service.check_rate_limit(client_key, limit, window, raise_exception=True)

    def _get_rate_limits(self, path: str, method: str) -> tuple | None:
        """Get rate limits for specific endpoint."""
        # Authentication endpoints with stricter limits
        if path.startswith("/api/v1/auth/"):
            if path.endswith("/login") and method == "POST":
                return (5, 60)  # 5 requests per minute for login
            elif path.endswith("/register") and method == "POST":
                return (10, 300)  # 10 requests per 5 minutes for registration
            elif path.endswith("/forgot-password") and method == "POST":
                return (3, 3600)  # 3 requests per hour for password reset
            elif path.endswith("/reset-password") and method == "POST":
                return (5, 3600)  # 5 requests per hour for password reset
            elif path.endswith("/resend-verification") and method == "POST":
                return (3, 300)  # 3 requests per 5 minutes for resend verification
            else:
                return (60, 60)  # 60 requests per minute for other auth endpoints

        # General API endpoints
        return (100, 60)  # 100 requests per minute for general endpoints


def create_rate_limit_decorator(limit: int, window: int):
    """Create a rate limit decorator for specific endpoints."""

    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Get request from args (FastAPI dependency injection)
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if request:
                user_id = getattr(request.state, "user_id", None)
                client_key = rate_limit_service.get_client_key(request, user_id)

                try:
                    rate_limit_service.check_rate_limit(client_key, limit, window, raise_exception=True)
                except RateLimitExceededError as e:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=str(e),
                        headers={"Retry-After": str(e.retry_after)},
                    ) from e

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Common rate limit decorators
login_rate_limit = create_rate_limit_decorator(5, 60)  # 5 per minute
register_rate_limit = create_rate_limit_decorator(10, 300)  # 10 per 5 minutes
password_reset_rate_limit = create_rate_limit_decorator(3, 3600)  # 3 per hour
