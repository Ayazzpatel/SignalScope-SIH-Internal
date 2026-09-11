import contextlib
import uuid

from fastapi import APIRouter, Request, Response

from signalscope.core.config import Settings
from signalscope.core.cookies import ACCESS_COOKIE, REFRESH_COOKIE, clear_auth_cookies, set_auth_cookies
from signalscope.core.errors import AppError, error_response
from signalscope.core.rate_limit import client_ip
from signalscope.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    SessionListResponse,
    SessionOut,
    SessionStateResponse,
    SignupRequest,
    UpdateProfileRequest,
    UserOut,
)
from signalscope.services.auth import IssuedTokens
from signalscope.services.devices import describe_device

from .deps import (
    AuthServiceDep,
    ClientInfoDep,
    CurrentAuthDep,
    DbDep,
    RateLimiterDep,
    SettingsDep,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookies(response: Response, settings: Settings, tokens: IssuedTokens) -> None:
    set_auth_cookies(
        response,
        settings,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        remember=tokens.remember,
    )


@router.post("/signup", response_model=AuthResponse, status_code=201, summary="Create an account")
async def signup(
    body: SignupRequest,
    request: Request,
    response: Response,
    db: DbDep,
    auth: AuthServiceDep,
    limiter: RateLimiterDep,
    client: ClientInfoDep,
    settings: SettingsDep,
) -> AuthResponse:
    limiter.hit(f"signup:{client_ip(request)}", settings.signup_rate_per_minute, 60)
    user, tokens = await auth.signup(
        db, email=body.email, password=body.password, display_name=body.display_name, client=client
    )
    _set_cookies(response, settings, tokens)
    return AuthResponse(user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthResponse, summary="Sign in")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: DbDep,
    auth: AuthServiceDep,
    limiter: RateLimiterDep,
    client: ClientInfoDep,
    settings: SettingsDep,
) -> AuthResponse:
    limiter.hit(f"login:{client_ip(request)}", settings.login_rate_per_minute, 60)
    user, tokens = await auth.login(
        db, email=body.email, password=body.password, remember=body.remember, client=client
    )
    _set_cookies(response, settings, tokens)
    return AuthResponse(user=UserOut.model_validate(user))


@router.post("/refresh", response_model=AuthResponse, summary="Rotate the session tokens")
async def refresh(
    request: Request,
    response: Response,
    db: DbDep,
    auth: AuthServiceDep,
    limiter: RateLimiterDep,
    client: ClientInfoDep,
    settings: SettingsDep,
) -> AuthResponse | Response:
    limiter.hit(f"refresh:{client_ip(request)}", 60, 60)
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise AppError(401, "not_authenticated", "Please sign in.")
    try:
        user, tokens = await auth.refresh(db, token, client)
    except AppError as exc:
        failed = error_response(request, exc.status_code, exc.code, exc.message, headers=exc.headers)
        if exc.code != "token_rotated":  # a sibling tab already holds valid cookies — leave them alone
            clear_auth_cookies(failed, settings)
        return failed
    _set_cookies(response, settings, tokens)
    return AuthResponse(user=UserOut.model_validate(user))


@router.get(
    "/session",
    response_model=SessionStateResponse,
    summary="Current user for app bootstrap (null for guests)",
)
async def session_state(
    request: Request,
    response: Response,
    db: DbDep,
    auth: AuthServiceDep,
    client: ClientInfoDep,
    settings: SettingsDep,
) -> SessionStateResponse:
    access = request.cookies.get(ACCESS_COOKIE)
    if access:
        try:
            ctx = await auth.authenticate_access(db, access)
            return SessionStateResponse(user=UserOut.model_validate(ctx.user))
        except AppError:
            pass

    # The refresh cookie is scoped to /auth, so it reaches this endpoint: refresh transparently.
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        try:
            user, tokens = await auth.refresh(db, token, client)
            _set_cookies(response, settings, tokens)
            return SessionStateResponse(user=UserOut.model_validate(user))
        except AppError:
            pass

    if access or token:
        clear_auth_cookies(response, settings)
    return SessionStateResponse(user=None)


@router.post("/logout", response_model=MessageResponse, summary="Sign out of this device")
async def logout(
    request: Request, response: Response, db: DbDep, auth: AuthServiceDep, settings: SettingsDep
) -> MessageResponse:
    family_id = None
    access = request.cookies.get(ACCESS_COOKIE)
    if access:
        with contextlib.suppress(AppError):  # expired / invalid access token: fall back to refresh cookie
            family_id = (await auth.authenticate_access(db, access)).session_family_id
    await auth.logout(db, refresh_token=request.cookies.get(REFRESH_COOKIE), family_id=family_id)
    clear_auth_cookies(response, settings)
    return MessageResponse(message="Signed out.")


@router.post("/logout-all", response_model=MessageResponse, summary="Sign out of every device")
async def logout_all(
    ctx: CurrentAuthDep, response: Response, db: DbDep, auth: AuthServiceDep, settings: SettingsDep
) -> MessageResponse:
    await auth.revoke_all(db, ctx.user.id)
    clear_auth_cookies(response, settings)
    return MessageResponse(message="Signed out of all devices.")


@router.get("/me", response_model=UserOut, summary="Current user")
async def me(ctx: CurrentAuthDep) -> UserOut:
    return UserOut.model_validate(ctx.user)


@router.patch("/me", response_model=UserOut, summary="Update profile")
async def update_me(
    body: UpdateProfileRequest, ctx: CurrentAuthDep, db: DbDep, auth: AuthServiceDep
) -> UserOut:
    user = await auth.update_profile(db, ctx.user, display_name=body.display_name)
    return UserOut.model_validate(user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password (signs out other devices)",
)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    ctx: CurrentAuthDep,
    db: DbDep,
    auth: AuthServiceDep,
    limiter: RateLimiterDep,
    settings: SettingsDep,
) -> MessageResponse:
    limiter.hit(f"change-password:{ctx.user.id}", settings.login_rate_per_minute, 60)
    await auth.change_password(
        db, ctx, current_password=body.current_password, new_password=body.new_password
    )
    return MessageResponse(message="Password changed. Other devices have been signed out.")


@router.get("/sessions", response_model=SessionListResponse, summary="Active sessions (devices)")
async def list_sessions(ctx: CurrentAuthDep, db: DbDep, auth: AuthServiceDep) -> SessionListResponse:
    rows = await auth.list_sessions(db, ctx.user.id)
    return SessionListResponse(
        sessions=[
            SessionOut(
                id=row.family_id,
                device=describe_device(row.user_agent),
                ip_address=row.ip_address,
                signed_in_at=row.family_started_at,
                last_active_at=row.created_at,
                expires_at=row.expires_at,
                remember=row.remember,
                current=row.family_id == ctx.session_family_id,
            )
            for row in rows
        ]
    )


@router.delete("/sessions/{session_id}", response_model=MessageResponse, summary="Revoke a session")
async def revoke_session(
    session_id: uuid.UUID,
    ctx: CurrentAuthDep,
    response: Response,
    db: DbDep,
    auth: AuthServiceDep,
    settings: SettingsDep,
) -> MessageResponse:
    await auth.revoke_session(db, ctx.user.id, session_id)
    if session_id == ctx.session_family_id:
        clear_auth_cookies(response, settings)
    return MessageResponse(message="Session revoked.")
