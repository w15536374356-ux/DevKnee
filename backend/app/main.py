# FastAPI 应用入口：只做装配（中间件、路由挂载、生命周期），不含业务逻辑。
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.storage.init_db import init_db

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动建库；连接采用懒加载，避免未启动依赖时崩溃。
    if settings.db_auto_create:
        try:
            await init_db()
            logger.info("database schema ensured")
        except Exception:
            logger.warning("database not ready yet, skip auto-create", exc_info=True)
    yield


app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"service": settings.project_name, "status": "ok"}
