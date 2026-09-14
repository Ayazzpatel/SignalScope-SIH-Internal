import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Float, ForeignKey, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from signalscope.db import Base, UTCDateTime, utcnow

JSONType = JSON().with_variant(JSONB(), "postgresql")


class Scan(Base):
    """One saved analysis in a user's history.

    Queryable facts are columns; the full result (verdict, cues, provenance…) is one JSON document so the
    history view can re-render exactly what the user saw. Files (heat-map, optional image) live in storage.
    """

    __tablename__ = "scans"
    __table_args__ = (
        Index("ix_scans_user_created", "user_id", "created_at"),
        Index("ix_scans_user_band", "user_id", "band"),
        Index("ix_scans_sha256_model", "sha256", "model_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255))

    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    phash: Mapped[int | None] = mapped_column(BigInteger)  # signed 64-bit perceptual hash

    band: Mapped[str] = mapped_column(String(20), nullable=False)
    prob_ai: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)

    image_key: Mapped[str | None] = mapped_column(String(255))
    heatmap_key: Mapped[str | None] = mapped_column(String(255))
    result: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
