import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from signalscope.db import Base, UTCDateTime, utcnow


class AuthSession(Base):
    """One row per refresh token. Rotation chains rows in the same `family_id` (= one signed-in device).

    Only the newest row of a family is live; older rows are kept (revoked, reason "rotated") so that
    re-use of a stolen, already-rotated token can be detected and the whole family revoked.
    """

    __tablename__ = "auth_sessions"
    __table_args__ = (Index("ix_auth_sessions_user_active", "user_id", "revoked_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    remember: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(300))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    family_started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    revoked_reason: Mapped[str | None] = mapped_column(String(30))
