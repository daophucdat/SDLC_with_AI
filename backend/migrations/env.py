"""Alembic environment (async, asyncpg). DATABASE_URL comes from chatdocs Settings / environment."""

from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from chatdocs.platform.config import get_settings


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=None, version_table_schema="public")
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    url = context.config.get_main_option("sqlalchemy.url") or get_settings().database_url
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        await conn.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=get_settings().database_url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(_run_async())
