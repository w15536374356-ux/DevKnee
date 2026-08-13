import asyncio
import logging

from sqlalchemy import text

import app.storage.models
from app.storage.db import Base, engine

logger = logging.getLogger(__name__)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database schema ensured")


if __name__ == "__main__":
    asyncio.run(init_db())
    print("database initialized.")
