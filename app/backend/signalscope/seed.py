"""Create demo accounts so judges can explore signed-in features immediately.

    python -m signalscope.seed          # uses DATABASE_URL from env / .env

Idempotent: existing accounts are left untouched. Passwords are documented in the README —
never enable this on a real deployment.
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from signalscope.core.config import get_settings
from signalscope.core.security import PasswordService
from signalscope.db import create_engine, create_sessionmaker
from signalscope.db.migrate import run_migrations
from signalscope.models import User, UserRole

logger = logging.getLogger("signalscope.seed")

DEMO_PASSWORD = "SignalScope#2026"
DEMO_USERS = [
    ("demo@signalscope.dev", "Demo User", UserRole.USER),
    ("reviewer@signalscope.dev", "Demo Reviewer", UserRole.REVIEWER),
    ("admin@signalscope.dev", "Demo Admin", UserRole.ADMIN),
]


async def seed_demo_users(
    sessionmaker: async_sessionmaker[AsyncSession], passwords: PasswordService
) -> list[str]:
    created: list[str] = []
    async with sessionmaker() as db:
        existing = set(await db.scalars(select(User.email).where(User.email.in_([u[0] for u in DEMO_USERS]))))
        password_hash = passwords.hash(DEMO_PASSWORD) if len(existing) < len(DEMO_USERS) else ""
        for email, name, role in DEMO_USERS:
            if email not in existing:
                db.add(User(email=email, display_name=name, role=role, password_hash=password_hash))
                created.append(email)
        await db.commit()
    if created:
        logger.info("Seeded demo accounts: %s", ", ".join(created))
    return created


async def _main() -> None:
    settings = get_settings()
    await asyncio.to_thread(run_migrations, settings.database_url)
    engine = create_engine(settings.database_url)
    try:
        passwords = PasswordService(settings.argon2_time_cost, settings.argon2_memory_kib)
        created = await seed_demo_users(create_sessionmaker(engine), passwords)
        print(f"Created: {', '.join(created) or 'nothing (already seeded)'}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
