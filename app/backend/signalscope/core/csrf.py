"""CSRF defence for cookie-authenticated requests.

Layer 1: auth cookies are SameSite=Lax, so browsers don't attach them to cross-site POSTs.
Layer 2 (here): state-changing requests that carry an auth cookie must come from an allowed Origin.
Non-browser clients (no Origin header, no cookies) are unaffected.
"""

from urllib.parse import urlsplit

from fastapi import FastAPI, Request, Response

from signalscope.core.cookies import ACCESS_COOKIE, REFRESH_COOKIE
from signalscope.core.errors import error_response

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def register_csrf_origin_check(app: FastAPI, allowed_origins: list[str]) -> None:
    allowed = {origin.rstrip("/").lower() for origin in allowed_origins}

    @app.middleware("http")
    async def _csrf(request: Request, call_next) -> Response:
        if request.method in _SAFE_METHODS:
            return await call_next(request)
        if ACCESS_COOKIE not in request.cookies and REFRESH_COOKIE not in request.cookies:
            return await call_next(request)

        origin = (request.headers.get("origin") or "").rstrip("/").lower()
        if not origin or origin == "null":
            referer = request.headers.get("referer")
            origin = _origin_of(referer) if referer else ""
        if not origin:
            return await call_next(request)  # non-browser client

        same_host = urlsplit(origin).netloc == (request.headers.get("host") or "").lower()
        if same_host or origin in allowed:
            return await call_next(request)
        return error_response(request, 403, "csrf_rejected", "Cross-site request blocked.")


def _origin_of(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}".lower() if parts.scheme and parts.netloc else ""
