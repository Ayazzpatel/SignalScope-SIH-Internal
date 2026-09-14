"""Background clean-up: expire scans past each user's retention period and purge dead sessions."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from signalscope.db import utcnow
from signalscope.models import AuthSession, Scan, User
from signalscope.services.storage import LocalStorage

logger = logging.getLogger("signalscope.retention")

_ADVISORY_LOCK_KEY = 7_202_609  # arbitrary, app-wide
SESSION_GRAVEYARD_DAYS = 30


@dataclass(frozen=True)
class RetentionReport:
    scans_deleted: int
    sessions_deleted: int


async def run_retention(
    sessionmaker: async_sessionmaker[AsyncSession], storage: LocalStorage, now: datetime | None = None
) -> RetentionReport:
    now = now or utcnow()
    keys: list[str | None] = []
    async with sessionmaker() as db:
        # With several backend instances on Postgres, only one runs the clean-up at a time.
        if db.bind.dialect.name == "postgresql":
            locked = await db.scalar(
                text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": _ADVISORY_LOCK_KEY}
            )
            if not locked:
                return RetentionReport(0, 0)

        expired_ids = []
        policies = (
            await db.execute(select(User.id, User.retention_days).where(User.retention_days.is_not(None)))
        ).all()
        for user_id, days in policies:
            rows = (
                await db.execute(
                    select(Scan.id, Scan.image_key, Scan.heatmap_key).where(
                        Scan.user_id == user_id, Scan.created_at < now - timedelta(days=days)
                    )
                )
            ).all()
            expired_ids += [r.id for r in rows]
            keys += [k for r in rows for k in (r.image_key, r.heatmap_key)]
        if expired_ids:
            await db.execute(delete(Scan).where(Scan.id.in_(expired_ids)))

        cutoff = now - timedelta(days=SESSION_GRAVEYARD_DAYS)
        sessions = await db.execute(
            delete(AuthSession).where(or_(AuthSession.revoked_at < cutoff, AuthSession.expires_at < cutoff))
        )
        await db.commit()

    await storage.delete(*keys)  # files after the commit: a crash leaves orphans, never dangling rows
    report = RetentionReport(len(expired_ids), sessions.rowcount or 0)
    if report.scans_deleted or report.sessions_deleted:
        logger.info("Retention: %d scans, %d sessions removed", report.scans_deleted, report.sessions_deleted)
    return report


async def retention_loop(
    sessionmaker: async_sessionmaker[AsyncSession], storage: LocalStorage, interval_s: int
) -> None:
    await asyncio.sleep(min(60, interval_s))  # don't compete with startup
    while True:
        try:
            await run_retention(sessionmaker, storage)
        except Exception:
            logger.exception("Retention run failed; will retry next interval")
        await asyncio.sleep(interval_s)
