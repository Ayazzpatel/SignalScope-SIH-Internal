"""Scan history: persistence, result cache, "seen before" matching, listing, deletion and export."""

import asyncio
import base64
import io
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import PurePosixPath
from typing import Any, Literal

from PIL import Image
from sqlalchemy import BigInteger, cast, delete, func, literal, or_, select
from sqlalchemy.dialects.postgresql import BIT
from sqlalchemy.ext.asyncio import AsyncSession

from signalscope.core.config import Settings
from signalscope.core.errors import AppError
from signalscope.db import utcnow
from signalscope.models import AuthSession, Scan, User
from signalscope.schemas.analysis import OwnMatch, SeenBefore, StoredResult, VerdictBand
from signalscope.services.analysis import CachedDetection
from signalscope.services.fingerprint import hamming
from signalscope.services.storage import LocalStorage, scan_key

logger = logging.getLogger("signalscope.scans")

SortOrder = Literal["newest", "oldest"]
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def clean_filename(name: str | None) -> str | None:
    """Keep only the base name, without control characters; never used as a path."""
    if not name:
        return None
    base = PurePosixPath(name.replace("\\", "/")).name
    return _CONTROL.sub("", base).strip()[:255] or None


def encode_stored_image(rgb: Image.Image, max_side: int) -> bytes:
    """Re-encode for history: bounded size, WebP, and no metadata (EXIF/GPS are dropped)."""
    copy = rgb.copy()
    copy.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    copy.save(buffer, format="WEBP", quality=82, method=4)
    return buffer.getvalue()


@dataclass(frozen=True)
class _Match:
    user_id: uuid.UUID
    scan_id: uuid.UUID
    created_at: datetime
    band: str
    exact: bool


