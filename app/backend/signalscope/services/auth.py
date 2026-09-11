"""Account & session logic. HTTP concerns (cookies, status codes) stay in the API layer.

Session model: each sign-in starts a refresh-token *family* (one device). Every refresh rotates the token:
the old row is revoked with reason "rotated" and a new row joins the family. Presenting an already-rotated
token outside a short grace window means it was copied — the whole family is revoked (reuse detection).
"""

import logging
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from signalscope.core.config import Settings
from signalscope.core.errors import AppError
from signalscope.core.security import (
    PasswordService,
    TokenExpiredError,
    TokenInvalidError,
    create_access_token,
    decode_access_token,
    hash_token,
    new_refresh_token,
)
from signalscope.db import utcnow
from signalscope.models import AuthSession, User, UserRole
from signalscope.services.password_policy import check_password

logger = logging.getLogger("signalscope.auth")

ROTATED = "rotated"


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    family_id: uuid.UUID
    remember: bool


@dataclass(frozen=True)
class AuthContext:
    user: User
    session_family_id: uuid.UUID


@dataclass(frozen=True)
class ClientInfo:
    user_agent: str | None
    ip_address: str | None


def _unauthorized(code: str, message: str) -> AppError:
    return AppError(401, code, message, headers={"WWW-Authenticate": "Bearer"})


