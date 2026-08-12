# 数据库初始化：先建 pg_trgm 扩展
import asyncio
import logging

from sqlalchemy import text

from app.storage.db import engine

logger = logging.getLogger(__name__)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    logger.info("database schema ensured")


if __name__ == "__main__":
    asyncio.run(init_db())
    print("database initialized.")
