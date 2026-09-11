from pathlib import Path

from alembic import command
from alembic.config import Config

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def run_migrations(database_url: str) -> None:
    """Upgrade the database to the latest revision. Blocking — call from a worker thread."""
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.attributes["database_url"] = database_url
    command.upgrade(config, "head")
