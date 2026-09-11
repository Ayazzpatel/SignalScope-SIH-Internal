from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from signalscope.core.config import Settings, get_settings
from signalscope.core.cookies import ACCESS_COOKIE
from signalscope.core.errors import AppError
from signalscope.core.rate_limit import RateLimiter, client_ip
from signalscope.models import UserRole
from signalscope.services.analysis import AnalysisService
from signalscope.services.auth import AuthContext, AuthService, ClientInfo
from signalscope.services.detector import Detector


def get_detector(request: Request) -> Detector:
    return request.app.state.detector


def get_analysis_service(request: Request) -> AnalysisService:
    return request.app.state.analysis


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth


def get_rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


def get_client_info(request: Request) -> ClientInfo:
    return ClientInfo(user_agent=request.headers.get("user-agent"), ip_address=client_ip(request))


SettingsDep = Annotated[Settings, Depends(get_settings)]
DetectorDep = Annotated[Detector, Depends(get_detector)]
AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
ClientInfoDep = Annotated[ClientInfo, Depends(get_client_info)]


def _access_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return request.cookies.get(ACCESS_COOKIE)


async def get_optional_auth(request: Request, db: DbDep, auth: AuthServiceDep) -> AuthContext | None:
    """Guests get None. An *expired* token still raises 401 so the client knows to refresh."""
    token = _access_token(request)
    if not token:
        return None
    try:
        return await auth.authenticate_access(db, token)
    except AppError as exc:
        if exc.code == "token_expired":
            raise
        return None


async def get_current_auth(request: Request, db: DbDep, auth: AuthServiceDep) -> AuthContext:
    token = _access_token(request)
    if not token:
        raise AppError(401, "not_authenticated", "Please sign in.", headers={"WWW-Authenticate": "Bearer"})
    return await auth.authenticate_access(db, token)


OptionalAuthDep = Annotated[AuthContext | None, Depends(get_optional_auth)]
CurrentAuthDep = Annotated[AuthContext, Depends(get_current_auth)]


def require_role(*roles: UserRole) -> Callable[..., Awaitable[AuthContext]]:
    """Dependency factory: `Depends(require_role(UserRole.REVIEWER, UserRole.ADMIN))`."""

    async def _check(ctx: CurrentAuthDep) -> AuthContext:
        if ctx.user.role not in roles:
            raise AppError(403, "forbidden", "You don't have permission to do that.")
        return ctx

    return _check
