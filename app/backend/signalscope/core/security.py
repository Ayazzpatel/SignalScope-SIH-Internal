"""Password hashing, access-token JWTs and opaque refresh tokens."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

JWT_ALGORITHM = "HS256"
_ISSUER = "signalscope"


class PasswordService:
    """Argon2id hashing. A dummy hash lets unknown-email logins cost the same time as real ones."""

    def __init__(self, time_cost: int, memory_kib: int) -> None:
        self._hasher = PasswordHasher(time_cost=time_cost, memory_cost=memory_kib)
        self._dummy_hash = self._hasher.hash(secrets.token_urlsafe(16))

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str | None, password: str) -> bool:
        try:
            return (
                self._hasher.verify(password_hash or self._dummy_hash, password) and password_hash is not None
            )
        except (VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        return self._hasher.check_needs_rehash(password_hash)


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    session_family_id: uuid.UUID
    expires_at: datetime


class TokenExpiredError(Exception):
    pass


class TokenInvalidError(Exception):
    pass


def create_access_token(
    user_id: uuid.UUID, family_id: uuid.UUID, secret: str, ttl_s: int
) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=ttl_s)
    payload = {
        "sub": str(user_id),
        "sid": str(family_id),
        "iat": now,
        "exp": expires,
        "iss": _ISSUER,
        "typ": "access",
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM), expires


def decode_access_token(token: str, secret: str) -> AccessClaims:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            issuer=_ISSUER,
            options={"require": ["sub", "sid", "exp", "iat", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError from exc
    except jwt.PyJWTError as exc:
        raise TokenInvalidError from exc

    if payload.get("typ") != "access":
        raise TokenInvalidError
    try:
        return AccessClaims(
            user_id=uuid.UUID(payload["sub"]),
            session_family_id=uuid.UUID(payload["sid"]),
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )
    except (ValueError, TypeError) as exc:
        raise TokenInvalidError from exc


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    # Refresh tokens are high-entropy random strings, so a fast hash is appropriate (unlike passwords).
    return hashlib.sha256(token.encode()).hexdigest()
