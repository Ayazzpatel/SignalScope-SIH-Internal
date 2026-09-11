from fastapi import Response

from signalscope.core.config import Settings

ACCESS_COOKIE = "ss_access"
REFRESH_COOKIE = "ss_refresh"


def refresh_cookie_path(settings: Settings) -> str:
    # The refresh token is only ever sent to the auth endpoints.
    return f"{settings.api_prefix}/auth"


def set_auth_cookies(
    response: Response,
    settings: Settings,
    *,
    access_token: str,
    refresh_token: str,
    remember: bool,
) -> None:
    # "Remember me" → persistent cookies; otherwise session cookies that die with the browser.
    max_age = int(settings.refresh_ttl_remember_s) if remember else None
    common = {"httponly": True, "secure": settings.secure_cookies, "samesite": "lax"}
    # The access cookie outlives the JWT inside it so an expired token reaches the server
    # as "token_expired" (→ client refreshes) instead of silently disappearing.
    response.set_cookie(ACCESS_COOKIE, access_token, max_age=max_age, path="/", **common)
    response.set_cookie(
        REFRESH_COOKIE, refresh_token, max_age=max_age, path=refresh_cookie_path(settings), **common
    )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    common = {"httponly": True, "secure": settings.secure_cookies, "samesite": "lax"}
    response.delete_cookie(ACCESS_COOKIE, path="/", **common)
    response.delete_cookie(REFRESH_COOKIE, path=refresh_cookie_path(settings), **common)
