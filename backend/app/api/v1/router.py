# V1 API 路由聚合点：各业务模块在此挂载，保持接口契约统一。
from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health", tags=["system"], summary="健康检查")
async def health() -> dict:
    """存活探针，供 docker compose healthcheck 与前端启动检测使用。"""
    return {"status": "ok"}
