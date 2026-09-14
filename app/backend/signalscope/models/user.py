import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, Enum, Integer, String, Uuid, false, text
from sqlalchemy.orm import Mapped, mapped_column

from signalscope.db import Base, TimestampMixin, UTCDateTime


class UserRole(StrEnum):
    USER = "user"
    REVIEWER = "reviewer"
    ADMIN = "admin"


DEFAULT_RETENTION_DAYS = 90


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]),
        default=UserRole.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    # Privacy preferences — images are not kept unless the user opts in.
    save_images_default: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    retention_days: Mapped[int | None] = mapped_column(
        Integer, default=DEFAULT_RETENTION_DAYS, server_default=text(str(DEFAULT_RETENTION_DAYS))
    )  # None = keep until deleted
