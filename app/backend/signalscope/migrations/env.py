import asyncio

from alembic import context
from sqlalchemy.engine import Connection

import signalscope.models  # noqa: F401  — registers all tables on Base.metadata
from signalscope.core.config import get_settings
from signalscope.db import Base, create_engine

config = context.config
target_metadata = Base.metadata


def _database_url() -> str:
    # The app passes its URL explicitly; the CLI falls back to settings.
    return config.attributes.get("database_url") or get_settings().database_url


def _configure(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=connection.dialect.name == "sqlite",  # SQLite needs batch mode for ALTERs
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_online() -> None:
    engine = create_engine(_database_url())
    async with engine.connect() as connection:
        await connection.run_sync(_configure)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=_database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(_run_online())