class ScanService:
    def __init__(self, settings: Settings, storage: LocalStorage) -> None:
        self._settings = settings
        self._storage = storage

    # ------------------------------------------------------------------ cache & matching

    async def cached_detection(
        self, db: AsyncSession, sha256: str, model_version: str
    ) -> CachedDetection | None:
        row = await db.scalar(
            select(Scan)
            .where(Scan.sha256 == sha256, Scan.model_version == model_version)
            .order_by(Scan.created_at.desc())
            .limit(1)
        )
        if row is None:
            return None
        heatmap = await self._storage.get(row.heatmap_key) if row.heatmap_key else None
        if row.heatmap_key and heatmap is None:
            return None  # file went missing — recompute rather than serve a partial result
        stored = StoredResult.model_validate(row.result)
        return CachedDetection(
            prob_ai=stored.verdict.prob_ai,
            model_version=row.model_version,
            cues=stored.cues,
            attribution=stored.attribution,
            heatmap_png=heatmap,
        )

    async def seen_before(
        self, db: AsyncSession, user_id: uuid.UUID | None, sha256: str, phash: int, band: VerdictBand
    ) -> SeenBefore | None:
        matches = await self._similar(db, sha256, phash)

        own = [m for m in matches if user_id is not None and m.user_id == user_id]
        latest = max(own, key=lambda m: m.created_at) if own else None
        other_users = {m.user_id for m in matches if m.user_id != user_id}
        others_count = len(other_users) if len(other_users) >= self._settings.seen_min_other_users else None

        compared = ([latest.band] if latest else []) + (
            [m.band for m in matches if m.user_id != user_id] if others_count else []
        )
        if not compared:
            return None
        return SeenBefore(
            yours=OwnMatch(
                scan_id=latest.scan_id, scanned_at=latest.created_at, band=latest.band, exact=latest.exact
            )
            if latest
            else None,
            others_count=others_count,
            consistent=all(b == band for b in compared),
        )

    async def _similar(self, db: AsyncSession, sha256: str, phash: int) -> list[_Match]:
        columns = (Scan.id, Scan.user_id, Scan.created_at, Scan.band, Scan.sha256, Scan.phash)
        max_distance = self._settings.phash_max_distance

        if db.bind.dialect.name == "postgresql":
            distance = func.bit_count(cast(Scan.phash.op("#")(literal(phash, BigInteger)), BIT(64)))
            rows = (
                await db.execute(
                    select(*columns)
                    .where(or_(Scan.sha256 == sha256, distance <= max_distance))
                    .order_by(Scan.created_at.desc())
                    .limit(500)
                )
            ).all()
        else:  # SQLite fallback: compare in Python
            rows = [
                r
                for r in (await db.execute(select(*columns))).all()
                if r.sha256 == sha256 or (r.phash is not None and hamming(r.phash, phash) <= max_distance)
            ]
        return [_Match(r.user_id, r.id, r.created_at, r.band, r.sha256 == sha256) for r in rows]

    # ------------------------------------------------------------------ writes

    async def save(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        stored: StoredResult,
        sha256: str,
        phash: int,
        filename: str | None,
        heatmap_png: bytes | None,
        rgb: Image.Image | None,
    ) -> Scan:
        scan = Scan(
            id=uuid.uuid4(),
            user_id=user_id,
            filename=filename,
            sha256=sha256,
            phash=phash,
            band=stored.verdict.band,
            prob_ai=stored.verdict.prob_ai,
            model_version=stored.model_version,
            result=stored.model_dump(mode="json"),
        )
        written: list[str] = []
        try:
            if heatmap_png:
                scan.heatmap_key = scan_key(user_id, scan.id, "heatmap.png")
                await self._storage.put(scan.heatmap_key, heatmap_png)
                written.append(scan.heatmap_key)
            if rgb is not None:
                data = await asyncio.to_thread(encode_stored_image, rgb, self._settings.stored_image_max_side)
                scan.image_key = scan_key(user_id, scan.id, "image.webp")
                await self._storage.put(scan.image_key, data)
                written.append(scan.image_key)
            db.add(scan)
            await db.commit()
        except BaseException:
            await db.rollback()
            await self._storage.delete(*written)
            raise
        return scan

    async def delete(self, db: AsyncSession, user_id: uuid.UUID, scan_id: uuid.UUID) -> None:
        scan = await self.get_owned(db, user_id, scan_id)
        keys = (scan.image_key, scan.heatmap_key)
        await db.delete(scan)
        await db.commit()
        await self._storage.delete(*keys)

    async def delete_many(self, db: AsyncSession, user_id: uuid.UUID, scan_ids: list[uuid.UUID]) -> int:
        rows = (
            await db.execute(
                select(Scan.id, Scan.image_key, Scan.heatmap_key).where(
                    Scan.user_id == user_id, Scan.id.in_(scan_ids)
                )
            )
        ).all()
        if not rows:
            return 0
        await db.execute(delete(Scan).where(Scan.id.in_([r.id for r in rows])))
        await db.commit()
        await self._storage.delete(*(k for r in rows for k in (r.image_key, r.heatmap_key)))
        return len(rows)

    async def delete_all(self, db: AsyncSession, user_id: uuid.UUID) -> int:
        result = await db.execute(delete(Scan).where(Scan.user_id == user_id))
        await db.commit()
        await self._storage.delete_user(user_id)
        return result.rowcount or 0

    # ------------------------------------------------------------------ reads

    async def get_owned(self, db: AsyncSession, user_id: uuid.UUID, scan_id: uuid.UUID) -> Scan:
        scan = await db.get(Scan, scan_id)
        if scan is None or scan.user_id != user_id:
            # 404 either way: never confirm that someone else's scan exists.
            raise AppError(404, "scan_not_found", "That scan does not exist or has been deleted.")
        return scan

    async def read_file(self, key: str | None) -> bytes | None:
        return await self._storage.get(key) if key else None

    async def list(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        *,
        band: VerdictBand | None = None,
        query: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort: SortOrder = "newest",
        cursor: str | None = None,
        limit: int = 24,
    ) -> tuple[list[Scan], str | None]:
        stmt = select(Scan).where(Scan.user_id == user_id)
        if band:
            stmt = stmt.where(Scan.band == band)
        if query:
            stmt = stmt.where(func.lower(Scan.filename).contains(query.lower(), autoescape=True))
        if date_from:
            stmt = stmt.where(Scan.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Scan.created_at < date_to)
        if cursor:
            at, scan_id = _decode_cursor(cursor)
            if sort == "newest":
                stmt = stmt.where(or_(Scan.created_at < at, (Scan.created_at == at) & (Scan.id < scan_id)))
            else:
                stmt = stmt.where(or_(Scan.created_at > at, (Scan.created_at == at) & (Scan.id > scan_id)))

        order = (Scan.created_at.desc(), Scan.id.desc()) if sort == "newest" else (Scan.created_at, Scan.id)
        rows = list(await db.scalars(stmt.order_by(*order).limit(limit + 1)))
        page, more = rows[:limit], len(rows) > limit
        return page, (_encode_cursor(page[-1]) if more and page else None)

    async def stats(self, db: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
        by_band = dict.fromkeys(VerdictBand, 0)
        for band, count in (
            await db.execute(
                select(Scan.band, func.count()).where(Scan.user_id == user_id).group_by(Scan.band)
            )
        ).all():
            by_band[VerdictBand(band)] = count
        this_week = await db.scalar(
            select(func.count()).where(
                Scan.user_id == user_id, Scan.created_at >= utcnow() - timedelta(days=7)
            )
        )
        return {"total": sum(by_band.values()), "by_band": by_band, "this_week": this_week or 0}

    async def export(self, db: AsyncSession, user: User) -> dict[str, Any]:
        scans = await db.scalars(select(Scan).where(Scan.user_id == user.id).order_by(Scan.created_at))
        sessions = await db.scalars(
            select(AuthSession).where(AuthSession.user_id == user.id).order_by(AuthSession.created_at)
        )
        return {
            "exported_at": utcnow().isoformat(),
            "account": {
                "id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "role": user.role,
                "created_at": user.created_at.isoformat(),
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            },
            "preferences": {
                "save_images_default": user.save_images_default,
                "retention_days": user.retention_days,
            },
            "sessions": [
                {
                    "device_user_agent": s.user_agent,
                    "ip_address": s.ip_address,
                    "created_at": s.created_at.isoformat(),
                    "expires_at": s.expires_at.isoformat(),
                    "revoked_at": s.revoked_at.isoformat() if s.revoked_at else None,
                }
                for s in sessions
            ],
            "scans": [
                {
                    "id": str(s.id),
                    "created_at": s.created_at.isoformat(),
                    "filename": s.filename,
                    "sha256": s.sha256,
                    "image_saved": s.image_key is not None,
                    "result": s.result,
                }
                for s in scans
            ],
        }


def _encode_cursor(scan: Scan) -> str:
    return base64.urlsafe_b64encode(f"{scan.created_at.isoformat()}|{scan.id}".encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        at, scan_id = raw.split("|", 1)
        return datetime.fromisoformat(at), uuid.UUID(scan_id)
    except (ValueError, UnicodeDecodeError) as exc:
        raise AppError(422, "invalid_cursor", "The page cursor is invalid. Reload the list.") from exc
