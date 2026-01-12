from typing import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

API_SECRET_HEADER = "X-Arthur-Client"
API_SECRET_VALUE = "Arthur-Prime-V1"

class FrontendAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Allow static files and root (frontend assets)
        path = request.url.path
        if (
            path == "/"
            or path.startswith("/assets")
            or path.endswith(".js")
            or path.endswith(".css")
            or path.endswith(".png")
            or path.endswith(".ico")
            or path.endswith(".svg")
            or path.endswith(".json")
            or path.endswith(".woff")
            or path.endswith(".woff2")
            or path == "/health" # Keep health check accessible
        ):
            return await call_next(request)

        # Check for the custom header on API routes
        client_header = request.headers.get(API_SECRET_HEADER)
        if client_header != API_SECRET_VALUE:
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied. Requests must originate from the Arthur Prime frontend."}
            )

        return await call_next(request)
