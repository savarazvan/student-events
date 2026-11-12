"""Apply Alembic migrations programmatically (used at startup and by the seed script)."""

import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import DATABASE_URL

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
BASELINE_REVISION = "0001"


def _alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.attributes["configure_logger"] = False
    return config


async def _existing_tables() -> set[str]:
    engine = create_async_engine(DATABASE_URL)
    try:
        async with engine.connect() as connection:
            return set(
                await connection.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
            )
    finally:
        await engine.dispose()


def run_migrations() -> None:
    """Upgrade the database to the latest revision.

    Databases created before migrations existed (via ``create_all``) have the
    tables but no ``alembic_version``; they are stamped first so the upgrade only
    applies what is missing. Must not be called from a running event loop thread.
    """
    config = _alembic_config()
    tables = asyncio.run(_existing_tables())
    if "alembic_version" not in tables and "users" in tables:
        revision = "head" if "tickets" in tables else BASELINE_REVISION
        logger.info("Existing schema without migration history; stamping %s.", revision)
        command.stamp(config, revision)
    command.upgrade(config, "head")


async def run_migrations_async() -> None:
    await asyncio.to_thread(run_migrations)