class AuthService:
    def __init__(self, settings: Settings, passwords: PasswordService) -> None:
        self._settings = settings
        self._passwords = passwords

    # ------------------------------------------------------------------ accounts

    async def signup(
        self, db: AsyncSession, *, email: str, password: str, display_name: str, client: ClientInfo
    ) -> tuple[User, IssuedTokens]:
        check_password(password, email)
        if await self._user_by_email(db, email):
            raise AppError(409, "email_taken", "An account with this email already exists.", field="email")

        user = User(
            email=email,
            display_name=display_name,
            password_hash=await run_in_threadpool(self._passwords.hash, password),
            role=UserRole.USER,
            last_login_at=utcnow(),
        )
        db.add(user)
        try:
            await db.flush()
        except IntegrityError as exc:  # concurrent signup with the same email
            await db.rollback()
            raise AppError(
                409, "email_taken", "An account with this email already exists.", field="email"
            ) from exc

        tokens = self._start_family(db, user, remember=False, client=client)
        await db.commit()
        logger.info("Signup user=%s", user.id)
        return user, tokens

    async def login(
        self, db: AsyncSession, *, email: str, password: str, remember: bool, client: ClientInfo
    ) -> tuple[User, IssuedTokens]:
        user = await self._user_by_email(db, email)
        now = utcnow()

        if user and user.locked_until and user.locked_until > now:
            minutes = math.ceil((user.locked_until - now).total_seconds() / 60)
            raise AppError(
                429,
                "account_locked",
                f"Too many failed attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}.",
            )

        # Always run a hash verification so unknown emails take as long as wrong passwords.
        valid = await run_in_threadpool(
            self._passwords.verify, user.password_hash if user else None, password
        )
        if not user or not valid:
            if user:
                await self._record_failed_login(db, user, now)
            raise _unauthorized("invalid_credentials", "Incorrect email or password.")
        if not user.is_active:
            raise AppError(403, "account_disabled", "This account has been disabled.")

        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = now
        if self._passwords.needs_rehash(user.password_hash):
            user.password_hash = await run_in_threadpool(self._passwords.hash, password)

        tokens = self._start_family(db, user, remember=remember, client=client)
        await db.commit()
        return user, tokens

    async def update_profile(self, db: AsyncSession, user: User, *, display_name: str) -> User:
        user.display_name = display_name
        await db.commit()
        return user

    async def change_password(
        self, db: AsyncSession, ctx: AuthContext, *, current_password: str, new_password: str
    ) -> None:
        user = ctx.user
        if not await run_in_threadpool(self._passwords.verify, user.password_hash, current_password):
            raise AppError(400, "wrong_password", "Current password is incorrect.", field="current_password")
        check_password(new_password, user.email, field="new_password")
        if new_password == current_password:
            raise AppError(
                422, "weak_password", "New password must differ from the current one.", field="new_password"
            )

        user.password_hash = await run_in_threadpool(self._passwords.hash, new_password)
        # A password change signs out every other device.
        await self._revoke(
            db,
            AuthSession.user_id == user.id,
            AuthSession.family_id != ctx.session_family_id,
            reason="password_changed",
        )
        await db.commit()

    # ------------------------------------------------------------------ tokens

    async def authenticate_access(self, db: AsyncSession, token: str) -> AuthContext:
        try:
            claims = decode_access_token(token, self._settings.secret_key)
        except TokenExpiredError as exc:
            raise _unauthorized("token_expired", "Your session needs refreshing.") from exc
        except TokenInvalidError as exc:
            raise _unauthorized("not_authenticated", "Please sign in.") from exc

        # Checked on every request so that revoking a session takes effect immediately.
        live = await db.scalar(
            select(AuthSession.id).where(
                AuthSession.family_id == claims.session_family_id,
                AuthSession.user_id == claims.user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > utcnow(),
            )
        )
        user = await db.get(User, claims.user_id) if live else None
        if not user or not user.is_active:
            raise _unauthorized("session_revoked", "This session has ended. Please sign in again.")
        return AuthContext(user=user, session_family_id=claims.session_family_id)

    async def refresh(
        self, db: AsyncSession, refresh_token: str, client: ClientInfo
    ) -> tuple[User, IssuedTokens]:
        now = utcnow()
        row = await db.scalar(
            select(AuthSession)
            .where(AuthSession.token_hash == hash_token(refresh_token))
            .with_for_update()  # serialises concurrent refreshes of the same token (Postgres)
        )
        if row is None:
            raise _unauthorized("session_revoked", "This session has ended. Please sign in again.")

        if row.revoked_at is not None:
            if row.revoked_reason == ROTATED:
                if now - row.revoked_at <= timedelta(seconds=self._settings.refresh_reuse_grace_s):
                    # Benign race: another tab refreshed a moment ago and already holds the new cookie.
                    raise _unauthorized("token_rotated", "Session was refreshed by another tab.")
                logger.warning("Refresh-token reuse detected; revoking family %s", row.family_id)
                await self._revoke(db, AuthSession.family_id == row.family_id, reason="reuse_detected")
                await db.commit()
            raise _unauthorized("session_revoked", "This session has ended. Please sign in again.")

        if row.expires_at <= now:
            raise _unauthorized("session_expired", "Your session has expired. Please sign in again.")

        user = await db.get(User, row.user_id)
        if not user or not user.is_active:
            raise _unauthorized("session_revoked", "This session has ended. Please sign in again.")

        row.revoked_at = now
        row.revoked_reason = ROTATED
        tokens = self._issue(
            db,
            user,
            family_id=row.family_id,
            family_started_at=row.family_started_at,
            remember=row.remember,
            client=client,
        )
        await db.commit()
        return user, tokens

    # ------------------------------------------------------------------ sessions

    async def list_sessions(self, db: AsyncSession, user_id: uuid.UUID) -> list[AuthSession]:
        rows = await db.scalars(
            select(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > utcnow(),
            )
            .order_by(AuthSession.created_at.desc())
        )
        return list(rows)

    async def revoke_session(self, db: AsyncSession, user_id: uuid.UUID, family_id: uuid.UUID) -> None:
        revoked = await self._revoke(
            db, AuthSession.user_id == user_id, AuthSession.family_id == family_id, reason="user_revoked"
        )
        if not revoked:
            raise AppError(404, "session_not_found", "That session does not exist or has already ended.")
        await db.commit()

    async def revoke_all(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        await self._revoke(db, AuthSession.user_id == user_id, reason="logout_all")
        await db.commit()

    async def logout(
        self, db: AsyncSession, *, refresh_token: str | None, family_id: uuid.UUID | None
    ) -> None:
        if refresh_token:
            row = await db.scalar(
                select(AuthSession).where(AuthSession.token_hash == hash_token(refresh_token))
            )
            family_id = row.family_id if row else family_id
        if family_id:
            await self._revoke(db, AuthSession.family_id == family_id, reason="logout")
            await db.commit()

    # ------------------------------------------------------------------ internals

    async def _user_by_email(self, db: AsyncSession, email: str) -> User | None:
        return await db.scalar(select(User).where(User.email == email))

    async def _record_failed_login(self, db: AsyncSession, user: User, now: datetime) -> None:
        user.failed_login_count += 1
        if user.failed_login_count >= self._settings.max_failed_logins:
            user.locked_until = now + timedelta(minutes=self._settings.lockout_minutes)
            user.failed_login_count = 0
            logger.warning("Account locked after repeated failures: user=%s", user.id)
        await db.commit()

    def _start_family(
        self, db: AsyncSession, user: User, *, remember: bool, client: ClientInfo
    ) -> IssuedTokens:
        return self._issue(
            db, user, family_id=uuid.uuid4(), family_started_at=utcnow(), remember=remember, client=client
        )

    def _issue(
        self,
        db: AsyncSession,
        user: User,
        *,
        family_id: uuid.UUID,
        family_started_at: datetime,
        remember: bool,
        client: ClientInfo,
    ) -> IssuedTokens:
        settings = self._settings
        refresh_token = new_refresh_token()
        now = utcnow()
        ttl = settings.refresh_ttl_remember_s if remember else settings.refresh_ttl_default_s
        db.add(
            AuthSession(
                user_id=user.id,
                family_id=family_id,
                token_hash=hash_token(refresh_token),
                remember=remember,
                user_agent=(client.user_agent or "")[:300] or None,
                ip_address=client.ip_address,
                family_started_at=family_started_at,
                created_at=now,
                expires_at=now + timedelta(seconds=ttl),
            )
        )
        access_token, _ = create_access_token(
            user.id, family_id, settings.secret_key, settings.access_token_ttl_s
        )
        return IssuedTokens(access_token, refresh_token, family_id, remember)

    async def _revoke(self, db: AsyncSession, *conditions, reason: str) -> int:
        result = await db.execute(
            update(AuthSession)
            .where(AuthSession.revoked_at.is_(None), *conditions)
            .values(revoked_at=utcnow(), revoked_reason=reason)
        )
        return result.rowcount or 0
